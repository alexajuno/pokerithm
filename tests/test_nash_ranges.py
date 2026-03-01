"""Tests for Nash equilibrium push/fold ranges."""

from pokerithm.nash_ranges import (
    get_shove_range,
    get_call_range,
    is_in_range,
    VILLAIN_CALL_RANGES,
)


class TestShoveRanges:
    def test_aa_always_shove(self):
        """AA is a shove at any stack depth and position."""
        for bb in [3, 6, 10, 15, 20]:
            rng = get_shove_range(stack_bb=bb, num_players=4)
            assert "AA" in rng, f"AA should be in shove range at {bb}bb"

    def test_deeper_stack_tighter_range(self):
        """Shove range should narrow as stacks get deeper."""
        range_5bb = get_shove_range(stack_bb=5, num_players=4)
        range_10bb = get_shove_range(stack_bb=10, num_players=4)
        range_15bb = get_shove_range(stack_bb=15, num_players=4)
        assert len(range_5bb) > len(range_10bb) > len(range_15bb)

    def test_fewer_players_wider_range(self):
        """Fewer remaining players = wider shove range."""
        range_6p = get_shove_range(stack_bb=8, num_players=6)
        range_3p = get_shove_range(stack_bb=8, num_players=3)
        assert len(range_3p) >= len(range_6p)

    def test_72o_never_shove_deep(self):
        """72o should not be in shove range at 15bb+."""
        rng = get_shove_range(stack_bb=15, num_players=6)
        assert "72o" not in rng


class TestCallRanges:
    def test_aa_always_calls(self):
        rng = get_call_range(stack_bb=10)
        assert "AA" in rng

    def test_call_range_subset_of_shove(self):
        """Call range should be tighter than shove range (risk premium)."""
        call_rng = get_call_range(stack_bb=8)
        shove_rng = get_shove_range(stack_bb=8, num_players=4)
        assert len(call_rng) <= len(shove_rng)


class TestVillainCallRanges:
    def test_tight_villain_tighter_than_normal(self):
        tight = VILLAIN_CALL_RANGES["tight"]
        normal = VILLAIN_CALL_RANGES["normal"]
        assert len(tight) < len(normal)

    def test_normal_tighter_than_loose(self):
        normal = VILLAIN_CALL_RANGES["normal"]
        loose = VILLAIN_CALL_RANGES["loose"]
        assert len(normal) < len(loose)

    def test_all_styles_include_aces(self):
        for style in ("tight", "normal", "loose"):
            assert "AA" in VILLAIN_CALL_RANGES[style]


class TestIsInRange:
    def test_hand_in_range(self):
        assert is_in_range("AA", {"AA", "KK", "QQ"})

    def test_hand_not_in_range(self):
        assert not is_in_range("72o", {"AA", "KK", "QQ"})
