import sys
import os
from random import shuffle, seed

# Add the backend directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from app.evaluators.evaluator import determine_winner_helper
from treys import Card

"""
Estimates the baseline win probability by simulating completely random hands.
Player gets 5 random cards, dealer gets 8 random cards.
"""
def estimate_baseline_win_probability(num_simulations):
    seed(os.urandom(4))

    suits = ['h', 'd', 'c', 's']
    ranks = ['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A']
    base_deck = [f"{rank}{suit}" for suit in suits for rank in ranks]
    treys_deck = [Card.new(card) for card in base_deck]
    
    player_wins = 0
    dealer_wins = 0
    draws = 0

    for _ in range(num_simulations):
        shuffle(treys_deck)
        
        player_hand = treys_deck[:5]
        dealer_hand = treys_deck[5:13]
        
        winner = determine_winner_helper(player_hand, dealer_hand)
        
        if winner == 'player':
            player_wins += 1
        else:
            dealer_wins += 1

    return {
        "player_win_prob": player_wins / num_simulations,
        "dealer_win_prob": dealer_wins / num_simulations,
        "tie_prob": draws / num_simulations,
        "total_simulations": num_simulations
    }

if __name__ == "__main__":
    print("Running baseline simulation...")
    results = estimate_baseline_win_probability(1000000)
    print(f"Results over {results['total_simulations']} simulations:")
    print(f"Player win probability: {results['player_win_prob']:.8f}")
    print(f"Dealer win probability: {results['dealer_win_prob']:.8f}")
    print(f"Tie probability: {results['tie_prob']:.8f}")
