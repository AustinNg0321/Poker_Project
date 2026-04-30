from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
import sys
import os

# Add the parent directory to sys.path to allow importing from backend modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.data.guest_games import Base, GuestGame, GameResponse, GameAction
from backend.app.core.game import GameState
from backend.app.evaluators.evaluator import determine_winner

# Database Setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./pokergame.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)

app = FastAPI()

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
def read_root():
    return {"status": "ok"}

@app.post("/new_game/{user_id}", response_model=GameResponse)
def new_game(user_id: str, db: Session = Depends(get_db)):
    game = db.query(GuestGame).filter(GuestGame.user_id == user_id).first()
    if not game:
        game = GuestGame(user_id=user_id)
        db.add(game)
    else:
        # Mark as abandoned if ongoing
        if game.deck and len(game.player_hand) < 5:
             game.abandoned += 1

    # Initialize new game state
    new_state = GameState()
    game.deck = new_state.deck
    game.player_hand = new_state.player_hand
    game.dealer_hand = new_state.dealer_hand
    game.current_card = new_state.current_card
    
    db.commit()
    db.refresh(game)
    return game

@app.post("/action/{user_id}", response_model=GameResponse)
def play_action(user_id: str, action_data: GameAction, db: Session = Depends(get_db)):
    game = db.query(GuestGame).filter(GuestGame.user_id == user_id).first()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found for this user")
    
    if not game.deck and not game.current_card:
         raise HTTPException(status_code=400, detail="Game is over. Start a new game.")
    
    # Reconstruct game state
    state = GameState()
    state.deck = game.deck
    state.player_hand = game.player_hand
    state.dealer_hand = game.dealer_hand
    state.current_card = game.current_card
    state.is_game_over = False if game.current_card else True
    
    try:
        if action_data.action.lower() == "keep":
            state.keep()
        elif action_data.action.lower() == "give":
            state.give()
        else:
            raise HTTPException(status_code=400, detail="Invalid action. Use 'keep' or 'give'.")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    # Save state back
    game.deck = state.deck
    game.player_hand = state.player_hand
    game.dealer_hand = state.dealer_hand
    game.current_card = state.current_card
    
    if getattr(state, 'is_game_over', False) or len(state.player_hand) == 5:
        # Determine winner if game is over
        if len(state.dealer_hand) >= 8:
            winner = determine_winner(state.player_hand, state.dealer_hand)
            if winner == 'player':
                game.wins += 1
            elif winner == 'dealer':
                game.losses += 1
            # ties leave it alone
    
    db.commit()
    db.refresh(game)
    return game

@app.get("/game/{user_id}", response_model=GameResponse)
def get_game(user_id: str, db: Session = Depends(get_db)):
    game = db.query(GuestGame).filter(GuestGame.user_id == user_id).first()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    return game

@app.get("/results/{user_id}")
def get_results(user_id: str, db: Session = Depends(get_db)):
    game = db.query(GuestGame).filter(GuestGame.user_id == user_id).first()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    # Basic check if game is over
    if len(game.player_hand) < 5 and game.current_card is not None:
        return {"status": "ongoing", "message": "Game is still ongoing"}
        
    try:
        winner = determine_winner(game.player_hand, game.dealer_hand)
        return {
            "status": "completed",
            "winner": winner,
            "player_hand": game.player_hand,
            "dealer_hand": game.dealer_hand,
            "wins": game.wins,
            "losses": game.losses,
            "abandoned": game.abandoned
        }
    except Exception as e:
         return {"status": "error", "message": str(e)}
