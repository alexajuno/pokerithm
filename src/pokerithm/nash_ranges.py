"""Pre-computed Nash equilibrium push/fold ranges.

Ranges are based on Sklansky-Chubukov rankings adapted for multi-way
pots. At <=10bb, the correct strategy is nearly always push-or-fold.

Ranges are indexed by stack depth; player count adjusts via multiplier.
"""

# ── Shove ranges by effective stack depth ──────────────────

_SHOVE_3BB: set[str] = {
    "AA", "KK", "QQ", "JJ", "TT", "99", "88", "77", "66", "55", "44", "33", "22",
    "AKs", "AQs", "AJs", "ATs", "A9s", "A8s", "A7s", "A6s", "A5s", "A4s", "A3s", "A2s",
    "AKo", "AQo", "AJo", "ATo", "A9o", "A8o", "A7o", "A6o", "A5o", "A4o", "A3o", "A2o",
    "KQs", "KJs", "KTs", "K9s", "K8s", "K7s", "K6s", "K5s", "K4s", "K3s", "K2s",
    "KQo", "KJo", "KTo", "K9o", "K8o", "K7o", "K6o", "K5o", "K4o", "K3o",
    "QJs", "QTs", "Q9s", "Q8s", "Q7s", "Q6s", "Q5s", "Q4s", "Q3s",
    "QJo", "QTo", "Q9o", "Q8o", "Q7o", "Q6o",
    "JTs", "J9s", "J8s", "J7s", "J6s", "J5s",
    "JTo", "J9o", "J8o", "J7o",
    "T9s", "T8s", "T7s", "T6s",
    "T9o", "T8o", "T7o",
    "98s", "97s", "96s", "95s",
    "98o", "97o",
    "87s", "86s", "85s",
    "87o", "86o",
    "76s", "75s", "74s",
    "76o",
    "65s", "64s", "63s",
    "54s", "53s",
    "43s",
}

_SHOVE_5BB: set[str] = {
    "AA", "KK", "QQ", "JJ", "TT", "99", "88", "77", "66", "55", "44", "33", "22",
    "AKs", "AQs", "AJs", "ATs", "A9s", "A8s", "A7s", "A6s", "A5s", "A4s", "A3s", "A2s",
    "AKo", "AQo", "AJo", "ATo", "A9o", "A8o", "A7o", "A6o", "A5o", "A4o", "A3o", "A2o",
    "KQs", "KJs", "KTs", "K9s", "K8s", "K7s", "K6s", "K5s", "K4s", "K3s", "K2s",
    "KQo", "KJo", "KTo", "K9o", "K8o", "K7o", "K6o", "K5o",
    "QJs", "QTs", "Q9s", "Q8s", "Q7s", "Q6s", "Q5s",
    "QJo", "QTo", "Q9o", "Q8o",
    "JTs", "J9s", "J8s", "J7s", "J6s",
    "JTo", "J9o", "J8o",
    "T9s", "T8s", "T7s", "T6s",
    "T9o", "T8o",
    "98s", "97s", "96s",
    "98o", "97o",
    "87s", "86s", "85s",
    "87o",
    "76s", "75s",
    "76o",
    "65s", "64s",
    "54s", "53s",
}

_SHOVE_8BB: set[str] = {
    "AA", "KK", "QQ", "JJ", "TT", "99", "88", "77", "66", "55", "44", "33", "22",
    "AKs", "AQs", "AJs", "ATs", "A9s", "A8s", "A7s", "A6s", "A5s", "A4s", "A3s", "A2s",
    "AKo", "AQo", "AJo", "ATo", "A9o", "A8o", "A7o", "A6o", "A5o", "A4o", "A3o", "A2o",
    "KQs", "KJs", "KTs", "K9s", "K8s", "K7s", "K6s",
    "KQo", "KJo", "KTo", "K9o",
    "QJs", "QTs", "Q9s", "Q8s",
    "QJo", "QTo",
    "JTs", "J9s", "J8s",
    "JTo",
    "T9s", "T8s",
    "T9o",
    "98s", "97s",
    "87s", "86s",
    "76s", "75s",
    "65s", "64s",
    "54s",
}

