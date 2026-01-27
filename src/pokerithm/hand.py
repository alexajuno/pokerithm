"""Poker hand evaluation for Texas Hold'em."""

from collections import Counter
from dataclasses import dataclass
from enum import IntEnum
from itertools import combinations
from typing import Self

from .card import Card, Rank


class HandRank(IntEnum):
    """Poker hand rankings from lowest to highest."""

    HIGH_CARD = 0
    ONE_PAIR = 1
    TWO_PAIR = 2
    THREE_OF_A_KIND = 3
    STRAIGHT = 4
    FLUSH = 5
    FULL_HOUSE = 6
    FOUR_OF_A_KIND = 7
    STRAIGHT_FLUSH = 8

    def __str__(self) -> str:
        return self.name.replace("_", " ").title()


@dataclass(frozen=True, slots=True, order=True)
class HandValue:
    """Comparable hand value for determining winners.

    Comparison works by:
    1. HandRank (pair beats high card, etc.)
    2. Primary kickers (the cards that make the hand)
    3. Secondary kickers (remaining high cards)
    """

    rank: HandRank
    primary: tuple[int, ...]  # Main hand values (e.g., pair rank)
    kickers: tuple[int, ...]  # Remaining cards for tiebreakers

    def __str__(self) -> str:
        return str(self.rank)


@dataclass
class Hand:
    """A poker hand with evaluation capabilities."""

    cards: list[Card]

    def __post_init__(self) -> None:
        if len(self.cards) < 5:
            raise ValueError("Hand must have at least 5 cards")

    @classmethod
    def from_cards(cls, *cards: Card) -> Self:
        """Create a hand from cards."""
        return cls(cards=list(cards))

    def evaluate(self) -> HandValue:
        """Evaluate the best 5-card hand from available cards.

        For Texas Hold'em, this finds the best 5-card combination
        from 7 cards (2 hole + 5 community).
        """
        if len(self.cards) == 5:
            return _evaluate_five(self.cards)

        # Find best 5-card combination
        best: HandValue | None = None
        for five_cards in combinations(self.cards, 5):
            value = _evaluate_five(list(five_cards))
            if best is None or value > best:
                best = value
        return best  # type: ignore

    @property
    def value(self) -> HandValue:
        """Shorthand for evaluate()."""
        return self.evaluate()


def _evaluate_five(cards: list[Card]) -> HandValue:
    """Evaluate exactly 5 cards."""
    ranks = sorted([c.rank for c in cards], reverse=True)
    suits = [c.suit for c in cards]
    rank_counts = Counter(ranks)

    is_flush = len(set(suits)) == 1
    is_straight, straight_high = _check_straight(ranks)

    # Straight flush (includes royal flush)
    if is_flush and is_straight:
        return HandValue(HandRank.STRAIGHT_FLUSH, (straight_high,), ())

    # Four of a kind
    if 4 in rank_counts.values():
        quad = _get_ranks_by_count(rank_counts, 4)[0]
        kicker = _get_ranks_by_count(rank_counts, 1)[0]
        return HandValue(HandRank.FOUR_OF_A_KIND, (quad,), (kicker,))

    # Full house
    if 3 in rank_counts.values() and 2 in rank_counts.values():
        trips = _get_ranks_by_count(rank_counts, 3)[0]
        pair = _get_ranks_by_count(rank_counts, 2)[0]
        return HandValue(HandRank.FULL_HOUSE, (trips, pair), ())

    # Flush
    if is_flush:
        return HandValue(HandRank.FLUSH, tuple(ranks), ())

    # Straight
    if is_straight:
        return HandValue(HandRank.STRAIGHT, (straight_high,), ())

    # Three of a kind
    if 3 in rank_counts.values():
        trips = _get_ranks_by_count(rank_counts, 3)[0]
        kickers = tuple(_get_ranks_by_count(rank_counts, 1)[:2])
        return HandValue(HandRank.THREE_OF_A_KIND, (trips,), kickers)

    # Two pair
    pairs = _get_ranks_by_count(rank_counts, 2)
    if len(pairs) == 2:
        kicker = _get_ranks_by_count(rank_counts, 1)[0]
        return HandValue(HandRank.TWO_PAIR, tuple(pairs), (kicker,))

    # One pair
    if len(pairs) == 1:
        kickers = tuple(_get_ranks_by_count(rank_counts, 1)[:3])
        return HandValue(HandRank.ONE_PAIR, (pairs[0],), kickers)

    # High card
    return HandValue(HandRank.HIGH_CARD, (ranks[0],), tuple(ranks[1:]))


def _check_straight(ranks: list[Rank]) -> tuple[bool, int]:
    """Check if sorted ranks form a straight. Returns (is_straight, high_card)."""
    values = [r.value for r in ranks]

    # Check regular straight
    if values == list(range(values[0], values[0] - 5, -1)):
        return True, values[0]

    # Check wheel (A-2-3-4-5) - ace plays low
    if values == [14, 5, 4, 3, 2]:
        return True, 5  # 5-high straight

    return False, 0


def _get_ranks_by_count(counts: Counter[Rank], count: int) -> list[int]:
    """Get rank values that appear exactly `count` times, sorted descending."""
    return sorted([r.value for r, c in counts.items() if c == count], reverse=True)
