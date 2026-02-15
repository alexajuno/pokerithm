"""Bot decision engine — TAG-style poker advisor."""

from __future__ import annotations

import random
from dataclasses import dataclass

from .action import Action, ActionType, BotDecision
from .calculator import calculate_equity
from .card import Card, Suit
from .position import Position
from .ranges import POSITION_RANGES, hole_cards_to_key

# ── Preflop push/fold chart for short stacks ────────────────
# Hands that are profitable all-in shoves at various stack depths.
# Based on Jennings-style push/fold tables.

_PUSH_15BB: set[str] = {
    "AA", "KK", "QQ", "JJ", "TT", "99", "88", "77", "66", "55", "44", "33", "22",
    "AKs", "AQs", "AJs", "ATs", "A9s", "A8s", "A7s", "A6s", "A5s", "A4s", "A3s", "A2s",
    "AKo", "AQo", "AJo", "ATo", "A9o", "A8o", "A7o",
    "KQs", "KJs", "KTs", "K9s",
    "KQo", "KJo",
    "QJs", "QTs",
    "JTs",
}

_PUSH_10BB: set[str] = _PUSH_15BB | {
    "A6o", "A5o", "A4o", "A3o", "A2o",
    "K8s", "K7s", "K6s",
    "KTo", "K9o",
    "Q9s", "Q8s",
    "QJo", "QTo",
    "J9s", "JTo",
    "T9s", "T8s",
    "98s", "87s", "76s",
}

_PUSH_6BB: set[str] = _PUSH_10BB | {
    "K5s", "K4s", "K3s", "K2s",
    "K8o", "K7o", "K6o", "K5o",
    "Q7s", "Q6s", "Q5s",
    "Q9o", "Q8o",
    "J8s", "J7s",
    "J9o",
    "T7s",
    "T9o",
    "97s", "96s",
    "86s", "85s",
    "76s", "75s",
    "65s", "64s",
    "54s", "53s",
}

# 3-bet shoving range — hands we jam over an opener's raise when short
_3BET_SHOVE: set[str] = {
    "AA", "KK", "QQ", "JJ", "TT", "99",
    "AKs", "AQs", "AJs", "ATs",
    "AKo", "AQo",
    "KQs",
}

# Tighter range for calling a raise vs. opening
_FACING_RAISE_CALL: set[str] = {
    "AA", "KK", "QQ", "JJ", "TT", "99", "88", "77",
    "AKs", "AQs", "AJs", "ATs", "A9s",
    "AKo", "AQo", "AJo",
    "KQs", "KJs",
    "QJs",
    "JTs",
}

_FACING_RAISE_3BET: set[str] = {
    "AA", "KK", "QQ", "JJ",
    "AKs", "AQs",
    "AKo",
}


@dataclass(frozen=True)
class BotConfig:
    """Tunable knobs for the bot's play-style.

    Attributes:
        aggression: 0 = passive, 1 = aggressive.  Shifts raise thresholds.
        bluff_frequency: Probability of attempting a bluff (0-1).
        tightness: 0 = loose, 1 = nit.  Contracts the opening ranges.
        raise_sizing: Default open-raise in big blinds.
        seed: RNG seed for reproducible decisions.
    """

    aggression: float = 0.6
    bluff_frequency: float = 0.15
    tightness: float = 0.5
    raise_sizing: float = 2.5
    seed: int | None = None


@dataclass
class GameState:
    """Snapshot of the game at decision time.

    All monetary values are in big-blind units.
    """

    hole_cards: list[Card]
    community: list[Card]
    position: Position
    num_opponents: int
    pot_bb: float
    to_call_bb: float
    street: str  # "preflop" | "flop" | "turn" | "river"
    stack_bb: float = 0.0  # hero's remaining stack in BB
    invested_bb: float = 0.0  # chips already invested this hand in BB


