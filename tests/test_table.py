"""Tests for table (single-hand orchestrator)."""

from pokerithm.action import Action, ActionType
from pokerithm.bot import BotConfig
from pokerithm.player import Player, PlayerActionContext
from pokerithm.table import Table


def _fold_action(player: Player, ctx: PlayerActionContext) -> Action:
    """Always fold (used for bots that should fold)."""
    return Action(ActionType.FOLD)


class TestTable:
    def test_all_fold_to_one_player(self):
        """When everyone folds, last player wins the pot."""
        # Hero is BB so bots (BTN/SB) act first and fold before hero needs to act
        players = [
            Player(name="Bot1", chips=1000, seat=0),
            Player(name="Bot2", chips=1000, seat=1),
            Player(name="Hero", chips=1000, seat=2, is_human=True),
        ]

        def get_human(p: Player, ctx: PlayerActionContext) -> Action:
            return Action(ActionType.CHECK)

        # Make bots always fold
        fold_config = BotConfig(tightness=1.0, bluff_frequency=0.0, seed=0)

        table = Table(
            players=players,
            dealer_seat=0,
            small_blind=10,
            big_blind=20,
            get_human_action=get_human,
            bot_configs={"Bot1": fold_config, "Bot2": fold_config},
        )

        result = table.play_hand()
        assert not result.went_to_showdown
        # Someone won the pot
        total_chips = sum(p.chips for p in players)
        assert total_chips == 3000  # chip conservation

    def test_showdown_with_two_players(self):
        """Two players reach showdown."""
        players = [
            Player(name="P1", chips=1000, seat=0),
            Player(name="P2", chips=1000, seat=1),
        ]

        # Both check through every street
        def always_check(p: Player, ctx: PlayerActionContext) -> Action:
            if ctx.to_call > 0:
                return Action(ActionType.CALL)
            return Action(ActionType.CHECK)

        table = Table(
            players=players,
            dealer_seat=0,
            small_blind=10,
            big_blind=20,
            get_human_action=always_check,
            bot_configs={
                "P1": BotConfig(tightness=1.0, aggression=0.0, bluff_frequency=0.0, seed=42),
                "P2": BotConfig(tightness=1.0, aggression=0.0, bluff_frequency=0.0, seed=43),
            },
        )
        # Override: make both players "human" so we control their actions
        players[0].is_human = True
        players[1].is_human = True

        result = table.play_hand()
        assert result.went_to_showdown
        assert len(result.community) == 5
        # Chip conservation
        assert sum(p.chips for p in players) == 2000

    def test_chip_conservation(self):
        """Total chips remain constant across a hand."""
        players = [
            Player(name=f"P{i}", chips=500, seat=i, is_human=True)
            for i in range(4)
        ]
        initial_total = sum(p.chips for p in players)

        call_count = [0]

        def always_call(p: Player, ctx: PlayerActionContext) -> Action:
            call_count[0] += 1
            if ctx.to_call > 0:
                return Action(ActionType.CALL)
            return Action(ActionType.CHECK)

        table = Table(
            players=players,
            dealer_seat=0,
            small_blind=10,
            big_blind=20,
            get_human_action=always_call,
        )

        table.play_hand()
        assert sum(p.chips for p in players) == initial_total
