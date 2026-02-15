"""AI-powered bot that uses Claude Code CLI for poker decisions."""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass, field

from .action import Action, ActionType, BotDecision
from .bot import GameState
from .card import Card
from .ranges import hole_cards_to_key


@dataclass(frozen=True)
class AiBotConfig:
    """Configuration for the AI bot.

    Attributes:
        model: Claude model to use (haiku for speed, sonnet for quality).
        persona: Play-style personality injected into the system prompt.
        timeout: Max seconds to wait for a response.
        debug: When True, store debug info on each decision.
    """

    model: str = "opus"
    persona: str = "You are an expert poker player. Play a tight-aggressive (TAG) style."
    timeout: int = 60
    debug: bool = False


@dataclass
class AiDebugInfo:
    """Debug trace from an AI bot decision."""

    prompt: str = ""
    raw_stdout: str = ""
    raw_stderr: str = ""
    returncode: int | None = None
    parsed_result: str = ""
    parsed_decision: dict = field(default_factory=dict)
    error: str = ""


_SYSTEM_PROMPT = """\
You are a poker bot making decisions in a Texas Hold'em tournament.
{persona}

You will receive the current game state and must decide on an action.

IMPORTANT RULES:
- Respond ONLY with valid JSON matching the schema below.
- "action" must be one of: "fold", "check", "call", "raise", "all_in"
- "amount" is required for "raise" and "all_in" (in big blinds), 0 for others
- "reasoning" is a brief explanation of your decision (1-2 sentences)
- Think about position, pot odds, equity, stack depth, and opponent count
- Consider whether you are pot committed before folding

You have access to these poker concepts:
- Pot odds: to_call / (pot + to_call)
- SPR (Stack-to-Pot Ratio): stack / pot — below 3 means you're committed
- Push/fold: with <=15 BB, prefer all-in or fold over standard raises

Response format (JSON only, no markdown, no explanation outside the JSON):
{{"action": "fold|check|call|raise|all_in", "amount": 0, "reasoning": "brief explanation"}}
"""


def _extract_json(text: str) -> str:
    """Strip markdown code fences and whitespace to get raw JSON."""
    text = text.strip()
    # Handle ```json ... ``` or ``` ... ```
    if text.startswith("```"):
        # Remove opening fence (with optional language tag)
        first_newline = text.index("\n") if "\n" in text else 3
        text = text[first_newline + 1 :]
        # Remove closing fence
        if text.endswith("```"):
            text = text[: -3]
        text = text.strip()
    return text


def _format_cards(cards: list[Card]) -> str:
    return " ".join(str(c) for c in cards) if cards else "none"


def _build_prompt(state: GameState) -> str:
    """Build a human-readable game state prompt."""
    key = hole_cards_to_key(state.hole_cards[0], state.hole_cards[1])
    spr = f"{state.stack_bb / state.pot_bb:.1f}" if state.pot_bb > 0 else "N/A"
    pot_odds = (
        f"{state.to_call_bb / (state.pot_bb + state.to_call_bb) * 100:.1f}%"
        if state.to_call_bb > 0
        else "N/A (nothing to call)"
    )
    invested_pct = ""
    if state.stack_bb > 0 and state.invested_bb > 0:
        eff = state.stack_bb + state.invested_bb
        invested_pct = f" ({state.invested_bb / eff * 100:.0f}% of effective stack invested)"

    return f"""\
Street: {state.street}
Hole cards: {_format_cards(state.hole_cards)} ({key})
Community: {_format_cards(state.community)}
Position: {state.position.label} ({state.position.short})
Opponents: {state.num_opponents}
Pot: {state.pot_bb:.1f} BB
To call: {state.to_call_bb:.1f} BB
Stack: {state.stack_bb:.1f} BB{invested_pct}
SPR: {spr}
Pot odds: {pot_odds}

What is your action?"""


