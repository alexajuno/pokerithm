"""Rich display layer for tournament simulation."""

from __future__ import annotations

import random
import time

from rich.columns import Columns
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from .action import Action, ActionType
from .ai_bot import AiBotConfig, AiDebugInfo
from .bot import BotConfig
from .card import Card, Suit
from .hand import HandValue
from .player import Player, PlayerActionContext
from .pot import SidePot
from .table import HandResult
from .tournament import BlindLevel, Tournament, TournamentConfig

BOT_NAMES = ["Alice", "Bob", "Charlie", "Diana", "Eddie", "Fiona", "George"]

# Timing
ACTION_DELAY = 1.2
STREET_DELAY = 2.0
SHOWDOWN_DELAY = 3.0
HAND_END_DELAY = 3.0

console = Console()


def _clear() -> None:
    console.clear()


def _pause(seconds: float) -> None:
    time.sleep(seconds)


def _format_card(c: Card) -> str:
    symbol = f"{c.rank.symbol}{c.suit.symbol}"
    if c.suit in (Suit.HEARTS, Suit.DIAMONDS):
        return f"[bold red]{symbol}[/bold red]"
    return f"[bold white]{symbol}[/bold white]"


def _format_cards(cards: list[Card]) -> str:
    return " ".join(_format_card(c) for c in cards)


def _generate_bot_personalities(names: list[str], seed: int = 42) -> dict[str, BotConfig]:
    """Generate diverse bot personalities with seeded randomness."""
    rng = random.Random(seed)
    personalities: dict[str, BotConfig] = {}

    presets = [
        (0.8, 0.25, 0.3, 3.0),   # aggressive, loose
        (0.3, 0.05, 0.8, 2.5),   # passive, tight
        (0.6, 0.15, 0.5, 2.5),   # balanced TAG
        (0.9, 0.30, 0.2, 3.5),   # maniac
        (0.4, 0.10, 0.7, 2.0),   # tight-passive (rock)
        (0.7, 0.20, 0.4, 2.8),   # loose-aggressive
        (0.5, 0.12, 0.6, 2.3),   # slightly tight TAG
    ]

    for i, name in enumerate(names):
        preset = presets[i % len(presets)]
        personalities[name] = BotConfig(
            aggression=max(0.0, min(1.0, preset[0] + rng.gauss(0, 0.05))),
            bluff_frequency=max(0.0, min(0.5, preset[1] + rng.gauss(0, 0.02))),
            tightness=max(0.0, min(1.0, preset[2] + rng.gauss(0, 0.05))),
            raise_sizing=max(2.0, preset[3] + rng.gauss(0, 0.2)),
            seed=rng.randint(0, 2**31),
        )

    return personalities


def _render_header(
    hand_number: int,
    blind_level: BlindLevel,
    pot_total: int,
    num_alive: int,
    total_players: int,
) -> None:
    """Render the persistent top bar."""
    left = f"Hand #{hand_number}"
    mid = f"Blinds {blind_level.small_blind}/{blind_level.big_blind}"
    right = f"Players {num_alive}/{total_players}"
    pot_str = f"Pot: {pot_total:,}" if pot_total > 0 else ""

    console.print(
        Panel(
            f"[bold]{left}[/bold]  |  {mid}  |  {pot_str}  |  {right}",
            style="blue",
            expand=True,
        )
    )


def _render_seats(
    players: list[Player],
    dealer_seat: int,
    community: list[Card] | None = None,
) -> None:
    """Render player seats as a compact grid."""
    seat_panels: list[Panel] = []

    for p in players:
        if p.is_eliminated:
            continue

        # Name line
        marker = "[yellow]D[/yellow] " if p.seat == dealer_seat else "  "
        name_color = "bold cyan" if p.is_human else "white"
        name_line = f"{marker}[{name_color}]{p.name}[/{name_color}]"

        # Cards
        if p.is_human and p.hole_cards:
            card_line = _format_cards(p.hole_cards)
        elif p.hole_cards and not p.is_folded:
            card_line = "[dim]\u2588\u2588 \u2588\u2588[/dim]"
        else:
            card_line = "    "

        # Chips
        chip_line = f"[green]{p.chips:,}[/green]" if p.chips > 0 else "[red]0[/red]"

        # Status
        if p.is_folded:
            border = "dim"
            status = "[dim]Folded[/dim]"
        elif p.is_all_in:
            border = "red"
            status = "[bold red]ALL IN[/bold red]"
        else:
            border = "green" if p.is_human else "white"
            status = ""

        body = f"{name_line}\n{card_line}\n{chip_line}"
        if status:
            body += f"\n{status}"

        seat_panels.append(Panel(body, border_style=border, width=16, height=6))

    console.print(Columns(seat_panels, equal=True, expand=True))

    if community:
        board_str = _format_cards(community)
        console.print(Panel(f"  {board_str}  ", title="Board", expand=False), justify="center")


