import itertools
from treys import Card, Evaluator

def determine_winner(player_hand, dealer_hand):
    evaluator = Evaluator()
    
    # Convert '7H' (my game format) to '7h' (Treys format)
    def to_treys(card_str):
        rank = card_str[0]
        suit = card_str[1].lower()
        return Card.new(f"{rank}{suit}")

    treys_player = [to_treys(c) for c in player_hand]
    treys_dealer = [to_treys(c) for c in dealer_hand]

    # Evaluate the player's exactly 5-card hand
    player_score = evaluator.evaluate(treys_player, [])
    
    # The dealer has 8+ cards, but Treys evaluates max 7 cards natively.
    # Therefore, we generate all 5-card combinations for the dealer and find the best (lowest score).
    best_dealer_score = float('inf')
    for combo in itertools.combinations(treys_dealer, 5):
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
