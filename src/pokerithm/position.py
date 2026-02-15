"""Table position representation for poker."""

from enum import IntEnum


class Position(IntEnum):
    """Player positions at a poker table, ordered by preflop action.

    UTG acts first preflop; BB acts last. Postflop order reverses
    (blinds act first, button last), but the enum value reflects
    preflop seating distance from UTG.
    """

    UTG = 0
    UTG_1 = 1
    MP = 2
    HJ = 3
    CO = 4
    BTN = 5
    SB = 6
    BB = 7

    @property
    def label(self) -> str:
        """Human-readable position name."""
        return {
            Position.UTG: "Under the Gun (UTG)",
            Position.UTG_1: "UTG+1",
            Position.MP: "Middle Position (MP)",
            Position.HJ: "Hijack (HJ)",
            Position.CO: "Cutoff (CO)",
            Position.BTN: "Button (BTN)",
            Position.SB: "Small Blind (SB)",
            Position.BB: "Big Blind (BB)",
        }[self]

    @property
    def short(self) -> str:
        """Short abbreviation (e.g. 'UTG', 'BTN')."""
        return {
            Position.UTG: "UTG",
            Position.UTG_1: "UTG+1",
            Position.MP: "MP",
            Position.HJ: "HJ",
            Position.CO: "CO",
            Position.BTN: "BTN",
            Position.SB: "SB",
            Position.BB: "BB",
        }[self]

    @property
    def is_early(self) -> bool:
        return self in (Position.UTG, Position.UTG_1)

    @property
    def is_middle(self) -> bool:
        return self in (Position.MP, Position.HJ)

    @property
    def is_late(self) -> bool:
        return self in (Position.CO, Position.BTN)

    @property
    def is_blind(self) -> bool:
        return self in (Position.SB, Position.BB)


def position_from_utg_distance(utg_distance: int, total_players: int) -> Position:
    """Map a seat's UTG distance to a named Position.

    The mapping works backward from the blinds: the last seat is always BB,
    second-to-last is SB, then BTN, CO, HJ. Remaining early seats compress
    into UTG / UTG+1 / MP.

    This is the same logic as the old ``_get_position_name`` in cli.py.
    """
    if utg_distance < 0 or utg_distance >= total_players:
        raise ValueError(
            f"utg_distance must be 0..{total_players - 1}, got {utg_distance}"
        )

    # Count from the end
    from_end = total_players - 1 - utg_distance

    if from_end == 0:
        return Position.BB
    if from_end == 1:
        return Position.SB
    if from_end == 2:
        return Position.BTN
    if from_end == 3:
        return Position.CO
    if from_end == 4:
        return Position.HJ

    # Early positions
    if utg_distance == 0:
        return Position.UTG
    if utg_distance == 1:
        return Position.UTG_1
    return Position.MP
