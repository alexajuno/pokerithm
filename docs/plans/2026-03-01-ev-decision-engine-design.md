# EV Decision Engine Design

## Context

Pokerithm currently calculates equity (win/tie/loss percentages) but doesn't answer the practical question: **"Should I shove, raise, or fold?"** In hyper-turbo company tournaments where blinds escalate fast and stacks are short, players need mathematically-grounded action recommendations with EV breakdowns.

### Game Format
- Winner-take-all payout (chip EV = tournament EV, no ICM needed)
- 4-8 players, hyper-turbo blind structure
- Opponents tend to play tight (fold too much with short stacks)
- Stack depths typically 3-25 BB

## Decision

Build a standalone EV decision engine using a hybrid approach:
- **Nash push/fold ranges** for stacks <=10bb (instant lookup)
- **EV calculation** for 10-25bb (Monte Carlo equity + fold equity modeling)
- **Villain profiling** (tight/normal/loose) to exploit opponent tendencies

## Architecture

### New Files

**`src/pokerithm/decision.py`** — Core decision engine
- `Situation` dataclass: hand, stack_bb, position, players, pot_bb, villain_style
- `Decision` dataclass: action, ev_shove, ev_fold, ev_raise, fold_equity, equity_called, reasoning, confidence
- `decide(situation) -> Decision`: Main entry point
- `calculate_shove_ev()`: `fold_equity * pot + (1 - fold_equity) * (equity * total_pot - stack)`
- `calculate_raise_ev()`: EV for open-raising (10-25bb range)
- `estimate_fold_equity()`: Based on villain profile + position + stack depth

**`src/pokerithm/nash_ranges.py`** — Pre-computed Nash equilibrium data
- Shove ranges indexed by (stack_bb, position, players_remaining)
- Call ranges indexed by (stack_bb, position)
- Foundation: Sklansky-Chubukov numbers adapted for multi-way pots

**`tests/test_decision.py`** — Decision engine tests

### Modified Files

- **`src/pokerithm/cli.py`** — Add `decide` command + enhance `interactive` with decision advice
- **`src/pokerithm/ranges.py`** — Extend with villain calling range data

### Unchanged
- hand.py, evaluator.py, card.py, deck.py, bot.py, tournament system

### Dependency Flow
```
cli.py -> decision.py -> nash_ranges.py  (<=10bb lookup)
                      -> calculator.py   (equity simulation)
                      -> ranges.py       (villain calling ranges)
                      -> position.py     (position awareness)
```

## Decision Logic

```
Input: Situation(hand, stack_bb, position, players, villain_style)
              |
    +---------+---------+
    | stack <= 10bb?    |
    | YES               | NO (10-25bb)
    v                   v
  Nash push/fold      Calculate:
  lookup table        - EV(raise 2.2x)
    |                 - EV(shove)
    v                 - EV(fold) = 0
  Hand in range?          |
  -> SHOVE            Best EV > 0?
  -> FOLD             -> Recommend best
    |                     |
    v                     v
  Calculate EV        Output with sizing
  for display
```

## Villain Calling Ranges

| Style  | Calling range vs shove | Use case                    |
|--------|------------------------|-----------------------------|
| tight  | Top 8-12%              | Default — matches company game |
| normal | Top 15-20%             | Standard Nash assumptions   |
| loose  | Top 25-30%             | Aggressive opponents        |

## CLI Interface

### Standalone Command
```
pokerithm decide "K7o" --stack 8 --position utg --players 4
pokerithm decide "AKs" --stack 18 --position btn --players 3 --villain tight
```

Parameters:
- `hand` (required): Hole cards — "K7o", "AKs", "JJ"
- `--stack` / `-s` (required): Stack in big blinds
- `--position` / `-p` (required): utg, mp, co, btn, sb, bb
- `--players` / `-n` (required): Players remaining
- `--villain` / `-v` (default: "tight"): Villain tendency
- `--pot` (default: 1.5): Current pot in BBs

### Output (Rich formatted)
```
╭─────────────────── Decision ───────────────────╮
│  Hand: K7o  |  Position: UTG  |  8.0 BB        │
│                                                 │
│  SHOVE  (EV: +1.24 BB)                         │
│                                                 │
│  EV Breakdown:                                  │
│  - Fold equity: 68% -> +1.02 BB                │
│  - Equity when called: 38%                      │
│  - Called by: ~12% (TT+, AQs+, AKo)            │
│  - EV when called: -0.52 BB                     │
│                                                 │
│  Net: fold_eq(+1.02) + called(-0.17) = +1.24   │
│  Confidence: HIGH                               │
╰─────────────────────────────────────────────────╯
```

### Interactive Mode Enhancement
After equity display, show one-line decision advice:
```
Decision: SHOVE (+1.24 BB EV) — K7o profitable at 8bb UTG vs tight field
```

## EV Formula

### Shove EV
```
EV(shove) = P(fold) * pot_before
          + P(call) * [equity * (pot_before + 2*stack) - stack]

Where:
  P(fold) = fold_equity (from villain profile)
  P(call) = 1 - fold_equity
  pot_before = current pot (typically 1.5bb from blinds)
  equity = hand equity vs villain calling range (Monte Carlo)
  stack = effective stack risked
```

### Raise EV (10-25bb)
```
EV(raise) = P(fold) * pot_before
          + P(call_flat) * [equity * (pot + 2*raise_size) - raise_size]
          + P(3bet_shove) * [equity_vs_3bet_range * (pot + 2*stack) - stack]

raise_size = 2.2x BB (standard)
```

## Scope Boundaries
- Chip EV only (no ICM) — correct for winner-take-all format
- Preflop decisions only for v1 (postflop decision engine is a separate feature)
- No multi-way pot calculations (assumes heads-up when called)
