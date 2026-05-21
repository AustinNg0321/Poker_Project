import json
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Literal

from sqlalchemy import Column, String, Integer, DateTime
from sqlalchemy.ext.declarative import declarative_base
from pydantic import BaseModel, Field

Base = declarative_base()

# Draws count as losses
class GuestGame(Base):
    __tablename__ = 'guest_games'

    user_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    _player_hand = Column("player_hand", String, default="[]")
    _dealer_hand = Column("dealer_hand", String, default="[]")
    _deck = Column("deck", String, default="[]")
    current_card = Column(String, nullable=True)
    wins = Column(Integer, default=0)
    losses = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    @property
    def player_hand(self):
        return json.loads(self._player_hand)

    @player_hand.setter
    def player_hand(self, value):
        self._player_hand = json.dumps(value)

    @property
    def dealer_hand(self):
        return json.loads(self._dealer_hand)

    @dealer_hand.setter
    def dealer_hand(self, value):
        self._dealer_hand = json.dumps(value)

    @property
    def deck(self):
        return json.loads(self._deck)

    @deck.setter
    def deck(self, value):
        self._deck = json.dumps(value)

# Pydantic Schemas
class GameBase(BaseModel):
    user_id: str
    current_card: Optional[str] = None
    wins: int = 0
    losses: int = 0

class GameCreate(BaseModel):
    pass

class GameAction(BaseModel):
    action: Literal["keep", "give"]

class GameResponse(GameBase):
    player_hand: List[str]
    dealer_hand: List[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class HintResponse(BaseModel):
    action: str
    keep_delta: float
    give_delta: float

class ResultResponse(BaseModel):
    status: str
    message: Optional[str] = None
    winner: Optional[str] = None
    player_hand: Optional[List[str]] = None
    dealer_hand: Optional[List[str]] = None
    wins: Optional[int] = None
    losses: Optional[int] = None
