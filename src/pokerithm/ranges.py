"""Preflop hand range tables for a TAG (tight-aggressive) strategy.

Each tier is a set of canonical hand keys:
  - Pairs:  "AA", "KK", ..., "22"
  - Suited: "AKs", "T9s", etc. (higher rank first)
  - Offsuit: "AKo", "KQo", etc.

Tiers are cumulative — _STRONG is a superset of _PREMIUM.
"""

from .card import Card
from .position import Position


# ── Helper ──────────────────────────────────────────────────


def hand_key(rank1_symbol: str, rank2_symbol: str, suited: bool) -> str:
    """Build a canonical range key like 'AKs', '77', 'T9o'.

    Ranks are ordered high-first. Pairs omit the suited/offsuit suffix.
    """
    # Rank ordering: A > K > Q > J > T > 9 > ... > 2
    order = "AKQJT98765432"
    # Rank.symbol returns "10" for ten — normalise to "T"
    r1 = "T" if rank1_symbol == "10" else rank1_symbol.upper()
    r2 = "T" if rank2_symbol == "10" else rank2_symbol.upper()
    if order.index(r1) > order.index(r2):
        r1, r2 = r2, r1
    if r1 == r2:
        return f"{r1}{r2}"
    return f"{r1}{r2}{'s' if suited else 'o'}"


def hole_cards_to_key(card1: Card, card2: Card) -> str:
    """Convert two Card objects into a canonical range key."""
    suited = card1.suit == card2.suit
    return hand_key(card1.rank.symbol, card2.rank.symbol, suited)


# ── Range tiers ─────────────────────────────────────────────

_PREMIUM: set[str] = {
    # ~5% of hands — the monsters
    "AA", "KK", "QQ", "JJ",
    "AKs", "AKo",
}

_STRONG: set[str] = _PREMIUM | {
    # ~10% — solid value hands
    "TT", "99",
    "AQs", "AQo", "AJs",
    "KQs",
}

_PLAYABLE: set[str] = _STRONG | {
    # ~20% — good but positional
    "88", "77", "66",
    "ATs", "A9s", "A8s", "A5s", "A4s",  # suited aces (wheel + blockers)
    "ATo",
    "KJs", "KTs",
    "QJs", "QTs",
    "JTs",
    "T9s", "98s", "87s",  # suited connectors
}

_WIDE: set[str] = _PLAYABLE | {
    # ~35% — late-position steals
    "55", "44", "33", "22",
    "A7s", "A6s", "A3s", "A2s",
    "AJo",
    "KQo", "KJo", "KTo",
    "K9s", "K8s",
    "QJo", "QTo",
    "Q9s",
    "J9s", "JTo",
    "T8s",
    "97s", "86s", "76s", "65s", "54s",
}


# ── Position → (raise_range, call_range) ────────────────────

POSITION_RANGES: dict[Position, tuple[set[str], set[str]]] = {
    Position.UTG:   (_STRONG,   set()),        # tight open, never flat
    Position.UTG_1: (_STRONG,   set()),
    Position.MP:    (_PLAYABLE, set()),
    Position.HJ:    (_PLAYABLE, set()),
    Position.CO:    (_WIDE,     set()),
    Position.BTN:   (_WIDE,     set()),         # widest open
    Position.SB:    (_PLAYABLE, _STRONG),       # 3-bet or flat premiums
    Position.BB:    (_STRONG,   _WIDE),         # wide defend, tight 3-bet
}
