"""Interactive CLI for poker odds calculation."""

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt

from .action import ActionType, BotDecision
from .bot import Bot, BotConfig, GameState
from .card import Card, card, Suit
from .calculator import calculate_equity, calculate_outs, preflop_equity
from .config import get_config
from .hand import Hand, HandRank
from .position import Position, position_from_utg_distance

app = typer.Typer(help="Poker odds calculator for Texas Hold'em")
console = Console()


def format_card(c: Card) -> str:
    """Format a card with color based on suit."""
    symbol = f"{c.rank.symbol}{c.suit.symbol}"
    if c.suit in (Suit.HEARTS, Suit.DIAMONDS):
        return f"[red]{symbol}[/red]"
    return f"[white]{symbol}[/white]"


def format_cards(cards: list[Card]) -> str:
    """Format multiple cards."""
    return " ".join(format_card(c) for c in cards)


def parse_cards(s: str) -> list[Card]:
    """Parse space or comma separated cards."""
    s = s.replace(",", " ")
    parts = s.split()
    return [card(p) for p in parts if p]


@app.command()
def equity(
    hero: str = typer.Argument(..., help="Your hole cards (e.g., 'As Kh')"),
    villain: str | None = typer.Option(None, "--vs", "-v", help="Opponent's cards (optional)"),
    board: str | None = typer.Option(None, "--board", "-b", help="Community cards"),
    players: int = typer.Option(2, "--players", "-p", help="Number of players"),
    sims: int | None = typer.Option(None, "--sims", "-n", help="Number of simulations"),
):
    """Calculate win equity against opponent(s)."""
    config = get_config()
    if sims is None:
        sims = config.simulation.default_simulations
    opponents = players - 1
    try:
        hero_cards = parse_cards(hero)
        villain_cards = parse_cards(villain) if villain else None
        community = parse_cards(board) if board else []

        console.print(f"\n[bold]Your hand:[/bold] {format_cards(hero_cards)}")
        if villain_cards:
            if opponents > 1:
                console.print(f"[bold]Opponents:[/bold] {format_cards(villain_cards)} + {opponents - 1} random")
            else:
                console.print(f"[bold]Opponent:[/bold]  {format_cards(villain_cards)}")
        else:
            console.print(f"[bold]Opponents:[/bold] {opponents} random")
        if community:
            console.print(f"[bold]Board:[/bold]     {format_cards(community)}")

        console.print(f"\n[dim]Running {sims:,} simulations...[/dim]")

        result = calculate_equity(
            hero_cards=hero_cards,
            villain_cards=villain_cards,
            community=community,
            num_opponents=opponents,
            num_simulations=sims,
        )

        # Results table
        table = Table(title="Equity Results")
        table.add_column("Outcome", style="cyan")
        table.add_column("Probability", justify="right")

        table.add_row("Win", f"[green]{result.win_percent:.1f}%[/green]")
        table.add_row("Tie", f"[yellow]{result.tie_rate * 100:.1f}%[/yellow]")
        table.add_row("Lose", f"[red]{result.lose_rate * 100:.1f}%[/red]")
        table.add_row("", "")
        table.add_row("[bold]Total Equity[/bold]", f"[bold]{result.equity:.1f}%[/bold]")

        console.print(table)

        # Hand distribution
        dist_table = Table(title="Hand Distribution (Your Hands)")
        dist_table.add_column("Hand", style="cyan")
        dist_table.add_column("Frequency", justify="right")

        for rank in reversed(HandRank):
            count = result.hand_distribution[rank]
            if count > 0:
                pct = count / result.simulations * 100
                dist_table.add_row(str(rank), f"{pct:.1f}%")

        console.print(dist_table)

    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def outs(
    hero: str = typer.Argument(..., help="Your hole cards (e.g., 'As Ks')"),
    board: str = typer.Argument(..., help="Community cards (3-4 cards)"),
):
    """Calculate outs - cards that improve your hand."""
    try:
        hero_cards = parse_cards(hero)
        community = parse_cards(board)

        console.print(f"\n[bold]Your hand:[/bold] {format_cards(hero_cards)}")
        console.print(f"[bold]Board:[/bold]     {format_cards(community)}")

        # Show current hand
        filler_count = 5 - len(hero_cards) - len(community)
        padded = hero_cards + community
        # Pad to evaluate current hand
        from .card import Card, Rank, Suit as S
        fillers = [Card(Rank.TWO, s) for s in [S.CLUBS, S.DIAMONDS, S.HEARTS, S.SPADES]]
        for f in fillers:
            if f not in padded and filler_count > 0:
                padded.append(f)
                filler_count -= 1

        current = Hand(cards=padded)
        console.print(f"[bold]Current:[/bold]   {current.value.rank}\n")

        outs_list = calculate_outs(hero_cards, community)

        if not outs_list:
            console.print("[dim]No cards improve your hand.[/dim]")
            return

        total_outs = sum(o.count for o in outs_list)

        table = Table(title=f"Outs ({total_outs} total)")
        table.add_column("Improves To", style="cyan")
        table.add_column("Outs", justify="right")
        table.add_column("Cards")

        for out in outs_list:
            cards_str = format_cards(out.cards[:8])
            if out.count > 8:
                cards_str += f" [dim]+{out.count - 8} more[/dim]"
            table.add_row(str(out.improves_to), str(out.count), cards_str)

        console.print(table)

        # Probability of hitting
        cards_left = 52 - len(hero_cards) - len(community)
        cards_to_come = 5 - len(community)

        if cards_to_come == 2:
            # Turn and river
            prob = 1 - (
                (cards_left - total_outs)
                / cards_left
                * (cards_left - 1 - total_outs)
                / (cards_left - 1)
            )
        else:
            # Just river
            prob = total_outs / cards_left

        console.print(f"\n[bold]Probability of hitting:[/bold] {prob * 100:.1f}%")

    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def preflop(
    hero: str = typer.Argument(..., help="Your hole cards (e.g., 'As Ah')"),
    opponents: int = typer.Option(1, "--opponents", "-o", help="Number of opponents"),
    sims: int | None = typer.Option(None, "--sims", "-n", help="Number of simulations"),
):
    """Calculate preflop equity against random opponents."""
    config = get_config()
    if sims is None:
        sims = config.simulation.default_simulations
    try:
        hero_cards = parse_cards(hero)

        console.print(f"\n[bold]Your hand:[/bold] {format_cards(hero_cards)}")
        console.print(f"[bold]Opponents:[/bold] {opponents} random")
        console.print(f"\n[dim]Running {sims:,} simulations...[/dim]")

        equity = preflop_equity(hero_cards, opponents, sims)

        panel = Panel(
            f"[bold green]{equity:.1f}%[/bold green]",
            title="Preflop Equity",
            expand=False,
        )
        console.print(panel)

    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


