"""Action types and bot decision output."""

from dataclasses import dataclass
from enum import Enum


class ActionType(Enum):
    """Possible actions a player can take."""

    FOLD = "fold"
    CHECK = "check"
    CALL = "call"
    RAISE = "raise"
    ALL_IN = "all_in"


@dataclass(frozen=True)
class Action:
    """A concrete poker action.

    Attributes:
        type: The action type.
        amount: Size in big blinds for raises/all-in, 0 otherwise.
    """

    type: ActionType
    amount: float = 0.0

    def __str__(self) -> str:
        if self.type == ActionType.RAISE:
            return f"Raise {self.amount:.1f} BB"
        if self.type == ActionType.ALL_IN:
            return f"All-in ({self.amount:.1f} BB)"
        return self.type.value.capitalize()


@dataclass(frozen=True)
class BotDecision:
    """The bot's recommended action with reasoning.

    Attributes:
        action: The recommended action.
        reasoning: Human-readable explanation.
        equity: Estimated hand equity (None preflop when using ranges).
        confidence: How confident the bot is (0-1).
    """

    action: Action
    reasoning: str
    equity: float | None
    confidence: float
