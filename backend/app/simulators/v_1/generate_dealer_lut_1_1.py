import sys
import os
import json
import math
import itertools
import concurrent.futures

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from app.simulators.v_1.v_1_1_logic import (
    FULL_DECK,
    FULL_DECK_BITS,
    FULL_DECK_RANK_COUNTS,
    get_hand_masks
)
from app.simulators.v_1.perfect_evaluator_v_1_1 import (
    _evaluate_dealer_loop,
    fast_iterator_array_8,
    FLUSH_LUT_13_BIT,
    COMB_LUT
)
import numba

def process_combination(dead_cards):
    # We restrict Numba to 1 thread per process to avoid thread oversubscription 
    # since we are using ProcessPoolExecutor.
    numba.set_num_threads(1)
    
    results = {}
    
    dead_bits, dead_rank_counts = get_hand_masks(dead_cards)
    available_set = FULL_DECK_BITS & ~dead_bits
    rem_rank_counts = FULL_DECK_RANK_COUNTS - dead_rank_counts
    
    # Iterate all ways to partition dead_cards into the dealer's hand
    # This automatically covers 2^k partitions.
    for r in range(len(dead_cards) + 1):
        for dealer_hand in itertools.combinations(dead_cards, r):
            dealer_bits, dealer_rank_counts = get_hand_masks(dealer_hand)
            cards_needed = 8 - len(dealer_hand)
            
            ev = _evaluate_dealer_loop(
                dealer_bits, 
                dealer_rank_counts, 
                available_set, 
                rem_rank_counts, 
                cards_needed, 
                fast_iterator_array_8,
                FLUSH_LUT_13_BIT,
                COMB_LUT
            )
            
            # Using a string key formatted as "dealerBits_deadBits"
            state_key = f"{dealer_bits}_{dead_bits}"
            results[state_key] = ev
            
    return results

def generate_lut():
    max_dead = 2
    print(f"Generating dealer LUT for <= {max_dead} dead cards...")
    
    all_combinations = []
    for k in range(max_dead + 1):
        for combo in itertools.combinations(FULL_DECK, k):
            all_combinations.append(combo)
            
    print(f"Total dead card combinations to process: {len(all_combinations)}")
    
    final_lut = {}
    
    # Using ProcessPoolExecutor to parallelize combinations evaluations
    with concurrent.futures.ProcessPoolExecutor() as executor:
        for result_batch in executor.map(process_combination, all_combinations, chunksize=100):
            final_lut.update(result_batch)
            
    output_path = os.path.join(os.path.dirname(__file__), 'early_game_dealer_lut_p09.json')
    with open(output_path, 'w') as f:
        json.dump(final_lut, f)
        
    print(f"Successfully generated LUT with {len(final_lut)} states!")
    print(f"Saved to: {output_path}")

if __name__ == '__main__':
    generate_lut()