def _render_action_log(
    log: list[str],
    max_lines: int = 8,
) -> None:
    """Show recent actions."""
    if not log:
        return
    recent = log[-max_lines:]
    body = "\n".join(recent)
    console.print(Panel(body, title="Action", border_style="dim", expand=True, height=min(len(recent) + 2, max_lines + 2)))


def _redraw(
    players: list[Player],
    hand_number: int,
    blind_level: BlindLevel,
    pot_total: int,
    dealer_seat: int,
    community: list[Card] | None,
    action_log: list[str],
    total_players: int,
) -> None:
    """Full screen redraw."""
    _clear()
    num_alive = sum(1 for p in players if not p.is_eliminated)
    _render_header(hand_number, blind_level, pot_total, num_alive, total_players)
    _render_seats(players, dealer_seat, community)
    _render_action_log(action_log)


def prompt_human_action(player: Player, ctx: PlayerActionContext) -> Action:
    """Prompt the human player for their action."""
    console.print()
    console.print(f"  [bold]Pot:[/bold] {ctx.pot_total:,}  |  [bold]To call:[/bold] {ctx.to_call}  |  [bold]Your chips:[/bold] {player.chips:,}")

    options = []
    if ctx.to_call == 0:
        options.append("[bold]c[/bold]heck")
    else:
        options.append(f"[bold]c[/bold]all ({ctx.to_call})")
    options.append("[bold]f[/bold]old")
    if player.chips > ctx.to_call:
        options.append(f"[bold]r[/bold]aise (min {ctx.min_raise})")
    options.append("[bold]a[/bold]ll-in ({})".format(player.chips + player.current_bet))

    console.print(f"  {' | '.join(options)}")

    while True:
        response = Prompt.ask("  [bold cyan]>>>[/bold cyan]").strip().lower()

        if response in ("c", "check") and ctx.to_call == 0:
            return Action(ActionType.CHECK)

        if response in ("c", "call") and ctx.to_call > 0:
            return Action(ActionType.CALL)

        if response in ("f", "fold"):
            if ctx.to_call == 0:
                console.print("  [yellow]You can check for free![/yellow]")
                continue
            return Action(ActionType.FOLD)

        if response in ("a", "all-in", "allin", "all"):
            return Action(ActionType.ALL_IN, player.chips + player.current_bet)

        if response.startswith("r") or response.startswith("raise"):
            parts = response.split()
            if len(parts) >= 2:
                try:
                    raise_to = int(parts[1])
                except ValueError:
                    console.print("  [red]Invalid raise amount[/red]")
                    continue
            else:
                try:
                    raise_to = int(Prompt.ask("  [bold]Raise to[/bold]"))
                except ValueError:
                    console.print("  [red]Invalid amount[/red]")
                    continue

            if raise_to < ctx.min_raise:
                console.print(f"  [red]Minimum raise is {ctx.min_raise}[/red]")
                continue
            if raise_to > ctx.max_raise:
                console.print(f"  [yellow]Capped to all-in ({ctx.max_raise})[/yellow]")
                return Action(ActionType.ALL_IN, ctx.max_raise)
            return Action(ActionType.RAISE, raise_to)

        console.print("  [red]Invalid action. Use c/f/r/a[/red]")


AI_PERSONAS = [
    "You are a loose-aggressive poker shark. You bluff often and put maximum pressure on opponents.",
    "You are a tight, disciplined grinder. You only play premium hands and rarely bluff.",
    "You are a balanced TAG player. You mix aggression with patience.",
    "You are a maniac who loves action. You raise and re-raise relentlessly.",
    "You are a rock — extremely tight and passive. You only bet with the nuts.",
    "You are a tricky, deceptive player. You slowplay monsters and bluff in unexpected spots.",
    "You are a solid, slightly aggressive player who exploits position ruthlessly.",
]


def _generate_ai_personalities(
    names: list[str], model: str = "opus"
) -> dict[str, AiBotConfig]:
    """Generate AI bot configs with distinct personas."""
    configs: dict[str, AiBotConfig] = {}
    for i, name in enumerate(names):
        persona = AI_PERSONAS[i % len(AI_PERSONAS)]
        configs[name] = AiBotConfig(
            model=model,
            persona=persona,
            timeout=120,
        )
    return configs


