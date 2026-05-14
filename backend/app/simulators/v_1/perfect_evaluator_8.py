# import sys
import itertools
import os
import json
import numpy as np
from functools import lru_cache

# Dynamically add the 'backend' directory to Python's module search path
# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from app.evaluators.evaluator import get_best_score
from numba import njit, int64, float64, prange
from numba.types import Tuple
from app.simulators.v_1.perfect_evaluator import RANKS, STENCILS, CARRY_CHECKER, COMB_LUT, ODD_CHECKER, custom_bit_count, custom_bit_length

# 1. Isomorphism Logic: Generate all unique 8-card rank multisets (max 4 of each rank)
ALL_MULTISETS_8 = list(itertools.combinations_with_replacement(RANKS, 8))
FILTERED_MULTISETS_8 = [m for m in ALL_MULTISETS_8 if not any(m.count(r) > 4 for r in set(m))]

# Global LUT Loading mirroring perfect_evaluator.py
LUT_PATH_8 = os.path.join(os.path.dirname(__file__), 'multisets_lut_8.json')
MULTISETS_EVAL_LUT_8 = {}

if os.path.exists(LUT_PATH_8):
    with open(LUT_PATH_8, 'r') as f:
        RAW_LUT_8 = json.load(f)
        
    for k, v in RAW_LUT_8.items():
        tup_key = tuple(map(int, k.split(',')))
        MULTISETS_EVAL_LUT_8[tup_key] = v['non_flush']

# Load the dynamically generated 13-bit Flush LUT
FLUSH_LUT_PATH = os.path.join(os.path.dirname(__file__), 'flush_lut_13_bit.json')
FLUSH_LUT_13_BIT = np.zeros(8192, dtype=np.int64)

if os.path.exists(FLUSH_LUT_PATH):
    with open(FLUSH_LUT_PATH, 'r') as f:
        raw_flush_lut = json.load(f)
        
    for k, v in raw_flush_lut.items():
        idx = int(k, 2) # Natively parse binary string to array index
        FLUSH_LUT_13_BIT[idx] = v

# --- NEW: Load your early game precomputed LUT ---
PRECOMPUTED_EARLY_GAME_LUT_PATH = os.path.join(os.path.dirname(__file__), 'early_game_dealer_lut.json') # Change to your actual filename
PRECOMPUTED_EARLY_GAME_LUT = {}

if os.path.exists(PRECOMPUTED_EARLY_GAME_LUT_PATH):
    with open(PRECOMPUTED_EARLY_GAME_LUT_PATH, 'r') as f:
        # Note: If your keys are strings of (hand_bits, dead_bits), load them appropriately
        PRECOMPUTED_EARLY_GAME_LUT = json.load(f)

FAST_ITERATOR_8 = []
for mset in FILTERED_MULTISETS_8:
    counts = 0
    for r in range(13):
        counts |= (mset.count(r) << (4 * r)) # Pack counts into nibbles for each rank in a single int64

    FAST_ITERATOR_8.append((
        counts, 
        MULTISETS_EVAL_LUT_8[mset] # non flush treys rank
    ))
fast_iterator_array_8 = np.array(FAST_ITERATOR_8, dtype=np.int64)

# available_set, hand bits from right to left: 
# 2h, 2d, 2c, 2s, 3h, 3d, ..., Ah, Ad, Ac, As, unused
#
# need_count, mset_count, hand_rank_counts, rem_rank_counts bits from right to left: 
# 4 bits each for ranks 2 through A (0-12) in binary format. the rest are unused

# the same as _calculate_base_weight in perfect_evaluator.py
# may just use the version in perfect_evaluator.py instead 
@njit(Tuple((int64, int64))(int64, int64, int64, int64[:, :]), cache=True, fastmath=True)
def _calculate_base_weight_8(mset_counts: int, hand_rank_counts: int, rem_rank_counts: int, COMB_LUT) -> tuple[int, int]:    
    weight = 1
    need_counts = mset_counts - hand_rank_counts
    temp_need_counts = need_counts

    # Numba defaults literals to 32-bit. 0xF << 48 (Ace shift) overflows 32-bit ints!
    # You MUST cast it to 64-bit to prevent corruption on high cards.
    while temp_need_counts:
        lsb = temp_need_counts & -temp_need_counts
        shift = ((custom_bit_length(lsb) - 1) >> 2) << 2
        weight *= COMB_LUT[(rem_rank_counts >> shift) & 0xF, (need_counts >> shift) & 0xF]
        temp_need_counts &= (~(np.int64(0xF) << np.int64(shift)))

    return weight, need_counts


