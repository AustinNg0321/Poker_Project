import random
import sys
import os

# Add the backend directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

# Pick the first royal flush, ensuring the dealer cannot also get a royal flush
def simulate_perfect_info_win():
    suits = ['h', 'd', 'c', 's']
    ranks = ['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A']
    deck = [f"{rank}{suit}" for suit in suits for rank in ranks]
    random.shuffle(deck)
    
    # Define the 4 possible royal flushes
    spade_index = max(deck.index(f"{rank}s") for rank in ['T', 'J', 'Q', 'K', 'A'])
    heart_index = max(deck.index(f"{rank}h") for rank in ['T', 'J', 'Q', 'K', 'A'])
    club_index = max(deck.index(f"{rank}c") for rank in ['T', 'J', 'Q', 'K', 'A'])
    diamond_index = max(deck.index(f"{rank}d") for rank in ['T', 'J', 'Q', 'K', 'A'])
    
    royal_flush_index = min(spade_index, heart_index, club_index, diamond_index)
    royal_flush_suit = deck[royal_flush_index][1]  # Get the suit of the royal flush
    player_hand = [f"{rank}{royal_flush_suit}" for rank in ['T', 'J', 'Q', 'K', 'A']]
    dealer_hand = [deck[i] for i in range(royal_flush_index) if deck[i] not in player_hand]

    print("Simulating perfect information win...")
    print(f"Player hand: {player_hand}")
    print(f"Dealer hand: {dealer_hand}")

if __name__ == "__main__":
    simulate_perfect_info_win()
