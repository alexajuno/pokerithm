"""Tests for odds calculator."""

import pytest
from pokerithm.card import card
from pokerithm.calculator import calculate_equity, calculate_outs, preflop_equity
from pokerithm.hand import HandRank


class TestEquityCalculator:
    def test_aces_vs_kings_preflop(self):
        """AA vs KK - aces should win ~80% of the time."""
        result = calculate_equity(
            hero_cards=[card("As"), card("Ah")],
            villain_cards=[card("Ks"), card("Kh")],
            num_simulations=5000,
        )
        # AA vs KK is roughly 80-20
        assert 75 < result.win_percent < 85
        assert result.win_rate + result.tie_rate + result.lose_rate == pytest.approx(1.0)

    def test_dominated_hand(self):
        """AK vs A5 - AK should dominate."""
        result = calculate_equity(
            hero_cards=[card("As"), card("Kh")],
            villain_cards=[card("Ad"), card("5c")],
            num_simulations=5000,
        )
        # AK dominates A5, should win ~70%+
        assert result.win_percent > 65

    def test_coin_flip(self):
        """Pair vs two overcards is roughly 50-50."""
        result = calculate_equity(
            hero_cards=[card("Jd"), card("Jc")],  # Pocket jacks
            villain_cards=[card("As"), card("Kh")],  # AK
            num_simulations=5000,
        )
        # JJ vs AK is roughly 55-45
        assert 45 < result.win_percent < 65

    def test_with_community_cards(self):
        """Test equity calculation with known community cards."""
        result = calculate_equity(
            hero_cards=[card("As"), card("Ks")],
            villain_cards=[card("Jd"), card("Jc")],
            community=[card("Qs"), card("Js"), card("2h")],  # Villain has trips
            num_simulations=5000,
        )
        # Hero has flush draw + gutshot, villain has trips
        # Hero needs flush or straight to win
        assert result.simulations == 5000

    def test_random_villain(self):
        """Test equity against unknown opponent."""
        result = calculate_equity(
            hero_cards=[card("As"), card("Ah")],
            villain_cards=None,  # Random opponent
            num_simulations=3000,
        )
        # AA vs random should win ~85%
        assert result.win_percent > 80

    def test_hand_distribution(self):
        """Check that hand distribution is tracked."""
        result = calculate_equity(
            hero_cards=[card("As"), card("Ah")],
            villain_cards=[card("Ks"), card("Kh")],
            num_simulations=1000,
        )
        total_hands = sum(result.hand_distribution.values())
        assert total_hands == 1000


class TestOutsCalculator:
    def test_flush_draw_outs(self):
        """Four to a flush has 9 outs."""
        outs_list = calculate_outs(
            hole_cards=[card("As"), card("Ks")],
            community=[card("5s"), card("7s"), card("Jd")],  # 4 spades
        )
        # Should have outs to flush
        flush_outs = [o for o in outs_list if o.improves_to == HandRank.FLUSH]
        assert len(flush_outs) > 0
        # 9 remaining spades
        assert flush_outs[0].count == 9

    def test_straight_draw_outs(self):
        """Open-ended straight draw has 8 outs."""
        outs_list = calculate_outs(
            hole_cards=[card("9s"), card("8d")],
            community=[card("7h"), card("6c"), card("2s")],  # 9-8-7-6
        )
        # Should have outs to straight (any 5 or T)
        straight_outs = [o for o in outs_list if o.improves_to == HandRank.STRAIGHT]
        assert len(straight_outs) > 0
        # 4 fives + 4 tens = 8 outs
        assert straight_outs[0].count == 8


class TestPreflopEquity:
    def test_aces_preflop(self):
        """Pocket aces vs 1 random opponent."""
        equity = preflop_equity(
            hero_cards=[card("As"), card("Ah")],
            num_opponents=1,
            num_simulations=3000,
        )
        # AA vs random ~85%
        assert equity > 80

    def test_more_opponents_reduces_equity(self):
        """More opponents = lower equity."""
        equity_1 = preflop_equity(
            hero_cards=[card("As"), card("Ah")],
            num_opponents=1,
            num_simulations=2000,
        )
        equity_3 = preflop_equity(
            hero_cards=[card("As"), card("Ah")],
            num_opponents=3,
            num_simulations=2000,
        )
        assert equity_1 > equity_3
