"""Interactive CLI for poker odds calculation."""

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt

from .card import Card, card, Suit
from .calculator import calculate_equity, calculate_outs, preflop_equity
from .config import get_config
from .hand import Hand, HandRank

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


def _get_position_name(utg_distance: int, total_players: int) -> str:
    """Get position name based on distance from UTG.

    Preflop order: UTG(0) -> UTG+1(1) -> ... -> CO -> BTN -> SB -> BB
    """
    # Late positions (from the end)
    if utg_distance == total_players - 1:
        return "Big Blind (BB)"
    if utg_distance == total_players - 2:
        return "Small Blind (SB)"
    if utg_distance == total_players - 3:
        return "Button (BTN)"
    if utg_distance == total_players - 4:
        return "Cutoff (CO)"
    if utg_distance == total_players - 5:
        return "Hijack (HJ)"
    # Early positions (from the start)
    if utg_distance == 0:
        return "Under the Gun (UTG)"
    if utg_distance == 1:
        return "UTG+1"
    return "Middle Position (MP)"


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


@app.command()
def interactive(
    players: int = typer.Option(2, "--players", "-p", help="Number of players"),
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
        position_name = _get_position_name(utg_distance, players)
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

            # At river, show final hand
            if len(community) >= 5:
                final = Hand(cards=hero_cards + community)
                console.print(f"[bold]Your hand: {final.value.rank}[/bold]\n")

    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
    except KeyboardInterrupt:
        console.print("\n[dim]Exiting...[/dim]")


def main():
    """Entry point."""
    app()


if __name__ == "__main__":
    main()
