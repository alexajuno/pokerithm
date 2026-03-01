# Pokerithm

Poker hand evaluation, equity calculator, and EV decision engine CLI. Built for hyper-turbo tournament play.

## Install

```bash
uv sync
```

## Usage

### Decide: Should I shove or fold?

The main tool for tournament play. Given your hand, stack, position, and table size, it tells you whether to shove, raise, or fold with full EV math.

```bash
# Short stack push/fold (<=10bb) — uses Nash equilibrium ranges
pokerithm decide K7o -s 8 -p utg -n 4 -v tight
pokerithm decide A5s -s 6 -p btn -n 3
pokerithm decide AA -s 5 -p sb -n 2

# Medium stack (10-25bb) — compares raise vs shove vs fold EV
pokerithm decide JJ -s 20 -p co -n 4 -v normal
pokerithm decide AKs -s 18 -p btn -n 3
```

Options:
- `-s` stack size in big blinds
- `-p` position: `utg`, `mp`, `co`, `btn`, `sb`, `bb`
- `-n` players remaining at table
- `-v` villain style: `tight` (default), `normal`, `loose`

### Equity: Win probability

```bash
# Your hand vs a specific opponent
pokerithm equity "As Kh" --vs "Qd Qc"

# Your hand vs random opponents
pokerithm equity "As Kh" --players 4

# With a board
pokerithm equity "As Kh" --vs "Qd Qc" --board "Js 9h 5d"
```

### Outs: Cards that improve your hand

```bash
# Flush draw on the flop
pokerithm outs "As Ks" "5s 7s Jd"
```

### Preflop: Quick preflop equity

```bash
pokerithm preflop "As Ah" --opponents 3
```

### Interactive: Track a hand street by street

```bash
# With EV decision advice on preflop
pokerithm interactive --players 4

# With bot advisor (equity-based recommendations each street)
pokerithm interactive --players 6 --bot
```

### Bot: Get advice for a specific spot

```bash
pokerithm bot "As Kh" --position 5 --board "Qs Js 9d" --pot 2.5
```

### Sim: Play a tournament against bots

```bash
pokerithm sim --bots 7 --stack 1500
pokerithm sim --bots 5 --ai 2 --model haiku
```

## Hand Notation

| Format | Meaning |
|--------|---------|
| `AA` | Pocket aces (pair) |
| `AKs` | Ace-king suited |
| `AKo` | Ace-king offsuit |
| `As Kh` | Ace of spades, King of hearts (specific cards) |

Suits: `s`pades, `h`earts, `d`iamonds, `c`lubs

## Development

```bash
uv run pytest          # Run tests
uv run ruff check .    # Lint
uv run pyright         # Type check
```
