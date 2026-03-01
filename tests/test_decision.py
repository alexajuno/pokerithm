"""Tests for EV decision engine."""

from pokerithm.decision import decide, Situation


class TestShortStackDecisions:
    """Push/fold decisions at <=10bb."""

    def test_aa_always_shove(self):
        """AA is always a shove regardless of position."""
        sit = Situation(
            hand="AA", stack_bb=6.0, position="utg",
            players=4, pot_bb=1.5, villain_style="tight",
        )
        result = decide(sit)
        assert result.action == "SHOVE"
        assert result.ev_shove > 0

    def test_72o_folds_utg(self):
        """72o should fold from UTG at any stack depth."""
        sit = Situation(
            hand="72o", stack_bb=8.0, position="utg",
            players=4, pot_bb=1.5, villain_style="tight",
        )
        result = decide(sit)
        assert result.action == "FOLD"

    def test_shove_ev_positive_for_good_hand(self):
        """A decent hand like A5s should have positive shove EV at 6bb."""
        sit = Situation(
            hand="A5s", stack_bb=6.0, position="btn",
            players=3, pot_bb=1.5, villain_style="tight",
        )
        result = decide(sit)
        assert result.action == "SHOVE"
        assert result.ev_shove > 0

    def test_fold_ev_is_zero(self):
        """EV of folding is always 0."""
        sit = Situation(
            hand="72o", stack_bb=8.0, position="utg",
            players=4, pot_bb=1.5, villain_style="tight",
        )
        result = decide(sit)
        assert result.ev_fold == 0.0

    def test_tight_villain_widens_shove_range(self):
        """Against tight villains, more hands become profitable shoves."""
        hand = "K7o"
        sit_tight = Situation(
            hand=hand, stack_bb=8.0, position="co",
            players=4, pot_bb=1.5, villain_style="tight",
        )
        sit_loose = Situation(
            hand=hand, stack_bb=8.0, position="co",
            players=4, pot_bb=1.5, villain_style="loose",
        )
        result_tight = decide(sit_tight)
        result_loose = decide(sit_loose)
        assert result_tight.ev_shove > result_loose.ev_shove


class TestMediumStackDecisions:
    """Raise/shove/fold decisions at 10-25bb."""

    def test_premium_hand_raises(self):
        """AA at 20bb should recommend raising, not just shoving."""
        sit = Situation(
            hand="AA", stack_bb=20.0, position="utg",
            players=4, pot_bb=1.5, villain_style="normal",
        )
        result = decide(sit)
        assert result.action in ("RAISE", "SHOVE")
        assert result.ev_shove > 0

    def test_raise_ev_calculated_for_medium_stacks(self):
        """At 18bb, raise EV should be calculated (not None)."""
        sit = Situation(
            hand="AKs", stack_bb=18.0, position="btn",
            players=3, pot_bb=1.5, villain_style="tight",
        )
        result = decide(sit)
        assert result.ev_raise is not None

    def test_raise_size_provided(self):
        """When raising, a specific size should be recommended."""
        sit = Situation(
            hand="AQs", stack_bb=20.0, position="co",
            players=4, pot_bb=1.5, villain_style="tight",
        )
        result = decide(sit)
        if result.action == "RAISE":
            assert result.raise_size is not None
            assert result.raise_size > 0


class TestDecisionMetadata:
    def test_reasoning_not_empty(self):
        sit = Situation(
            hand="AA", stack_bb=8.0, position="utg",
            players=4, pot_bb=1.5, villain_style="tight",
        )
        result = decide(sit)
        assert len(result.reasoning) > 0

    def test_fold_equity_between_0_and_1(self):
        sit = Situation(
            hand="AKs", stack_bb=8.0, position="btn",
            players=3, pot_bb=1.5, villain_style="tight",
        )
        result = decide(sit)
        assert 0.0 <= result.fold_equity <= 1.0

    def test_equity_called_between_0_and_100(self):
        sit = Situation(
            hand="AKs", stack_bb=8.0, position="btn",
            players=3, pot_bb=1.5, villain_style="tight",
        )
        result = decide(sit)
        assert 0.0 <= result.equity_called <= 100.0

    def test_confidence_present(self):
        sit = Situation(
            hand="AA", stack_bb=8.0, position="utg",
            players=4, pot_bb=1.5, villain_style="tight",
        )
        result = decide(sit)
        assert result.confidence in ("high", "medium", "low")
