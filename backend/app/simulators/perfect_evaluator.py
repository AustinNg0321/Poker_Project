import itertools
import math
import os
import json
import numpy as np
from treys import Evaluator
from app.evaluators.evaluator import get_best_score, FULL_DECK
from numba import njit, int64, float64
from numba.types import Tuple

evaluator = Evaluator()

# Stencils for each suit_num (0=h, 1=d, 2=c, 3=s)
STENCILS = (0x1111111111111, 0x2222222222222, 0x4444444444444, 0x8888888888888)
GT1_CHECKER = 0xEEEEEEEEEEEEE
ODD_CHECKER = 0x1111111111111
CARRY_CHECKER = 0x8888888888888

RANKS = list(range(13))
ALL_MULTISETS_5 = list(itertools.combinations_with_replacement(RANKS, 5)) 
FILTERED_MULTISETS_5 = [m for m in ALL_MULTISETS_5 if not any(m.count(r) > 4 for r in set(m))] 

LUT_PATH = os.path.join(os.path.dirname(__file__), 'multisets_lut.json')
with open(LUT_PATH, 'r') as f:
    RAW_LUT = json.load(f)
    
MULTISETS_EVAL_LUT = {}
for k, v in RAW_LUT.items():
    tup_key = tuple(map(int, k.split(',')))
    MULTISETS_EVAL_LUT[tup_key] = (v['flush'], v['non_flush'])

COMB_LUT = tuple(tuple(math.comb(n, k) for k in range(6)) for n in range(5))

FAST_ITERATOR = []
for mset in FILTERED_MULTISETS_5:
    counts = 0
    for r in range(13):
        counts |= (mset.count(r) << (4 * r))

    FAST_ITERATOR.append((
        counts, 
        MULTISETS_EVAL_LUT[mset][0], 
        MULTISETS_EVAL_LUT[mset][1]
    ))
fast_iterator_array = np.array(FAST_ITERATOR, dtype=np.int64)



@njit(int64(int64), cache=True, fastmath=True)
def custom_bit_length(n: int) -> int:
    length = 0
    while n > 0:
        length += 1
        n >>= 1
    return length

@njit(int64(int64), cache=True, fastmath=True)
def custom_bit_count(n: int) -> int:
    count = 0
    while n > 0:
        n &= n - 1
        count += 1
    return count

# available_set, hand bits from right to left: 
# 2h, 2d, 2c, 2s, 3h, 3d, ..., Ah, Ad, Ac, As, unused
#
# need_count, mset_count, hand_rank_counts, rem_rank_counts bits from right to left: 
# 4 bits each for ranks 2 through A (0-12) in binary format. the rest are unused

# bitmasked and fairly optimized
@njit(Tuple((int64, int64))(int64, int64, int64), cache=True, fastmath=True)
def _calculate_base_weight(mset_counts: int, hand_rank_counts: int, rem_rank_counts: int) -> tuple[int, int]:
    # Is mset <= (hand + rem) AND hand <= mset?
    if (((((hand_rank_counts + rem_rank_counts) | CARRY_CHECKER) - mset_counts) & CARRY_CHECKER) != CARRY_CHECKER or
        (((mset_counts | CARRY_CHECKER) - hand_rank_counts) & CARRY_CHECKER) != CARRY_CHECKER):
        return 0, 0

    weight = 1
    need_counts = mset_counts - hand_rank_counts
    temp_need_counts = need_counts

    # Numba defaults literals to 32-bit. 0xF << 48 (Ace shift) overflows 32-bit ints!
    # You MUST cast it to 64-bit to prevent corruption on high cards.
    while temp_need_counts:
        lsb = temp_need_counts & -temp_need_counts
        shift = ((custom_bit_length(lsb) - 1) >> 2) << 2
        weight *= COMB_LUT[(rem_rank_counts >> shift) & 0xF][(need_counts >> shift) & 0xF]
        temp_need_counts &= (~(np.int64(0xF) << np.int64(shift)))
      
    return weight, need_counts

# bitmasked and should be optimized
@njit(int64(int64, int64, int64, int64), cache=True, fastmath=True)
def _calculate_flush_weight(hand: int, total_needed: int, need_counts: int, available_set: int) -> int:
    # Checks if bits 2, 3, or 4 of any nibble are set
    # you cannot have 2 or more of the same card
    if need_counts & GT1_CHECKER: 
        return 0
    
    needed_ranks_mask = need_counts & ODD_CHECKER
    target = 5 - total_needed
    flush_weight = 0

    for suit_num in range(4):
        needed_in_suit = needed_ranks_mask << suit_num
        if (custom_bit_count(hand & STENCILS[suit_num]) >= target and 
            (needed_in_suit & available_set) == needed_in_suit):
            flush_weight += 1
            
    return flush_weight


# The core C-compiled loop that evaluates all 6,175 multisets at pure C-speed
@njit(float64(int64, int64, int64, int64, int64, int64[:, :]), cache=True, fastmath=True)
def _evaluate_player_loop(hand_bits, hand_rank_counts, available_set, rem_rank_counts, cards_needed, fast_iter_arr):
    total_ev = 0.0
    total_weight = 0
    
    for i in range(fast_iter_arr.shape[0]):
        mset_counts = fast_iter_arr[i, 0]
        flush_score = fast_iter_arr[i, 1]
        non_flush_score = fast_iter_arr[i, 2]
        
        weight, need_counts = _calculate_base_weight(mset_counts, hand_rank_counts, rem_rank_counts)
        if weight > 0:
            flush_weight = _calculate_flush_weight(hand_bits, cards_needed, need_counts, available_set)
            non_flush_weight = weight - flush_weight
            total_ev += (non_flush_weight * non_flush_score) + (flush_weight * flush_score)
            total_weight += weight
            
    return total_ev / total_weight if total_weight > 0 else 10000.0

# hand_bits, hand_rank_counts, available_set, rem_rank_counts are all passed in to avoid recomputation across the loop
def evaluate_player_deterministic(hand, hand_bits, hand_rank_counts, available_set, rem_rank_counts):
    cards_needed = 5 - len(hand)
    if cards_needed == 0:
        return get_best_score(hand)
    
    # Enter the C-compiled boundary exactly onces
    return _evaluate_player_loop(
        hand_bits, 
        hand_rank_counts, 
        available_set, 
        rem_rank_counts, 
        cards_needed, 
        fast_iterator_array
    )
