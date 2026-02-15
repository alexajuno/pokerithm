"""Betting round state machine."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .action import Action, ActionType
from .player import Player, PlayerActionContext
from .pot import PotManager


@dataclass
class BettingRound:
    """Runs a single betting round (one street).

    Players are in action order for this street.  The round ends when
    all active players have acted at least once AND either matched the
    current bet, gone all-in, or checked through.
    """

    players: list[Player]
    pot: PotManager
    big_blind: int
    current_bet: int = 0
    min_raise: int = 0
    max_raises: int = 4

    def is_complete(self) -> bool:
        """True if only one player remains in the hand."""
        return sum(1 for p in self.players if p.is_in_hand) <= 1

    def run(
        self,
        get_action: Callable[[Player, PlayerActionContext], Action],
        make_context: Callable[[Player], PlayerActionContext],
        on_action: Callable[[Player, Action], None] | None = None,
    ) -> None:
        """Run the betting round to completion.

        Args:
            get_action: Returns the action a player wants to take.
            make_context: Builds a PlayerActionContext for a given player.
            on_action: Optional callback fired after each action.
        """
        if self.min_raise == 0:
            self.min_raise = self.big_blind

        active = [p for p in self.players if p.is_active]
        if len(active) <= 1:
            return

        acted: set[int] = set()
        last_raiser: int | None = None
        raise_count = 0

        while True:
            all_done = True

            for player in self.players:
                if not player.is_active:
                    continue

                # Skip if already acted and no new raise to respond to
                if player.seat in acted and (
                    last_raiser is None or player.seat == last_raiser
                ):
                    continue

                # Skip if already matched the current bet
                if (
                    player.seat in acted
                    and player.current_bet >= self.current_bet
                ):
                    continue

                ctx = make_context(player)
                action = get_action(player, ctx)

                # Enforce raise cap — convert raises to calls once limit hit
                if raise_count >= self.max_raises and action.type in (
                    ActionType.RAISE,
                    ActionType.ALL_IN,
                ):
                    if ctx.to_call > 0:
                        action = Action(ActionType.CALL)
                    else:
                        action = Action(ActionType.CHECK)

                self._apply_action(player, action)
                acted.add(player.seat)

                if on_action:
                    on_action(player, action)

                if action.type == ActionType.RAISE or action.type == ActionType.ALL_IN:
                    if player.current_bet > self.current_bet:
                        raise_increment = player.current_bet - self.current_bet
                        self.current_bet = player.current_bet
                        self.min_raise = max(self.min_raise, raise_increment)
                        last_raiser = player.seat
                        raise_count += 1
                        all_done = False
                        break  # restart the loop so everyone gets to respond

                if self.is_complete():
                    return

            if all_done:
                break

            # Check if anyone still needs to act
            needs_action = False
            for p in self.players:
                if not p.is_active:
                    continue
                if p.seat == last_raiser:
                    continue
                if p.current_bet < self.current_bet:
                    needs_action = True
                    break
            if not needs_action:
                break

    def _apply_action(self, player: Player, action: Action) -> None:
        """Apply an action to a player and update the pot."""
        if action.type == ActionType.FOLD:
            player.fold()

        elif action.type == ActionType.CHECK:
            pass

        elif action.type == ActionType.CALL:
            call_amount = self.current_bet - player.current_bet
            actual = player.bet(call_amount)
            self.pot.add(actual)

        elif action.type == ActionType.RAISE:
            raise_to = int(action.amount)
            amount_needed = raise_to - player.current_bet
            actual = player.bet(amount_needed)
            self.pot.add(actual)

        elif action.type == ActionType.ALL_IN:
            actual = player.bet(player.chips)
            self.pot.add(actual)
