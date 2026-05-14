import sys
import os
import json
import math
import itertools
import concurrent.futures

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from app.simulators.v_1.v_1_0_logic import (
    FULL_DECK,
    FULL_DECK_BITS,
    FULL_DECK_RANK_COUNTS,
    get_hand_masks
)
from app.simulators.v_1.perfect_evaluator import (
    _evaluate_player_loop,
    fast_iterator_array,
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
    
    # Iterate all ways to partition dead_cards into the player's hand
    for r in range(len(dead_cards) + 1):
        for player_hand in itertools.combinations(dead_cards, r):
            player_bits, player_rank_counts = get_hand_masks(player_hand)
            cards_needed = 5 - len(player_hand)
            
            # _evaluate_player_loop takes 7 args (adjust if your order is different):
            # hand_bits, hand_rank_counts, available_set, rem_rank_counts, cards_needed, COMB_LUT, fast_iter_arr
            ev = _evaluate_player_loop(
                player_bits, 
                player_rank_counts, 
                available_set, 
                rem_rank_counts, 
                cards_needed, 
                COMB_LUT,
                fast_iterator_array
            )
            
            # Using a string key formatted as "playerBits_deadBits"
            state_key = f"{player_bits}_{dead_bits}"
            results[state_key] = ev
            
    return results

def generate_lut():
    # You mentioned changing max_dead to 1 for the dealer to save time. 
    # You can safely raise this for the player (e.g., 3 or 4) since the player loop evaluates ~6k multisets instead of ~120k.
    max_dead = 3
    print(f"Generating player LUT for <= {max_dead} dead cards...")
    
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
            
    output_path = os.path.join(os.path.dirname(__file__), 'early_game_player_lut.json')
    with open(output_path, 'w') as f:
        json.dump(final_lut, f)
        
    print(f"Successfully generated LUT with {len(final_lut)} states!")
    print(f"Saved to: {output_path}")

if __name__ == '__main__':
    generate_lut()