class AiBot:
    """Poker bot powered by Claude Code CLI."""

    def __init__(self, config: AiBotConfig | None = None) -> None:
        self._cfg = config or AiBotConfig()
        self.last_debug: AiDebugInfo | None = None

    def decide(self, state: GameState) -> BotDecision:
        """Ask Claude for a poker decision."""
        prompt = _build_prompt(state)
        system = _SYSTEM_PROMPT.format(persona=self._cfg.persona)
        debug = AiDebugInfo(prompt=prompt)

        try:
            # Build a clean env: inherit PATH/HOME but unset CLAUDECODE
            # to avoid the "nested session" check.
            env = {**os.environ}
            env.pop("CLAUDECODE", None)

            result = subprocess.run(
                [
                    "claude",
                    "-p", prompt,
                    "--output-format", "json",
                    "--model", self._cfg.model,
                    "--system-prompt", system,
                    "--dangerously-skip-permissions",
                    "--no-session-persistence",
                ],
                capture_output=True,
                text=True,
                timeout=self._cfg.timeout,
                env=env,
            )
        except subprocess.TimeoutExpired:
            debug.error = f"Timed out after {self._cfg.timeout}s"
            self.last_debug = debug
            return self._fallback(state, debug.error)
        except FileNotFoundError:
            debug.error = "claude CLI not found in PATH"
            self.last_debug = debug
            return self._fallback(state, debug.error)

        debug.raw_stdout = result.stdout[:2000]
        debug.raw_stderr = result.stderr[:2000]
        debug.returncode = result.returncode

        if result.returncode != 0:
            debug.error = f"exit code {result.returncode}: {result.stderr[:300]}"
            self.last_debug = debug
            return self._fallback(state, debug.error)

        try:
            envelope = json.loads(result.stdout)
            raw_result = envelope.get("result", "")
        except (json.JSONDecodeError, TypeError) as e:
            debug.error = f"JSON envelope parse failed: {e}"
            self.last_debug = debug
            return self._fallback(state, debug.error)

        # result can be a dict (already parsed) or a string (needs parsing)
        if isinstance(raw_result, dict):
            decision = raw_result
            debug.parsed_result = json.dumps(raw_result)[:1000]
        else:
            response_text = _extract_json(str(raw_result))
            debug.parsed_result = response_text[:1000]
            try:
                decision = json.loads(response_text)
            except (json.JSONDecodeError, TypeError) as e:
                debug.error = (
                    f"Decision parse failed: {e} — raw: {response_text[:200]}"
                )
                self.last_debug = debug
                return self._fallback(state, debug.error)

        debug.parsed_decision = decision

        self.last_debug = debug
        return self._parse_decision(decision, state)

    def _parse_decision(self, data: dict, state: GameState) -> BotDecision:
        """Convert Claude's JSON response to a BotDecision."""
        action_str = data.get("action", "fold")
        amount = float(data.get("amount", 0))
        reasoning = data.get("reasoning", "AI decision")

        action_map = {
            "fold": ActionType.FOLD,
            "check": ActionType.CHECK,
            "call": ActionType.CALL,
            "raise": ActionType.RAISE,
            "all_in": ActionType.ALL_IN,
        }
        action_type = action_map.get(action_str, ActionType.FOLD)

        # Sanity checks
        if action_type == ActionType.CHECK and state.to_call_bb > 0:
            action_type = ActionType.CALL
        if action_type == ActionType.FOLD and state.to_call_bb == 0:
            action_type = ActionType.CHECK

        return BotDecision(
            action=Action(action_type, amount),
            reasoning=f"[AI] {reasoning}",
            equity=None,
            confidence=0.70,
        )

    def _fallback(self, state: GameState, reason: str) -> BotDecision:
        """Conservative fallback when Claude is unavailable."""
        if state.to_call_bb == 0:
            return BotDecision(
                action=Action(ActionType.CHECK),
                reasoning=f"[AI fallback: {reason}]",
                equity=None,
                confidence=0.10,
            )
        return BotDecision(
            action=Action(ActionType.FOLD),
            reasoning=f"[AI fallback: {reason}]",
            equity=None,
            confidence=0.10,
        )
