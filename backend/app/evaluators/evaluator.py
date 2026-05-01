import itertools
from treys import Card, Evaluator

evaluator = Evaluator()

# before converting to treys int format
def determine_winner(player_hand, dealer_hand):
    return determine_winner_helper(
        [Card.new(card) for card in player_hand],
        [Card.new(card) for card in dealer_hand]
    )

# treys format: 2h, 3d, 4c, 5s, Th, Jd, Qc, Ks, Ah
# remember to convert it to treys int format before calling
def determine_winner_helper(player_hand, dealer_hand):
    if len(player_hand) != 5:
        raise ValueError("Player must have exactly 5 cards.")
    if len(dealer_hand) < 8:
        raise ValueError("Dealer must have at least 8 cards.")
    if len(set(player_hand + dealer_hand)) != len(player_hand) + len(dealer_hand): 
        raise ValueError("Duplicate cards detected between player and dealer hands.")

    # Evaluate the player's exactly 5-card hand
    player_score = evaluator.evaluate(player_hand, [])
    
    # The dealer has 8+ cards, but Treys evaluates max 7 cards natively.
    # Therefore, we generate all 5-card combinations for the dealer and find the best (lowest score).
    best_dealer_score = 10000 # the max for treys is 7462
    for combo in itertools.combinations(dealer_hand, 5):
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
