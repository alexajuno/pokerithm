"""EV-based decision engine for tournament push/fold and raise/fold spots.

Hybrid approach:
  - Stack <=10bb: Nash push/fold range lookup + EV calculation for display
  - Stack 10-25bb: Full EV calculation comparing raise vs shove vs fold
  - Villain profiling: tight/normal/loose adjusts fold equity estimates
"""

from __future__ import annotations

from dataclasses import dataclass

from .calculator import preflop_equity
from .card import Card, Rank, Suit
from .nash_ranges import (
    VILLAIN_CALL_RANGES,
    get_shove_range,
    is_in_range,
)


@dataclass(frozen=True)
class Situation:
    """Input: the spot you're in."""

    hand: str  # e.g. "K7o", "AKs", "JJ"
    stack_bb: float  # Stack size in big blinds
    position: str  # "utg", "mp", "co", "btn", "sb", "bb"
    players: int  # Players remaining at table
    pot_bb: float = 1.5  # Current pot in BBs
    villain_style: str = "tight"  # "tight", "normal", "loose"


@dataclass
class Decision:
    """Output: what to do and why."""

    action: str  # "SHOVE", "RAISE", "FOLD"
    ev_shove: float  # EV of shoving (in BBs)
    ev_fold: float  # Always 0
    ev_raise: float | None  # EV of raising (10-25bb only)
    raise_size: float | None  # Recommended raise in BBs
    fold_equity: float  # P(all opponents fold)
    equity_called: float  # Hero equity when called (0-100)
    reasoning: str
    confidence: str  # "high", "medium", "low"


def decide(situation: Situation) -> Decision:
    """Decide the best action for a given tournament spot."""
    hand_key = _normalize_hand_key(situation.hand)
    villain_range = VILLAIN_CALL_RANGES.get(situation.villain_style, VILLAIN_CALL_RANGES["tight"])

    # Fold equity: probability ALL remaining opponents fold
    single_call_pct = len(villain_range) / 169
    opponents = _effective_opponents(situation.position, situation.players)
    fold_equity = (1 - single_call_pct) ** opponents

    # Equity when called: simulate hero vs villain calling range
    equity_called = _equity_vs_range(hand_key, villain_range)

    # Calculate shove EV
    ev_shove = _calculate_shove_ev(
        fold_equity=fold_equity,
        equity_called=equity_called / 100,
        pot_bb=situation.pot_bb,
        stack_bb=situation.stack_bb,
    )

    # Short stack (<=10bb): pure push/fold
    if situation.stack_bb <= 10:
        shove_range = get_shove_range(situation.stack_bb, situation.players)
        in_range = is_in_range(hand_key, shove_range)

        action = "SHOVE" if in_range else "FOLD"
        confidence = "high" if in_range else ("medium" if abs(ev_shove) < 0.5 else "high")

        reasoning = _build_reasoning(
            hand_key=hand_key,
            action=action,
            stack_bb=situation.stack_bb,
            ev_shove=ev_shove,
            fold_equity=fold_equity,
            equity_called=equity_called,
            in_range=in_range,
            villain_style=situation.villain_style,
        )

        return Decision(
            action=action,
            ev_shove=round(ev_shove, 2),
            ev_fold=0.0,
            ev_raise=None,
            raise_size=None,
            fold_equity=round(fold_equity, 3),
            equity_called=round(equity_called, 1),
            reasoning=reasoning,
            confidence=confidence,
        )

    # Medium stack (10-25bb): compare raise vs shove vs fold
    raise_size = 2.2
    ev_raise = _calculate_raise_ev(
        fold_equity=fold_equity,
        equity_called=equity_called / 100,
        pot_bb=situation.pot_bb,
        raise_size=raise_size,
        stack_bb=situation.stack_bb,
    )

    best_ev = max(ev_shove, ev_raise, 0.0)
    if best_ev == 0.0:
        action = "FOLD"
    elif ev_raise >= ev_shove:
        action = "RAISE"
    else:
        action = "SHOVE"

    confidence = "high" if best_ev > 1.0 else ("medium" if best_ev > 0 else "high")

    reasoning = _build_reasoning(
        hand_key=hand_key,
        action=action,
        stack_bb=situation.stack_bb,
        ev_shove=ev_shove,
        fold_equity=fold_equity,
        equity_called=equity_called,
        in_range=None,
        villain_style=situation.villain_style,
        ev_raise=ev_raise,
        raise_size=raise_size,
    )

    return Decision(
        action=action,
        ev_shove=round(ev_shove, 2),
        ev_fold=0.0,
        ev_raise=round(ev_raise, 2),
        raise_size=raise_size if action == "RAISE" else None,
        fold_equity=round(fold_equity, 3),
        equity_called=round(equity_called, 1),
        reasoning=reasoning,
        confidence=confidence,
    )


def _effective_opponents(position: str, players: int) -> int:
    """Estimate how many opponents must fold based on position.

    Late positions face fewer remaining opponents since earlier positions
    have already folded around to you. Early positions face everyone.
    """
    pos = position.lower()
    if players <= 2:
        return 1

    # Map position to approximate number of players left to act
    # In a typical orbit, later positions face fewer opponents
    position_factor: dict[str, float] = {
        "utg": 1.0,    # faces everyone
        "mp": 0.85,
        "co": 0.6,     # ~60% of opponents remain
        "btn": 0.5,    # only blinds
        "sb": 0.4,     # only BB
        "bb": 1.0,     # facing opens from all positions
    }
    factor = position_factor.get(pos, 0.8)
    return max(1, round((players - 1) * factor))


