import pytest
from app.core.game import GameState
from app.evaluators.evaluator import determine_winner

@pytest.fixture
def game():
    return GameState()

# Helper functions
def game_start_test(game):
    assert game.current_card is not None
    assert len(game.player_hand) == 0
    assert len(game.dealer_hand) == 0
    assert len(game.deck) == 51
    assert game.is_game_over == False

def game_end_test(game):
    assert game.is_game_over == True
    assert len(game.player_hand) == 5
    assert len(game.dealer_hand) >= 8

    winner = determine_winner(game.player_hand, game.dealer_hand)
    assert winner in ['player', 'dealer']


def test_all_keep(game):
    game_start_test(game)
    keeps = 0
    
    while not game.is_game_over:
        if keeps < 5:
            game.keep()
            keeps += 1
        else:
            break

    game_end_test(game)

def test_all_give(game):
    game_start_test(game)
    gives = 0
    
    for _ in range(47):
        game.give()
        gives += 1

    # should raise error when trying to give with insufficient cards left
    with pytest.raises(ValueError):
        game.give()

    for _ in range(5):
        game.keep()

    game_end_test(game)

def test_5_keeps_8_gives(game):
    game_start_test(game)
    for _ in range(4):
        game.keep()
    for _ in range(8):
        game.give()
    game.keep()
    game_end_test(game)

def test_5_keeps_less_than_8_gives(game):
    game_start_test(game)
    for _ in range(4):
        game.keep()
    for _ in range(4): # less than 8 gives
        game.give()
    game.keep()
    game_end_test(game)

def test_5_keeps_more_than_8_gives(game):
    game_start_test(game)
    for _ in range(4):
        game.keep()
    for _ in range(12):
        game.give()
    game.keep()
    game_end_test(game)


def test_evaluation_error_handling():
    with pytest.raises(ValueError, match="exactly 5 cards"):
        determine_winner(['Ah', 'Kh', 'Qh', 'Jh'], ['2s', '3s', '4s', '5s', '6s', '7s', '8s', '9s'])
    
    with pytest.raises(ValueError, match="at least 8 cards"):
        determine_winner(['Ah', 'Kh', 'Qh', 'Jh', 'Th'], ['2s', '3s', '4s', '5s', '6s', '7s', '8s'])
    
    with pytest.raises(ValueError, match="Duplicate cards detected between player and dealer hands."):
        determine_winner(['Ah', 'Kh', 'Qh', 'Jh', 'Th'], ['Ah', '2s', '3s', '4s', '5s', '6s', '7s', '8s'])

def test_evaluation_1():
    player_hand = ['Ah', 'Kh', 'Qh', 'Jh', 'Th'] # royal flush
    dealer_hand = ['2s', '2c', '3d', '4d', '5d', '7c', '8c', '9s'] # pair of 2s

    winner = determine_winner(player_hand, dealer_hand)
    assert winner == 'player'

def test_evaluation_2():
    player_hand = ['2h', '4d', '6s', '8c', 'Th'] # high card
    dealer_hand = ['As', 'Ac', 'Ad', 'Ks', 'Kc', '7c', '8s', '9s'] # full house

    winner = determine_winner(player_hand, dealer_hand)
    assert winner == 'dealer'

def test_evaluation_3():
    # Straight flush vs 4-of-a-kind, dealer has 10 cards (more than 8)
    player_hand = ['8c', '9c', 'Tc', 'Jc', 'Qc']
    dealer_hand = ['Ah', 'As', 'Ac', 'Ad', '2c', '3c', '4c', '5c', '6c', '7h']
    assert determine_winner(player_hand, dealer_hand) == 'player'

def test_evaluation_4():
    # 4-of-a-kind vs Full house
    player_hand = ['9d', '9c', '9s', '9h', 'Ad']
    dealer_hand = ['8h', '8s', '8c', 'Kh', 'Ks', '2c', '3c', '4c']
    assert determine_winner(player_hand, dealer_hand) == 'player'

def test_evaluation_5():
    # Full house vs Full house (same combo type)
    player_hand = ['Qc', 'Qs', 'Qh', '9c', '9s']
    dealer_hand = ['Jc', 'Js', 'Jh', 'Tc', 'Ts', '2c', '3c', '4c']
    assert determine_winner(player_hand, dealer_hand) == 'player'

def test_evaluation_6():
    # Flush vs Straight
    player_hand = ['2s', '4s', '6s', '8s', 'Ts']
    dealer_hand = ['5d', '6h', '7c', '8h', '9d', '2c', 'Kc', 'Ah']
    assert determine_winner(player_hand, dealer_hand) == 'player'

def test_evaluation_7():
    # Straight vs Three of a kind
    player_hand = ['5h', '6s', '7d', '8c', '9h']
    dealer_hand = ['Jd', 'Js', 'Jc', '2h', '4c', 'Ah', 'Kh', 'Qh']
    assert determine_winner(player_hand, dealer_hand) == 'player'

def test_evaluation_8():
    # Three of a kind vs Two pair
    player_hand = ['4s', '4c', '4h', 'Th', 'Jd']
    dealer_hand = ['As', 'Ac', 'Ks', 'Kc', '7h', '8d', '9c', '2s']
    assert determine_winner(player_hand, dealer_hand) == 'player'

def test_evaluation_9():
    # Two pair vs Pair
    player_hand = ['Th', 'Tc', '9h', '9c', 'As']
    dealer_hand = ['Kh', 'Ks', '2h', '3h', '4h', '5c', '7d', '8s']
    assert determine_winner(player_hand, dealer_hand) == 'player'

def test_evaluation_10():
    # Tie (same straights)
    player_hand = ['2h', '3h', '4h', '5h', '6s']
    dealer_hand = ['2d', '3d', '4d', '5d', '6c', '9s', 'Ts', 'Js']
    assert determine_winner(player_hand, dealer_hand) == 'dealer'
