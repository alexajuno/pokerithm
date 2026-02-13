# Pokerithm

Poker hand evaluation and probability calculator CLI (Python).

## Commands

| Command | Description |
|---------|-------------|
| `uv run pytest` | Run tests |
| `uv run ruff check .` | Lint code |
| `uv run pyright` | Type check |
| `uv run pokerithm` | Run CLI |

## Architecture

```
pokerithm/
├── src/pokerithm/
│   ├── card.py         # Card representation
│   ├── deck.py         # Deck management
│   ├── hand.py         # Hand representation
│   ├── evaluator.py    # Hand evaluation logic
│   ├── calculator.py   # Probability calculations
│   └── cli.py          # Typer CLI app
└── tests/              # Pytest tests
```

## Tech Stack

- Python 3.11+
- Typer (CLI framework)
- Rich (terminal output)
- uv (package manager)

## Linting

Run `ruff check .` and `pyright` on file changes before committing.