@njit(Tuple((int64, int64))(int64, int64, int64, int64, int64[:], int64, int64[:, :]), cache=True, fastmath=True)
def _calculate_flush_weight_8(hand: int, total_needed: int, need_counts: int, available_set: int, flush_lut: np.ndarray, non_flush_score: int, COMB_LUT) -> tuple[int, int]:
    flush_weight = 0
    flush_treys_rank_sum = 0
    avail_counts_packed = 0
    for r in range(13):
        count = custom_bit_count((available_set >> (4 * r)) & 0xF)
        avail_counts_packed |= (np.int64(count) << (4 * r))

    # This check ensures that for every rank, the number of available cards (in the flush suit)
    # is sufficient to meet the need_counts
    if (((avail_counts_packed | CARRY_CHECKER) - need_counts) & CARRY_CHECKER) != CARRY_CHECKER:
        return 0, 0
    
    needed_suit_mask = 0
    for r in range(13):
        if (need_counts >> (4 * r)) & 0xF:  # If we need cards of this rank
            needed_suit_mask |= (1 << r)

    for suit_num in range(4):
        prepicked_suit_count = custom_bit_count(hand & STENCILS[suit_num])

        # 1. If not enough available and existing cards to form a flush, skip
        if (prepicked_suit_count + min(custom_bit_count(available_set & STENCILS[suit_num]), total_needed)) >= 5:
            # 2. Extract existing flush suit subset into a 13-bit mask (one bit per rank)
            hand_suit_mask = 0
            for r in range(13):
                if hand & (np.int64(1) << (4 * r + suit_num)):
                    hand_suit_mask |= (1 << r)

            # 3. Figure out mathematical paths (weights) if we DO or DO NOT pick the flush suit for each needed rank
            candidate_mask = 0
            ways_pick = 0 # nibbles for 2, ..., A, unused
            ways_no_pick = 0 # nibbles for 2, ..., A, unused

            # A mask where the bits are 1 if the flush suit is available at that rank
            # Every 4th bit corresponds to the flush suit for ranks 2 through A
            has_flush_suit_mask = (available_set >> suit_num) & ODD_CHECKER
            temp_mask = needed_suit_mask
            while temp_mask:
                lsb = temp_mask & -temp_mask
                r = custom_bit_length(lsb) - 1
                shift = 4 * r
                needed = (need_counts >> shift) & 0xF
                avail_r = (available_set >> shift) & 0xF
                has_flush_suit = (has_flush_suit_mask >> shift) & 1
                others_avail = custom_bit_count(avail_r) - has_flush_suit
                
                # Use precompiled combinations LUT. math.comb(n, k) -> 0 natively if k > n
                wnp = np.int64(COMB_LUT[others_avail, needed])
                wp = np.int64(COMB_LUT[others_avail, needed - 1]) if has_flush_suit else 0

                if wp > 0:
                    candidate_mask |= (1 << r) # We optionally physically can pick a flush suit card here
                
                ways_no_pick |= (wnp << shift)
                ways_pick |= (wp << shift)
                temp_mask ^= lsb # Clear the least significant bit that we just processed

            # 1. Pre-calculate the base product for ranks that MUST be picked from other suits
            # because they aren't in the candidate_mask (i.e., wp == 0)
            fixed_weight_mask = needed_suit_mask ^ candidate_mask 
            base_w = np.int64(1)
            temp_fixed = fixed_weight_mask
            while temp_fixed:
                lsb = temp_fixed & -temp_fixed
                r = custom_bit_length(lsb) - 1
                base_w *= ((ways_no_pick >> (4 * r)) & 0xF)
                temp_fixed ^= lsb
            
            # 2. Submask iteration
            sub = candidate_mask

            # ensure we include the sub=0 case if a flush is already prepicked
            while True:
                flush_cards_mask = hand_suit_mask | sub
                
                # Fast bit count check
                if custom_bit_count(flush_cards_mask) >= 5:
                    w = base_w

                    # Only iterate over ranks that are in the candidate_mask
                    temp_cand = candidate_mask
                    while temp_cand:
                        lsb = temp_cand & -temp_cand
                        r = custom_bit_length(lsb) - 1
                        
                        # If the bit is set in 'sub', we use wp, else wnp
                        shift = 4 * r
                        if sub & lsb:
                            w *= (ways_pick >> shift) & 0xF
                        else:
                            w *= (ways_no_pick >> shift) & 0xF
                        
                        if w == 0: 
                            break
                        temp_cand ^= lsb
                    
                    if w > 0:
                        flush_weight += w
                        # 2. Take the min of the flush score and the existing non-flush score (Full House / Quads)
                        best_flush_branch_score = min(flush_lut[flush_cards_mask], non_flush_score)
                        flush_treys_rank_sum += w * best_flush_branch_score

                if sub == 0: 
                    break
                    
                sub = (sub - 1) & candidate_mask
            
    return flush_weight, flush_treys_rank_sum


