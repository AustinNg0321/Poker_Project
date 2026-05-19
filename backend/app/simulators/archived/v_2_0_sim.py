import sys
import os
import pandas as pd
import numpy as np
import xgboost as xgb
from treys import Card

# Add the backend directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from app.core.game import GameState
from app.evaluators.evaluator import determine_winner, get_best_score
from app.simulators.v_2.generate_training_data import get_max_suit_count, get_longest_straight_stretch
from app.evaluators.evaluator import FULL_DECK

# --- DIAGNOSTIC CONFIGURATION ---
# Toggle this to True if your XGBoost model was trained on 'final_player_rank' (lower score is better) 
# instead of the binary 'game_won' (higher probability is better) target.
# INVERT_SELECTION_LOGIC = False

def get_rank_int(card):
    return Card.get_rank_int(card)

def get_suit_int(card):
    return Card.get_suit_int(card)

# Fast lookup tables using Treys internal integer cards as keys
CARD_TO_BIT = {c: 1 << ((get_rank_int(c) << 2) + (get_suit_int(c).bit_length() - 1)) for c in FULL_DECK}
CARD_TO_RANK_SHIFT = {c: 1 << (get_rank_int(c) << 2) for c in FULL_DECK}
FULL_DECK_BITS = 0xFFFFFFFFFFFFF
FULL_DECK_RANK_COUNTS = 0x4444444444444


"""
Converts a list of Treys integer cards into your custom bitmask format.
Returns: (hand_bits, hand_rank_counts)
"""
def get_hand_masks(hand_treys):
    hand_bits = 0
    hand_rank_counts = 0
    for c in hand_treys:
        hand_bits |= CARD_TO_BIT[c]
        hand_rank_counts += CARD_TO_RANK_SHIFT[c]
    return hand_bits, hand_rank_counts

"""Fallback scoring metric used during training data phase."""
def evaluate_mini_score(hand_treys):
    if len(hand_treys) >= 5:
        return get_best_score(hand_treys)
    return 7463 + ((5 - len(hand_treys)) * 100)

"""
Constructs a feature dictionary matching the exact column names 
and feature definitions from your training CSV.
"""
def extract_feature_vector(player_cards_raw, dealer_cards_raw, deck_count):
    treys_player = [Card.new(c) for c in player_cards_raw]
    treys_dealer = [Card.new(c) for c in dealer_cards_raw]
    
    player_hand_mask, _ = get_hand_masks(treys_player)
    dealer_hand_mask, _ = get_hand_masks(treys_dealer)
    
    return {
        # "current_card_mask": 0, # Omitted or zeroed if expected by model, handled by expected_features lookup
        "player_hand_mask": player_hand_mask,
        "dealer_hand_mask": dealer_hand_mask,
        "player_card_count": len(player_cards_raw),
        "dealer_card_count": len(dealer_cards_raw),
        "dealer_draw_shortfall": max(0, 8 - len(dealer_cards_raw)),
        "player_max_suit_count": get_max_suit_count(treys_player),
        "player_is_consecutive_count": get_longest_straight_stretch(treys_player),
        "current_player_rank_score": evaluate_mini_score(treys_player),
        "current_dealer_rank_score": evaluate_mini_score(treys_dealer),
        "cards_remaining_in_deck": deck_count
    }

def run_ml_simulation(num_games=1000):
    # Load your optimized 1000-tree JSON model
    model_path = os.path.join(os.path.dirname(__file__), 'poker_bot_regressor_0.json')
    model = xgb.XGBRegressor()
    model.load_model(model_path)
    
    # Get exact feature order expected by the model
    expected_features = model.get_booster().feature_names
    
    player_wins = 0
    print(f"Starting ML-driven lookahead simulation of {num_games} games...")

    for game_id in range(1, num_games + 1):
        game = GameState()
        

        while not game.is_game_over:
            can_give = (len(game.player_hand) + len(game.deck)) > 4
            can_keep = len(game.player_hand) < 5
            
            # Handle forced state transitions
            if not can_give:
                game.keep()
                continue
            if not can_keep:
                game.give()
                continue
                
            deck_remaining = len(game.deck)
            
            # --- EVALUATE CURRENT STATIC HYPOTHETICALS ---

            # --- SCENARIO A: What if we KEEP? ---
            # Evaluate the base state without lookahead logic
            features_keep = extract_feature_vector(
                player_cards_raw=game.player_hand + [game.current_card],
                dealer_cards_raw=game.dealer_hand,
                deck_count=deck_remaining
            )
            
            # Fill missing model parameters like current_card_mask gracefully if expected
            for feat in expected_features:
                if feat not in features_keep:
                    features_keep[feat] = 0

            vals_keep = [features_keep[name] for name in expected_features]
            X_keep = np.array([vals_keep], dtype=np.float32)
            prob_keep = model.predict(X_keep)[0]

            # --- SCENARIO B: What if we GIVE? ---
            features_give = extract_feature_vector(
                player_cards_raw=game.player_hand,
                dealer_cards_raw=game.dealer_hand + [game.current_card],
                deck_count=deck_remaining
            )
            
            for feat in expected_features:
                if feat not in features_give:
                    features_give[feat] = 0

            vals_give = [features_give[name] for name in expected_features]
            X_give = np.array([vals_give], dtype=np.float32)
            prob_give = model.predict(X_give)[0]
            
            # --- SELECTION ---
            # If predicting win probability (higher is better)
            if prob_keep > prob_give:
                game.keep()
            else:
                game.give()
                
        # Evaluate final match outcome
        winner = determine_winner(game.player_hand, game.dealer_hand)
        if winner == 'player':
            player_wins += 1
            
        if game_id % 10 == 0:
            print(f"Completed {game_id}/{num_games} games... Current Win Rate: {(player_wins / game_id) * 100:.2f}%")
            
    print("\n--- ML Simulation Results ---")
    print(f"Total Games Played: {num_games}")
    print(f"Player Wins:        {player_wins}")
    print(f"Player Win Rate:    {(player_wins / num_games) * 100:.2f}%")
    print(f"Dealer Win Rate:    {((num_games - player_wins) / num_games) * 100:.2f}%")

if __name__ == "__main__":
    run_ml_simulation(1000)