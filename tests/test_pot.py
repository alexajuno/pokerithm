"""Tests for pot management and side pot calculation."""

from pokerithm.player import Player
from pokerithm.pot import PotManager


class TestPotManager:
    def test_add_and_total(self):
        pot = PotManager()
        pot.add(100)
        pot.add(200)
        assert pot.total == 300

    def test_reset(self):
        pot = PotManager()
        pot.add(500)
        pot.reset()
        assert pot.total == 0


class TestSidePots:
    def test_two_player_single_pot(self):
        """Two players with equal bets = one pot."""
        p1 = Player(name="A", chips=0, seat=0)
        p2 = Player(name="B", chips=0, seat=1)
        p1.total_bet_this_hand = 100
        p2.total_bet_this_hand = 100

        pots = PotManager.calculate_side_pots([p1, p2])
        assert len(pots) == 1
        assert pots[0].amount == 200
        assert sorted(p.name for p in pots[0].eligible_players) == ["A", "B"]

    def test_three_player_with_short_all_in(self):
        """Short stack all-in creates main pot + side pot."""
        p1 = Player(name="Short", chips=0, seat=0, is_all_in=True)
        p2 = Player(name="Mid", chips=500, seat=1)
        p3 = Player(name="Big", chips=500, seat=2)

        p1.total_bet_this_hand = 50
        p2.total_bet_this_hand = 100
        p3.total_bet_this_hand = 100

        pots = PotManager.calculate_side_pots([p1, p2, p3])
        assert len(pots) == 2

        # Main pot: 50 * 3 = 150, all three eligible
        assert pots[0].amount == 150
        assert len(pots[0].eligible_players) == 3

        # Side pot: 50 * 2 = 100, only p2 and p3
        assert pots[1].amount == 100
        assert sorted(p.name for p in pots[1].eligible_players) == ["Big", "Mid"]

    def test_folded_player_not_eligible(self):
        """Folded player's chips stay in pot but they can't win."""
        p1 = Player(name="Folder", chips=500, seat=0)
        p2 = Player(name="Winner", chips=500, seat=1)

        p1.total_bet_this_hand = 100
        p1.is_folded = True
        p2.total_bet_this_hand = 100

        pots = PotManager.calculate_side_pots([p1, p2])
        assert len(pots) == 1
        assert pots[0].amount == 200
        # Only p2 is eligible (p1 folded)
        assert pots[0].eligible_players == [p2]

    def test_no_bets_no_pots(self):
        """No bets = no pots."""
        p1 = Player(name="A", chips=500, seat=0)
        p2 = Player(name="B", chips=500, seat=1)
        pots = PotManager.calculate_side_pots([p1, p2])
        assert len(pots) == 0

    def test_three_different_all_in_levels(self):
        """Three players all-in for different amounts = 3 pots."""
        p1 = Player(name="Small", chips=0, seat=0, is_all_in=True)
        p2 = Player(name="Mid", chips=0, seat=1, is_all_in=True)
        p3 = Player(name="Big", chips=0, seat=2, is_all_in=True)

        p1.total_bet_this_hand = 50
        p2.total_bet_this_hand = 150
        p3.total_bet_this_hand = 300

        pots = PotManager.calculate_side_pots([p1, p2, p3])
        assert len(pots) == 3

        # Main pot: 50 * 3 = 150
        assert pots[0].amount == 150
        assert len(pots[0].eligible_players) == 3

        # Side pot 1: 100 * 2 = 200
        assert pots[1].amount == 200
        assert len(pots[1].eligible_players) == 2

        # Side pot 2: 150 * 1 = 150
        assert pots[2].amount == 150
        assert len(pots[2].eligible_players) == 1