def _prompt_int(
    prompt_text: str,
    default: str | None = None,
    min_val: int = 0,
    max_val: int | None = None,
) -> int | None:
    """Prompt for an integer with validation. Returns None if user quits."""
    while True:
        if default:
            response = Prompt.ask(prompt_text, default=default)
        else:
            response = Prompt.ask(prompt_text)

        if response.lower() == "quit":
            return None

        try:
            value = int(response)
            if value < min_val:
                console.print(f"[red]Must be at least {min_val}[/red]")
                continue
            if max_val is not None and value > max_val:
                console.print(f"[red]Must be at most {max_val}[/red]")
                continue
            return value
        except ValueError:
            console.print("[red]Please enter a valid number[/red]")


def _prompt_cards(prompt_text: str, expected_count: int | None = None) -> list[Card] | None:
    """Prompt for cards with validation. Returns None if user quits."""
    while True:
        response = Prompt.ask(prompt_text)

        if response.lower() == "quit":
            return None

        try:
            cards = parse_cards(response)
            if expected_count is not None and len(cards) != expected_count:
                console.print(f"[red]Expected {expected_count} card(s), got {len(cards)}[/red]")
                continue
            return cards
        except ValueError as e:
            console.print(f"[red]Invalid card: {e}[/red]")


def _prompt_float(
    prompt_text: str,
    default: str | None = None,
    min_val: float = 0.0,
) -> float | None:
    """Prompt for a float with validation. Returns None if user quits."""
    while True:
        if default:
            response = Prompt.ask(prompt_text, default=default)
        else:
            response = Prompt.ask(prompt_text)

        if response.lower() == "quit":
            return None

        try:
            value = float(response)
            if value < min_val:
                console.print(f"[red]Must be at least {min_val}[/red]")
                continue
            return value
        except ValueError:
            console.print("[red]Please enter a valid number[/red]")