_SHOVE_10BB: set[str] = {
    "AA", "KK", "QQ", "JJ", "TT", "99", "88", "77", "66", "55", "44", "33", "22",
    "AKs", "AQs", "AJs", "ATs", "A9s", "A8s", "A7s", "A6s", "A5s", "A4s", "A3s", "A2s",
    "AKo", "AQo", "AJo", "ATo", "A9o", "A8o", "A7o",
    "KQs", "KJs", "KTs", "K9s",
    "KQo", "KJo",
    "QJs", "QTs",
    "QJo",
    "JTs", "J9s",
    "T9s",
    "98s",
    "87s",
    "76s",
    "65s",
}

_SHOVE_15BB: set[str] = {
    "AA", "KK", "QQ", "JJ", "TT", "99", "88", "77", "66", "55",
    "AKs", "AQs", "AJs", "ATs", "A9s", "A8s", "A7s", "A6s", "A5s",
    "AKo", "AQo", "AJo", "ATo",
    "KQs", "KJs", "KTs",
    "KQo",
    "QJs", "QTs",
    "JTs",
}

_SHOVE_20BB: set[str] = {
    "AA", "KK", "QQ", "JJ", "TT", "99",
    "AKs", "AQs", "AJs", "ATs",
    "AKo", "AQo",
    "KQs",
}

# ── Call ranges (facing an all-in) ─────────────────────────

_CALL_8BB: set[str] = {
    "AA", "KK", "QQ", "JJ", "TT", "99", "88", "77",
    "AKs", "AQs", "AJs", "ATs", "A9s",
    "AKo", "AQo", "AJo",
    "KQs", "KJs",
    "QJs",
}

_CALL_15BB: set[str] = {
    "AA", "KK", "QQ", "JJ", "TT",
    "AKs", "AQs", "AJs",
    "AKo", "AQo",
    "KQs",
}

# ── Villain call ranges by tendancy ────────────────────────

VILLAIN_CALL_RANGES: dict[str, set[str]] = {
    "tight": {
        "AA", "KK", "QQ", "JJ", "TT",
        "AKs", "AQs",
        "AKo",
    },
    "normal": {
        "AA", "KK", "QQ", "JJ", "TT", "99", "88", "77",
        "AKs", "AQs", "AJs", "ATs",
        "AKo", "AQo", "AJo",
        "KQs", "KJs",
        "QJs",
    },
    "loose": {
        "AA", "KK", "QQ", "JJ", "TT", "99", "88", "77", "66", "55",
        "AKs", "AQs", "AJs", "ATs", "A9s", "A8s", "A7s", "A5s",
        "AKo", "AQo", "AJo", "ATo", "A9o",
        "KQs", "KJs", "KTs", "K9s",
        "KQo", "KJo",
        "QJs", "QTs",
        "JTs",
    },
}


# ── Public API ─────────────────────────────────────────────


def get_shove_range(stack_bb: float, num_players: int = 6) -> set[str]:
    """Get the Nash shove range for a given stack depth."""
    if stack_bb <= 3:
        base = _SHOVE_3BB
    elif stack_bb <= 5:
        base = _SHOVE_5BB
    elif stack_bb <= 8:
        base = _SHOVE_8BB
    elif stack_bb <= 10:
        base = _SHOVE_10BB
    elif stack_bb <= 15:
        base = _SHOVE_15BB
    else:
        base = _SHOVE_20BB

    # Fewer players means wider range — step up one tier
    if num_players <= 3:
        if base is _SHOVE_20BB:
            return set(_SHOVE_15BB)
        if base is _SHOVE_15BB:
            return set(_SHOVE_10BB)
        if base is _SHOVE_10BB:
            return set(_SHOVE_8BB)
        if base is _SHOVE_8BB:
            return set(_SHOVE_5BB)

    return set(base)


def get_call_range(stack_bb: float) -> set[str]:
    """Get the calling range for facing an all-in."""
    if stack_bb <= 10:
        return set(_CALL_8BB)
    return set(_CALL_15BB)


def is_in_range(hand_key: str, range_set: set[str]) -> bool:
    """Check if a hand key is in a given range."""
    return hand_key in range_set
