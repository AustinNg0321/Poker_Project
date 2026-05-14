import sys
import os
import random

# Add the backend directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from app.core.game import GameState
from app.evaluators.evaluator import determine_winner
from treys import Card
# Adjust this import to whatever logic file actually contains the `calculate_move_delta` you intend to use.
# I am assuming v_0_3_logic based on recent context.
from app.simulators.v_0.v_0_3_logic import calculate_move_delta

def run_debug_game():
    print("=== STARTING 1 DEBUG GAME ===")
    
    # Initialize game with a fixed seed so we have reproducible logic behavior
    random.seed(42)
    game = GameState()
    
    move_count = 1
    
    while not game.is_game_over:
        print(f"\n--- Turn {move_count} ---")
        
        # Determine strict constraints
        can_give = (len(game.player_hand) + len(game.deck)) > 4
        can_keep = len(game.player_hand) < 5
        
        print(f"Cards Left in Deck: {len(game.deck)}")
        print(f"Player Hand ({len(game.player_hand)}/5): {game.player_hand}")
        print(f"Dealer Hand ({len(game.dealer_hand)}/8 limit): {game.dealer_hand}")
        print(f"Current Drawn Card: {game.current_card}")
        
        # Check forced moves
        if not can_give:
            print("Action: FORCED KEEP (Not enough cards to finish player hand if given)")
            game.keep()
            move_count += 1
            continue
        if not can_keep:
            print("Action: FORCED GIVE (Player hand already has 5 cards)")
            game.give()
            move_count += 1
            continue

        # Prepare for evaluator
        treys_player = [Card.new(c) for c in game.player_hand]
        treys_dealer = [Card.new(c) for c in game.dealer_hand]
        treys_card = Card.new(game.current_card)

        # Get deterministic expectations
        results = calculate_move_delta(treys_player, treys_dealer, treys_card)

        # Print all the deterministic data points
        print("\n--- Evaluator Data ---")
        print(f"Expected Player (if KEEP): {results['expected_player_keep']:.2f}")
        print(f"Expected Player (if GIVE): {results['expected_player_give']:.2f}")
        print(f"Expected Dealer (if KEEP): {results['expected_dealer_keep']:.2f} (Card given to Player)")
        print(f"Expected Dealer (if GIVE): {results['expected_dealer_give']:.2f} (Card given to Dealer)")
        
        print(f"\nKEEP Utility (DealerEV - PlayerEV): {results['keep_utility']:.2f}")
        print(f"GIVE Utility (DealerEV - PlayerEV): {results['give_utility']:.2f}")
        print(f"Delta (KEEP - GIVE): {results['delta']:.2f}")
        
        # Determine actual action based on utility delta
        if results['delta'] > 0:
            print(f">>> Action Chosen: KEEP")
            game.keep()
        else:
            print(f">>> Action Chosen: GIVE")
            game.give()
            
        move_count += 1

    print("\n=== GAME OVER ===")
    print(f"Final Player Hand: {game.player_hand}")
    print(f"Final Dealer Hand: {game.dealer_hand}")
    
    winner = determine_winner(game.player_hand, game.dealer_hand)
    print(f"\nWINNER: {winner.upper()}")

if __name__ == "__main__":
    run_debug_game()