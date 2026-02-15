"""Tests for game evaluation."""

from pokerithm.card import card
from pokerithm.evaluator import PlayerHand, evaluate_game, compare_hands
from pokerithm.hand import Hand, HandRank


class TestEvaluateGame:
    def test_single_winner(self):
        players = [
            PlayerHand("Alice", [card("As"), card("Ad")]),  # Pair of aces in hole
            PlayerHand("Bob", [card("Ks"), card("Kd")]),    # Pair of kings in hole
        ]
        community = [card("2h"), card("5c"), card("9s"), card("Jd"), card("3h")]

        result = evaluate_game(players, community)

        assert not result.is_tie
        assert result.winner is not None
        assert result.winner.player_id == "Alice"
        assert result.winner.hand_value is not None
        assert result.winner.hand_value.rank == HandRank.ONE_PAIR

    def test_tie_game(self):
        players = [
            PlayerHand("Alice", [card("As"), card("2d")]),
            PlayerHand("Bob", [card("Ac"), card("3d")]),
        ]
        # Community makes the best hand for both (broadway straight)
        community = [card("Kh"), card("Qh"), card("Jh"), card("Th"), card("4s")]

        result = evaluate_game(players, community)

        # Both have the same straight from community
        assert result.is_tie
        assert len(result.winners) == 2

    def test_flush_beats_straight(self):
        players = [
            PlayerHand("Alice", [card("2s"), card("3s")]),  # Will make flush
            PlayerHand("Bob", [card("9d"), card("8c")]),    # Will make straight
        ]
        community = [card("As"), card("Ks"), card("7s"), card("6h"), card("5d")]

        result = evaluate_game(players, community)

        assert result.winner is not None
        assert result.winner.player_id == "Alice"
        assert result.winner.hand_value is not None
        assert result.winner.hand_value.rank == HandRank.FLUSH

    def test_kicker_decides(self):
        players = [
            PlayerHand("Alice", [card("As"), card("Kd")]),  # Pair of aces, K kicker
            PlayerHand("Bob", [card("Ac"), card("Qd")]),    # Pair of aces, Q kicker
        ]
        community = [card("Ad"), card("5h"), card("7c"), card("9s"), card("2h")]

        result = evaluate_game(players, community)

        # Both have three aces, but Alice has K kicker
        assert result.winner is not None
        assert result.winner.player_id == "Alice"

    def test_all_hands_ranked(self):
        players = [
            PlayerHand("Alice", [card("2s"), card("3d")]),
            PlayerHand("Bob", [card("As"), card("Ad")]),
            PlayerHand("Charlie", [card("Ks"), card("Kd")]),
        ]
        community = [card("5h"), card("7c"), card("9s"), card("Jd"), card("2h")]

        result = evaluate_game(players, community)

        # Check all hands are sorted best to worst
        assert result.all_hands[0].player_id == "Bob"      # Pair of aces
        assert result.all_hands[1].player_id == "Charlie"  # Pair of kings
        assert result.all_hands[2].player_id == "Alice"    # Pair of twos


class TestCompareHands:
    def test_compare_different_ranks(self):
        flush = Hand([card("As"), card("Ks"), card("9s"), card("5s"), card("2s")])
        pair = Hand([card("As"), card("Ad"), card("Kh"), card("5c"), card("2h")])

        assert compare_hands(flush, pair) == 1
        assert compare_hands(pair, flush) == -1

    def test_compare_equal_hands(self):
        hand1 = Hand([card("As"), card("Kd"), card("Qh"), card("Jc"), card("9s")])
        hand2 = Hand([card("Ac"), card("Kh"), card("Qs"), card("Jd"), card("9h")])

        assert compare_hands(hand1, hand2) == 0
