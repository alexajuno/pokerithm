"""Poker game evaluation - comparing hands and determining winners."""

from dataclasses import dataclass

from .card import Card
from .hand import Hand, HandValue


@dataclass
class PlayerHand:
    """A player's hand in a game."""

    player_id: str | int
    hole_cards: list[Card]
    hand_value: HandValue | None = None

    def evaluate(self, community: list[Card]) -> HandValue:
        """Evaluate this player's hand with community cards."""
        all_cards = self.hole_cards + community
        hand = Hand(cards=all_cards)
        self.hand_value = hand.evaluate()
        return self.hand_value


@dataclass
class GameResult:
    """Result of evaluating a poker game."""

    winners: list[PlayerHand]
    all_hands: list[PlayerHand]
    is_tie: bool

    @property
    def winner(self) -> PlayerHand | None:
        """Get the single winner, or None if tie."""
        if len(self.winners) == 1:
            return self.winners[0]
        return None


def evaluate_game(
    players: list[PlayerHand],
    community: list[Card],
) -> GameResult:
    """Evaluate all players and determine winner(s).

    Args:
        players: List of PlayerHand with hole cards
        community: The 5 community cards (flop + turn + river)

    Returns:
        GameResult with winners and all evaluated hands
    """
    if len(community) < 5:
        raise ValueError(f"Need 5 community cards, got {len(community)}")

    # Evaluate all hands
    for player in players:
        player.evaluate(community)

    # Sort by hand value (highest first)
    sorted_hands = sorted(players, key=lambda p: p.hand_value, reverse=True)  # type: ignore

    # Find all players with the best hand (handles ties)
    best_value = sorted_hands[0].hand_value
    winners = [p for p in sorted_hands if p.hand_value == best_value]

    return GameResult(
        winners=winners,
        all_hands=sorted_hands,
        is_tie=len(winners) > 1,
    )


def compare_hands(hand1: Hand, hand2: Hand) -> int:
    """Compare two hands.

    Returns:
        1 if hand1 wins, -1 if hand2 wins, 0 if tie
    """
    v1, v2 = hand1.value, hand2.value
    if v1 > v2:
        return 1
    elif v1 < v2:
        return -1
    return 0
