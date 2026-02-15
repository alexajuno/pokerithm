"""Tests for betting round state machine."""

from pokerithm.action import Action, ActionType
from pokerithm.betting import BettingRound
from pokerithm.player import Player, PlayerActionContext
from pokerithm.pot import PotManager


def _make_players(n: int, chips: int = 1000) -> list[Player]:
    return [Player(name=f"P{i}", chips=chips, seat=i) for i in range(n)]


def _make_context(player: Player, betting: BettingRound, pot: PotManager) -> PlayerActionContext:
    to_call = max(0, betting.current_bet - player.current_bet)
    return PlayerActionContext(
        hole_cards=[],
        community=[],
        pot_total=pot.total,
        to_call=to_call,
        min_raise=betting.current_bet + betting.min_raise,
        max_raise=player.current_bet + player.chips,
        current_bet=player.current_bet,
        street="flop",
        num_active_players=sum(1 for p in betting.players if p.is_active),
        position_label="UTG",
    )


class TestBettingRound:
    def test_check_around(self):
        """All players check — round completes."""
        players = _make_players(3)
        pot = PotManager()
        betting = BettingRound(players=players, pot=pot, big_blind=20)

        actions = iter([
            Action(ActionType.CHECK),
            Action(ActionType.CHECK),
            Action(ActionType.CHECK),
        ])

        def get_action(p: Player, ctx: PlayerActionContext) -> Action:
            return next(actions)

        betting.run(get_action, lambda p: _make_context(p, betting, pot))

        # All players still active, no money in pot
        assert pot.total == 0
        assert all(p.is_active for p in players)

    def test_bet_call_call(self):
        """One player bets, two call."""
        players = _make_players(3)
        pot = PotManager()
        betting = BettingRound(players=players, pot=pot, big_blind=20)

        action_map = {
            0: [Action(ActionType.RAISE, 100)],  # P0 raises to 100
            1: [Action(ActionType.CALL)],          # P1 calls
            2: [Action(ActionType.CALL)],          # P2 calls
        }
        indices = {0: 0, 1: 0, 2: 0}

        def get_action(p: Player, ctx: PlayerActionContext) -> Action:
            idx = indices[p.seat]
            indices[p.seat] += 1
            return action_map[p.seat][idx]

        betting.run(get_action, lambda p: _make_context(p, betting, pot))

        assert pot.total == 300
        assert all(p.current_bet == 100 for p in players)

    def test_bet_raise_fold_call(self):
        """P0 bets, P1 raises, P2 folds, P0 calls."""
        players = _make_players(3)
        pot = PotManager()
        betting = BettingRound(players=players, pot=pot, big_blind=20)

        action_map = {
            0: [Action(ActionType.RAISE, 100), Action(ActionType.CALL)],
            1: [Action(ActionType.RAISE, 200)],
            2: [Action(ActionType.FOLD)],
        }
        indices = {0: 0, 1: 0, 2: 0}

        def get_action(p: Player, ctx: PlayerActionContext) -> Action:
            idx = indices[p.seat]
            indices[p.seat] += 1
            return action_map[p.seat][idx]

        betting.run(get_action, lambda p: _make_context(p, betting, pot))

        assert players[0].current_bet == 200
        assert players[1].current_bet == 200
        assert players[2].is_folded
        assert pot.total == 400

    def test_everyone_folds_to_one(self):
        """All but one player folds."""
        players = _make_players(3)
        pot = PotManager()
        betting = BettingRound(players=players, pot=pot, big_blind=20)

        action_map = {
            0: [Action(ActionType.RAISE, 100)],
            1: [Action(ActionType.FOLD)],
            2: [Action(ActionType.FOLD)],
        }
        indices = {0: 0, 1: 0, 2: 0}

        def get_action(p: Player, ctx: PlayerActionContext) -> Action:
            idx = indices[p.seat]
            indices[p.seat] += 1
            return action_map[p.seat][idx]

        betting.run(get_action, lambda p: _make_context(p, betting, pot))

        assert players[0].is_active
        assert players[1].is_folded
        assert players[2].is_folded

    def test_all_in_response(self):
        """Player goes all-in, others must respond."""
        players = _make_players(2, chips=500)
        pot = PotManager()
        betting = BettingRound(players=players, pot=pot, big_blind=20)

        action_map = {
            0: [Action(ActionType.ALL_IN, 500)],
            1: [Action(ActionType.CALL)],
        }
        indices = {0: 0, 1: 0}

        def get_action(p: Player, ctx: PlayerActionContext) -> Action:
            idx = indices[p.seat]
            indices[p.seat] += 1
            return action_map[p.seat][idx]

        betting.run(get_action, lambda p: _make_context(p, betting, pot))

        assert players[0].is_all_in
        assert pot.total == 1000
