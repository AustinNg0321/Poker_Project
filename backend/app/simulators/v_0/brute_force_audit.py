import itertools
import math
import sys
import os
from treys import Card

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from app.evaluators.evaluator import get_best_score, FULL_DECK
from app.simulators.v_0.v_0_3_logic import build_bitmasks
from app.simulators.v_0.perfect_evaluator_8 import evaluate_dealer_deterministic

def debug_brute_force(hand, available_cards, needed):
    total_rank = 0
    count = 0
    # Warning: 5 cards from ~44 cards is ~1,086,008 combinations. 
    # Takes a few seconds in pure Python.
    for combo in itertools.combinations(available_cards, needed):
        eval_hand = hand + list(combo)
        rank = get_best_score(eval_hand)
        total_rank += rank
        count += 1
    return total_rank / count if count > 0 else 0, count

def run_audit():
    # Setup test scenario: Dealer holds 3 cards, needing 5 more to reach 8.
    dealer_hand = [Card.new('Ah'), Card.new('Kh'), Card.new('Qh')]
    player_hand = [Card.new('2s'), Card.new('3c'), Card.new('4d')] # Mocking dead cards
    all_dead = dealer_hand + player_hand
    
    available_cards = [c for c in FULL_DECK if c not in all_dead]
    cards_needed = 8 - len(dealer_hand)
    expected_combinations = math.comb(len(available_cards), cards_needed)
    
    # 1. Run Numba Evaluator
    hb, hrc, avail_set, rem_rc = build_bitmasks(dealer_hand, all_dead)
    numba_ev = evaluate_dealer_deterministic(dealer_hand, hb, hrc, avail_set, rem_rc)
    
    # 2. Run Brute Force
    print(f"Running brute force on {expected_combinations} combinations...")
    bf_ev, bf_count = debug_brute_force(dealer_hand, available_cards, cards_needed)
    
    print("\n--- FIRST PRINCIPLES AUDIT ---")
    print(f"Expected Combos: {expected_combinations}")
    print(f"Brute Force EV:  {bf_ev} (over {bf_count} combos)")
    print(f"Numba Engine EV: {numba_ev}")
    
    diff = abs(bf_ev - numba_ev)
    print(f"Difference:      {diff}")
    if diff > 0.01:
        print("❌ BUG DETECTED: The Numba engine EV does not match true mathematical EV.")
    else:
        print("✅ PASS: The Numba evaluator mathematically matches brute force.")

if __name__ == "__main__":
    run_audit()