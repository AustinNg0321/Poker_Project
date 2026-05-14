import sys
import os
import random
import numpy as np
import math
from treys import Card, Deck

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
import app.simulators.v_0.v_0_2_logic as v2
import app.simulators.v_0.v_0_3_logic as v3

import app.simulators.v_0.perfect_evaluator as pe
import app.simulators.v_0.perfect_evaluator_8 as pe8

def _get_player_weight(hand_bits, hand_rank_counts, available_set, rem_rank_counts, cards_needed):
    if cards_needed == 0: return 1
    total_w = 0
    fast_iter = pe.fast_iterator_array
    for i in range(fast_iter.shape[0]):
        mset_counts = fast_iter[i, 0]
        w, _ = pe._calculate_base_weight(mset_counts, hand_rank_counts, rem_rank_counts)
        total_w += w
    return total_w

def _get_dealer_weight(hand_bits, hand_rank_counts, available_set, rem_rank_counts, cards_needed):
    if cards_needed == 0: return 1
    total_w = 0
    fast_iter = pe8.fast_iterator_array_8
    for i in range(fast_iter.shape[0]):
        mset_counts = fast_iter[i, 0]
        w, _ = pe8._calculate_base_weight_8(mset_counts, hand_rank_counts, rem_rank_counts)
        total_w += w
    return total_w

def run_comparison(num_games=50):
    for game_idx in range(num_games):
        random.seed(game_idx)
        np.random.seed(game_idx)
        deck = Deck()
        
        player_hand = []
        dealer_hand = []
        
        player_hand.extend([deck.draw(1)[0], deck.draw(1)[0]])
        dealer_hand.extend([deck.draw(1)[0], deck.draw(1)[0]])
        
        for turn in range(8):
            if not deck.cards: break
            current_card = deck.draw(1)[0]
            
            v2_res = v2.calculate_move_delta(player_hand, dealer_hand, current_card, 100)
            v2_action = 'KEEP' if v2_res['delta'] > 0 else 'GIVE'
            
            v3_res = v3.calculate_move_delta(player_hand, dealer_hand, current_card)
            v3_action = 'KEEP' if v3_res['delta'] > 0 else 'GIVE'
            
            if v2_action != v3_action:
                print(f"=== Game {game_idx} Turn {turn} DIVERGENCE ===")
                print(f"Player Hand: {[Card.int_to_str(c) for c in player_hand]}")
                print(f"Dealer Hand: {[Card.int_to_str(c) for c in dealer_hand]}")
                print(f"Current Card: {Card.int_to_str(current_card)}")
                print(f"v0.2 (MC): {v2_action} | Delta: {v2_res['delta']:.2f}")
                print(f"   => Keep Utility: {v2_res['keep_utility']:.2f}, Give Utility: {v2_res['give_utility']:.2f}")
                print(f"v0.3 (Det): {v3_action} | Delta: {v3_res['delta']:.2f}")
                print(f"   => Keep Utility: {v3_res['keep_utility']:.2f}, Give Utility: {v3_res['give_utility']:.2f}")
                
                suits = [Card.get_suit_int(c) for c in player_hand + [current_card]]
                suit_counts = {s: suits.count(s) for s in set(suits)}
                flush_draw = any(c >= 4 for c in suit_counts.values())
                if flush_draw and v3_action == 'GIVE' and v2_action == 'KEEP':
                    print("--> [FLAG] v0.3 gave up a potential flush draw that v0.2 kept.")
                
                # Check weights
                p_hand_give_bits, p_hand_give_rnk, p_avail, p_rem_rnk = v3.build_bitmasks(player_hand, player_hand+dealer_hand+[current_card])
                p_hand_keep_bits, p_hand_keep_rnk, _, _ = v3.build_bitmasks(player_hand+[current_card], player_hand+dealer_hand+[current_card])

                d_hand_give_bits, d_hand_give_rnk, d_avail, d_rem_rnk = v3.build_bitmasks(dealer_hand+[current_card], player_hand+dealer_hand+[current_card])
                d_hand_keep_bits, d_hand_keep_rnk, _, _ = v3.build_bitmasks(dealer_hand, player_hand+dealer_hand+[current_card])

                w_p_give = _get_player_weight(p_hand_give_bits, p_hand_give_rnk, p_avail, p_rem_rnk, max(0, 5 - len(player_hand)))
                w_p_keep = _get_player_weight(p_hand_keep_bits, p_hand_keep_rnk, p_avail, p_rem_rnk, max(0, 5 - (len(player_hand) + 1)))
                w_d_give = _get_dealer_weight(d_hand_give_bits, d_hand_give_rnk, d_avail, d_rem_rnk, max(0, 8 - (len(dealer_hand) + 1)))
                w_d_keep = _get_dealer_weight(d_hand_keep_bits, d_hand_keep_rnk, d_avail, d_rem_rnk, max(0, 8 - len(dealer_hand)))
                
                dead_cards = len(player_hand+dealer_hand+[current_card])
                rem_cards = 52 - dead_cards
                expected_w_p_give = math.comb(rem_cards, max(0, 5 - len(player_hand)))
                expected_w_p_keep = math.comb(rem_cards, max(0, 5 - (len(player_hand) + 1)))
                expected_w_d_give = math.comb(rem_cards, max(0, 8 - (len(dealer_hand) + 1)))
                expected_w_d_keep = math.comb(rem_cards, max(0, 8 - len(dealer_hand)))

                print(f"Weight Audit:")
                print(f"  Player Give: {w_p_give} (Expected: {expected_w_p_give})")
                print(f"  Player Keep: {w_p_keep} (Expected: {expected_w_p_keep})")
                print(f"  Dealer Give (Gets card): {w_d_give} (Expected: {expected_w_d_give})")
                print(f"  Dealer Keep (No card): {w_d_keep} (Expected: {expected_w_d_keep})")
                
                if w_d_give < expected_w_d_give or w_d_keep < expected_w_d_keep:
                    print("--> [FLAG] DEALER WEIGHT MISMATCH! Multiset rejection bug suspected.")
                if w_p_give < expected_w_p_give or w_p_keep < expected_w_p_keep:
                    print("--> [FLAG] PLAYER WEIGHT MISMATCH! Multiset rejection bug suspected.")

            if v3_action == "KEEP":
                if len(player_hand) < 5:
                    player_hand.append(current_card)
                else:
                    dealer_hand.append(current_card)
            else:
                if len(dealer_hand) < 8:
                    dealer_hand.append(current_card)
                else:
                    player_hand.append(current_card)

if __name__ == "__main__":
    run_comparison(50)
