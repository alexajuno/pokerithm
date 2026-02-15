"""Player abstraction for tournament play."""

from __future__ import annotations

from dataclasses import dataclass, field

from .card import Card


@dataclass(frozen=True)
class PlayerActionContext:
    """Read-only snapshot given to human/bot when deciding.

    All monetary values are in chips (int), not big blinds.
    """

    hole_cards: list[Card]
    community: list[Card]
    pot_total: int
    to_call: int
    min_raise: int
    max_raise: int
    current_bet: int
    street: str
    num_active_players: int
    position_label: str


@dataclass
class Player:
    """A player at the poker table."""

    name: str
    chips: int
    seat: int
    is_human: bool = False

    hole_cards: list[Card] = field(default_factory=list)
    is_folded: bool = False
    is_all_in: bool = False
    current_bet: int = 0
    total_bet_this_hand: int = 0

    @property
    def is_active(self) -> bool:
        """Can still act this round (not folded, not all-in, has chips)."""
        return not self.is_folded and not self.is_all_in and self.chips > 0

    @property
    def is_in_hand(self) -> bool:
        """Still competing for the pot (not folded)."""
        return not self.is_folded

    @property
    def is_eliminated(self) -> bool:
        """Out of the tournament (no chips, not in a hand)."""
        return self.chips == 0 and not self.is_all_in

    def reset_for_new_hand(self) -> None:
        """Reset per-hand state."""
        self.hole_cards = []
        self.is_folded = False
        self.is_all_in = False
        self.current_bet = 0
        self.total_bet_this_hand = 0

    def reset_for_new_round(self) -> None:
        """Reset per-street state (current_bet resets, total_bet persists)."""
        self.current_bet = 0

    def bet(self, amount: int) -> int:
        """Place a bet, capped at stack. Returns the actual amount bet."""
        actual = min(amount, self.chips)
        self.chips -= actual
        self.current_bet += actual
        self.total_bet_this_hand += actual
        if self.chips == 0:
            self.is_all_in = True
        return actual

    def fold(self) -> None:
        """Fold the hand."""
        self.is_folded = True
