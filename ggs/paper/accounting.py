from __future__ import annotations
from typing import Any


def open_position(*, slug: str, side: str, token_id: str, entry_price: float, stake_usd: float, market_start_ts: int, market_end_ts: int, price_to_beat: float, resolution_window_s: int, decision: dict[str, Any], opened_at: str) -> dict[str, Any]:
    effective_unit_cost = float(decision.get("effective_unit_cost") or entry_price)
    shares = float(stake_usd) / effective_unit_cost
    return {
        "status": "OPEN",
        "slug": slug,
        "side": side,
        "token_id": str(token_id),
        "entry_price": float(entry_price),
        "effective_unit_cost": effective_unit_cost,
        "stake_usd": float(stake_usd),
        "shares": shares,
        "potential_payout": shares,
        "potential_profit": shares - float(stake_usd),
        "payout_multiple": 1.0 / effective_unit_cost,
        "gross_payout_multiple": 1.0 / float(entry_price),
        "market_start_ts": int(market_start_ts),
        "market_end_ts": int(market_end_ts),
        "price_to_beat": float(price_to_beat),
        "resolution_window_s": int(resolution_window_s),
        "opened_at": opened_at,
        "decision_snapshot": decision,
    }


def resolve_position(position: dict[str, Any], outcome: str, resolved_at: str, *, close_price: float | None = None, resolution_method: str = "chainlink") -> dict[str, Any]:
    win = str(position.get("side")) == str(outcome)
    stake = float(position["stake_usd"])
    payout = float(position["shares"]) if win else 0.0
    row = dict(position)
    row.update({
        "status": "RESOLVED",
        "outcome": outcome,
        "result": "WIN" if win else "LOSS",
        "payout": payout,
        "pnl": payout - stake,
        "resolved_at": resolved_at,
        "resolution_method": resolution_method,
    })
    if close_price is not None:
        row["close_price"] = float(close_price)
    return row
