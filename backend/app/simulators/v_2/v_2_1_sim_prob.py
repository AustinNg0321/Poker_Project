import sys
import os
import pandas as pd
import numpy as np
import xgboost as xgb
from treys import Card

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from app.core.game import GameState
from app.evaluators.evaluator import determine_winner
from app.simulators.v_1.v_1_0_logic import CARD_TO_BIT
from app.simulators.v_2.generate_training_data import get_max_suit_count, get_longest_straight_stretch

SUITS = ['h', 'd', 'c', 's']
RANKS = ['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A']
CARDS = [r + s for r in RANKS for s in SUITS]

def extract_feature_vector(treys_player, treys_dealer, deck_count):
    player_mask = sum(CARD_TO_BIT[c] for c in treys_player)
    dealer_mask = sum(CARD_TO_BIT[c] for c in treys_dealer)
    deck_mask = 0xFFFFFFFFFFFFF ^ (player_mask | dealer_mask)

    features = {
        "player_card_count": len(treys_player),
        "dealer_card_count": len(treys_dealer),
        "cards_remaining_in_deck": deck_count,
        "dealer_draw_shortfall": max(0, 8 - len(treys_dealer)),
        "player_max_suit_count": get_max_suit_count(treys_player),
        "player_is_consecutive_count": get_longest_straight_stretch(treys_player),
        "dealer_max_suit_count": get_max_suit_count(treys_dealer),
        "dealer_max_consecutive_count": get_longest_straight_stretch(treys_dealer)
    }

    # Expand the masks into individual binary columns
    for i, c in enumerate(CARDS):
        bit = 1 << i
        features[f"p_has_{c}"] = 1 if (player_mask & bit) else 0
        features[f"d_has_{c}"] = 1 if (dealer_mask & bit) else 0
        features[f"deck_has_{c}"] = 1 if (deck_mask & bit) else 0

    return features

def print_debug_log(game_id, move_num, features_keep, features_give, prob_keep, prob_give, decision):
    """
    Modular logging block for detailed feature bounds, vector snapshots, and delta tracing.
    """
    print(f"\n[{'='*40}]")
    print(f"[GAME {game_id} | MOVE {move_num}] - DETAILED LOOKAHEAD TRACE")
    print(f"[{'='*40}]")
    
    print("\n--- 1. SCENARIO RAW VECTORS ---")
    print("KEEP SCENARIO VECTOR:")
    for key, val in list(features_keep.items())[:12]:
        print(f"  {key:<30}: {val}")
    print("  ... (card booleans hidden for brevity) ...")
        
    print("\nGIVE SCENARIO VECTOR:")
    for key, val in list(features_give.items())[:12]:
        print(f"  {key:<30}: {val}")
    print("  ... (card booleans hidden for brevity) ...")
        
    print("\n--- 2. PREDICTION EXPECTED WIN PROBABILITY ---")
    print(f"Keep Win Prob : {prob_keep:.4f}")
    print(f"Give Win Prob : {prob_give:.4f}")
    
    delta = prob_give - prob_keep
    print(f"DELTA (Give - Keep) : {delta:.4f}")
        
    choice_str = "KEEP" if decision else "GIVE"
    print(f"-> BOT SELECTED: {choice_str}")

def run_ml_simulation(num_games=1000):
    base_dir = os.path.dirname(__file__)
    model_path = os.path.join(base_dir, 'player_prob_model_v2_1.json')
    
    prob_model = xgb.XGBRegressor()
    prob_model.load_model(model_path)
    
    expected_features = prob_model.get_booster().feature_names
    
    # --- 3. FEATURE BOUNDARY AUDIT ---
    print("\n[STARTUP] --- FEATURE BOUNDARY AUDIT ---")
    print(f"Model Expected Features (Length {len(expected_features)}):")
    if len(expected_features) <= 20:
        print(expected_features)
    else:
        print(f"[{', '.join(expected_features[:5])}, ..., {', '.join(expected_features[-5:])}]")
    print("------------------------------------------\n")
    
    wins = 0
    
    for game_id in range(1, num_games + 1):
        game = GameState()
        move_num = 1
        
        while not game.is_game_over:
            can_give = (len(game.player_hand) + len(game.deck)) > 4
            can_keep = len(game.player_hand) < 5
            
            if not can_give:
                game.keep()
                continue
            if not can_keep:
                game.give()
                continue
                
            treys_player = [Card.new(c) for c in game.player_hand]
            treys_dealer = [Card.new(c) for c in game.dealer_hand]
            treys_card = Card.new(game.current_card)
            
            # --- EVALUATE KEEP ---
            treys_player_keep = treys_player.copy()
            treys_player_keep.append(treys_card)
            
            features_keep = extract_feature_vector(treys_player_keep, treys_dealer, len(game.deck) - 1)
            X_keep = pd.DataFrame([features_keep])[expected_features]
            prob_keep = prob_model.predict(X_keep)[0]

            # --- EVALUATE GIVE ---
            treys_dealer_give = treys_dealer.copy()
            treys_dealer_give.append(treys_card)
            
            features_give = extract_feature_vector(treys_player, treys_dealer_give, len(game.deck) - 1)
            X_give = pd.DataFrame([features_give])[expected_features]
            prob_give = prob_model.predict(X_give)[0]
            
            bot_kept = prob_keep > prob_give
            
            # if game_id == 1:
            #     print_debug_log(game_id, move_num, features_keep, features_give, prob_keep, prob_give, bot_kept)
                
            if bot_kept:
                game.keep()
            else:
                game.give()
                
            move_num += 1
            
        if determine_winner(game.player_hand, game.dealer_hand) == 'player':
            wins += 1
        
        if game_id % 10 == 0:
            print(f"Completed {game_id} games... Current Win Rate: {(wins / game_id) * 100:.2f}%")
            
    print(f"\nSimulation Complete")
    print(f"Total Games Played: {num_games}")
    print(f"Total Wins:         {wins}")
    print(f"Win Rate:           {(wins / num_games) * 100:.2f}%")

if __name__ == "__main__":
    run_ml_simulation(1000)
