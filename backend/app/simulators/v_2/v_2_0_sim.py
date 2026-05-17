import sys
import os
import pandas as pd
import xgboost as xgb
from treys import Card

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from app.core.game import GameState
from app.evaluators.evaluator import determine_winner, get_best_score
from app.simulators.v_1.v_1_0_logic import CARD_TO_BIT
from app.simulators.v_2.generate_training_data import get_max_suit_count, get_longest_straight_stretch

def evaluate_mini_score(hand_treys):
    if len(hand_treys) >= 5:
        return get_best_score(hand_treys)
    return 7463 + ((5 - len(hand_treys)) * 100)

def run_ml_simulation(num_games=1000):
    # Load Model
    model_path = os.path.join(os.path.dirname(__file__), 'poker_bot_v2_0.json')
    model = xgb.XGBClassifier()
    model.load_model(model_path)
    
    wins = 0
    
    for game_id in range(1, num_games + 1):
        game = GameState()
        move_num = 1
        
        while not game.is_game_over:
            can_give = (len(game.player_hand) + len(game.deck)) > 4
            can_keep = len(game.player_hand) < 5
            
            # Forced moves - advance clock to keep sync with training data format
            if not can_give:
                game.keep()
                move_num += 1
                continue
            if not can_keep:
                game.give()
                move_num += 1
                continue
                
            # --- FEATURE EXTRACTION ---
            treys_player = [Card.new(c) for c in game.player_hand]
            treys_dealer = [Card.new(c) for c in game.dealer_hand]
            current_card = Card.new(game.current_card)
            
            # Extract features exactly matching what the newly trained model expects
            current_card_mask = CARD_TO_BIT[current_card]
            player_mask = sum(CARD_TO_BIT[c] for c in treys_player)
            dealer_mask = sum(CARD_TO_BIT[c] for c in treys_dealer)
            
            features = {
                "current_card_mask": current_card_mask, 
                "player_hand_mask": player_mask,
                "dealer_hand_mask": dealer_mask,
                "dealer_draw_shortfall": max(0, 8 - len(game.dealer_hand)),
                "player_max_suit_count": get_max_suit_count(treys_player),
                "player_is_consecutive_count": get_longest_straight_stretch(treys_player),
                "current_player_rank_score": evaluate_mini_score(treys_player),
                "current_dealer_rank_score": evaluate_mini_score(treys_dealer)
            }
            
            # Convert directly to DataFrame for the prediction row
            X_infer = pd.DataFrame([features])
            
            # --- ML INFERENCE ---
            decision = model.predict(X_infer)[0]
            
            if decision == 1:
                game.keep()
            else:
                game.give()
                
            move_num += 1
            
        # Track the win rate metrics
        if determine_winner(game.player_hand, game.dealer_hand) == 'player':
            wins += 1
            
    print(f"\nSimulation Complete")
    print(f"Total Games Played: {num_games}")
    print(f"Total Wins:         {wins}")
    print(f"Win Rate:           {(wins / num_games) * 100:.2f}%")

if __name__ == "__main__":
    run_ml_simulation(1000)