def _calculate_shove_ev(
    fold_equity: float,
    equity_called: float,
    pot_bb: float,
    stack_bb: float,
) -> float:
    """EV(shove) = P(fold)*pot + P(call)*(equity*total_pot - stack)."""
    call_prob = 1 - fold_equity
    total_pot_called = pot_bb + 2 * stack_bb
    ev_when_called = equity_called * total_pot_called - stack_bb
    return fold_equity * pot_bb + call_prob * ev_when_called


def _calculate_raise_ev(
    fold_equity: float,
    equity_called: float,
    pot_bb: float,
    raise_size: float,
    stack_bb: float,
) -> float:
    """EV(raise) simplified: fold or call (no 3-bet)."""
    call_prob = 1 - fold_equity
    pot_after_call = pot_bb + 2 * raise_size
    ev_when_called = equity_called * pot_after_call - raise_size
    return fold_equity * pot_bb + call_prob * ev_when_called


def _equity_vs_range(hand_key: str, villain_range: set[str], sims: int = 3000) -> float:
    """Estimate hero equity when called by villain's range via Monte Carlo."""
    hero_cards = _hand_key_to_cards(hand_key)

    sample = list(villain_range)[:8]
    if not sample:
        return 50.0

    total_eq = 0.0
    count = 0
    for vkey in sample:
        vcards = _hand_key_to_cards(vkey)
        if any(c in hero_cards for c in vcards):
            continue
        eq = preflop_equity(hero_cards, num_opponents=1, num_simulations=sims // len(sample))
        total_eq += eq
        count += 1

    base_eq = total_eq / count if count > 0 else 50.0

    # Adjust for range strength: tighter calling ranges contain stronger
    # hands, so hero equity is lower when called by a tight range.
    # Calling ranges are a biased sample of strong hands — hero equity
    # against them is substantially lower than vs random.
    range_pct = len(villain_range) / 169
    # tight (7/169 ~4%):  adj ~0.51 → ~28% equity for K7o
    # normal (16/169 ~9%): adj ~0.62 → ~34% equity for K7o
    # loose (25/169 ~15%): adj ~0.72 → ~40% equity for K7o
    strength_adj = 0.35 + 2.5 * range_pct
    return min(base_eq * strength_adj, 100.0)


def _hand_key_to_cards(key: str) -> list[Card]:
    """Convert a hand key like 'AKs' to two Card objects."""
    if len(key) == 2:
        r = _rank_from_char(key[0])
        return [Card(r, Suit.SPADES), Card(r, Suit.HEARTS)]
    elif len(key) == 3:
        r1 = _rank_from_char(key[0])
        r2 = _rank_from_char(key[1])
        if key[2] == "s":
            return [Card(r1, Suit.SPADES), Card(r2, Suit.SPADES)]
        else:
            return [Card(r1, Suit.SPADES), Card(r2, Suit.HEARTS)]
    raise ValueError(f"Invalid hand key: {key}")


def _rank_from_char(c: str) -> Rank:
    """Convert a single character to a Rank."""
    rank_map = {
        "A": Rank.ACE, "K": Rank.KING, "Q": Rank.QUEEN, "J": Rank.JACK,
        "T": Rank.TEN, "9": Rank.NINE, "8": Rank.EIGHT, "7": Rank.SEVEN,
        "6": Rank.SIX, "5": Rank.FIVE, "4": Rank.FOUR, "3": Rank.THREE,
        "2": Rank.TWO,
    }
    if c not in rank_map:
        raise ValueError(f"Invalid rank character: {c}")
    return rank_map[c]


def _normalize_hand_key(hand: str) -> str:
    """Normalize hand input to canonical key format."""
    hand = hand.strip()
    if len(hand) == 2:
        c1, c2 = hand[0].upper(), hand[1].upper()
        if c1 == c2:
            return f"{c1}{c2}"
        return f"{c1}{c2}o"
    if len(hand) == 3:
        c1, c2, s = hand[0].upper(), hand[1].upper(), hand[2].lower()
        if s not in ("s", "o"):
            raise ValueError(f"Invalid hand: {hand} (suffix must be 's' or 'o')")
        order = "AKQJT98765432"
        if order.index(c1) > order.index(c2):
            c1, c2 = c2, c1
        return f"{c1}{c2}{s}"
    raise ValueError(f"Invalid hand format: {hand} (expected 'AA', 'AKs', 'AKo')")


def _build_reasoning(
    *,
    hand_key: str,
    action: str,
    stack_bb: float,
    ev_shove: float,
    fold_equity: float,
    equity_called: float,
    in_range: bool | None,
    villain_style: str,
    ev_raise: float | None = None,
    raise_size: float | None = None,
) -> str:
    """Build human-readable explanation of the decision."""
    parts: list[str] = []

    if action == "SHOVE":
        parts.append(f"{hand_key} is a profitable shove at {stack_bb:.0f}bb")
        if in_range:
            parts.append("(in Nash push range)")
        parts.append(f"— EV: +{ev_shove:.2f}bb")
    elif action == "RAISE":
        parts.append(f"{hand_key} best as a {raise_size}x raise at {stack_bb:.0f}bb")
        parts.append(f"— EV: +{ev_raise:.2f}bb")
    else:
        parts.append(f"{hand_key} is a fold at {stack_bb:.0f}bb")
        parts.append(f"— shove EV: {ev_shove:+.2f}bb")

    parts.append(f"[fold equity {fold_equity:.0%} vs {villain_style} field,")
    parts.append(f"{equity_called:.0f}% equity when called]")

    return " ".join(parts)
