from __future__ import annotations

from typing import Any

from .client import LiveUnavailable, get_live_client


def execute_shadow(*, decision: dict[str, Any], token_id: str, stake_usd: float) -> dict[str, Any]:
    entry = float(decision["entry_price"])
    return get_live_client().preview_buy(
        token_id=token_id,
        stake_usd=stake_usd,
        max_price=entry,
    )


def execute_live(*, decision: dict[str, Any], token_id: str, stake_usd: float) -> dict[str, Any]:
    entry = float(decision["entry_price"])
    return get_live_client().place_buy(
        token_id=token_id,
        stake_usd=stake_usd,
        max_price=entry,
    )


__all__ = ["LiveUnavailable", "execute_live", "execute_shadow"]
