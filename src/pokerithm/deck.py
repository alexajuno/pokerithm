"""Deck of cards for poker."""

import random
from dataclasses import dataclass, field

from .card import Card, Rank, Suit


@dataclass
class Deck:
    """A standard 52-card deck."""

    cards: list[Card] = field(default_factory=list)
    _dealt: set[Card] = field(default_factory=set, repr=False)

    def __post_init__(self) -> None:
        if not self.cards:
            self.reset()

    def reset(self) -> None:
        """Reset to a full 52-card deck."""
        self.cards = [Card(rank, suit) for suit in Suit for rank in Rank]
        self._dealt = set()

    def shuffle(self) -> None:
        """Shuffle the remaining cards."""
        random.shuffle(self.cards)

    def deal(self, n: int = 1) -> list[Card]:
        """Deal n cards from the top of the deck."""
        if n > len(self.cards):
            raise ValueError(f"Cannot deal {n} cards, only {len(self.cards)} remaining")
        dealt = [self.cards.pop() for _ in range(n)]
        self._dealt.update(dealt)
        return dealt

    def deal_one(self) -> Card:
        """Deal a single card."""
        return self.deal(1)[0]

    def remove(self, *cards: Card) -> None:
        """Remove specific cards from the deck (e.g., known cards)."""
        for card in cards:
            if card in self.cards:
                self.cards.remove(card)
                self._dealt.add(card)
            elif card not in self._dealt:
                raise ValueError(f"Card {card} not in deck")

    def __len__(self) -> int:
        return len(self.cards)

    def __contains__(self, card: Card) -> bool:
        return card in self.cards
