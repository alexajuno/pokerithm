"""Card representations for poker."""

from enum import IntEnum
from dataclasses import dataclass
from typing import Self


class Suit(IntEnum):
    """Card suits. Values don't affect poker hand ranking."""

    CLUBS = 0
    DIAMONDS = 1
    HEARTS = 2
    SPADES = 3

    @property
    def symbol(self) -> str:
        """Unicode symbol for the suit."""
        return ["♣", "♦", "♥", "♠"][self.value]

    def __str__(self) -> str:
        return self.symbol


class Rank(IntEnum):
    """Card ranks. Higher value = higher rank."""

    TWO = 2
    THREE = 3
    FOUR = 4
    FIVE = 5
    SIX = 6
    SEVEN = 7
    EIGHT = 8
    NINE = 9
    TEN = 10
    JACK = 11
    QUEEN = 12
    KING = 13
    ACE = 14

    @property
    def symbol(self) -> str:
        """Short symbol for the rank."""
        if self.value <= 10:
            return str(self.value)
        return {11: "J", 12: "Q", 13: "K", 14: "A"}[self.value]

    def __str__(self) -> str:
        return self.symbol


@dataclass(frozen=True, slots=True)
class Card:
    """A playing card with rank and suit."""

    rank: Rank
    suit: Suit

    def __str__(self) -> str:
        return f"{self.rank.symbol}{self.suit.symbol}"

    def __repr__(self) -> str:
        return f"Card({self.rank.symbol}{self.suit.symbol})"

    @classmethod
    def from_str(cls, s: str) -> Self:
        """Parse a card from string like 'As', 'Kh', '10d', '2c'.

        Rank: 2-10, J, Q, K, A
        Suit: c(lubs), d(iamonds), h(earts), s(pades)
        """
        s = s.strip().upper()
        if len(s) < 2:
            raise ValueError(f"Invalid card string: {s}")

        # Parse suit (last character)
        suit_char = s[-1]
        suit_map = {"C": Suit.CLUBS, "D": Suit.DIAMONDS, "H": Suit.HEARTS, "S": Suit.SPADES}
        if suit_char not in suit_map:
            raise ValueError(f"Invalid suit: {suit_char}")
        suit = suit_map[suit_char]

        # Parse rank (everything before suit)
        rank_str = s[:-1]
        rank_map = {
            "2": Rank.TWO,
            "3": Rank.THREE,
            "4": Rank.FOUR,
            "5": Rank.FIVE,
            "6": Rank.SIX,
            "7": Rank.SEVEN,
            "8": Rank.EIGHT,
            "9": Rank.NINE,
            "10": Rank.TEN,
            "T": Rank.TEN,
            "J": Rank.JACK,
            "Q": Rank.QUEEN,
            "K": Rank.KING,
            "A": Rank.ACE,
        }
        if rank_str not in rank_map:
            raise ValueError(f"Invalid rank: {rank_str}")
        rank = rank_map[rank_str]

        return cls(rank=rank, suit=suit)


# Convenience function
def card(s: str) -> Card:
    """Shorthand for Card.from_str()."""
    return Card.from_str(s)
