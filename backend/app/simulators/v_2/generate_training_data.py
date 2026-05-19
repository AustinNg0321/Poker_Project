import sys
import os
import csv
from treys import Card

# Add backend directory to sys path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from app.core.game import GameState
from app.evaluators.evaluator import determine_winner, get_best_score
from app.simulators.v_1.v_1_0_logic import calculate_move_delta, CARD_TO_BIT

def get_max_suit_count(hand_treys):
    if not hand_treys:
        return 0
    counts = {}
    for c in hand_treys:
        suit = Card.get_suit_int(c)
        counts[suit] = counts.get(suit, 0) + 1
    return max(counts.values()) if counts else 0

def get_longest_straight_stretch(hand_treys):
    if not hand_treys:
        return 0
    ranks = {Card.get_rank_int(c) for c in hand_treys}
    sorted_ranks = sorted(list(ranks))
    if 12 in ranks:
        sorted_ranks.insert(0, -1)
        
    max_streak = 1
    current_streak = 1
    for i in range(1, len(sorted_ranks)):
        if sorted_ranks[i] == sorted_ranks[i-1] + 1:
            current_streak += 1
            max_streak = max(max_streak, current_streak)
        else:
            current_streak = 1
    return max_streak


def run_simulation(target_games=50000):
    output_file = os.path.join(os.path.dirname(__file__), 'training_data_v2_0.csv')
    
    headers = [
        "game_id", "move_num", "current_card_mask", "player_hand_mask", "dealer_hand_mask",
        "player_card_count", "dealer_card_count", 
        "decision", 
        "cards_remaining_in_deck",
        "dealer_draw_shortfall", 
        "player_max_suit_count", "player_is_consecutive_count",
        "dealer_max_suit_count", "dealer_max_consecutive_count",
        "final_player_rank", "final_dealer_rank",
        "game_won"
    ]
    
    games_recorded = 0
    game_id = 1
    
    with open(output_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        
        while games_recorded < target_games:
            game = GameState()
            game_log_cache = []
            move_num = 1
            
            while not game.is_game_over:
                can_give = (len(game.player_hand) + len(game.deck)) > 4
                can_keep = len(game.player_hand) < 5
                
                # Execute forced moves and cleanly advance the loop clock without tracking
                if not can_give:
                    game.keep()
                    move_num += 1
                    continue
                if not can_keep:
                    game.give()
                    move_num += 1
                    continue
                    
                treys_player = [Card.new(c) for c in game.player_hand]
                treys_dealer = [Card.new(c) for c in game.dealer_hand]
                treys_card = Card.new(game.current_card)
                
                # Ask best v_1_0 bot for choice
                res = calculate_move_delta(treys_player, treys_dealer, treys_card)
                bot_kept = res['delta'] > 0
                
                # Calculate True Native Bitmasks
                player_hand_mask = sum(CARD_TO_BIT[c] for c in treys_player)
                dealer_hand_mask = sum(CARD_TO_BIT[c] for c in treys_dealer)
                current_card_mask = CARD_TO_BIT[treys_card]

                log_row = {
                    "game_id": game_id,
                    "move_num": move_num,
                    "current_card_mask": current_card_mask,
                    "player_hand_mask": player_hand_mask,
                    "dealer_hand_mask": dealer_hand_mask,
                    "player_card_count": len(game.player_hand),
                    "dealer_card_count": len(game.dealer_hand),
                    "decision": 1 if bot_kept else 0,
                    "cards_remaining_in_deck": len(game.deck),
                    "dealer_draw_shortfall": max(0, 8 - len(game.dealer_hand)),
                    "player_max_suit_count": get_max_suit_count(treys_player),
                    "player_is_consecutive_count": get_longest_straight_stretch(treys_player),
                    "dealer_max_suit_count": get_max_suit_count(treys_dealer),
                    "dealer_max_consecutive_count": get_longest_straight_stretch(treys_dealer),
                }
                game_log_cache.append(log_row)
                
                if bot_kept:
                    game.keep()
                else:
                    game.give()
                    
                move_num += 1
                
            # Log all games (wins and losses)
            winner = determine_winner(game.player_hand, game.dealer_hand)
            is_win = 1 if winner == 'player' else 0
            
            # --- Calculate True Final Ranks ---
            final_treys_player = [Card.new(c) for c in game.player_hand]
            final_treys_dealer = [Card.new(c) for c in game.dealer_hand]
            
            final_p_rank = get_best_score(final_treys_player)
            final_d_rank = get_best_score(final_treys_dealer)
            
            # Backfill the final outcome data into every move of the game
            for row in game_log_cache:
                row["final_player_rank"] = final_p_rank
                row["final_dealer_rank"] = final_d_rank
                row["game_won"] = is_win
                writer.writerow(row)
                
            games_recorded += 1
            print(f"\rSimulating Game: {games_recorded}/{target_games}", end="", flush=True)
                
            game_id += 1

if __name__ == "__main__":
    run_simulation(50000)
    print("\nScript successfully generated: training_data_v2_0.csv")