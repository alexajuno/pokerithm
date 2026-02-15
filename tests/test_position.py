"""Tests for position module."""

import pytest
from pokerithm.position import Position, position_from_utg_distance


class TestPositionProperties:
    def test_early_positions(self):
        assert Position.UTG.is_early
        assert Position.UTG_1.is_early
        assert not Position.CO.is_early

    def test_middle_positions(self):
        assert Position.MP.is_middle
        assert Position.HJ.is_middle
        assert not Position.UTG.is_middle

    def test_late_positions(self):
        assert Position.CO.is_late
        assert Position.BTN.is_late
        assert not Position.SB.is_late

    def test_blind_positions(self):
        assert Position.SB.is_blind
        assert Position.BB.is_blind
        assert not Position.BTN.is_blind

    def test_label_format(self):
        assert "UTG" in Position.UTG.label
        assert "Button" in Position.BTN.label
        assert "Big Blind" in Position.BB.label

    def test_short_format(self):
        assert Position.UTG.short == "UTG"
        assert Position.BTN.short == "BTN"
        assert Position.BB.short == "BB"


class TestPositionFromUtgDistance:
    def test_6max_table(self):
        """6-player table: UTG, MP, CO, BTN, SB, BB."""
        assert position_from_utg_distance(0, 6) == Position.UTG
        assert position_from_utg_distance(1, 6) == Position.HJ
        assert position_from_utg_distance(2, 6) == Position.CO
        assert position_from_utg_distance(3, 6) == Position.BTN
        assert position_from_utg_distance(4, 6) == Position.SB
        assert position_from_utg_distance(5, 6) == Position.BB

    def test_9max_table(self):
        """9-player table: UTG, UTG+1, MP, HJ, CO, BTN, SB, BB."""
        assert position_from_utg_distance(0, 9) == Position.UTG
        assert position_from_utg_distance(1, 9) == Position.UTG_1
        assert position_from_utg_distance(2, 9) == Position.MP
        assert position_from_utg_distance(3, 9) == Position.MP
        assert position_from_utg_distance(4, 9) == Position.HJ
        assert position_from_utg_distance(5, 9) == Position.CO
        assert position_from_utg_distance(6, 9) == Position.BTN
        assert position_from_utg_distance(7, 9) == Position.SB
        assert position_from_utg_distance(8, 9) == Position.BB

    def test_heads_up(self):
        """2-player: SB, BB."""
        assert position_from_utg_distance(0, 2) == Position.SB
        assert position_from_utg_distance(1, 2) == Position.BB

    def test_invalid_distance(self):
        with pytest.raises(ValueError):
            position_from_utg_distance(-1, 6)
        with pytest.raises(ValueError):
            position_from_utg_distance(6, 6)

    def test_regression_matches_old_labels(self):
        """Ensure the new enum produces the same labels as the old _get_position_name."""
        # 6-max mapping from old code
        expected = {
            (0, 6): "Under the Gun (UTG)",
            (3, 6): "Button (BTN)",
            (4, 6): "Small Blind (SB)",
            (5, 6): "Big Blind (BB)",
        }
        for (dist, total), label in expected.items():
            assert position_from_utg_distance(dist, total).label == label
