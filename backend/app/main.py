from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from dotenv import load_dotenv
import sys
import os
import uuid

# Add the parent directory to sys.path to allow importing from backend modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.app.models.guest_games import Base, GuestGame, GameResponse, GameAction, ResultResponse
from backend.app.core.game import GameState
from backend.app.evaluators.evaluator import determine_winner

# Database Setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./pokergame.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"], # Update with your frontend URL
    allow_credentials=True, # Required for cookies/sessions
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add Session Middleware for signed cookies
load_dotenv()
app.add_middleware(SessionMiddleware, secret_key=os.getenv("SESSION_SECRET_KEY"))

# create a game only when a user presses "start game" or similar
def get_or_create_player(user_id: str, db: Session):
    player = db.query(GuestGame).filter(GuestGame.user_id == user_id).first()
    if not player:
        player = GuestGame(user_id=user_id)
        db.add(player)
        db.commit()

# determine if the user has initialized any game
def is_game_started(game: GuestGame):
    return game and (len(game.player_hand) > 0 or len(game.dealer_hand) > 0 or
                      len(game.deck) > 0 or game.current_card is not None)

# determine game progress solely with game info
# no game -> false
def is_game_over(game: GuestGame):
    if game and not is_game_valid(game):
        raise HTTPException(status_code=400, detail="Game is invalid.")
    return game and len(game.player_hand) == 5

def is_game_valid(game: GuestGame):
    if not game or not is_game_started(game):
        return False
    if len(game.player_hand) > 5:
        return False
    if len(game.player_hand) == 5 and len(game.dealer_hand) < 8:
        return False
    if len(game.player_hand) < 5 and not game.current_card:
        return False
    return True

# Dependencies
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_session_id(request: Request):
    if "session_id" not in request.session:
        request.session["session_id"] = str(uuid.uuid4())
    return request.session["session_id"]

@app.get("/")
def read_root():
    return {"status": "ok"}

# New Session-based endpoint
@app.post("/game/new", response_model=GameResponse)
def create_new_game(db: Session = Depends(get_db), user_id: str = Depends(get_session_id)):
    get_or_create_player(user_id, db)
    
    # Treat session_id as user_id for GuestGame
    game = db.query(GuestGame).filter(GuestGame.user_id == user_id).first()
    if is_game_started(game) and not is_game_over(game):
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

@app.post("/action", response_model=GameResponse)
def play_action(action_data: GameAction, db: Session = Depends(get_db), user_id: str = Depends(get_session_id)):
    game = db.query(GuestGame).filter(GuestGame.user_id == user_id).first()
    if not game or not is_game_started(game):
        raise HTTPException(status_code=404, detail="Game not found for this user")
    if not is_game_valid(game):
        raise HTTPException(status_code=400, detail="Game is invalid.")
    
    state = GameState()
    state.deck = game.deck
    state.player_hand = game.player_hand
    state.dealer_hand = game.dealer_hand
    state.current_card = game.current_card
    state.is_game_over = is_game_over(game)

    if state.is_game_over:
        raise HTTPException(status_code=400, detail="Game is over. Start a new game.")

    try:
        if action_data.action == "keep":
            state.keep()
        else:
            state.give()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    # Save state back
    game.deck = state.deck
    game.player_hand = state.player_hand
    game.dealer_hand = state.dealer_hand
    game.current_card = state.current_card
    
    if is_game_over(game):
        winner = determine_winner(state.player_hand, state.dealer_hand)
        if winner == 'player':
            game.wins += 1
        elif winner == 'dealer':
            game.losses += 1
    
    db.commit()
    db.refresh(game)
    return game

@app.get("/game", response_model=GameResponse)
def get_game(db: Session = Depends(get_db), user_id: str = Depends(get_session_id)):
    game = db.query(GuestGame).filter(GuestGame.user_id == user_id).first()
    if not game or not is_game_started(game):
        raise HTTPException(status_code=404, detail="Game not found")
    return game

@app.get("/results", response_model=ResultResponse)
def get_results(db: Session = Depends(get_db), user_id: str = Depends(get_session_id)):
    game = db.query(GuestGame).filter(GuestGame.user_id == user_id).first()
    if not game or not is_game_started(game):
        raise HTTPException(status_code=404, detail="Game not found")
    if not is_game_over(game):
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
        raise HTTPException(status_code=500, detail=str(e))
