"""Single-hand orchestrator — deals, runs betting rounds, resolves showdown."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from .action import Action, ActionType
from .ai_bot import AiBot, AiBotConfig, AiDebugInfo
from .betting import BettingRound
from .bot import Bot, BotConfig, GameState
from .card import Card
from .deck import Deck
from .evaluator import PlayerHand, evaluate_game
from .hand import HandValue
from .player import Player, PlayerActionContext
from .position import Position, position_from_utg_distance
from .pot import PotManager, SidePot

STREETS = ["preflop", "flop", "turn", "river"]


@dataclass
class HandResult:
    """Outcome of a single hand."""

    pots: list[SidePot]
    pot_winners: list[tuple[SidePot, list[Player], HandValue | None]]
    community: list[Card]
    went_to_showdown: bool


@dataclass
class Table:
    """Orchestrates a single hand of Texas Hold'em."""

    players: list[Player]
    dealer_seat: int
    small_blind: int
    big_blind: int

    get_human_action: Callable[[Player, PlayerActionContext], Action] | None = None
    bot_configs: dict[str, BotConfig] = field(default_factory=dict)
    ai_bot_configs: dict[str, AiBotConfig] = field(default_factory=dict)
    _bot_cache: dict[str, Bot] = field(default_factory=dict, repr=False)
    _ai_bot_cache: dict[str, AiBot] = field(default_factory=dict, repr=False)

    on_action: Callable[[Player, Action], None] | None = None
    on_before_action: Callable[[Player], None] | None = None
    on_ai_debug: Callable[[Player, AiDebugInfo, str], None] | None = None
    on_deal: Callable[[str, list[Card]], None] | None = None
    on_showdown: Callable[[list[tuple[SidePot, list[Player], HandValue | None]]], None] | None = None

    def play_hand(self) -> HandResult:
        """Play a complete hand. Returns the result."""
        # Setup
        deck = Deck()
        deck.shuffle()
        pot = PotManager()
        community: list[Card] = []

        alive = [p for p in self.players if not p.is_eliminated]
        for p in alive:
            p.reset_for_new_hand()

        # Post blinds
        sb_player, bb_player = self._post_blinds(alive, pot)

        # Deal hole cards
        for p in alive:
            p.hole_cards = deck.deal(2)
        if self.on_deal:
            self.on_deal("hole_cards", [])

        # Assign positions for this hand
        positions = self._assign_positions(alive)

        went_to_showdown = False

        for street_idx, street in enumerate(STREETS):
            # Deal community cards
            if street == "flop":
                deck.deal(1)  # burn
                community.extend(deck.deal(3))
                if self.on_deal:
                    self.on_deal("flop", list(community))
            elif street == "turn":
                deck.deal(1)  # burn
                community.extend(deck.deal(1))
                if self.on_deal:
                    self.on_deal("turn", list(community))
            elif street == "river":
                deck.deal(1)  # burn
                community.extend(deck.deal(1))
                if self.on_deal:
                    self.on_deal("river", list(community))

            # Reset per-round bets
            for p in alive:
                p.reset_for_new_round()

            # Determine action order
            if street == "preflop":
                action_order = self._preflop_order(alive, sb_player, bb_player)
                initial_bet = self.big_blind
            else:
                action_order = self._postflop_order(alive)
                initial_bet = 0

            # Run betting round
            betting = BettingRound(
                players=action_order,
                pot=pot,
                big_blind=self.big_blind,
                current_bet=initial_bet,
                min_raise=self.big_blind,
            )

            def make_context(
                player: Player,
                _community: list[Card] = community,
                _pot: PotManager = pot,
                _betting: BettingRound = betting,
                _positions: dict[int, str] = positions,
                _alive: list[Player] = alive,
            ) -> PlayerActionContext:
                to_call = max(0, _betting.current_bet - player.current_bet)
                min_raise_to = _betting.current_bet + _betting.min_raise
                max_raise_to = player.current_bet + player.chips
                return PlayerActionContext(
                    hole_cards=list(player.hole_cards),
                    community=list(_community),
                    pot_total=_pot.total,
                    to_call=to_call,
                    min_raise=min_raise_to,
                    max_raise=max_raise_to,
                    current_bet=player.current_bet,
                    street=street,
                    num_active_players=sum(1 for p in _alive if p.is_in_hand),
                    position_label=_positions.get(player.seat, "?"),
                )

            def get_action(
                player: Player,
                ctx: PlayerActionContext,
                _street: str = street,
                _community: list[Card] = community,
                _positions: dict[int, str] = positions,
            ) -> Action:
                if self.on_before_action:
                    self.on_before_action(player)
                if player.is_human and self.get_human_action:
                    return self.get_human_action(player, ctx)
                return self._get_bot_action(
                    player, ctx, _street, _community, _positions
                )

            betting.run(get_action, make_context, self.on_action)

            # Check if hand is over (only one player left)
            in_hand = [p for p in alive if p.is_in_hand]
            if len(in_hand) <= 1:
                break

        # Showdown / resolve
        in_hand = [p for p in alive if p.is_in_hand]
        side_pots = PotManager.calculate_side_pots(alive)

        # If no side pots (everyone folded to one player), make a single pot
        if not side_pots and pot.total > 0:
            side_pots = [SidePot(amount=pot.total, eligible_players=in_hand)]

        pot_winners: list[tuple[SidePot, list[Player], HandValue | None]] = []

        if len(in_hand) == 1:
            # Everyone else folded — single winner takes the whole pot
            winner = in_hand[0]
            total_won = sum(sp.amount for sp in side_pots)
            winner.chips += total_won
            combined = SidePot(amount=total_won, eligible_players=[winner])
            pot_winners = [(combined, [winner], None)]
        else:
            # Showdown
            went_to_showdown = True

            # Deal remaining community cards if needed (all-in before river)
            while len(community) < 5:
                deck.deal(1)  # burn
                community.extend(deck.deal(1))

            for sp in side_pots:
                eligible = [p for p in sp.eligible_players if p.is_in_hand]
                if not eligible:
                    continue

                player_hands = [
                    PlayerHand(
                        player_id=p.seat,
                        hole_cards=list(p.hole_cards),
                    )
                    for p in eligible
                ]
                result = evaluate_game(player_hands, community)

                winning_seats = {w.player_id for w in result.winners}
                winners = [p for p in eligible if p.seat in winning_seats]

                share = sp.amount // len(winners)
                remainder = sp.amount % len(winners)
                for i, w in enumerate(winners):
                    w.chips += share + (1 if i < remainder else 0)

                hand_value = result.winners[0].hand_value
                pot_winners.append((sp, winners, hand_value))

        if self.on_showdown:
            self.on_showdown(pot_winners)

        return HandResult(
            pots=side_pots,
            pot_winners=pot_winners,
            community=community,
            went_to_showdown=went_to_showdown,
        )

    def _post_blinds(
        self, alive: list[Player], pot: PotManager
    ) -> tuple[Player, Player]:
        """Post small and big blinds. Returns (sb_player, bb_player)."""
        seats = [p.seat for p in alive]
        dealer_idx = self._find_seat_index(seats, self.dealer_seat)

        if len(alive) == 2:
            # Heads-up: dealer posts SB, other posts BB
            sb_idx = dealer_idx
            bb_idx = (dealer_idx + 1) % len(alive)
        else:
            sb_idx = (dealer_idx + 1) % len(alive)
            bb_idx = (dealer_idx + 2) % len(alive)

        sb_player = alive[sb_idx]
        bb_player = alive[bb_idx]

        sb_actual = sb_player.bet(self.small_blind)
        pot.add(sb_actual)
        bb_actual = bb_player.bet(self.big_blind)
        pot.add(bb_actual)

        return sb_player, bb_player

    def _preflop_order(
        self,
        alive: list[Player],
        sb_player: Player,
        bb_player: Player,
    ) -> list[Player]:
        """Preflop: UTG acts first (player after BB), BB acts last."""
        seats = [p.seat for p in alive]
        bb_idx = seats.index(bb_player.seat)
        # Start from player after BB
        order = []
        for i in range(1, len(alive)):
            idx = (bb_idx + i) % len(alive)
            order.append(alive[idx])
        # BB acts last
        order.append(bb_player)
        return order

    def _postflop_order(self, alive: list[Player]) -> list[Player]:
        """Postflop: SB acts first (first player after dealer)."""
        seats = [p.seat for p in alive]
        dealer_idx = self._find_seat_index(seats, self.dealer_seat)
        order = []
        for i in range(1, len(alive) + 1):
            idx = (dealer_idx + i) % len(alive)
            p = alive[idx]
            if p.is_in_hand:
                order.append(p)
        return order

    def _assign_positions(self, alive: list[Player]) -> dict[int, str]:
        """Assign position labels to seats."""
        seats = [p.seat for p in alive]
        dealer_idx = self._find_seat_index(seats, self.dealer_seat)
        n = len(alive)
        positions: dict[int, str] = {}

        for i in range(n):
            idx = (dealer_idx + 1 + i) % n
            player = alive[idx]
            try:
                pos = position_from_utg_distance(i, n)
                positions[player.seat] = pos.short
            except ValueError:
                positions[player.seat] = "?"

        return positions

    def _get_bot_action(
        self,
        player: Player,
        ctx: PlayerActionContext,
        street: str,
        community: list[Card],
        positions: dict[int, str],
    ) -> Action:
        """Adapter: convert bot's BB-based decision to chip-based action."""
        bb = self.big_blind
        pos_label = positions.get(player.seat, "UTG")

        # Check if this player uses the AI bot
        if player.name in self.ai_bot_configs:
            return self._get_ai_bot_action(
                player, ctx, street, community, positions
            )

        if player.name not in self._bot_cache:
            config = self.bot_configs.get(player.name, BotConfig())
            self._bot_cache[player.name] = Bot(config)
        bot = self._bot_cache[player.name]

        # Map position label to Position enum
        label_to_pos = {
            "UTG": Position.UTG,
            "UTG+1": Position.UTG_1,
            "MP": Position.MP,
            "HJ": Position.HJ,
            "CO": Position.CO,
            "BTN": Position.BTN,
            "SB": Position.SB,
            "BB": Position.BB,
        }
        position = label_to_pos.get(pos_label, Position.UTG)

        num_opponents = ctx.num_active_players - 1
        if num_opponents < 1:
            num_opponents = 1

        game_state = GameState(
            hole_cards=list(player.hole_cards),
            community=list(community),
            position=position,
            num_opponents=num_opponents,
            pot_bb=ctx.pot_total / bb if bb > 0 else 0,
            to_call_bb=ctx.to_call / bb if bb > 0 else 0,
            street=street,
            stack_bb=player.chips / bb if bb > 0 else 0,
            invested_bb=player.total_bet_this_hand / bb if bb > 0 else 0,
        )

        decision = bot.decide(game_state)
        action = decision.action

        # Convert BB-based action to chip-based
        if action.type == ActionType.FOLD:
            if ctx.to_call == 0:
                return Action(ActionType.CHECK)
            return Action(ActionType.FOLD)

        if action.type == ActionType.CHECK:
            if ctx.to_call > 0:
                return Action(ActionType.CALL)
            return Action(ActionType.CHECK)

        if action.type == ActionType.CALL:
            return Action(ActionType.CALL)

        if action.type in (ActionType.RAISE, ActionType.ALL_IN):
            raise_bb = action.amount
            raise_chips = int(raise_bb * bb)

            # The bot's preflop sizing is a raise-to amount (e.g., 2.5 BB).
            # Postflop sizing is a bet/raise amount relative to the pot.
            # Convert postflop bets to raise-to by adding the current bet level.
            current_total = player.current_bet + ctx.to_call
            if street == "preflop":
                raise_to = raise_chips
            else:
                raise_to = current_total + raise_chips

            # If raise-to is at or below what we'd need to just call,
            # the bot didn't really intend to raise — just call/check.
            if raise_to <= current_total:
                if ctx.to_call > 0:
                    return Action(ActionType.CALL)
                return Action(ActionType.CHECK)
            # Clamp to legal range
            if raise_to >= player.current_bet + player.chips:
                return Action(ActionType.ALL_IN, player.current_bet + player.chips)
            if raise_to < ctx.min_raise:
                raise_to = ctx.min_raise
            return Action(ActionType.RAISE, raise_to)

        return Action(ActionType.CHECK)

    def _get_ai_bot_action(
        self,
        player: Player,
        ctx: PlayerActionContext,
        street: str,
        community: list[Card],
        positions: dict[int, str],
    ) -> Action:
        """Get action from AI-powered bot (Claude Code CLI)."""
        if player.name not in self._ai_bot_cache:
            config = self.ai_bot_configs[player.name]
            self._ai_bot_cache[player.name] = AiBot(config)
        ai_bot = self._ai_bot_cache[player.name]

        bb = self.big_blind
        pos_label = positions.get(player.seat, "UTG")

        label_to_pos = {
            "UTG": Position.UTG, "UTG+1": Position.UTG_1,
            "MP": Position.MP, "HJ": Position.HJ,
            "CO": Position.CO, "BTN": Position.BTN,
            "SB": Position.SB, "BB": Position.BB,
        }
        position = label_to_pos.get(pos_label, Position.UTG)

        num_opponents = ctx.num_active_players - 1
        if num_opponents < 1:
            num_opponents = 1

        game_state = GameState(
            hole_cards=list(player.hole_cards),
            community=list(community),
            position=position,
            num_opponents=num_opponents,
            pot_bb=ctx.pot_total / bb if bb > 0 else 0,
            to_call_bb=ctx.to_call / bb if bb > 0 else 0,
            street=street,
            stack_bb=player.chips / bb if bb > 0 else 0,
            invested_bb=player.total_bet_this_hand / bb if bb > 0 else 0,
        )

        decision = ai_bot.decide(game_state)
        action = decision.action

        # Fire debug callback
        if self.on_ai_debug and ai_bot.last_debug:
            self.on_ai_debug(player, ai_bot.last_debug, decision.reasoning)

        # Convert BB-based action to chip-based (same logic as rule-based bot)
        if action.type == ActionType.FOLD:
            if ctx.to_call == 0:
                return Action(ActionType.CHECK)
            return Action(ActionType.FOLD)

        if action.type == ActionType.CHECK:
            if ctx.to_call > 0:
                return Action(ActionType.CALL)
            return Action(ActionType.CHECK)

        if action.type == ActionType.CALL:
            return Action(ActionType.CALL)

        if action.type in (ActionType.RAISE, ActionType.ALL_IN):
            raise_bb = action.amount
            raise_chips = int(raise_bb * bb)
            current_total = player.current_bet + ctx.to_call

            if street == "preflop":
                raise_to = raise_chips
            else:
                raise_to = current_total + raise_chips

            if raise_to <= current_total:
                if ctx.to_call > 0:
                    return Action(ActionType.CALL)
                return Action(ActionType.CHECK)
            if raise_to >= player.current_bet + player.chips:
                return Action(ActionType.ALL_IN, player.current_bet + player.chips)
            if raise_to < ctx.min_raise:
                raise_to = ctx.min_raise
            return Action(ActionType.RAISE, raise_to)

        return Action(ActionType.CHECK)

    @staticmethod
    def _find_seat_index(seats: list[int], target: int) -> int:
        """Find the index of `target` in seats, or closest seat after it."""
        if target in seats:
            return seats.index(target)
        # Find next seat clockwise
        for i, s in enumerate(seats):
            if s > target:
                return i
        return 0
