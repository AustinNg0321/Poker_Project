# Poker_Project

## The Game

A niche poker variant played against a dealer.

### Rules

- **Deck:** Single 52-card deck, dealt face-up one at a time. Suits matter.
- **Player Decision:** For each card, the player decides to **keep** or **give** to the dealer.
- **End Condition (Player):** The game ends when the player keeps exactly **5 cards**.
- **End Condition (Dealer):** The dealer gets all rejected cards. When the player finishes, if the dealer has < 8 cards, they draw until they have 8. (Keeps all if 8+).
- **Showdown:** The dealer picks their best 5-card hand from all accumulated cards.
- **Visibility:** The player can see the dealer's cards accumulating.
- **Outcome:** Pure win/lose/tie based on standard poker hand rankings. No betting.

---

## Technical Decisions & Hint System

### The Hint System & Logic

- **Monte Carlo Simulation:** Full brute force of game states is infeasible (~10²¹). Monte Carlo simulations estimate win probabilities.
- **Asynchronous Feel:** When a card is dealt, a Monte Carlo run triggers asynchronously. If the player clicks "Hint", the result returns instantly.
- **Incremental Hand Evaluation:** When a card is added, the evaluator only checks the new `C(N-1, 4)` combinations involving that card, rather than fully recalculating `C(N,5)` from scratch.

---

## Tech Stack

- **Backend:** Python + FastAPI
- **Frontend:** React + Vite
- **Database:** SQLite (initially) → Postgres (later)
- **Auth:** JWT (username/password)

---

## MVP Build Order (TODOs)

Goal: Get the core game fully playable first before touching auth, hints, or ML.

- [ ] **1. Hand Evaluator:** Python, pure logic (incremental checking, strict suit tracking).
- [ ] **2. Game State & Simulator:** Core loop and Monte Carlo shell.
- [ ] **3. FastAPI Routes:** Expose game actions via API.
- [ ] **4. React + Vite Frontend:** Playable UI.
- [ ] **5. Persistence (Later):** SQLite + JWT Auth + Game History.
- [ ] **6. Hint System (Later):** Utility function + Monte Carlo background tasks.
- [ ] **7. ML Pipeline (Stretch):** Future heuristic modeling.

---

## Target File Structure

```text
Poker_Project/
├── backend/
│   ├── app/
│   │   ├── api/              # FastAPI route handlers
│   │   ├── core/             # Game objects (Deck, Card) and state machine
│   │   ├── evaluators/       # Incremental hand evaluation logic
│   │   ├── models/           # Pydantic data validation models
│   │   ├── simulators/       # Monte Carlo hint system (Future)
│   │   └── main.py           # FastAPI entry point
│   ├── tests/                # Pytest suit (crucial for poker hand math!)
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api/              # Axios/Fetch client for backend communication
│   │   ├── components/       # UI components (Card, Hand, Board)
│   │   ├── hooks/            # Game state management (e.g., useGame)
│   │   ├── App.jsx           # Main game view
│   │   └── main.jsx          # React entry point
│   ├── package.json
│   └── vite.config.js
└── README.md
```
