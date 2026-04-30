import itertools
from treys import Card, Evaluator

# treys format: 2h, 3d, 4c, 5s, Th, Jd, Qc, Ks, Ah
# card representation from game.py is consistent with
def determine_winner(player_hand, dealer_hand):
    if len(player_hand) != 5:
        raise ValueError("Player must have exactly 5 cards.")
    if len(dealer_hand) < 8:
        raise ValueError("Dealer must have at least 8 cards.")
    if len(set(player_hand + dealer_hand)) != len(player_hand) + len(dealer_hand): 
        raise ValueError("Duplicate cards detected between player and dealer hands.")

    evaluator = Evaluator()

    treys_player_hand = [Card.new(card) for card in player_hand]
    treys_dealer_hand = [Card.new(card) for card in dealer_hand]

    # Evaluate the player's exactly 5-card hand
    player_score = evaluator.evaluate(treys_player_hand, [])
    
    # The dealer has 8+ cards, but Treys evaluates max 7 cards natively.
    # Therefore, we generate all 5-card combinations for the dealer and find the best (lowest score).
    best_dealer_score = float('inf')
    for combo in itertools.combinations(treys_dealer_hand, 5):
        score = evaluator.evaluate(list(combo), [])
        if score < best_dealer_score:
            best_dealer_score = score

    # In Treys, a lower score indicates a stronger poker hand
    if player_score < best_dealer_score:
        return 'player'
    elif best_dealer_score < player_score:
        return 'dealer'
    else:
        return 'tie'
