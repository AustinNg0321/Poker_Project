import sys
import os

# Add the backend directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from treys import Card
from app.core.game import GameState
from app.evaluators.evaluator import determine_winner
from app.simulators.v_0_1_logic import calculate_move_delta

def simulate_games(num_games=10, mc_sims_per_move=100):
    player_wins = 0
    dealer_wins = 0

    print(f"Starting simulation of {num_games} games...")
    
    for i in range(num_games):
        game = GameState()
        
        while not game.is_game_over:
            can_give = (len(game.player_hand) + len(game.deck)) > 4
            can_keep = len(game.player_hand) < 5
            
            if not can_give:
                game.keep()
                continue
            if not can_keep:
                game.give()
                continue
                
            # Convert state to Treys format for the "AI"
            treys_player = [Card.new(c) for c in game.player_hand]
            treys_dealer = [Card.new(c) for c in game.dealer_hand]
            treys_card = Card.new(game.current_card)

            results = calculate_move_delta(
                treys_player, 
                treys_dealer, 
                treys_card, 
                num_simulations=mc_sims_per_move
            )
            
            if results['delta'] > 0:
                game.keep()
            else:
                game.give()
                
        winner = determine_winner(game.player_hand, game.dealer_hand)
        if winner == 'player':
            player_wins += 1
        else:
            dealer_wins += 1
        
    print("\n--- Simulation Results ---")
    print(f"Total Games: {num_games}")
    print(f"Player Wins: {player_wins} ({(player_wins/num_games)*100:.2f}%)")
    print(f"Dealer Wins: {dealer_wins} ({(dealer_wins/num_games)*100:.2f}%)")

if __name__ == "__main__":
    simulate_games(num_games=2500, mc_sims_per_move=100) # will take a bit more than a minute