def _display_bot_decision(decision: BotDecision) -> None:
    """Display a bot recommendation with Rich formatting."""
    action = decision.action
    color = {
        ActionType.FOLD: "red",
        ActionType.CHECK: "yellow",
        ActionType.CALL: "yellow",
        ActionType.RAISE: "green",
        ActionType.ALL_IN: "bold green",
    }.get(action.type, "white")

    # Confidence bar
    filled = int(decision.confidence * 10)
    bar = "[green]" + "█" * filled + "[/green][dim]" + "░" * (10 - filled) + "[/dim]"

    console.print(
        Panel(
            f"[{color}]{action}[/{color}]\n"
            f"[dim]{decision.reasoning}[/dim]\n"
            + (f"Equity: {decision.equity:.0f}%  " if decision.equity is not None else "")
            + f"Confidence: {bar}",
            title="[bold magenta]Bot Advice[/bold magenta]",
            expand=False,
        )
    )


@app.command()
def interactive(
    players: int = typer.Option(2, "--players", "-p", help="Number of players"),
    bot_mode: bool = typer.Option(False, "--bot", help="Enable bot advisor"),
):
    """Interactive mode - track a hand as it progresses."""
    config = get_config()
    console.print(Panel("[bold]Poker Calculator - Interactive Mode[/bold]"))
    console.print("Enter your cards and track equity as the hand develops.\n")
    console.print("[dim]Card format: As Kh Td 9c 2s (rank + suit)[/dim]")
    console.print("[dim]Type 'quit' to exit[/dim]\n")

    try:
        # Get number of players
        if players == 2:
            result = _prompt_int(
                "[bold]Number of players[/bold]", default="2", min_val=2, max_val=10
            )
            if result is None:
                return
            players = result
        opponents = players - 1
        console.print(f"  → {players} players\n")

        # Get position (distance from UTG, who acts first preflop)
        result = _prompt_int(
            "[bold]Position from UTG[/bold] (0=UTG, acts first)",
            default="0",
            min_val=0,
            max_val=players - 1,
        )
        if result is None:
            return
        utg_distance = result
        position = position_from_utg_distance(utg_distance, players)
        position_name = position.label
        console.print(f"  → Position: {position_name}\n")

        # Get hero's cards
        hero_cards = _prompt_cards("[bold]Your hole cards[/bold]", expected_count=2)
        if hero_cards is None:
            return
        console.print(f"  → {format_cards(hero_cards)}\n")

        # Track through streets
        community: list[Card] = []
        streets = [("Preflop", 0), ("Flop", 3), ("Turn", 1), ("River", 1)]

        for street_idx, (street_name, cards_needed) in enumerate(streets):
            console.print(f"[bold cyan]── {street_name} ──[/bold cyan]")

            # Show position on preflop
            if street_idx == 0:
                console.print(f"Position: {position_name}")

            # Ask about folds FIRST (before calculating)
            # Preflop: utg_distance = number of players who act before you
            # Postflop: any remaining opponent could fold
            if street_idx == 0:
                max_folds = min(utg_distance, opponents)
            else:
                max_folds = opponents

            if max_folds > 0 and opponents > 1:
                folded = _prompt_int(
                    f"[bold]Players folded[/bold] (0-{max_folds})",
                    default="0",
                    min_val=0,
                    max_val=max_folds,
                )
                if folded is None:
                    return
                if folded > 0:
                    opponents -= folded
                    if opponents == 0:
                        console.print(
                            "\n[bold green]All opponents folded - you win![/bold green]\n"
                        )
                        return
                    console.print(f"  → {opponents} remaining")

            # Deal community cards (if any)
            if cards_needed > 0:
                new_cards = _prompt_cards(
                    f"[bold]{street_name} cards[/bold]", expected_count=cards_needed
                )
                if new_cards is None:
                    return
                community.extend(new_cards)
                console.print(f"  → Board: {format_cards(community)}")

            # Calculate equity with current opponent count
            equity_result = calculate_equity(
                hero_cards=hero_cards,
                villain_cards=None,
                community=community if community else None,
                num_opponents=opponents,
                num_simulations=config.simulation.interactive_simulations,
            )

            console.print(
                f"Equity vs {opponents}: [green]{equity_result.win_percent:.1f}%[/green] win, "
                f"[yellow]{equity_result.tie_rate * 100:.1f}%[/yellow] tie\n"
            )

            # Bot advice
            if bot_mode:
                pot_bb = _prompt_float(
                    "[bold]Current pot[/bold] (BB)", default="3.0", min_val=0.0
                )
                if pot_bb is None:
                    return
                to_call_bb = _prompt_float(
                    "[bold]To call[/bold] (BB)", default="0.0", min_val=0.0
                )
                if to_call_bb is None:
                    return

                street_map = {0: "preflop", 1: "flop", 2: "turn", 3: "river"}
                bot_cfg = BotConfig(
                    aggression=config.bot.aggression,
                    bluff_frequency=config.bot.bluff_frequency,
                    tightness=config.bot.tightness,
                    raise_sizing=config.bot.raise_sizing,
                )
                game_state = GameState(
                    hole_cards=hero_cards,
                    community=list(community),
                    position=position,
                    num_opponents=opponents,
                    pot_bb=pot_bb,
                    to_call_bb=to_call_bb,
                    street=street_map[street_idx],
                )
                decision = Bot(bot_cfg).decide(game_state)
                _display_bot_decision(decision)
                console.print()

            # At river, show final hand
            if len(community) >= 5:
                final = Hand(cards=hero_cards + community)
                console.print(f"[bold]Your hand: {final.value.rank}[/bold]\n")

    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
    except KeyboardInterrupt:
        console.print("\n[dim]Exiting...[/dim]")


