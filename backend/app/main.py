from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import OperationalError
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from dotenv import load_dotenv
from typing import Optional
import sys
import os
import uuid
import logging

# Add the parent directory to sys.path to allow importing from backend modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.models.guest_games import Base, GuestGame, GameResponse, GameAction, ResultResponse, HintResponse
from app.core.game import GameState
from app.evaluators.evaluator import determine_winner
from app.simulators.v_1.v_1_0_logic import calculate_move_delta
from treys import Card

load_dotenv()

# Database Setup
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(
    DATABASE_URL, 
    # check_same_thread is only needed for SQLite
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)

app = FastAPI()
app.router.redirect_slashes = False

FRONTEND_URL = os.getenv("FRONTEND_URL")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL], # Update with your frontend URL
    allow_credentials=True, # Required for cookies/sessions
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add Session Middleware for signed cookies
app.add_middleware(SessionMiddleware, secret_key=os.getenv("SESSION_SECRET_KEY"))

def get_session_id(request: Request):
    if "session_id" not in request.session:
        request.session["session_id"] = str(uuid.uuid4())
    return request.session["session_id"]

# Global Exception Handlers
logger = logging.getLogger(__name__)
limiter = Limiter(key_func=get_session_id)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# 1. Catch-all for unexpected server errors (500)
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected server error occurred. Please try again later."}
    )

# 2. Standardize expected HTTP exceptions (e.g., 400, 404)
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    logger.info(f"HTTP error {exc.status_code}: {exc.detail} - path={request.url.path}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )

# 3. Clean up Pydantic validation errors (422)
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.info(f"Validation error on {request.url.path}: {exc.errors()}")
    return JSONResponse(
        status_code=422,
        content={
            "detail": "Request validation failed.",
            "errors": exc.errors()
        },
    )

@app.exception_handler(RateLimitExceeded)
async def rate_limit_exception_handler(request: Request, exc: RateLimitExceeded):
    logger.warning(f"Rate limit breached by {request.client.host}")
    return JSONResponse(
        status_code=429,
        content={"detail": "Too many requests! Please try again in a moment."}
    )


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

@app.get("/")
def read_root():
    return {"status": "ok"}

# New Session-based endpoint
@app.post("/game/new", response_model=GameResponse)
@limiter.limit("10/minute")
def create_new_game(request: Request, db: Session = Depends(get_db), user_id: str = Depends(get_session_id)):
    get_or_create_player(user_id, db)
    
    try:
        game = db.query(GuestGame).filter(GuestGame.user_id == user_id).with_for_update().first()  # <-- CHANGED
    except OperationalError:
        game = db.query(GuestGame).filter(GuestGame.user_id == user_id).first()  # <-- CHANGED (SQLite Fallback)

    if is_game_started(game) and not is_game_over(game):
        raise HTTPException(status_code=400, detail="Cannot start a new game while one is in progress.")

    # Initialize new game state
    new_state = GameState()
    game.deck = new_state.deck
    game.player_hand = new_state.player_hand
    game.dealer_hand = new_state.dealer_hand
    game.current_card = new_state.current_card
    
    db.commit()
    db.refresh(game)
    return game # deck will be filtered out by response model

@app.post("/action", response_model=GameResponse)
@limiter.limit("2/second")
def play_action(request: Request, action_data: GameAction, db: Session = Depends(get_db), user_id: str = Depends(get_session_id)):
    try:
        game = db.query(GuestGame).filter(GuestGame.user_id == user_id).with_for_update().first()
    except OperationalError:
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
    return game # deck will be filtered out by response model

@app.get("/game", response_model=Optional[GameResponse])
@limiter.limit("60/minute")
def get_game(request: Request, db: Session = Depends(get_db), user_id: str = Depends(get_session_id)):
    game = db.query(GuestGame).filter(GuestGame.user_id == user_id).first()
    if not game or not is_game_started(game):
        return None
    return game

@app.get("/hint", response_model=HintResponse)
@limiter.limit("30/minute")
def get_hint(request: Request, db: Session = Depends(get_db), user_id: str = Depends(get_session_id)):
    game = db.query(GuestGame).filter(GuestGame.user_id == user_id).first()
    if not game or not is_game_started(game):
        raise HTTPException(status_code=404, detail="Game not found")
    if is_game_over(game):
        raise HTTPException(status_code=400, detail="Game is over.")
    if not game.current_card:
        raise HTTPException(status_code=400, detail="No current card to make a decision on.")

    player_hand_treys = [Card.new(c) for c in game.player_hand]
    dealer_hand_treys = [Card.new(c) for c in game.dealer_hand]
    current_card_treys = Card.new(game.current_card)

    results = calculate_move_delta(player_hand_treys, dealer_hand_treys, current_card_treys)
    
    keep_utility = results["keep_utility"]
    give_utility = results["give_utility"]

    return {
        "action": "keep" if keep_utility >= give_utility else "give",
        "keep_delta": keep_utility,
        "give_delta": give_utility
    }

@app.get("/results", response_model=ResultResponse)
@limiter.limit("20/minute")
def get_results(request: Request, db: Session = Depends(get_db), user_id: str = Depends(get_session_id)):
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
            "losses": game.losses
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
