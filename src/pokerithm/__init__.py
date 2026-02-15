"""Pokerithm - Poker hand tracking and probability calculator."""

__version__ = "0.1.0"

from .action import Action, ActionType, BotDecision
from .ai_bot import AiBot, AiBotConfig, AiDebugInfo
from .bot import Bot, BotConfig, GameState
from .card import Card, Rank, Suit, card
from .calculator import calculate_equity, calculate_outs, preflop_equity, EquityResult
from .deck import Deck
from .evaluator import PlayerHand, GameResult, evaluate_game, compare_hands
from .hand import Hand, HandRank, HandValue
from .player import Player, PlayerActionContext
from .position import Position, position_from_utg_distance
from .pot import PotManager, SidePot
from .table import HandResult, Table
from .tournament import BlindLevel, Tournament, TournamentConfig

__all__ = [
    "Action",
    "ActionType",
    "AiBot",
    "AiBotConfig",
    "AiDebugInfo",
    "BlindLevel",
    "Bot",
    "BotConfig",
    "BotDecision",
    "Card",
    "Deck",
    "EquityResult",
    "GameResult",
    "GameState",
    "Hand",
    "HandRank",
    "HandResult",
    "HandValue",
    "Player",
    "PlayerActionContext",
    "PlayerHand",
    "Position",
    "PotManager",
    "Rank",
    "SidePot",
    "Suit",
    "Table",
    "Tournament",
    "TournamentConfig",
    "calculate_equity",
    "calculate_outs",
    "card",
    "compare_hands",
    "evaluate_game",
    "position_from_utg_distance",
    "preflop_equity",
]
