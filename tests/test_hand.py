"""Tests for hand evaluation."""

import pytest
from pokerithm.card import card
from pokerithm.hand import Hand, HandRank, HandValue


class TestHandRanking:
    """Test that hands are correctly identified."""

    def test_high_card(self):
        hand = Hand([card("As"), card("Kd"), card("9h"), card("5c"), card("2s")])
        assert hand.value.rank == HandRank.HIGH_CARD

    def test_one_pair(self):
        hand = Hand([card("As"), card("Ad"), card("Kh"), card("5c"), card("2s")])
        assert hand.value.rank == HandRank.ONE_PAIR
        assert hand.value.primary == (14,)  # Pair of aces

    def test_two_pair(self):
        hand = Hand([card("As"), card("Ad"), card("Kh"), card("Kc"), card("2s")])
        assert hand.value.rank == HandRank.TWO_PAIR
        assert hand.value.primary == (14, 13)  # Aces and kings

    def test_three_of_a_kind(self):
        hand = Hand([card("As"), card("Ad"), card("Ah"), card("Kc"), card("2s")])
        assert hand.value.rank == HandRank.THREE_OF_A_KIND
        assert hand.value.primary == (14,)

    def test_straight(self):
        hand = Hand([card("9s"), card("8d"), card("7h"), card("6c"), card("5s")])
        assert hand.value.rank == HandRank.STRAIGHT
        assert hand.value.primary == (9,)  # 9-high straight

    def test_straight_wheel(self):
        """A-2-3-4-5 is the lowest straight (wheel)."""
        hand = Hand([card("As"), card("2d"), card("3h"), card("4c"), card("5s")])
        assert hand.value.rank == HandRank.STRAIGHT
        assert hand.value.primary == (5,)  # 5-high (ace plays low)

    def test_straight_broadway(self):
        """A-K-Q-J-10 is the highest straight (broadway)."""
        hand = Hand([card("As"), card("Kd"), card("Qh"), card("Jc"), card("Ts")])
        assert hand.value.rank == HandRank.STRAIGHT
        assert hand.value.primary == (14,)

    def test_flush(self):
        hand = Hand([card("As"), card("Ks"), card("9s"), card("5s"), card("2s")])
        assert hand.value.rank == HandRank.FLUSH

    def test_full_house(self):
        hand = Hand([card("As"), card("Ad"), card("Ah"), card("Kc"), card("Ks")])
        assert hand.value.rank == HandRank.FULL_HOUSE
        assert hand.value.primary == (14, 13)  # Aces full of kings

    def test_four_of_a_kind(self):
        hand = Hand([card("As"), card("Ad"), card("Ah"), card("Ac"), card("Ks")])
        assert hand.value.rank == HandRank.FOUR_OF_A_KIND
        assert hand.value.primary == (14,)

    def test_straight_flush(self):
        hand = Hand([card("9s"), card("8s"), card("7s"), card("6s"), card("5s")])
        assert hand.value.rank == HandRank.STRAIGHT_FLUSH
        assert hand.value.primary == (9,)

    def test_royal_flush(self):
        """Royal flush is just the highest straight flush."""
        hand = Hand([card("As"), card("Ks"), card("Qs"), card("Js"), card("Ts")])
        assert hand.value.rank == HandRank.STRAIGHT_FLUSH
        assert hand.value.primary == (14,)


class TestHandComparison:
    """Test that hands compare correctly."""

    def test_rank_beats_rank(self):
        pair = Hand([card("As"), card("Ad"), card("Kh"), card("5c"), card("2s")])
        high_card = Hand([card("As"), card("Kd"), card("Qh"), card("5c"), card("2s")])
        assert pair.value > high_card.value

    def test_higher_pair_wins(self):
        pair_aces = Hand([card("As"), card("Ad"), card("Kh"), card("5c"), card("2s")])
        pair_kings = Hand([card("Ks"), card("Kd"), card("Qh"), card("5c"), card("2s")])
        assert pair_aces.value > pair_kings.value

    def test_same_pair_kicker_decides(self):
        pair_ace_kicker = Hand([card("Ks"), card("Kd"), card("Ah"), card("5c"), card("2s")])
        pair_queen_kicker = Hand([card("Ks"), card("Kh"), card("Qd"), card("5c"), card("2s")])
        assert pair_ace_kicker.value > pair_queen_kicker.value

    def test_flush_high_card_wins(self):
        flush_ace = Hand([card("As"), card("Ks"), card("9s"), card("5s"), card("2s")])
        flush_king = Hand([card("Kh"), card("Qh"), card("9h"), card("5h"), card("2h")])
        assert flush_ace.value > flush_king.value


class TestSevenCardHand:
    """Test evaluation with 7 cards (Texas Hold'em)."""

    def test_best_five_selected(self):
        # 7 cards: should find the flush
        hand = Hand([
            card("As"), card("Ks"), card("Qs"),  # 3 spades
            card("Js"), card("9s"),              # 2 more spades = flush
            card("2h"), card("3d"),              # garbage
        ])
        assert hand.value.rank == HandRank.FLUSH

    def test_finds_straight(self):
        hand = Hand([
            card("9s"), card("8d"), card("7h"), card("6c"), card("5s"),
            card("2h"), card("2d"),
        ])
        # Straight beats the pair
        assert hand.value.rank == HandRank.STRAIGHT
