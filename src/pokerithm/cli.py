"""Interactive CLI for poker odds calculation."""

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt

from .card import Card, card, Suit
from .calculator import calculate_equity, calculate_outs, preflop_equity
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
    villain: str = typer.Option(None, "--vs", "-v", help="Opponent's cards (optional)"),
    board: str = typer.Option(None, "--board", "-b", help="Community cards"),
    sims: int = typer.Option(10000, "--sims", "-n", help="Number of simulations"),
):
    """Calculate win equity against an opponent."""
    try:
        hero_cards = parse_cards(hero)
        villain_cards = parse_cards(villain) if villain else None
        community = parse_cards(board) if board else []

        console.print(f"\n[bold]Your hand:[/bold] {format_cards(hero_cards)}")
        if villain_cards:
            console.print(f"[bold]Opponent:[/bold]  {format_cards(villain_cards)}")
        else:
            console.print("[bold]Opponent:[/bold]  [dim]Random[/dim]")
        if community:
            console.print(f"[bold]Board:[/bold]     {format_cards(community)}")

        console.print(f"\n[dim]Running {sims:,} simulations...[/dim]")

        result = calculate_equity(
            hero_cards=hero_cards,
            villain_cards=villain_cards,
            community=community,
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
    sims: int = typer.Option(10000, "--sims", "-n", help="Number of simulations"),
):
    """Calculate preflop equity against random opponents."""
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


@app.command()
def interactive():
    """Interactive mode - track a hand as it progresses."""
    console.print(Panel("[bold]Poker Calculator - Interactive Mode[/bold]"))
    console.print("Enter your cards and track equity as the hand develops.\n")
    console.print("[dim]Card format: As Kh Td 9c 2s (rank + suit)[/dim]")
    console.print("[dim]Type 'quit' to exit[/dim]\n")

    try:
        # Get hero's cards
        hero_input = Prompt.ask("[bold]Your hole cards[/bold]")
        if hero_input.lower() == "quit":
            return
        hero_cards = parse_cards(hero_input)
        console.print(f"  → {format_cards(hero_cards)}\n")

        # Get opponent's cards (optional)
        villain_input = Prompt.ask(
            "[bold]Opponent's cards[/bold] [dim](Enter to skip)[/dim]",
            default="",
        )
        villain_cards = parse_cards(villain_input) if villain_input else None
        if villain_cards:
            console.print(f"  → {format_cards(villain_cards)}\n")

        # Track through streets
        community: list[Card] = []
        streets = [("Preflop", 0), ("Flop", 3), ("Turn", 1), ("River", 1)]

        for street_name, cards_needed in streets:
            # Calculate current equity
            result = calculate_equity(
                hero_cards=hero_cards,
                villain_cards=villain_cards,
                community=community if community else None,
                num_simulations=5000,
            )

            console.print(f"[bold cyan]── {street_name} ──[/bold cyan]")
            if community:
                console.print(f"Board: {format_cards(community)}")
            console.print(
                f"Equity: [green]{result.win_percent:.1f}%[/green] win, "
                f"[yellow]{result.tie_rate * 100:.1f}%[/yellow] tie\n"
            )

            if len(community) >= 5:
                # Show final hand
                final = Hand(cards=hero_cards + community)
                console.print(f"[bold]Your hand: {final.value.rank}[/bold]\n")
                break

            if cards_needed > 0:
                prompt = f"[bold]{street_name} cards ({cards_needed})[/bold]"
                street_input = Prompt.ask(prompt)
                if street_input.lower() == "quit":
                    return
                new_cards = parse_cards(street_input)
                community.extend(new_cards)
                console.print(f"  → {format_cards(new_cards)}\n")

    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
    except KeyboardInterrupt:
        console.print("\n[dim]Exiting...[/dim]")


def main():
    """Entry point."""
    app()


if __name__ == "__main__":
    main()