def run_tournament_cli(
    num_bots: int = 7,
    starting_stack: int = 1500,
    hands_per_level: int = 10,
    ai_opponents: int = 0,
    ai_model: str = "opus",
    debug: bool = False,
) -> None:
    """Entry point: set up and run a full tournament.

    Args:
        num_bots: Total number of opponents.
        starting_stack: Starting chip stack for all players.
        hands_per_level: Hands before blinds increase.
        ai_opponents: How many opponents use Claude AI (0 = all rule-based).
        ai_model: Claude model for AI opponents.
        debug: Show AI prompt/response debug info.
    """
    ai_opponents = max(0, min(ai_opponents, num_bots))

    _clear()
    mode_label = f"{ai_opponents} AI ({ai_model})" if ai_opponents else "rule-based"
    if ai_opponents and ai_opponents < num_bots:
        mode_label += f" + {num_bots - ai_opponents} rule-based"
    console.print(
        Panel(
            "[bold]Texas Hold'em Tournament[/bold]\n"
            f"You vs {num_bots} opponents ({mode_label})  |  Starting stack: {starting_stack:,}\n"
            "[dim]Actions: c(heck/all) | f(old) | r(aise) N | a(ll-in)[/dim]",
            expand=False,
            border_style="green",
        )
    )
    _pause(1.5)

    # Create players
    bot_names = BOT_NAMES[:num_bots]

    # Split names into AI and rule-based
    ai_names = bot_names[:ai_opponents]
    rule_names = bot_names[ai_opponents:]

    rule_personalities = _generate_bot_personalities(rule_names) if rule_names else {}
    ai_personalities = _generate_ai_personalities(ai_names, ai_model) if ai_names else {}

    players: list[Player] = []
    players.append(Player(name="You", chips=starting_stack, seat=0, is_human=True))
    for i, name in enumerate(bot_names):
        players.append(Player(name=name, chips=starting_stack, seat=i + 1))

    total_players = len(players)

    config = TournamentConfig(
        num_bots=num_bots,
        starting_stack=starting_stack,
        hands_per_level=hands_per_level,
    )

    # Mutable state for callbacks
    action_log: list[str] = []
    current_community: list[Card] = []
    current_blind_level = config.blind_schedule[0]
    current_hand_number = 0
    current_dealer_seat = 0
    current_pot = 0
    human_in_hand = True

    def _redraw_current() -> None:
        _redraw(
            players, current_hand_number, current_blind_level,
            current_pot, current_dealer_seat,
            current_community if current_community else None,
            action_log, total_players,
        )

    def on_hand_start(hand_num: int, level: BlindLevel, dealer: int) -> None:
        nonlocal current_community, current_blind_level, current_hand_number
        nonlocal current_dealer_seat, current_pot, human_in_hand
        current_community = []
        current_blind_level = level
        current_hand_number = hand_num
        current_dealer_seat = dealer
        current_pot = 0
        action_log.clear()
        human_in_hand = any(p.is_human and not p.is_eliminated for p in players)
        _redraw_current()

    def on_deal(street: str, community: list[Card]) -> None:
        nonlocal current_community
        if community:
            current_community = community

        if street == "hole_cards":
            action_log.append("[bold]Cards dealt[/bold]")
        elif street in ("flop", "turn", "river"):
            action_log.append(f"[bold cyan]── {street.capitalize()} ──  {_format_cards(community)}[/bold cyan]")
            _pause(STREET_DELAY)

        # Update pot from player bets
        _sync_pot()
        _redraw_current()

    def _sync_pot() -> None:
        nonlocal current_pot
        current_pot = sum(p.total_bet_this_hand for p in players if not p.is_eliminated)

    def on_action(player: Player, action: Action) -> None:
        # Remove thinking indicator if present
        if action_log and action_log[-1].endswith("is thinking..."):
            action_log.pop()

        color = {
            ActionType.FOLD: "dim",
            ActionType.CHECK: "yellow",
            ActionType.CALL: "yellow",
            ActionType.RAISE: "green",
            ActionType.ALL_IN: "bold red",
        }.get(action.type, "white")

        if action.type == ActionType.RAISE:
            text = f"raises to {int(action.amount)}"
        elif action.type == ActionType.ALL_IN:
            text = f"ALL IN ({int(action.amount)})"
        elif action.type == ActionType.CALL:
            text = "calls"
        elif action.type == ActionType.CHECK:
            text = "checks"
        else:
            text = "folds"

        is_ai = player.name in ai_personalities
        label = "[bold cyan]You[/bold cyan]" if player.is_human else player.name
        ai_tag = " [magenta](AI)[/magenta]" if is_ai else ""
        action_log.append(f"[{color}]{label}{ai_tag} {text}[/{color}]")

        _sync_pot()
        _redraw_current()

        if not player.is_human:
            _pause(ACTION_DELAY)

    def on_showdown(
        pot_winners: list[tuple[SidePot, list[Player], HandValue | None]],
    ) -> None:
        _pause(SHOWDOWN_DELAY)
        action_log.append("")

        # Reveal bot hands
        for p in players:
            if p.is_in_hand and not p.is_human and p.hole_cards:
                action_log.append(f"  {p.name}: {_format_cards(p.hole_cards)}")

        action_log.append("")
        for sp, winners, hand_value in pot_winners:
            names = ", ".join(
                "[bold cyan]You[/bold cyan]" if w.is_human else w.name
                for w in winners
            )
            hand_str = f" with [bold]{hand_value}[/bold]" if hand_value else ""
            action_log.append(f"[bold green]{names} wins {sp.amount:,}{hand_str}[/bold green]")

        _redraw_current()
        _pause(SHOWDOWN_DELAY)

    def on_hand_end(result: HandResult) -> None:
        # Brief chip leaderboard
        alive = sorted(
            [p for p in players if not p.is_eliminated],
            key=lambda p: p.chips,
            reverse=True,
        )
        action_log.append("")
        for i, p in enumerate(alive):
            marker = " [bold cyan]*[/bold cyan]" if p.is_human else ""
            action_log.append(f"  {i + 1}. {p.name}: {p.chips:,}{marker}")

        _redraw_current()
        _pause(HAND_END_DELAY)

    def on_elimination(player: Player, place: int) -> None:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(place, "th")
        action_log.append(f"[bold red]{player.name} eliminated in {place}{suffix} place![/bold red]")
        _redraw_current()
        _pause(HAND_END_DELAY)

        if player.is_human:
            console.print()
            console.print(
                Panel(
                    "[bold red]You've been knocked out![/bold red]\nBetter luck next time.",
                    expand=False,
                )
            )
            _pause(2.0)

    def on_blind_increase(level: BlindLevel, idx: int) -> None:
        action_log.append(
            f"[bold yellow]Blinds increase to {level.small_blind}/{level.big_blind}![/bold yellow]"
        )
        _redraw_current()
        _pause(1.0)

    def on_tournament_end(winner: Player) -> None:
        _clear()
        console.print()
        if winner.is_human:
            console.print(
                Panel(
                    "[bold green]YOU WIN THE TOURNAMENT![/bold green]",
                    expand=False,
                    border_style="green",
                ),
                justify="center",
            )
        else:
            console.print(
                Panel(
                    f"[bold]{winner.name}[/bold] wins the tournament!\n"
                    f"Final chips: {winner.chips:,}",
                    expand=False,
                ),
                justify="center",
            )

    def on_before_action(player: Player) -> None:
        if player.name in ai_personalities and not player.is_human:
            action_log.append(f"[magenta]{player.name} is thinking...[/magenta]")
            _redraw_current()

    def on_ai_debug(player: Player, info: AiDebugInfo, reasoning: str) -> None:
        if not debug:
            return
        decision = info.parsed_decision
        action = decision.get("action", "?") if decision else "?"
        amount = decision.get("amount", 0) if decision else 0
        action_str = f"{action}" + (f" {amount}" if amount else "")

        lines = [f"[bold]{player.name}[/bold]  →  [cyan]{action_str}[/cyan]"]
        if info.error:
            lines.append(f"[red]Error: {info.error}[/red]")
        lines.append(f"[dim]{reasoning}[/dim]")

        console.print(Panel("\n".join(lines), border_style="magenta", expand=False))
        Prompt.ask("[dim]Enter[/dim]")

    tournament = Tournament(
        config=config,
        players=players,
        bot_configs=rule_personalities,
        ai_bot_configs=ai_personalities,
        get_human_action=prompt_human_action,
        on_hand_start=on_hand_start,
        on_hand_end=on_hand_end,
        on_elimination=on_elimination,
        on_blind_increase=on_blind_increase,
        on_tournament_end=on_tournament_end,
        on_action=on_action,
        on_before_action=on_before_action,
        on_ai_debug=on_ai_debug,
        on_deal=on_deal,
        on_showdown=on_showdown,
    )

    try:
        tournament.run()
    except KeyboardInterrupt:
        console.print("\n[dim]Tournament interrupted.[/dim]")