# needs changes in EV calculation !!!

# The core C-compiled loop that evaluates about all of 120k multisets at pure C-speed
@njit((float64)(int64, int64, int64, int64, int64, int64[:, :], int64[:], int64[:, :]), cache=True, fastmath=True, parallel=True)
def _evaluate_dealer_loop(hand_bits, hand_rank_counts, available_set, rem_rank_counts, cards_needed, fast_iter_arr, flush_lut, COMB_LUT):
    total_ev = 0.0
    total_weight = 0
    
    for i in prange(fast_iter_arr.shape[0]):
        mset_counts = fast_iter_arr[i, 0]
        
        # Is mset <= (hand + rem) AND hand <= mset?
        if not (((((hand_rank_counts + rem_rank_counts) | CARRY_CHECKER) - mset_counts) & CARRY_CHECKER) != CARRY_CHECKER or
            (((mset_counts | CARRY_CHECKER) - hand_rank_counts) & CARRY_CHECKER) != CARRY_CHECKER):
            
            non_flush_score = fast_iter_arr[i, 1]
            weight, need_counts = _calculate_base_weight_8(mset_counts, hand_rank_counts, rem_rank_counts, COMB_LUT)
            flush_weight, total_flush_score = _calculate_flush_weight_8(
                hand_bits, cards_needed, need_counts, available_set, flush_lut, non_flush_score, COMB_LUT
            )
            non_flush_weight = weight - flush_weight
            total_ev += (non_flush_weight * non_flush_score) + total_flush_score
            total_weight += weight
            
    return total_ev / total_weight if total_weight > 0 else 10000.0

@lru_cache(maxsize=131072)
def _cached_evaluate_dealer(hand_bits, hand_rank_counts, available_set, rem_rank_counts, cards_needed):
    return _evaluate_dealer_loop(
        hand_bits, 
        hand_rank_counts, 
        available_set, 
        rem_rank_counts, 
        cards_needed, 
        fast_iterator_array_8,
        FLUSH_LUT_13_BIT,
        COMB_LUT
    )

# hand_bits, hand_rank_counts, available_set, rem_rank_counts are all passed in to avoid recomputation across the loop
def evaluate_dealer_deterministic(hand, hand_bits, hand_rank_counts, available_set, rem_rank_counts):
    cards_needed = 8 - len(hand)
    if cards_needed <= 0:
        return get_best_score(hand)
    
    # --- NEW: Check the precomputed lookup table first ---
    # Construct the key EXACTLY as you did in your generator script. 
    # For example, if you stored it using stringified hand_bits and dead_bits:
    dead_bits = 0xFFFFFFFFFFFFF & ~available_set # Assuming FULL_DECK_BITS is 0xFFFFFFFFFFFFF
    
    # Example key format: adjust this to match how you serialized the LUT keys!
    lut_key = f"{hand_bits}_{dead_bits}" 
    
    if lut_key in PRECOMPUTED_EARLY_GAME_LUT:
        return PRECOMPUTED_EARLY_GAME_LUT[lut_key]

    # Enter the C-compiled boundary exactly onces
    return _cached_evaluate_dealer(
        hand_bits, 
        hand_rank_counts, 
        available_set, 
        rem_rank_counts, 
        cards_needed)
