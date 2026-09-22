from __future__ import annotations
from typing import Any


def can_open(*, balance: float, stake: float, open_position: dict[str, Any] | None, seen_market: bool) -> tuple[bool, str]:
    if open_position is not None:
        return False, "POSITION_ALREADY_OPEN"
    if seen_market:
        return False, "ROUND_ALREADY_USED"
    if balance < stake:
        return False, "INSUFFICIENT_PAPER_BALANCE"
    return True, "OK"
