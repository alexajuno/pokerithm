"""Tournament loop — manages blinds, elimination, and game progression."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from .action import Action
from .ai_bot import AiBotConfig, AiDebugInfo
from .bot import BotConfig
from .card import Card
from .player import Player, PlayerActionContext
from .table import HandResult, Table


@dataclass(frozen=True)
class BlindLevel:
    """A blind level in the tournament schedule."""

    small_blind: int
    big_blind: int


DEFAULT_BLIND_SCHEDULE: list[BlindLevel] = [
    BlindLevel(10, 20),
    BlindLevel(15, 30),
    BlindLevel(25, 50),
    BlindLevel(50, 100),
    BlindLevel(75, 150),
    BlindLevel(100, 200),
    BlindLevel(150, 300),
    BlindLevel(200, 400),
    BlindLevel(300, 600),
    BlindLevel(500, 1000),
]

STARTING_STACK = 1500
HANDS_PER_LEVEL = 10


@dataclass
class TournamentConfig:
    """Configuration for a tournament."""

    num_bots: int = 7
    starting_stack: int = STARTING_STACK
    hands_per_level: int = HANDS_PER_LEVEL
    blind_schedule: list[BlindLevel] = field(
        default_factory=lambda: list(DEFAULT_BLIND_SCHEDULE)
    )


@dataclass
class Tournament:
    """Tournament loop — plays hands until one player remains."""

    config: TournamentConfig
    players: list[Player]
    bot_configs: dict[str, BotConfig] = field(default_factory=dict)
    ai_bot_configs: dict[str, AiBotConfig] = field(default_factory=dict)

    get_human_action: Callable[[Player, PlayerActionContext], Action] | None = None

    # Callbacks
    on_hand_start: Callable[[int, BlindLevel, int], None] | None = None
    on_hand_end: Callable[[HandResult], None] | None = None
    on_elimination: Callable[[Player, int], None] | None = None
    on_blind_increase: Callable[[BlindLevel, int], None] | None = None
    on_tournament_end: Callable[[Player], None] | None = None
    on_action: Callable[[Player, Action], None] | None = None
    on_before_action: Callable[[Player], None] | None = None
    on_ai_debug: Callable[[Player, AiDebugInfo, str], None] | None = None
    on_deal: Callable[[str, list[Card]], None] | None = None
    on_showdown: Callable[..., None] | None = None

    dealer_seat: int = 0
    hand_number: int = 0
    blind_level_idx: int = 0

    def run(self) -> Player:
        """Run the tournament to completion. Returns the winner."""
        alive = [p for p in self.players if not p.is_eliminated]
        self.dealer_seat = alive[0].seat

        while len(alive) > 1:
            self.hand_number += 1

            # Check for blind increase
            if (
                self.hand_number > 1
                and (self.hand_number - 1) % self.config.hands_per_level == 0
            ):
                if self.blind_level_idx < len(self.config.blind_schedule) - 1:
                    self.blind_level_idx += 1
                    level = self.config.blind_schedule[self.blind_level_idx]
                    if self.on_blind_increase:
                        self.on_blind_increase(level, self.blind_level_idx)

            level = self.config.blind_schedule[self.blind_level_idx]

            if self.on_hand_start:
                self.on_hand_start(self.hand_number, level, self.dealer_seat)

            # Play the hand
            table = Table(
                players=self.players,
                dealer_seat=self.dealer_seat,
                small_blind=level.small_blind,
                big_blind=level.big_blind,
                get_human_action=self.get_human_action,
                bot_configs=self.bot_configs,
                ai_bot_configs=self.ai_bot_configs,
                on_action=self.on_action,
                on_before_action=self.on_before_action,
                on_ai_debug=self.on_ai_debug,
                on_deal=self.on_deal,
                on_showdown=self.on_showdown,
            )

            result = table.play_hand()

            if self.on_hand_end:
                self.on_hand_end(result)

            # Clear hand state so is_eliminated works correctly
            for p in self.players:
                p.is_all_in = False
                p.is_folded = False

            # Check for eliminations
            for p in alive:
                if p.is_eliminated:
                    place = len([x for x in self.players if x.is_eliminated])
                    finish_position = len(self.players) - place + 1
                    if self.on_elimination:
                        self.on_elimination(p, finish_position)

            # Advance dealer
            alive = [p for p in self.players if not p.is_eliminated]
            if alive:
                self.dealer_seat = self._next_dealer(alive)

        winner = alive[0]
        if self.on_tournament_end:
            self.on_tournament_end(winner)
        return winner

    def _next_dealer(self, alive: list[Player]) -> int:
        """Advance dealer to the next alive player."""
        seats = sorted(p.seat for p in alive)
        current_idx = None
        for i, s in enumerate(seats):
            if s >= self.dealer_seat:
                current_idx = i
                break
        if current_idx is None:
            current_idx = 0

        next_idx = (current_idx + 1) % len(seats)
        return seats[next_idx]
