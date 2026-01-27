"""Tests for card module."""

import pytest
from pokerithm.card import Card, Rank, Suit, card


class TestCard:
    def test_card_creation(self):
        c = Card(Rank.ACE, Suit.SPADES)
        assert c.rank == Rank.ACE
        assert c.suit == Suit.SPADES

    def test_card_str(self):
        c = Card(Rank.ACE, Suit.SPADES)
        assert str(c) == "A♠"

        c = Card(Rank.TEN, Suit.HEARTS)
        assert str(c) == "10♥"

    def test_card_from_str(self):
        assert Card.from_str("As") == Card(Rank.ACE, Suit.SPADES)
        assert Card.from_str("kh") == Card(Rank.KING, Suit.HEARTS)
        assert Card.from_str("10d") == Card(Rank.TEN, Suit.DIAMONDS)
        assert Card.from_str("2c") == Card(Rank.TWO, Suit.CLUBS)
        assert Card.from_str("Tc") == Card(Rank.TEN, Suit.CLUBS)

    def test_card_shorthand(self):
        assert card("As") == Card(Rank.ACE, Suit.SPADES)

    def test_invalid_card(self):
        with pytest.raises(ValueError):
            Card.from_str("Xx")
        with pytest.raises(ValueError):
            Card.from_str("1s")

    def test_rank_comparison(self):
        assert Rank.ACE > Rank.KING
        assert Rank.TWO < Rank.THREE

    def test_card_hashable(self):
        # Cards should be usable in sets/dicts
        cards = {card("As"), card("Kh"), card("As")}
        assert len(cards) == 2
