"""Pot management with side pot calculation."""

from __future__ import annotations

from dataclasses import dataclass, field

from .player import Player


@dataclass
class SidePot:
    """A single pot (main or side) with its eligible winners."""

    amount: int
    eligible_players: list[Player]


@dataclass
class PotManager:
    """Tracks the pot and calculates side pots."""

    _total: int = 0
    _contributions: dict[int, int] = field(default_factory=dict)

    def add(self, amount: int) -> None:
        self._total += amount

    def reset(self) -> None:
        self._total = 0
        self._contributions.clear()

    @property
    def total(self) -> int:
        return self._total

    @staticmethod
    def calculate_side_pots(players: list[Player]) -> list[SidePot]:
        """Calculate main pot and side pots from player bets.

        Algorithm:
        1. Collect all unique total_bet_this_hand values, sorted ascending
        2. For each level, each contributor puts in min(their_bet, level) - prev_level
        3. Eligible = non-folded players whose bet >= that level
        4. Folded players' chips stay in the pot but they can't win it
        """
        in_hand = [p for p in players if p.total_bet_this_hand > 0]
        if not in_hand:
            return []

        bet_levels = sorted({p.total_bet_this_hand for p in in_hand})
        pots: list[SidePot] = []
        prev_level = 0

        for level in bet_levels:
            pot_amount = 0
            for p in in_hand:
                contribution = min(p.total_bet_this_hand, level) - min(
                    p.total_bet_this_hand, prev_level
                )
                pot_amount += contribution

            eligible = [
                p
                for p in in_hand
                if not p.is_folded and p.total_bet_this_hand >= level
            ]

            if pot_amount > 0:
                pots.append(SidePot(amount=pot_amount, eligible_players=eligible))

            prev_level = level

        return pots
