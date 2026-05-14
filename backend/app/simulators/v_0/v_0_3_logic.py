import sys
import os
import numpy as np

# Add the backend directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from app.evaluators.evaluator import FULL_DECK
from app.simulators.v_0.perfect_evaluator import evaluate_player_deterministic
from app.simulators.v_0.perfect_evaluator_8 import evaluate_dealer_deterministic
from treys import Card

def get_rank_int(card):
    return Card.get_rank_int(card)

def get_suit_int(card):
    return Card.get_suit_int(card)

CARD_TO_BIT = {c: np.int64(1) << ((get_rank_int(c) << np.int64(2)) + (get_suit_int(c).bit_length() - 1)) for c in FULL_DECK}
CARD_TO_RANK_SHIFT = {c: 1 << (get_rank_int(c) * 4) for c in FULL_DECK}

# convert hand, dead_cards into bitmasks before using
def build_bitmasks(hand, dead_cards):
    dead_set = set(hand) | set(dead_cards) # Combine into a fast O(1) lookup set
    available_cards = [c for c in FULL_DECK if c not in dead_set]
    
    hand_bits = 0
    hand_rank_counts = 0
    available_set = 0
    rem_rank_counts = 0

    for c in hand:
        hand_bits |= CARD_TO_BIT[c]
        hand_rank_counts += CARD_TO_RANK_SHIFT[c]

    for c in available_cards:
        available_set |= CARD_TO_BIT[c]
        rem_rank_counts += CARD_TO_RANK_SHIFT[c]

    #print(bin(rem_rank_counts))

    return hand_bits, hand_rank_counts, available_set, rem_rank_counts


# cards should be converted to treys cards before calling this function
def calculate_move_delta(player_hand, dealer_hand, current_card):
    all_dead = player_hand + dealer_hand + [current_card]

    player_give_hand_bits, player_give_rank_counts, player_available_set, player_rem_rank_counts = (
        build_bitmasks(player_hand, all_dead))
    
    player_keep_hand_bits = player_give_hand_bits | CARD_TO_BIT[current_card]
    player_keep_rank_counts = player_give_rank_counts + CARD_TO_RANK_SHIFT[current_card]
    
    # Exact deterministic expected value for the player (limit 5)
    expected_player_keep = evaluate_player_deterministic(player_hand + [current_card], 
                                                         player_keep_hand_bits, 
                                                         player_keep_rank_counts, 
                                                         player_available_set, 
                                                         player_rem_rank_counts)    
    expected_player_give = evaluate_player_deterministic(player_hand, 
                                                         player_give_hand_bits, 
                                                         player_give_rank_counts, 
                                                         player_available_set, 
                                                         player_rem_rank_counts)  
    
    # Exact deterministic expected value for the dealer (limit 8)
    dealer_base_hand_bits, dealer_base_rank_counts, dealer_available_set, dealer_rem_rank_counts = (
        build_bitmasks(dealer_hand, all_dead))
    
    dealer_with_card_hand_bits = dealer_base_hand_bits | CARD_TO_BIT[current_card]
    dealer_with_card_rank_counts = dealer_base_rank_counts + CARD_TO_RANK_SHIFT[current_card]


    expected_dealer_keep = evaluate_dealer_deterministic(dealer_hand, 
                                                         dealer_base_hand_bits, 
                                                         dealer_base_rank_counts, 
                                                         dealer_available_set, 
                                                         dealer_rem_rank_counts)
    
    expected_dealer_give = evaluate_dealer_deterministic(dealer_hand + [current_card], 
                                                         dealer_with_card_hand_bits, 
                                                         dealer_with_card_rank_counts, 
                                                         dealer_available_set, 
                                                         dealer_rem_rank_counts)
    
    # Utility = Expected Dealer Score - Expected Player Score 
    # Higher is better for Player, as lower scores represent stronger hands
    utility_keep = expected_dealer_keep - expected_player_keep
    utility_give = expected_dealer_give - expected_player_give
    delta = utility_keep - utility_give
    
    return {
        "keep_utility": utility_keep,
        "give_utility": utility_give,
        "delta": delta,
        "expected_player_keep": expected_player_keep,
        "expected_dealer_keep": expected_dealer_keep,
        "expected_player_give": expected_player_give,
        "expected_dealer_give": expected_dealer_give
    }

# An example usage
if __name__ == "__main__":
    from treys import Card

    player_hand = [Card.new('Ah'), Card.new('Kh'), Card.new('Qh'), Card.new('Th')]
    dealer_hand = [Card.new('2s'), Card.new('3c'), Card.new('4d')]
    current_card = Card.new('Jh')
    
    print("Running evaluation...")
    results = calculate_move_delta(player_hand, dealer_hand, current_card)
    
    print(f"--- Utility if KEEP ---")
    print(f"Expected Player Rank: {results['expected_player_keep']:.2f}")
    print(f"Expected Dealer Rank: {results['expected_dealer_keep']:.2f}")
    print(f"Net Utility (Dealer - Player): {results['keep_utility']:.2f}\n")
    
    print(f"--- Utility if GIVE ---")
    print(f"Expected Player Rank: {results['expected_player_give']:.2f}")
    print(f"Expected Dealer Rank: {results['expected_dealer_give']:.2f}")
    print(f"Net Utility (Dealer - Player): {results['give_utility']:.2f}\n")
    
    print(f"Delta (Keep - Give): {results['delta']:.2f}")
    if results['delta'] > 0:
        print("Decision: KEEP the card.")
    else:
        print("Decision: GIVE the card.")
