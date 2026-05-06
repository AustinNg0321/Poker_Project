import itertools
from treys import Card, Evaluator

evaluator = Evaluator()

SUITS = ['h', 'd', 'c', 's']
RANKS = ['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A']
FULL_DECK = [Card.new(f"{r}{s}") for s in SUITS for r in RANKS]

# Helper to find the best 5-card score for hands of 5+ cards.
# In Treys, a lower score indicates a stronger poker hand
def get_best_score(hand):
    return evaluator.evaluate(hand, []) if len(hand) == 5 else min(
        evaluator.evaluate(list(combo), []) 
        for combo in itertools.combinations(hand, 5))

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

    player_score = get_best_score(player_hand)
    best_dealer_score = get_best_score(dealer_hand)

    # Draws count as losses
    return "player" if player_score < best_dealer_score else "dealer"
