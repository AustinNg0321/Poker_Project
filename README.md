# Holdout — A Custom Poker Variant with an Analytical AI

**[Live Demo](https://poker-project-green.vercel.app/)** · **[Algorithm Notebook](notebook/Poker_Simulations.ipynb)**

Holdout is a custom single-player poker variant introduced to me by a quant at a math summer camp. The game's core mechanic — deciding whether to keep or give each card to the dealer — turns out to be a surprisingly deep stochastic optimization problem. This project documents the full journey from a naive Monte Carlo baseline to an exact analytical evaluator running at C-speed via Numba JIT compilation.

---

## The Game

Cards are dealt one at a time from a standard 52-card deck. For each card the player decides to **keep** it or **give** it to the dealer. The game ends when the player has kept exactly 5 cards. The dealer draws until it has at least 8 cards total, then picks its best 5-card hand. Standard poker rankings apply; ties go to the dealer.

The key insight that makes this interesting: with perfect information the player can always win (build the earliest royal flush and denying the rest to the dealer). With imperfect information the optimal win rate is strictly below 100%, and the gap between naive and optimal play is large — a keep-first-5 baseline achieves only ~15%.

---

## Algorithm Development

### The Core Utility Function

The blocking insight — introduced by the quant who taught me the game — is that every decision affects both hands simultaneously. Keeping a card improves your hand and denies it to the dealer; giving it away does the opposite. This leads naturally to a utility function:

```
utility(keep) = E[dealer_rank | keep] - E[player_rank | keep]
utility(give) = E[dealer_rank | give] - E[player_rank | give]
delta = utility(keep) - utility(give)
decision = keep if delta > 0 else give
```

Lower treys rank means a stronger hand, so higher utility means better expected outcome for the player. This delta logic is the foundation of every version.

---

### v0.1 — Pure Monte Carlo

Both expected values estimated via random rollout: sample random completions of each hand, evaluate, average. Simple but slow — ~900ms per game at 1,000 simulations per decision.

**Win rate: ~56% at 100 sims/decision, ~61.8% at 1,000 sims/decision**

---

### v0.2 — Hybrid: Exact Player + Monte Carlo Dealer

I realized the player's expected hand strength is exactly computable without simulation. The key observation: instead of sampling random card completions, enumerate all valid rank multisets and count how many ways each can be drawn from the remaining deck combinatorially.

A 52-card deck has only 6,175 valid 5-card rank multisets (accounting for the constraint of at most 4 of any rank). For each multiset, the number of ways to draw it from the remaining deck is a product of binomial coefficients — computable in microseconds. Suits are handled separately via a 13-bit flush lookup table (8,192 entries).

This is implemented in pure Python first, then JIT-compiled to C-speed via Numba. The dealer side remained Monte Carlo in this version.

**Win rate: ~58% at 100 sims/decision, ~62.5% at 1,000 sims/decision**

---

### v0.3 — Fully Deterministic: Exact Player + Exact Dealer

I initially assumed the dealer's 8-card evaluation would be intractable — the search space felt too large. After more thought, I realized the same multiset isomorphism argument applies: there are only ~120,000 valid 8-card rank multisets, and the combinatorial weight counting works identically.

The implementation was written, but subtle bugs made the results wrong in ways that weren't immediately obvious. After hours staring at the code, I wrote audit scripts comparing expected values against a brute-force reference implementation to isolate the discrepancy. One bug took several more hours — a single `==` that should have been `<=`. I stepped away, came back the next morning, and fixed it in under five minutes.

The bitmask representation encodes all 52 cards in a single 64-bit integer (4 bits per rank, one bit per suit within each nibble), enabling fast set operations throughout:

```
Layout: 2h 2d 2c 2s | 3h 3d 3c 3s | ... | Ah Ad Ac As
```

**Win rate: ~62.8% ± 0.5% (35k games)**

---

### v1.0 — Engineering: 10x Speedup

v0.3 was correct but not fast enough for practical use. The optimizations applied:

- **Numba `prange`** — parallel execution across the multiset iterator loop
- **`lru_cache`** on evaluation calls — repeated game states (common in early game) hit cache instead of recomputing
- **Early game LUT** — precomputed expected values for all states with ≤3 dead cards via `ProcessPoolExecutor`, covering the first few decisions where states repeat across games
- **Bitmask arithmetic throughout** — eliminated Python-level set operations in the hot path

Result: ~50ms per game, a 10x+ improvement over v0.3 with identical decision quality. The win rate is the same because the algorithm is unchanged — v1.0 simply computes the same exact values faster.

This equivalence is the key insight of the whole project: **Monte Carlo at infinite simulations converges to the deterministic result**. v0.1 and v1.0 compute the same quantity — v1.0 just does it analytically in 50ms instead of stochastically in ~1s.

**Win rate: 62.76% ± 0.19% (250k games, 95% confidence)**

---

### v1.1 — Rank Mapping Exploration

The treys rank scale is nonlinear in terms of win probability — the difference between rank 1 and rank 100 matters far more than between rank 7000 and rank 7100. v1.1 parameterizes the utility function with a custom mapping `f: rank → value`, allowing non-linear scalings to be plugged in without recompilation via in-place numpy array mutation.

Mappings tested: `rank^0.7`, `rank^0.8`, `rank^0.9`, `sqrt(rank)`. None achieved a statistically significant improvement over the identity mapping. Proving a sub-1% improvement requires ~224,000 games per variant for 95% confidence — days of compute on a laptop. The statistical validation bottleneck, not the algorithm design, is the binding constraint.

**Win rates: 62.18%–62.62% across all mappings (not significantly different from v1.0)**

---

### v2.x — ML Attempt

With a working 62.8% deterministic baseline, I attempted to use supervised ML to push further. v1.0 generated training data (156-column feature matrix including bitmask card indicators) and XGBoost was trained to predict win probability or final hand rank.

The attempt failed to beat the baseline for two fundamental reasons:

**Credit assignment** — mapping a final game outcome back to individual early-game decisions is noisy. An early-game state where the player holds two good cards doesn't have a clean relationship to the final result because several random card draws happen between that state and the end.

**Stochastic variance** — binary win/loss targets introduce enormous noise at the decision level. A single random card draw can flip the outcome, making it hard for any model to learn a stable decision boundary from intermediate states.

Switching to rank regression reduced variance but produced MAE over 1,000 on a 1–7,462 scale — the model was essentially predicting noise for early game states where outcomes are genuinely unknowable.

The root cause: the training signal is fundamentally weak for early game decisions regardless of model architecture or target variable. Addressing this would require either much deeper rollout policies to reduce variance, or a bootstrap laddering approach (training iteratively on data generated by progressively better policies) — neither feasible within the project timeline.

---

## Results Summary

| Version | Approach | Win Rate | Speed |
|---|---|---|---|
| Baseline | Keep first 5 | ~15.1% | — |
| v0.1 | Monte Carlo both sides (100 sims) | ~56% | ~900ms/game |
| v0.1 | Monte Carlo both sides (1k sims) | ~61.8% | ~9s/game |
| v0.2 | Exact player + MC dealer (1k sims) | ~62.5% | ~550ms/game |
| v0.3 | Fully deterministic | 62.88% ± 0.51% | ~500ms/game |
| v1.0 | Optimized deterministic | **62.76% ± 0.19%** | **~50ms/game** |
| v1.1 | Rank mapping variants | 62.18–62.62% | ~50ms/game |
| v2.x | ML (XGBoost) | <45% | — |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python, FastAPI, PostgreSQL |
| Frontend | React, Vite, Tailwind CSS |
| Deployment | Railway (backend), Vercel (frontend) |
| AI Engine | Numba JIT, NumPy, treys |
| Notebook | Jupyter, pandas, matplotlib, scipy |

---

## Repository Structure

```
Poker_Project/
├── backend/
│   ├── app/
│   │   ├── core/           # Game state machine
│   │   ├── evaluators/     # Hand evaluation
│   │   └── simulators/
│   │       ├── v_0/        # v0.1, v0.2, v0.3 logic + sims
│   │       └── v_1/        # v1.0, v1.1 logic + sims + LUT generators
├── frontend/               # React + Vite
└── notebooks/
    └── Poker_Simulations.ipynb  # Full algorithm analysis
```

---

## Running Locally

```bash
# Backend
cd backend
pip install -r requirements.txt
fastapi dev
# or uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

Set .env.example on the backend to set environment variables:
```
DATABASE_URL="postgresql://username:pwd@localhost:5432/db_name"
SESSION_SECRET_KEY="your-secret-key"
FRONTEND_URL="http://localhost:5173"
```

On the frontend:
```
VITE_API_BASE="http://localhost:8000"
```
