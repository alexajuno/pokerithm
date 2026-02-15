"""Tests for bot decision engine."""

from pokerithm.card import card
from pokerithm.action import ActionType
from pokerithm.bot import Bot, BotConfig, GameState
from pokerithm.position import Position
from pokerithm.ranges import hole_cards_to_key


class TestRangeKeys:
    def test_suited_hand(self):
        assert hole_cards_to_key(card("As"), card("Ks")) == "AKs"

    def test_offsuit_hand(self):
        assert hole_cards_to_key(card("As"), card("Kh")) == "AKo"

    def test_pair(self):
        assert hole_cards_to_key(card("7s"), card("7h")) == "77"

    def test_order_independence(self):
        assert hole_cards_to_key(card("9d"), card("Ts")) == "T9o"
        assert hole_cards_to_key(card("Ts"), card("9s")) == "T9s"


class TestPreflopDecisions:
    def test_premium_raises_from_utg(self):
        """AA should always raise, even from the tightest position."""
        bot = Bot(BotConfig(seed=42, bluff_frequency=0.0))
        state = GameState(
            hole_cards=[card("As"), card("Ah")],
            community=[],
            position=Position.UTG,
            num_opponents=5,
            pot_bb=1.5,
            to_call_bb=0.0,
            street="preflop",
            stack_bb=100.0,
        )
        decision = bot.decide(state)
        assert decision.action.type == ActionType.RAISE

    def test_trash_folds_from_utg(self):
        """72o should fold from UTG (no bluffs)."""
        bot = Bot(BotConfig(seed=42, bluff_frequency=0.0))
        state = GameState(
            hole_cards=[card("7d"), card("2c")],
            community=[],
            position=Position.UTG,
            num_opponents=5,
            pot_bb=1.5,
            to_call_bb=1.0,
            street="preflop",
            stack_bb=100.0,
        )
        decision = bot.decide(state)
        assert decision.action.type == ActionType.FOLD

    def test_wider_from_button(self):
        """A marginal hand like K9s should open from BTN but not UTG."""
        cfg = BotConfig(seed=42, bluff_frequency=0.0, tightness=0.3)

        state_btn = GameState(
            hole_cards=[card("Ks"), card("9s")],
            community=[],
            position=Position.BTN,
            num_opponents=2,
            pot_bb=1.5,
            to_call_bb=0.0,
            street="preflop",
            stack_bb=100.0,
        )
        state_utg = GameState(
            hole_cards=[card("Ks"), card("9s")],
            community=[],
            position=Position.UTG,
            num_opponents=5,
            pot_bb=1.5,
            to_call_bb=1.0,
            street="preflop",
            stack_bb=100.0,
        )
        assert Bot(cfg).decide(state_btn).action.type == ActionType.RAISE
        assert Bot(cfg).decide(state_utg).action.type == ActionType.FOLD

    def test_free_check_bb(self):
        """With trash in the BB and no raise to face, should check."""
        bot = Bot(BotConfig(seed=42, bluff_frequency=0.0))
        state = GameState(
            hole_cards=[card("7d"), card("2c")],
            community=[],
            position=Position.BB,
            num_opponents=2,
            pot_bb=2.0,
            to_call_bb=0.0,
            street="preflop",
            stack_bb=100.0,
        )
        decision = bot.decide(state)
        assert decision.action.type == ActionType.CHECK


class TestBluffing:
    def test_always_bluff_limped_pot(self):
        """With bluff_frequency=1.0, trash bluff-raises in a limped pot (1 BB to call)."""
        bot = Bot(BotConfig(seed=42, bluff_frequency=1.0, aggression=1.0))
        state = GameState(
            hole_cards=[card("7d"), card("2c")],
            community=[],
            position=Position.UTG,
            num_opponents=5,
            pot_bb=1.5,
            to_call_bb=1.0,  # just the BB, not a raise
            street="preflop",
            stack_bb=100.0,
        )
        decision = bot.decide(state)
        assert decision.action.type == ActionType.RAISE
        assert "Bluff" in decision.reasoning

    def test_always_bluff_unopened(self):
        """With bluff_frequency=1.0 and high aggression, trash should bluff in unopened pot."""
        bot = Bot(BotConfig(seed=42, bluff_frequency=1.0, aggression=1.0))
        state = GameState(
            hole_cards=[card("7d"), card("2c")],
            community=[],
            position=Position.BTN,
            num_opponents=2,
            pot_bb=1.5,
            to_call_bb=0.0,
            street="preflop",
            stack_bb=100.0,
        )
        decision = bot.decide(state)
        assert decision.action.type == ActionType.RAISE
        assert "Bluff" in decision.reasoning

    def test_never_bluff(self):
        """With bluff_frequency=0, trash should never bluff."""
        bot = Bot(BotConfig(seed=42, bluff_frequency=0.0))
        state = GameState(
            hole_cards=[card("7d"), card("2c")],
            community=[],
            position=Position.BTN,
            num_opponents=2,
            pot_bb=1.5,
            to_call_bb=1.0,
            street="preflop",
            stack_bb=100.0,
        )
        decision = bot.decide(state)
        assert decision.action.type == ActionType.FOLD


