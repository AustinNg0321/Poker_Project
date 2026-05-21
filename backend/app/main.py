from fastapi import FastAPI, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
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
    allow_origins=[FRONTEND_URL] if FRONTEND_URL else ["*"],
    allow_credentials=True,  # Required for cookies/sessions
    allow_methods=["*"],
    allow_headers=["*"],
)

# Instead of ProxyHeadersMiddleware, handle Railway's X-Forwarded-Proto manually so FastAPI sees HTTPS.
@app.middleware("http")
async def trust_proxy_headers(request: Request, call_next):
    # This manually handles the headers provided by Railway's load balancer
    if request.headers.get("X-Forwarded-Proto", "").lower() == "https":
        request.scope["scheme"] = "https"
    return await call_next(request)

# Add Session Middleware for signed cookies (do NOT pass secure/samesite args for older Starlette)
app.add_middleware(SessionMiddleware, secret_key=os.getenv("SESSION_SECRET_KEY"))

# Middleware to ensure Set-Cookie headers include SameSite=None and Secure when missing.
# This is a broad fallback for older Starlette versions that reject secure/samesite in constructor.
class SessionCookieAttributeMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, same_site: str = "None", secure: bool = True):
        super().__init__(app)
        self.same_site = same_site
        self.secure = secure

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # Rebuild raw_headers: for every Set-Cookie header ensure SameSite and Secure added if missing
        new_headers = []
        for name, value in response.raw_headers:
            if name.lower() == b"set-cookie":
                val = value.decode()
                lower = val.lower()
                if "samesite" not in lower:
                    val += f"; SameSite={self.same_site}"
                if self.secure and "secure" not in lower:
                    val += "; Secure"
                new_headers.append((name, val.encode()))
            else:
                new_headers.append((name, value))
        response.raw_headers = new_headers
        return response

app.add_middleware(SessionCookieAttributeMiddleware, same_site="None", secure=True)

def _read_session_id_from_request(request: Request) -> Optional[str]:
    # Prefer session dict value set by SessionMiddleware
    try:
        sid = request.session.get("session_id")
        if sid:
            return sid
    except Exception:
        pass
    # Fallback to dedicated cookie (we set this in get_session_id)
    return request.cookies.get(os.getenv("SESSION_COOKIE_NAME", "session_id"))

# Dependency used by routes and by the rate limiter key_func.
# Response is optional so Limiter (which calls with only request) still works.
def get_session_id(request: Request, response: Optional[Response] = None) -> str:
    """
    Ensure a stable session identifier:
    - Prefer request.session["session_id"]
    - Fall back to a dedicated cookie 'session_id' stored on the client (SameSite=None; Secure)
    - If none exists, create a new id and persist it both into request.session and into a cookie (when Response available)
    """
    cookie_name = os.getenv("SESSION_COOKIE_NAME", "session_id")
    # Try session store
    try:
        sid = request.session.get("session_id")
    except Exception:
        sid = None

    if sid:
        # Ensure we also emit a simple cross-site cookie for browsers that won't include the signed session cookie
        if response is not None and cookie_name not in request.cookies:
            try:
                response.set_cookie(
                    key=cookie_name,
                    value=sid,
                    httponly=True,
                    secure=True,
                    samesite="None",
                    path="/",
                    max_age=30 * 24 * 3600,
                )
            except TypeError:
                # Older Starlette may not accept samesite kw; append raw header
                cookie_val = f"{cookie_name}={sid}; Path=/; Max-Age={30*24*3600}; HttpOnly; Secure; SameSite=None"
                if hasattr(response.headers, "append"):
                    response.headers.append("set-cookie", cookie_val)
                else:
                    response.headers["set-cookie"] = cookie_val
        return sid

    # Check fallback cookie
    sid = request.cookies.get(cookie_name)
    if sid:
        # Populate session so application code using request.session works
        try:
            request.session["session_id"] = sid
        except Exception:
            pass
        return sid

    # Create new session id
    sid = str(uuid.uuid4())
    try:
        request.session["session_id"] = sid
    except Exception:
        pass

    if response is not None:
        try:
            response.set_cookie(
                key=cookie_name,
                value=sid,
                httponly=True,
                secure=True,
                samesite="None",
                path="/",
                max_age=30 * 24 * 3600,
            )
        except TypeError:
            cookie_val = f"{cookie_name}={sid}; Path=/; Max-Age={30*24*3600}; HttpOnly; Secure; SameSite=None"
            if hasattr(response.headers, "append"):
                response.headers.append("set-cookie", cookie_val)
            else:
                response.headers["set-cookie"] = cookie_val

    return sid

# Global Exception Handlers
logger = logging.getLogger(__name__)
limiter = Limiter(key_func=lambda request: _read_session_id_from_request(request) or str(request.client.host))
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected server error occurred. Please try again later."}
    )

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    logger.info(f"HTTP error {exc.status_code}: {exc.detail} - path={request.url.path}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )

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

# Define this at the top
def get_response(response: Response = Depends()):
    return response

# Endpoints
@app.post("/game/new", response_model=GameResponse)
@limiter.limit("10/minute")
def create_new_game(
    request: Request,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_session_id),
    response: Response = Depends(get_response),  # avoid Pydantic introspection by providing a default
):
    # Ensure player exists
    get_or_create_player(user_id, db)

    try:
        game = db.query(GuestGame).filter(GuestGame.user_id == user_id).with_for_update().first()
    except OperationalError:
        game = db.query(GuestGame).filter(GuestGame.user_id == user_id).first()

    if is_game_started(game) and not is_game_over(game):
        raise HTTPException(status_code=400, detail="Cannot start a new game while one is in progress.")

    new_state = GameState()
    game.deck = new_state.deck
    game.player_hand = new_state.player_hand
    game.dealer_hand = new_state.dealer_hand
    game.current_card = new_state.current_card

    db.commit()
    db.refresh(game)
    return game

@app.post("/action", response_model=GameResponse)
@limiter.limit("2/second")
def play_action(
    request: Request,
    action_data: GameAction,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_session_id),
    response: Response = None,  # avoid Pydantic introspection by providing a default
):
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

# Debug endpoint to inspect cookies/session (useful in prod to check if browser is sending cookie)
@app.get("/_debug/session")
def debug_session(request: Request):
    cookie_name = os.getenv("SESSION_COOKIE_NAME", "session_id")
    return {
        "cookies_header": request.headers.get("cookie"),
        "cookie_sent": bool(request.cookies.get(cookie_name)),
        "cookie_value": request.cookies.get(cookie_name),
        "session_obj": dict(request.session) if hasattr(request, "session") else None,
    }

# Utility functions used above (defined here for completeness)
def get_or_create_player(user_id: str, db: Session):
    player = db.query(GuestGame).filter(GuestGame.user_id == user_id).first()
    if not player:
        player = GuestGame(user_id=user_id)
        db.add(player)
        db.commit()

def is_game_started(game: GuestGame):
    return game and (len(game.player_hand) > 0 or len(game.dealer_hand) > 0 or
                     len(game.deck) > 0 or game.current_card is not None)

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