class Bot:
    """TAG poker decision engine."""

    def __init__(self, config: BotConfig | None = None) -> None:
        self._cfg = config or BotConfig()
        self._rng = random.Random(self._cfg.seed)

    def decide(self, state: GameState) -> BotDecision:
        if state.street == "preflop":
            return self._preflop(state)
        return self._postflop(state)

    # ── Preflop ──────────────────────────────────────────────

    def _preflop(self, state: GameState) -> BotDecision:
        key = hole_cards_to_key(state.hole_cards[0], state.hole_cards[1])
        effective_stack = state.stack_bb + state.invested_bb

        # Short-stack push/fold mode
        if effective_stack > 0 and effective_stack <= 15:
            return self._short_stack_preflop(state, key, effective_stack)

        # Facing a raise (someone raised before us)
        if state.to_call_bb >= 2.0:
            return self._facing_raise_preflop(state, key)

        # Standard open-raise logic
        return self._open_preflop(state, key)

    def _short_stack_preflop(
        self, state: GameState, key: str, effective_stack: float
    ) -> BotDecision:
        """Push/fold strategy for short stacks (<=15 BB)."""
        # Choose the push range based on stack depth
        if effective_stack <= 6:
            push_range = _PUSH_6BB
        elif effective_stack <= 10:
            push_range = _PUSH_10BB
        else:
            push_range = _PUSH_15BB

        facing_raise = state.to_call_bb >= 2.0

        if facing_raise:
            # Facing a raise short-stacked: shove or fold
            if key in _3BET_SHOVE:
                return BotDecision(
                    action=Action(ActionType.ALL_IN, effective_stack),
                    reasoning=f"Short stack ({effective_stack:.0f} BB) — shoving {key} over raise",
                    equity=None,
                    confidence=0.80,
                )
            # Can check for free in the BB
            if state.to_call_bb == 0:
                return BotDecision(
                    action=Action(ActionType.CHECK),
                    reasoning=f"Short stack, {key} not strong enough to shove — free check",
                    equity=None,
                    confidence=0.50,
                )
            return BotDecision(
                action=Action(ActionType.FOLD),
                reasoning=f"Short stack ({effective_stack:.0f} BB) — {key} too weak vs raise",
                equity=None,
                confidence=0.75,
            )

        # Unopened pot: push or fold
        if key in push_range:
            return BotDecision(
                action=Action(ActionType.ALL_IN, effective_stack),
                reasoning=f"Short stack ({effective_stack:.0f} BB) — pushing {key}",
                equity=None,
                confidence=0.80,
            )

        if state.to_call_bb == 0:
            return BotDecision(
                action=Action(ActionType.CHECK),
                reasoning=f"Short stack, {key} not in push range — free check",
                equity=None,
                confidence=0.50,
            )

        return BotDecision(
            action=Action(ActionType.FOLD),
            reasoning=f"Short stack ({effective_stack:.0f} BB) — {key} outside push range",
            equity=None,
            confidence=0.80,
        )

    def _facing_raise_preflop(self, state: GameState, key: str) -> BotDecision:
        """Tighter ranges when facing a raise (not opening)."""
        pos_note = state.position.short

        # 3-bet with premium hands
        if key in _FACING_RAISE_3BET:
            sizing = state.to_call_bb * 3
            return BotDecision(
                action=Action(ActionType.RAISE, sizing),
                reasoning=f"{key} — 3-betting vs raise from {pos_note}",
                equity=None,
                confidence=0.85,
            )

        # Call with strong but not 3-bet-worthy hands
        if key in _FACING_RAISE_CALL:
            return BotDecision(
                action=Action(ActionType.CALL),
                reasoning=f"{key} — calling raise from {pos_note}",
                equity=None,
                confidence=0.65,
            )

        # Bluff 3-bet occasionally from late position
        if state.position.is_late and self._should_bluff(state):
            sizing = state.to_call_bb * 3
            return BotDecision(
                action=Action(ActionType.RAISE, sizing),
                reasoning=f"Bluff 3-bet with {key} from {pos_note}",
                equity=None,
                confidence=0.25,
            )

        return BotDecision(
            action=Action(ActionType.FOLD),
            reasoning=f"{key} too weak to continue vs raise from {pos_note}",
            equity=None,
            confidence=0.80,
        )

    def _open_preflop(self, state: GameState, key: str) -> BotDecision:
        """Standard open-raise logic for unopened pots."""
        # Widen ranges when fewer opponents remain
        effective_pos = state.position
        if state.num_opponents <= 1:
            effective_pos = Position.BTN
        elif state.num_opponents <= 2:
            effective_pos = max(effective_pos, Position.CO, key=lambda p: p.value)
        elif state.num_opponents <= 4:
            effective_pos = max(effective_pos, Position.HJ, key=lambda p: p.value)

        raise_range, call_range = POSITION_RANGES.get(
            effective_pos, (set(), set())
        )

        # Add noise to tightness
        noise = self._rng.gauss(0, 0.08)
        effective_tightness = max(0.0, min(1.0, self._cfg.tightness + noise))

        in_raise = key in raise_range
        in_call = key in call_range

        # Tight players occasionally fold hands at the bottom of their range
        if effective_tightness > 0.7 and not self._is_premium(key):
            if self._rng.random() < (effective_tightness - 0.5):
                in_raise = False
                in_call = False

        pos_note = state.position.short
        if effective_pos != state.position:
            pos_note = f"{state.position.short} (playing as {effective_pos.short}, {state.num_opponents} opp)"

        if in_raise:
            sizing = self._open_raise_sizing()
            return BotDecision(
                action=Action(ActionType.RAISE, sizing),
                reasoning=f"{key} is in raise range for {pos_note}",
                equity=None,
                confidence=0.85,
            )

        if in_call and state.to_call_bb > 0:
            return BotDecision(
                action=Action(ActionType.CALL),
                reasoning=f"{key} is in call range for {pos_note}",
                equity=None,
                confidence=0.65,
            )

        # Bluff check
        if self._should_bluff(state):
            sizing = self._open_raise_sizing()
            return BotDecision(
                action=Action(ActionType.RAISE, sizing),
                reasoning=f"Bluff-raise with {key} from {pos_note}",
                equity=None,
                confidence=0.30,
            )

        # Can check for free in the BB
        if state.to_call_bb == 0:
            return BotDecision(
                action=Action(ActionType.CHECK),
                reasoning=f"{key} outside range — checking for free",
                equity=None,
                confidence=0.50,
            )

        return BotDecision(
            action=Action(ActionType.FOLD),
            reasoning=f"{key} outside range for {pos_note}",
            equity=None,
            confidence=0.80,
        )

    # ── Postflop ─────────────────────────────────────────────

    def _postflop(self, state: GameState) -> BotDecision:
        equity_result = calculate_equity(
            hero_cards=state.hole_cards,
            community=state.community,
            num_opponents=state.num_opponents,
            num_simulations=2000,
        )
        raw_equity = equity_result.equity  # 0-100

        # Add noise for imperfect play
        equity = raw_equity + self._rng.gauss(0, 5)
        equity = max(0.0, min(100.0, equity))

        pot_odds = (
            state.to_call_bb / (state.pot_bb + state.to_call_bb) * 100
            if state.to_call_bb > 0
            else 0.0
        )

        # Pot commitment — if we've invested >40% of our stack, lower fold threshold
        spr = self._spr(state)
        committed = self._is_pot_committed(state)

        # Dynamic thresholds based on aggression
        raise_threshold = 65 - (self._cfg.aggression * 15)  # 50-65%
        call_threshold = max(pot_odds, 25.0) if state.to_call_bb > 0 else 15.0

        # Pot committed: only fold complete air
        if committed and state.to_call_bb > 0:
            call_threshold = min(call_threshold, 15.0)

        # Low SPR: commit with stronger hands more readily
        if spr is not None and spr < 3:
            raise_threshold -= 10

        # Raise strong hands
        if equity >= raise_threshold:
            sizing = self._postflop_raise_sizing(state, equity, spr)
            return BotDecision(
                action=Action(ActionType.RAISE, sizing),
                reasoning=(
                    f"Strong hand ({raw_equity:.0f}% equity) — "
                    f"raising {sizing:.1f} BB"
                ),
                equity=raw_equity,
                confidence=min(0.95, equity / 100),
            )

        # Call with sufficient equity
        if equity >= call_threshold and state.to_call_bb > 0:
            reason = (
                f"{raw_equity:.0f}% equity vs "
                f"{pot_odds:.0f}% pot odds — calling"
            )
            if committed:
                reason += " (pot committed)"
            return BotDecision(
                action=Action(ActionType.CALL),
                reasoning=reason,
                equity=raw_equity,
                confidence=min(0.80, equity / 100),
            )

        # Free check
        if state.to_call_bb == 0:
            # Semi-bluff with draws when checked to
            if self._has_draw(state) and self._should_bluff(state):
                sizing = self._postflop_raise_sizing(state, equity, spr)
                return BotDecision(
                    action=Action(ActionType.RAISE, sizing),
                    reasoning=f"Semi-bluff with draw from {state.position.short} ({raw_equity:.0f}% equity)",
                    equity=raw_equity,
                    confidence=0.40,
                )
            return BotDecision(
                action=Action(ActionType.CHECK),
                reasoning=f"Checking with {raw_equity:.0f}% equity",
                equity=raw_equity,
                confidence=0.50,
            )

        # Postflop bluff — prefer semi-bluffs and dry boards
        if self._should_bluff_postflop(state, raw_equity):
            sizing = self._postflop_raise_sizing(state, equity, spr)
            return BotDecision(
                action=Action(ActionType.RAISE, sizing),
                reasoning=f"Bluff from {state.position.short} ({raw_equity:.0f}% equity)",
                equity=raw_equity,
                confidence=0.25,
            )

        return BotDecision(
            action=Action(ActionType.FOLD),
            reasoning=(
                f"{raw_equity:.0f}% equity < "
                f"{pot_odds:.0f}% pot odds — folding"
            ),
            equity=raw_equity,
            confidence=0.75,
        )

    # ── Helpers ───────────────────────────────────────────────

    def _open_raise_sizing(self) -> float:
        """Randomised open-raise size around the configured default."""
        base = self._cfg.raise_sizing
        noise = self._rng.gauss(0, 0.3)
        return round(max(2.0, base + noise), 1)

    def _postflop_raise_sizing(
        self, state: GameState, equity: float, spr: float | None
    ) -> float:
        """2/3 pot baseline, polarised larger for very strong/weak hands."""
        base = state.pot_bb * 2 / 3

        # Polarise: bet bigger with nuts or air, smaller with medium
        if equity > 80 or equity < 30:
            base *= 1.3
        elif equity < 50:
            base *= 0.8

        # Low SPR: jam instead of fractional bets
        if spr is not None and spr < 2 and state.stack_bb > 0:
            base = max(base, state.stack_bb)

        # Add noise (±15%)
        noise = self._rng.gauss(1.0, 0.15)
        return round(max(1.0, base * noise), 1)

    def _should_bluff(self, state: GameState) -> bool:
        """Roll the dice for a bluff attempt."""
        if self._cfg.bluff_frequency <= 0:
            return False
        return self._rng.random() < self._cfg.bluff_frequency * self._cfg.aggression

    def _should_bluff_postflop(self, state: GameState, equity: float) -> bool:
        """Smarter postflop bluff: considers position, board texture, and draws."""
        if self._cfg.bluff_frequency <= 0:
            return False

        # Only bluff from late position or blinds (can represent a check-raise)
        if not (state.position.is_late or state.position.is_blind):
            return False

        base_freq = self._cfg.bluff_frequency * self._cfg.aggression

        # Boost bluff frequency on dry boards (fewer draws = more fold equity)
        if self._is_dry_board(state.community):
            base_freq *= 1.5

        # Semi-bluffs (has some equity) are better candidates
        if equity > 15:
            base_freq *= 1.3

        # River bluffs need to be less frequent (no more cards to improve)
        if state.street == "river":
            base_freq *= 0.5

        return self._rng.random() < base_freq

    def _spr(self, state: GameState) -> float | None:
        """Stack-to-pot ratio. None if stack info unavailable."""
        if state.stack_bb <= 0 or state.pot_bb <= 0:
            return None
        return state.stack_bb / state.pot_bb

    def _is_pot_committed(self, state: GameState) -> bool:
        """True if hero has invested >40% of effective stack this hand."""
        if state.stack_bb <= 0 and state.invested_bb <= 0:
            return False
        effective = state.stack_bb + state.invested_bb
        if effective <= 0:
            return False
        return state.invested_bb / effective > 0.4

    def _has_draw(self, state: GameState) -> bool:
        """Quick check for flush or straight draw potential."""
        if state.street == "river":
            return False
        all_cards = state.hole_cards + state.community
        # Flush draw: 4 cards of the same suit
        suit_counts: dict[Suit, int] = {}
        for c in all_cards:
            suit_counts[c.suit] = suit_counts.get(c.suit, 0) + 1
        if any(count >= 4 for count in suit_counts.values()):
            return True
        # Open-ended straight draw: 4 consecutive ranks
        ranks = sorted({c.rank.value for c in all_cards})
        for i in range(len(ranks) - 3):
            if ranks[i + 3] - ranks[i] == 3:
                return True
        return False

    @staticmethod
    def _is_dry_board(community: list[Card]) -> bool:
        """A board is 'dry' if it has no flush draws and no connected cards."""
        if len(community) < 3:
            return True
        # Flush draw check: 3+ cards of same suit
        suit_counts: dict[Suit, int] = {}
        for c in community:
            suit_counts[c.suit] = suit_counts.get(c.suit, 0) + 1
        if any(count >= 3 for count in suit_counts.values()):
            return False
        # Connectedness: any two community cards within 2 ranks
        ranks = sorted(c.rank.value for c in community)
        for i in range(len(ranks) - 1):
            if ranks[i + 1] - ranks[i] <= 2:
                return False
        return True

    @staticmethod
    def _is_premium(key: str) -> bool:
        return key in {"AA", "KK", "QQ", "JJ", "AKs", "AKo"}