class TestSeedDeterminism:
    def test_same_seed_same_decision(self):
        """Identical seed + state must produce identical output."""
        cfg = BotConfig(seed=123)
        state = GameState(
            hole_cards=[card("Td"), card("9d")],
            community=[],
            position=Position.CO,
            num_opponents=3,
            pot_bb=1.5,
            to_call_bb=0.0,
            street="preflop",
            stack_bb=100.0,
        )
        d1 = Bot(cfg).decide(state)
        d2 = Bot(cfg).decide(state)
        assert d1.action == d2.action
        assert d1.reasoning == d2.reasoning


class TestPostflopDecisions:
    def test_high_equity_raises(self):
        """Top set on a dry board should raise."""
        bot = Bot(BotConfig(seed=42, bluff_frequency=0.0, aggression=0.8))
        state = GameState(
            hole_cards=[card("As"), card("Ah")],
            community=[card("Ad"), card("7c"), card("2h")],
            position=Position.BTN,
            num_opponents=1,
            pot_bb=6.0,
            to_call_bb=3.0,
            street="flop",
            stack_bb=100.0,
        )
        decision = bot.decide(state)
        assert decision.action.type == ActionType.RAISE
        assert decision.equity is not None
        assert decision.equity > 50

    def test_low_equity_folds(self):
        """Complete air on a wet board facing a big bet should fold."""
        bot = Bot(BotConfig(seed=42, bluff_frequency=0.0))
        state = GameState(
            hole_cards=[card("7d"), card("2c")],
            community=[card("As"), card("Ks"), card("Qs")],
            position=Position.UTG,
            num_opponents=3,
            pot_bb=10.0,
            to_call_bb=8.0,
            street="flop",
            stack_bb=100.0,
        )
        decision = bot.decide(state)
        assert decision.action.type == ActionType.FOLD

    def test_free_check_postflop(self):
        """Should check when there's nothing to call."""
        bot = Bot(BotConfig(seed=42, bluff_frequency=0.0, aggression=0.0))
        state = GameState(
            hole_cards=[card("9d"), card("8c")],
            community=[card("2s"), card("3h"), card("Kd")],
            position=Position.UTG,
            num_opponents=2,
            pot_bb=4.0,
            to_call_bb=0.0,
            street="flop",
            stack_bb=100.0,
        )
        decision = bot.decide(state)
        assert decision.action.type in (ActionType.CHECK, ActionType.RAISE)

    def test_postflop_bluff_late_position_only(self):
        """Bluffs should only happen from late position or blinds."""
        # From UTG with max bluff — still shouldn't bluff postflop
        bot = Bot(BotConfig(seed=42, bluff_frequency=1.0, aggression=1.0))
        state = GameState(
            hole_cards=[card("7d"), card("2c")],
            community=[card("As"), card("Ks"), card("Qs")],
            position=Position.UTG,
            num_opponents=3,
            pot_bb=10.0,
            to_call_bb=8.0,
            street="flop",
            stack_bb=100.0,
        )
        decision = bot.decide(state)
        # From UTG, should fold — no postflop bluffing from early position
        assert decision.action.type == ActionType.FOLD


