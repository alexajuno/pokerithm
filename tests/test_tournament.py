"""Tests for tournament loop."""

from pokerithm.action import Action, ActionType
from pokerithm.player import Player, PlayerActionContext
from pokerithm.tournament import BlindLevel, Tournament, TournamentConfig


def _make_tournament(
    num_players: int = 3,
    starting_stack: int = 100,
    hands_per_level: int = 5,
) -> tuple[Tournament, list[Player]]:
    """Create a small test tournament."""
    players = [
        Player(name=f"P{i}", chips=starting_stack, seat=i, is_human=True)
        for i in range(num_players)
    ]

    config = TournamentConfig(
        num_bots=num_players - 1,
        starting_stack=starting_stack,
        hands_per_level=hands_per_level,
        blind_schedule=[
            BlindLevel(5, 10),
            BlindLevel(10, 20),
            BlindLevel(25, 50),
        ],
    )

    tournament = Tournament(config=config, players=players)
    return tournament, players


class TestTournament:
    def test_dealer_rotation(self):
        """Dealer moves to next player each hand."""
        tournament, players = _make_tournament()
        dealers: list[int] = []

        def track_dealer(hand_num: int, level: BlindLevel, dealer: int) -> None:
            dealers.append(dealer)

        # All players just call/check to keep things simple
        def passive_action(p: Player, ctx: PlayerActionContext) -> Action:
            if ctx.to_call > 0:
                return Action(ActionType.CALL)
            return Action(ActionType.CHECK)

        tournament.get_human_action = passive_action
        tournament.on_hand_start = track_dealer

        # Run just a few hands by capping via callback
        hand_count = [0]

        class StopAfterN(Exception):
            pass

        def stop_after_3(result):
            hand_count[0] += 1
            if hand_count[0] >= 3:
                raise StopAfterN

        tournament.on_hand_end = stop_after_3

        try:
            tournament.run()
        except StopAfterN:
            pass

        assert len(dealers) >= 3
        # Dealers should be different (rotation)
        assert len(set(dealers)) > 1

    def test_blind_level_increase(self):
        """Blinds increase after hands_per_level hands."""
        tournament, players = _make_tournament(
            starting_stack=5000, hands_per_level=3
        )

        blind_levels: list[BlindLevel] = []

        def track_blinds(level: BlindLevel, idx: int) -> None:
            blind_levels.append(level)

        def passive_action(p: Player, ctx: PlayerActionContext) -> Action:
            if ctx.to_call > 0:
                return Action(ActionType.CALL)
            return Action(ActionType.CHECK)

        tournament.get_human_action = passive_action
        tournament.on_blind_increase = track_blinds

        hand_count = [0]

        class StopAfterN(Exception):
            pass

        def stop_after_7(result):
            hand_count[0] += 1
            if hand_count[0] >= 7:
                raise StopAfterN

        tournament.on_hand_end = stop_after_7

        try:
            tournament.run()
        except StopAfterN:
            pass

        # After 3 hands, blinds should increase at least once
        assert len(blind_levels) >= 1
        assert blind_levels[0].big_blind == 20  # Second level

    def test_elimination(self):
        """Player with no chips is eliminated."""
        # Give one player very few chips so they bust quickly
        players = [
            Player(name="Rich", chips=1000, seat=0, is_human=True),
            Player(name="Poor", chips=5, seat=1, is_human=True),  # < SB
            Player(name="Mid", chips=1000, seat=2, is_human=True),
        ]

        config = TournamentConfig(
            num_bots=2,
            starting_stack=1000,
            hands_per_level=100,
            blind_schedule=[BlindLevel(10, 20)],
        )

        tournament = Tournament(config=config, players=players)
        eliminated: list[str] = []

        def track_elimination(p: Player, place: int) -> None:
            eliminated.append(p.name)

        def passive(p: Player, ctx: PlayerActionContext) -> Action:
            if ctx.to_call > 0:
                return Action(ActionType.CALL)
            return Action(ActionType.CHECK)

        tournament.get_human_action = passive
        tournament.on_elimination = track_elimination

        hand_count = [0]

        class StopAfterN(Exception):
            pass

        def stop_after_10(result):
            hand_count[0] += 1
            if hand_count[0] >= 10:
                raise StopAfterN

        tournament.on_hand_end = stop_after_10

        try:
            tournament.run()
        except StopAfterN:
            pass

        # Poor should be eliminated (only 15 chips, BB is 10)
        assert "Poor" in eliminated

    def test_tournament_ends_with_one_player(self):
        """Tournament ends when only one player has chips."""
        # Three players: two short stacks that will bust fast
        players = [
            Player(name="Big", chips=500, seat=0, is_human=True),
            Player(name="Tiny1", chips=10, seat=1, is_human=True),
            Player(name="Tiny2", chips=10, seat=2, is_human=True),
        ]

        config = TournamentConfig(
            num_bots=2,
            starting_stack=500,
            hands_per_level=100,
            blind_schedule=[BlindLevel(10, 20)],
        )

        tournament = Tournament(config=config, players=players)
        winner_name: list[str | None] = [None]

        def track_winner(p: Player) -> None:
            winner_name[0] = p.name

        def passive(p: Player, ctx: PlayerActionContext) -> Action:
            if ctx.to_call > 0:
                return Action(ActionType.CALL)
            return Action(ActionType.CHECK)

        tournament.get_human_action = passive
        tournament.on_tournament_end = track_winner

        result = tournament.run()
        assert winner_name[0] is not None
        assert result.chips > 0