@app.command(name="bot")
def bot_command(
    hero: str = typer.Argument(..., help="Your hole cards (e.g., 'As Kh')"),
    position_idx: int = typer.Option(4, "--position", "-P", help="Position (0=UTG .. 5=BTN, 6=SB, 7=BB)"),
    players: int = typer.Option(6, "--players", "-p", help="Number of players"),
    board: str | None = typer.Option(None, "--board", "-b", help="Community cards"),
    pot: float = typer.Option(1.5, "--pot", help="Pot size in BB"),
    to_call: float = typer.Option(0.0, "--to-call", help="Amount to call in BB"),
):
    """Get bot advice for a specific situation."""
    try:
        hero_cards = parse_cards(hero)
        community = parse_cards(board) if board else []
        pos = Position(position_idx)
        opponents = players - 1

        # Determine street from board size
        street_map = {0: "preflop", 3: "flop", 4: "turn", 5: "river"}
        street = street_map.get(len(community))
        if street is None:
            console.print(f"[red]Invalid board: expected 0, 3, 4, or 5 cards, got {len(community)}[/red]")
            raise typer.Exit(1)

        config = get_config()
        bot_cfg = BotConfig(
            aggression=config.bot.aggression,
            bluff_frequency=config.bot.bluff_frequency,
            tightness=config.bot.tightness,
            raise_sizing=config.bot.raise_sizing,
        )
        game_state = GameState(
            hole_cards=hero_cards,
            community=community,
            position=pos,
            num_opponents=opponents,
            pot_bb=pot,
            to_call_bb=to_call,
            street=street,
        )

        console.print(f"\n[bold]Hand:[/bold]     {format_cards(hero_cards)}")
        console.print(f"[bold]Position:[/bold] {pos.label}")
        console.print(f"[bold]Street:[/bold]   {street.capitalize()}")
        if community:
            console.print(f"[bold]Board:[/bold]    {format_cards(community)}")
        console.print(f"[bold]Pot:[/bold]      {pot} BB  |  To call: {to_call} BB")
        console.print()

        decision = Bot(bot_cfg).decide(game_state)
        _display_bot_decision(decision)

    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def sim(
    bots: int = typer.Option(7, "--bots", "-b", help="Number of bot opponents (1-7)"),
    stack: int = typer.Option(1500, "--stack", "-s", help="Starting chip stack"),
    hands_per_level: int = typer.Option(10, "--level-hands", "-l", help="Hands per blind level"),
    ai: int = typer.Option(0, "--ai", "-a", help="Number of AI opponents powered by Claude (0-7)"),
    model: str = typer.Option("opus", "--model", "-m", help="Claude model for AI opponents (opus, sonnet, haiku)"),
    debug: bool = typer.Option(False, "--debug", "-d", help="Show AI prompt/response debug info"),
):
    """Play a Texas Hold'em tournament against bots."""
    from .sim_display import run_tournament_cli

    bots = max(1, min(7, bots))
    ai = max(0, min(ai, bots))
    run_tournament_cli(
        num_bots=bots,
        starting_stack=stack,
        hands_per_level=hands_per_level,
        ai_opponents=ai,
        ai_model=model,
        debug=debug,
    )


def main():
    """Entry point."""
    app()


if __name__ == "__main__":
    main()
