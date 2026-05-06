import itertools
import math
import os
import json
from collections import Counter
from treys import Card, Evaluator
from app.evaluators.evaluator import get_best_score, FULL_DECK

evaluator = Evaluator()

RANKS = list(range(13))
ALL_MULTISETS_5 = list(itertools.combinations_with_replacement(RANKS, 5)) 
FILTERED_MULTISETS_5 = [m for m in ALL_MULTISETS_5 if not any(m.count(r) > 4 for r in set(m))] 

def get_rank_int(card):
    return Card.get_rank_int(card)

def get_suit_int(card):
    return Card.get_suit_int(card)

LUT_PATH = os.path.join(os.path.dirname(__file__), 'multisets_lut.json')
with open(LUT_PATH, 'r') as f:
    RAW_LUT = json.load(f)
    
MULTISETS_EVAL_LUT = {}
for k, v in RAW_LUT.items():
    tup_key = tuple(map(int, k.split(',')))
    MULTISETS_EVAL_LUT[tup_key] = (v['flush'], v['non_flush'])

COMB_LUT = [[math.comb(n, k) for k in range(6)] for n in range(5)]

FAST_ITERATOR = []
for mset in FILTERED_MULTISETS_5:
    counts = [mset.count(r) for r in range(13)]
    FAST_ITERATOR.append((
        counts, 
        MULTISETS_EVAL_LUT[mset][0], 
        MULTISETS_EVAL_LUT[mset][1]
    ))

def _calculate_base_weight(mset_counts, hand_rank_counts, rem_rank_counts):
    weight = 1
    need_counts = {}
    for r in range(13):
        needed = mset_counts[r] - hand_rank_counts[r]
        if needed < 0 or needed > rem_rank_counts[r]:
            return 0, {}
        need_counts[r] = needed
        
    for r, needed in need_counts.items():
        if needed > 0:
            weight *= COMB_LUT[rem_rank_counts[r]][needed]
            
    return weight, need_counts

def _calculate_flush_weight(hand_suits, total_needed, need_counts, available_set):
    flush_weight = 0
    for suit in [1, 2, 4, 8]: 
        if hand_suits.get(suit, 0) + total_needed != 5:
            continue
            
        can_make_flush = True
        for r, needed in need_counts.items():
            if needed > 0:
                if (r, suit) not in available_set:
                    can_make_flush = False
                    break
                if needed > 1:
                    can_make_flush = False
                    break
                    
        if can_make_flush:
            flush_weight += 1
            
    return flush_weight

def evaluate_player_deterministic(hand, dead_cards):
    cards_needed = 5 - len(hand)
    if cards_needed == 0:
        return get_best_score(hand)

    available_cards = [c for c in FULL_DECK if c not in hand and c not in dead_cards]
    
    rem_rank_counts = [0] * 13
    for c in available_cards:
        rem_rank_counts[get_rank_int(c)] += 1
        
    available_set = set((get_rank_int(c), get_suit_int(c)) for c in available_cards)
    
    hand_rank_counts = [0] * 13
    hand_suits = {1: 0, 2: 0, 4: 0, 8: 0}
    for c in hand:
        hand_rank_counts[get_rank_int(c)] += 1
        hand_suits[get_suit_int(c)] += 1
    
    total_ev = 0.0
    total_weight = 0
    
    for mset_counts, flush_score, non_flush_score in FAST_ITERATOR:
        weight, need_counts = _calculate_base_weight(mset_counts, hand_rank_counts, rem_rank_counts)
        if weight == 0:
            continue
            
        flush_weight = _calculate_flush_weight(hand_suits, cards_needed, need_counts, available_set)
        non_flush_weight = weight - flush_weight
        
        total_ev += (non_flush_weight * non_flush_score) + (flush_weight * flush_score)
        total_weight += weight
        
    if total_weight == 0:
        return 10000
    return total_ev / total_weight
