import random

class GameState:
    def __init__(self):
        self.deck = self._initialize_deck()
        self.player_hand = []
        self.dealer_hand = []
        self.current_card = None
        self.is_game_over = False
        
        self._deal_next_card()

    def _initialize_deck(self):
        suits = ['h', 'd', 'c', 's']
        ranks = ['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A']
        deck = [f"{rank}{suit}" for suit in suits for rank in ranks]
        random.shuffle(deck)
        return deck

    def _deal_next_card(self):
        if self.deck and not self.is_game_over:
            self.current_card = self.deck.pop()
        else:
            self.current_card = None

    def keep(self):
        if self.is_game_over:
            raise ValueError("Game is already over.")
        if self.current_card is None:
            raise ValueError("No card to make a decision on.")
        
        self.player_hand.append(self.current_card)
        if len(self.player_hand) == 5 or not self.deck:
            self._finalize_game()
        else:
            self._deal_next_card()
    
    def give(self):
        if self.is_game_over:
            raise ValueError("Game is already over.")
        if self.current_card is None:
            raise ValueError("No card to make a decision on.")
        # also account for current card
        if len(self.player_hand) + len(self.deck) <= 4: 
            raise ValueError("Not enough cards left to give to the dealer.")
        
        self.dealer_hand.append(self.current_card)
        if len(self.player_hand) == 5 or not self.deck:
            self._finalize_game()
        else:
            self._deal_next_card()

    def _finalize_game(self):
        self.is_game_over = True
        self.current_card = None 
        
        # Dealer must have at least 8 cards
        while len(self.dealer_hand) < 8 and self.deck:
            self.dealer_hand.append(self.deck.pop())
