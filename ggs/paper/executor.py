from __future__ import annotations
from typing import Any

from .accounting import open_position


def execute_paper(*, decision: dict[str, Any], slug: str, token_id: str, stake_usd: float, market_start_ts: int, market_end_ts: int, price_to_beat: float, resolution_window_s: int, opened_at: str) -> dict[str, Any]:
    side = str(decision["side"])
    return open_position(
        slug=slug,
        side=side,
        token_id=token_id,
        entry_price=float(decision["entry_price"]),
        stake_usd=stake_usd,
        market_start_ts=market_start_ts,
        market_end_ts=market_end_ts,
        price_to_beat=price_to_beat,
        resolution_window_s=resolution_window_s,
        decision=decision,
        opened_at=opened_at,
    )
