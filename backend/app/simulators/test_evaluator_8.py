import sys
import os
import itertools
from treys import Evaluator, Card

# Dynamically add the 'backend' directory to Python's module search path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from app.simulators.perfect_evaluator_8 import evaluate_dealer_deterministic

def debug_brute_force(hand_cards, deck_cards, needed):
    evaluator = Evaluator()
    total_rank = 0
    count = 0
    
    for combo in itertools.combinations(deck_cards, needed):
        # The hand + combo has length 8
        full_hand = hand_cards + list(combo)
        # Find best 5-card subset out of 8
        best_score = 10000
        for sub_combo in itertools.combinations(full_hand, 5):
            score = evaluator.evaluate(list(sub_combo), [])
            if score < best_score:
                best_score = score
        total_rank += best_score
        count += 1
    
    return total_rank / count, count

def run_test():
    # Dealer hand: Ad (Ace of diamonds), Kd (King of diamonds), Qd (Queen of diamonds)
    # 3 cards, so 5 needed
    hand = [Card.new('Ad'), Card.new('Kd'), Card.new('Qd')]
    
    # Create the remaining deck properly
    all_ranks = '23456789TJQKA'
    all_suits = 'hdsc'
    
    all_cards = []
    for r in all_ranks:
        for s in all_suits:
            all_cards.append(Card.new(r + s))
            
    deck = [c for c in all_cards if c not in hand]
    
    # Run brute force
    print(f"Running brute force approach...")
    actual_ev, total_combinations = debug_brute_force(hand, deck, 5)
    print(f"Brute Force EV: {actual_ev}")
    print(f"Total Combinations (49 chose 5): {total_combinations}")
    
    # Initialize variables for Numba
    hand_bits = 0
    hand_rank_counts = 0
    available_set = 0
    rem_rank_counts = 0
    
    # Map treys string format back to our custom format for rank counts
    treys_ranks = {
        '2': 0, '3': 1, '4': 2, '5': 3, '6': 4, '7': 5, '8': 6, '9': 7, 
        'T': 8, 'J': 9, 'Q': 10, 'K': 11, 'A': 12
    }
    treys_suits = {'h': 0, 'd': 1, 'c': 2, 's': 3}
    
    # Calculate hand variables
    for c in hand:
        s_str = Card.int_to_str(c)
        r = treys_ranks[s_str[0]]
        s = treys_suits[s_str[1]]
        hand_bits |= (1 << (4 * r + s))
        
        # update hand rank count nibble
        current_count = (hand_rank_counts >> (4 * r)) & 0xF
        hand_rank_counts &= ~(0xF << (4 * r))
        hand_rank_counts |= ((current_count + 1) << (4 * r))
        
    print(f"Hand Rank Counts: {hex(hand_rank_counts)}")
        
    for c in deck:
        s_str = Card.int_to_str(c)
        r = treys_ranks[s_str[0]]
        s = treys_suits[s_str[1]]
        available_set |= (1 << (4 * r + s))
        
        # update rem rank count nibble
        current_count = (rem_rank_counts >> (4 * r)) & 0xF
        rem_rank_counts &= ~(0xF << (4 * r))
        rem_rank_counts |= ((current_count + 1) << (4 * r))

    print(f"Rem Rank Counts: {hex(rem_rank_counts)}")

    # Run Numba
    print("Running Numba evaluator...")
    expected_dealer_keep = evaluate_dealer_deterministic(hand, hand_bits, hand_rank_counts, available_set, rem_rank_counts)
    
    print(f"Numba Engine EV: {expected_dealer_keep}")

if __name__ == '__main__':
    run_test()
