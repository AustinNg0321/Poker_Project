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

def extract_feature_vector(treys_player, treys_dealer, deck_count):
    player_mask = sum(CARD_TO_BIT[c] for c in treys_player)
    dealer_mask = sum(CARD_TO_BIT[c] for c in treys_dealer)
    
    return {
        "current_card_mask": 0,
        "player_hand_mask": player_mask,
        "dealer_hand_mask": dealer_mask,
        "player_card_count": len(treys_player),
        "dealer_card_count": len(treys_dealer),
        "cards_remaining_in_deck": deck_count,
        "dealer_draw_shortfall": max(0, 8 - len(treys_dealer)),
        "player_max_suit_count": get_max_suit_count(treys_player),
        "player_is_consecutive_count": get_longest_straight_stretch(treys_player),
        "dealer_max_suit_count": get_max_suit_count(treys_dealer),
        "dealer_max_consecutive_count": get_longest_straight_stretch(treys_dealer)
    }

def print_debug_log(game_id, move_num, features_keep, features_give, r_p_keep, r_p_give, r_d, decision):
    """
    Modular logging block for detailed feature bounds, vector snapshots, and delta tracing.
    """
    print(f"\n[{'='*40}]")
    print(f"[GAME {game_id} | MOVE {move_num}] - DETAILED LOOKAHEAD TRACE")
    print(f"[{'='*40}]")
    
    print("\n--- 1. SCENARIO RAW VECTORS ---")
    print("KEEP SCENARIO VECTOR:")
    for key, val in features_keep.items():
        print(f"  {key:<30}: {val}")
        
    print("\nGIVE SCENARIO VECTOR:")
    for key, val in features_give.items():
        print(f"  {key:<30}: {val}")
        
    print("\n--- 2. PREDICTION EXPECTED RANKS ---")
    print(f"Keep Rank  (r_p_keep) : {r_p_keep:.2f}")
    print(f"Give Rank  (r_p_give) : {r_p_give:.2f}")
    print(f"Dealer Rank (r_d)     : {r_d:.2f}")
    
    delta_keep = r_d - r_p_keep
    delta_give = r_d - r_p_give
    print(f"DELTA Keep : {delta_keep:.2f}")
    print(f"DELTA Give : {delta_give:.2f}")
        
    choice_str = "KEEP" if decision else "GIVE"
    print(f"-> BOT SELECTED: {choice_str}")

def run_ml_simulation(num_games=1000):
    base_dir = os.path.dirname(__file__)
    player_model_path = os.path.join(base_dir, 'player_rank_model.json')
    dealer_model_path = os.path.join(base_dir, 'dealer_rank_model.json')
    
    player_model = xgb.XGBRegressor()
    player_model.load_model(player_model_path)
    
    dealer_model = xgb.XGBRegressor()
    dealer_model.load_model(dealer_model_path)
    
    expected_features = player_model.get_booster().feature_names
    
    # --- 3. FEATURE BOUNDARY AUDIT ---
    print("\n[STARTUP] --- FEATURE BOUNDARY AUDIT ---")
    print(f"Model Expected Features (Length {len(expected_features)}):")
    print(expected_features)
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
            r_p_keep = player_model.predict(X_keep)[0]

            # --- EVALUATE GIVE ---
            treys_dealer_give = treys_dealer.copy()
            treys_dealer_give.append(treys_card)
            
            features_give = extract_feature_vector(treys_player, treys_dealer_give, len(game.deck) - 1)
            X_give = pd.DataFrame([features_give])[expected_features]
            r_p_give = player_model.predict(X_give)[0]
            
            # --- EVALUATE DEALER ---
            features_dealer = extract_feature_vector(treys_player, treys_dealer, len(game.deck))
            X_dealer = pd.DataFrame([features_dealer])[expected_features]
            r_d = dealer_model.predict(X_dealer)[0]
            
            # Delta calculation: We want to Maximize (Dealer Rank - Player Rank)
            # Higher delta = better position for player
            delta_keep = r_d - r_p_keep
            delta_give = r_d - r_p_give
            
            bot_kept = delta_keep > delta_give
            
            if game_id == 1:
                print_debug_log(game_id, move_num, features_keep, features_give, r_p_keep, r_p_give, r_d, bot_kept)
                
            if bot_kept:
                game.keep()
            else:
                game.give()
                
            move_num += 1
            
        if determine_winner(game.player_hand, game.dealer_hand) == 'player':
            wins += 1
            
    print(f"\nSimulation Complete")
    print(f"Total Games Played: {num_games}")
    print(f"Total Wins:         {wins}")
    print(f"Win Rate:           {(wins / num_games) * 100:.2f}%")

if __name__ == "__main__":
    run_ml_simulation(1000)
