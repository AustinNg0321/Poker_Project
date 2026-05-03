# Poker_Project

## The Game
A niche poker variant played against a dealer requiring strategic card "drafting."

### Rules
*   **Deck:** Single 52-card deck, dealt face-up one at a time.
*   **Player Decision:** For each card, decide to **keep** for yourself or **give** to the dealer.
*   **End Condition:** Game ends when the player keeps exactly **5 cards**.
*   **Dealer Rules:** The dealer receives all rejected cards. If the dealer has fewer than 8 cards at the end, they draw from the deck until they hit 8.
*   **Showdown:** Standard poker rankings. Dealer uses their best 5-card combination from their accumulated pool.
*   **Outcome:** Pure Win/Lose/Tie. (Current strategy treats ties as losses to optimize for a higher win-rate ceiling).

---

## Technical Architecture: The "Manual" ML Approach

This project avoids "black-box" machine learning libraries in favor of a first-principles **Policy Iteration** loop. This demonstrates a deep understanding of how optimization and heuristic modeling work under the hood.

### 1. Decomposed Analytical Utility Function
To resolve the "chicken-and-egg" problem of rollout policies, the decision engine evaluates moves using a weighted sum of three mathematical terms:
*   **Immediate Hand Strength:** The current ranking of the player's 5-card hand.
*   **Potential (Outs):** An analytically computed probability of completing high-value hands based on remaining "keeps" and deck composition.
*   **Denial Utility (Dealer Threat):** A defensive term that penalizes discarding cards that significantly improve the dealer's visible state (e.g., blocking a potential flush).

### 2. Iterative Policy Refinement
The bot's intelligence is improved through a self-referential training loop:
*   **v0 (Baseline):** Naive random rollouts (Expected Win Rate: ~25%).
*   **v1-v10 (Recursive Improvement):** Using the strategy from iteration $n$ as the rollout policy for iteration $n+1$. This allows the bot to "anticipate" smarter future decisions during Monte Carlo trials.
*   **M LOps & Experiment Tracking:** Every training run is exported via **Pandas** to structured CSVs in a dedicated `/experiments` folder, tracking win-rate convergence against hyperparameter weights ($w_1, w_2, w_3$).

---

## Tech Stack
*   **Backend:** Python (FastAPI, Pandas for experiment logging).
*   **Frontend:** React + Vite.
*   **Simulation:** Monte Carlo Tree Search (MCTS) principles with custom rollout policies.
*   **Data Persistence:** SQLite for game history; CSV for ML iteration logs.

---

## MVP Build Order

- [x] **1. Hand Evaluator:** Incremental checking with strict suit tracking.
- [x] **2. Game Logic:** Core state machine and "draw-as-loss" rule implementation.
- [ ] **3. ML Utility Engine:** Implementation of the Analytical Utility Function ($U_{keep}$).
- [ ] **4. Experiment Tracker:** Automated Pandas logging for Monte Carlo trial results.
- [ ] **5. FastAPI Routes:** Expose game actions and asynchronous hint logic.
- [ ] **6. React + Vite Frontend:** Playable UI for human-vs-bot benchmarking.

---

## Target File Structure
```text
Poker_Project/
├── backend/
│   ├── app/
│   │   ├── api/              # FastAPI route handlers
│   │   ├── core/             # Game objects (Deck, Card) and state machine
│   │   ├── evaluators/       # Incremental hand evaluation logic
│   │   ├── simulators/       # Monte Carlo trials & Utility functions
│   │   └── models/           # Database schemas and Pydantic models
│   ├── tests/                # Pytest suite (crucial for poker hand math)
|   ├── data/                 # CSV logs of game history and ML iterations  
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api/              # Fetch client
│   │   ├── components/       # UI (Card, Hand, Board)
│   │   └── App.jsx           # Main game view
│   └── vite.config.js
└── README.md