class TestShortStackPushFold:
    def test_premium_shove_short_stack(self):
        """AA should shove with a short stack."""
        bot = Bot(BotConfig(seed=42, bluff_frequency=0.0))
        state = GameState(
            hole_cards=[card("As"), card("Ah")],
            community=[],
            position=Position.BTN,
            num_opponents=2,
            pot_bb=1.5,
            to_call_bb=0.0,
            street="preflop",
            stack_bb=8.0,
            invested_bb=0.0,
        )
        decision = bot.decide(state)
        assert decision.action.type == ActionType.ALL_IN

    def test_trash_folds_short_stack(self):
        """72o should fold even when short-stacked."""
        bot = Bot(BotConfig(seed=42, bluff_frequency=0.0))
        state = GameState(
            hole_cards=[card("7d"), card("2c")],
            community=[],
            position=Position.UTG,
            num_opponents=5,
            pot_bb=1.5,
            to_call_bb=1.0,
            street="preflop",
            stack_bb=8.0,
            invested_bb=0.0,
        )
        decision = bot.decide(state)
        assert decision.action.type == ActionType.FOLD

    def test_wider_push_very_short(self):
        """With 5 BB, push range should be wider — K7o is a shove."""
        bot = Bot(BotConfig(seed=42, bluff_frequency=0.0))
        state = GameState(
            hole_cards=[card("Kd"), card("7h")],
            community=[],
            position=Position.BTN,
            num_opponents=2,
            pot_bb=1.5,
            to_call_bb=0.0,
            street="preflop",
            stack_bb=5.0,
            invested_bb=1.0,
        )
        decision = bot.decide(state)
        assert decision.action.type == ActionType.ALL_IN

    def test_deep_stack_does_not_push(self):
        """With 100 BB, should open-raise, not shove."""
        bot = Bot(BotConfig(seed=42, bluff_frequency=0.0))
        state = GameState(
            hole_cards=[card("As"), card("Ah")],
            community=[],
            position=Position.BTN,
            num_opponents=2,
            pot_bb=1.5,
            to_call_bb=0.0,
            street="preflop",
            stack_bb=100.0,
        )
        decision = bot.decide(state)
        assert decision.action.type == ActionType.RAISE
        assert decision.action.type != ActionType.ALL_IN


class TestFacingRaise:
    def test_3bet_with_aces_facing_raise(self):
        """AA should 3-bet when facing a raise."""
        bot = Bot(BotConfig(seed=42, bluff_frequency=0.0))
        state = GameState(
            hole_cards=[card("As"), card("Ah")],
            community=[],
            position=Position.BTN,
            num_opponents=3,
            pot_bb=5.5,
            to_call_bb=2.5,
            street="preflop",
            stack_bb=100.0,
        )
        decision = bot.decide(state)
        assert decision.action.type == ActionType.RAISE
        assert "3-bet" in decision.reasoning

    def test_call_with_mid_pair_facing_raise(self):
        """88 should call a raise, not fold."""
        bot = Bot(BotConfig(seed=42, bluff_frequency=0.0))
        state = GameState(
            hole_cards=[card("8s"), card("8h")],
            community=[],
            position=Position.CO,
            num_opponents=3,
            pot_bb=5.5,
            to_call_bb=2.5,
            street="preflop",
            stack_bb=100.0,
        )
        decision = bot.decide(state)
        assert decision.action.type == ActionType.CALL

    def test_fold_trash_facing_raise(self):
        """72o should fold facing a raise."""
        bot = Bot(BotConfig(seed=42, bluff_frequency=0.0))
        state = GameState(
            hole_cards=[card("7d"), card("2c")],
            community=[],
            position=Position.CO,
            num_opponents=3,
            pot_bb=5.5,
            to_call_bb=2.5,
            street="preflop",
            stack_bb=100.0,
        )
        decision = bot.decide(state)
        assert decision.action.type == ActionType.FOLD


class TestPotCommitment:
    def test_pot_committed_calls_with_marginal_equity(self):
        """When >40% of stack invested, should call with weak equity rather than fold."""
        bot = Bot(BotConfig(seed=42, bluff_frequency=0.0, aggression=0.5))
        state = GameState(
            hole_cards=[card("Td"), card("9d")],
            community=[card("As"), card("7c"), card("2h")],
            position=Position.BTN,
            num_opponents=1,
            pot_bb=30.0,
            to_call_bb=5.0,
            street="flop",
            stack_bb=10.0,
            invested_bb=15.0,  # invested 60% of 25 BB effective stack
        )
        decision = bot.decide(state)
        # Should call rather than fold due to pot commitment
        assert decision.action.type in (ActionType.CALL, ActionType.RAISE)
