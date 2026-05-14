import sys
import os

# Add the backend directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from app.evaluators.evaluator import get_best_score, FULL_DECK
from random import sample

"""
Evaluates hand strength using Treys (lower is better).
If limit is reached, returns exact score.
If limit is not reached, uses a random rollout Monte Carlo policy to estimate expected score.
"""
def evaluate_hand_strength(hand, limit, dead_cards, num_simulations=100):
    if num_simulations <= 0:
        raise ValueError("num_simulations must be a positive integer.")
    if len(hand) >= limit:
        return get_best_score(hand)
            
    available_cards = [c for c in FULL_DECK if c not in hand and c not in dead_cards]
    cards_needed = limit - len(hand)
    total_score = 0

    for _ in range(num_simulations):
        simulated_hand = hand + sample(available_cards, cards_needed)
        score = get_best_score(simulated_hand)
        total_score += score
    
    return total_score / num_simulations

"""
Calculates the expected Utility (Treys Rank) of keeping vs giving the current card.
Utility here is represented by difference in expected Treys ranks. Lower Treys rank = better hand.
We want Delta to be transparent.
"""
# cards should be converted to treys cards before calling this function
def calculate_move_delta(player_hand, dealer_hand, current_card, num_simulations=100):
    all_dead = player_hand + dealer_hand + [current_card]
    expected_player_keep = evaluate_hand_strength(player_hand + [current_card], 5, all_dead, num_simulations)
    expected_dealer_keep = evaluate_hand_strength(dealer_hand, 8, all_dead, num_simulations)
    expected_player_give = evaluate_hand_strength(player_hand, 5, all_dead, num_simulations)
    expected_dealer_give = evaluate_hand_strength(dealer_hand + [current_card], 8, all_dead, num_simulations)
    
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

    player_hand = [Card.new('Ah'), Card.new('Kh'), Card.new('Qh')]
    dealer_hand = [Card.new('2s'), Card.new('3c'), Card.new('4d')]
    current_card = Card.new('Jh')
    
    print("Running evaluation...")
    results = calculate_move_delta(player_hand, dealer_hand, current_card, num_simulations=100)
    
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
