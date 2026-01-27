"""Poker odds and equity calculator using Monte Carlo simulation."""

import random
from dataclasses import dataclass
from typing import Sequence

from .card import Card, Rank, Suit
from .deck import Deck
from .hand import Hand, HandRank


@dataclass
class EquityResult:
    """Result of an equity calculation."""

    win_rate: float       # Probability of winning (0-1)
    tie_rate: float       # Probability of tying (0-1)
    lose_rate: float      # Probability of losing (0-1)
    simulations: int      # Number of simulations run
    hand_distribution: dict[HandRank, int]  # How often each hand was made

    @property
    def win_percent(self) -> float:
        """Win rate as percentage."""
        return self.win_rate * 100

    @property
    def equity(self) -> float:
        """Total equity (wins + half of ties) as percentage."""
        return (self.win_rate + self.tie_rate / 2) * 100


@dataclass
class Outs:
    """Cards that improve your hand."""

    cards: list[Card]
    improves_to: HandRank

    @property
    def count(self) -> int:
        return len(self.cards)


def calculate_equity(
    hero_cards: Sequence[Card],
    villain_cards: Sequence[Card] | None = None,
    community: Sequence[Card] | None = None,
    num_simulations: int = 10000,
) -> EquityResult:
    """Calculate win probability using Monte Carlo simulation.

    Args:
        hero_cards: Your hole cards (2 cards)
        villain_cards: Opponent's hole cards (2 cards), or None for random
        community: Known community cards (0-5), or None for none
        num_simulations: Number of random simulations to run

    Returns:
        EquityResult with win/tie/lose rates
    """
    hero_cards = list(hero_cards)
    villain_cards = list(villain_cards) if villain_cards else None
    community = list(community) if community else []

    if len(hero_cards) != 2:
        raise ValueError("Hero must have exactly 2 hole cards")
    if villain_cards and len(villain_cards) != 2:
        raise ValueError("Villain must have exactly 2 hole cards")
    if len(community) > 5:
        raise ValueError("Community can have at most 5 cards")

    wins = 0
    ties = 0
    losses = 0
    hand_counts: dict[HandRank, int] = {rank: 0 for rank in HandRank}

    # Cards that are already known
    known_cards = set(hero_cards + (villain_cards or []) + community)

    for _ in range(num_simulations):
        # Create deck without known cards
        deck = Deck()
        deck.cards = [c for c in deck.cards if c not in known_cards]
        deck.shuffle()

        # Deal villain cards if not known
        sim_villain = villain_cards if villain_cards else deck.deal(2)

        # Complete community cards
        cards_needed = 5 - len(community)
        sim_community = community + deck.deal(cards_needed)

        # Evaluate hands
        hero_hand = Hand(cards=hero_cards + sim_community)
        villain_hand = Hand(cards=sim_villain + sim_community)

        hero_value = hero_hand.value
        villain_value = villain_hand.value

        hand_counts[hero_value.rank] += 1

        # Compare
        if hero_value > villain_value:
            wins += 1
        elif hero_value < villain_value:
            losses += 1
        else:
            ties += 1

    return EquityResult(
        win_rate=wins / num_simulations,
        tie_rate=ties / num_simulations,
        lose_rate=losses / num_simulations,
        simulations=num_simulations,
        hand_distribution=hand_counts,
    )


def calculate_outs(
    hole_cards: Sequence[Card],
    community: Sequence[Card],
) -> list[Outs]:
    """Calculate outs - cards that improve your hand.

    Args:
        hole_cards: Your 2 hole cards
        community: Current community cards (3 or 4 cards - flop or turn)

    Returns:
        List of Outs showing which cards improve to which hands
    """
    hole_cards = list(hole_cards)
    community = list(community)

    if len(community) not in (3, 4):
        raise ValueError("Need 3 (flop) or 4 (turn) community cards")

    current_hand = Hand(cards=hole_cards + community + [_placeholder_card()])
    # Pad to 5 for evaluation during comparison
    if len(community) == 3:
        # On flop, add 2 placeholders
        padded = hole_cards + community
        # We need at least 5 cards, so pad with worst possible cards not in hand
        while len(padded) < 5:
            padded = padded + [_find_filler(set(padded))]
        current_hand = Hand(cards=padded)
    else:
        # On turn, just need 1 filler
        padded = hole_cards + community
        padded = padded + [_find_filler(set(padded))]
        current_hand = Hand(cards=padded)

    current_value = current_hand.value
    known = set(hole_cards + community)

    # Check each unknown card
    improvements: dict[HandRank, list[Card]] = {}

    for suit in Suit:
        for rank in Rank:
            card = Card(rank, suit)
            if card in known:
                continue

            # Evaluate with this card added
            test_cards = hole_cards + community + [card]
            if len(community) == 3:
                # On flop, add another filler
                test_cards = test_cards + [_find_filler(set(test_cards))]
            test_hand = Hand(cards=test_cards)
            test_value = test_hand.value

            if test_value > current_value:
                if test_value.rank not in improvements:
                    improvements[test_value.rank] = []
                improvements[test_value.rank].append(card)

    return [
        Outs(cards=cards, improves_to=rank)
        for rank, cards in sorted(improvements.items(), key=lambda x: x[0], reverse=True)
    ]


def _placeholder_card() -> Card:
    """Return a low card for padding hands."""
    return Card(Rank.TWO, Suit.CLUBS)


def _find_filler(exclude: set[Card]) -> Card:
    """Find a low card not in the excluded set."""
    for suit in Suit:
        for rank in [Rank.TWO, Rank.THREE, Rank.FOUR]:
            c = Card(rank, suit)
            if c not in exclude:
                return c
    raise ValueError("Could not find filler card")


def preflop_equity(
    hero_cards: Sequence[Card],
    num_opponents: int = 1,
    num_simulations: int = 10000,
) -> float:
    """Calculate preflop win equity against random opponents.

    Args:
        hero_cards: Your 2 hole cards
        num_opponents: Number of opponents with random hands
        num_simulations: Number of simulations

    Returns:
        Win equity as percentage (0-100)
    """
    hero_cards = list(hero_cards)
    wins = 0
    ties = 0

    for _ in range(num_simulations):
        deck = Deck()
        deck.cards = [c for c in deck.cards if c not in hero_cards]
        deck.shuffle()

        # Deal opponents
        opponents = [deck.deal(2) for _ in range(num_opponents)]

        # Deal community
        community = deck.deal(5)

        # Evaluate all hands
        hero_value = Hand(cards=hero_cards + community).value
        opponent_values = [Hand(cards=opp + community).value for opp in opponents]

        best_opponent = max(opponent_values)

        if hero_value > best_opponent:
            wins += 1
        elif hero_value == best_opponent:
            ties += 1

    return (wins + ties / 2) / num_simulations * 100
