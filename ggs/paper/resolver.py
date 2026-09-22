from __future__ import annotations

import json
from typing import Any, Optional

import certifi
import requests

from .accounting import resolve_position


def _list(v: Any) -> list[Any]:
    if isinstance(v, list):
        return v
    if isinstance(v, str):
        try:
            x = json.loads(v)
            return x if isinstance(x, list) else []
        except Exception:
            return []
    return []


def gamma_outcome(gamma_base: str, slug: str) -> Optional[str]:
    try:
        r = requests.get(f"{gamma_base.rstrip('/')}/markets", params={"slug": slug}, timeout=6, verify=certifi.where(), headers={"User-Agent": "GGS/1.0"})
        r.raise_for_status()
        arr = r.json()
        market = arr[0] if isinstance(arr, list) and arr else None
        if not isinstance(market, dict):
            return None
        outcomes = [str(x).upper() for x in _list(market.get("outcomes"))]
        prices = [float(x) for x in _list(market.get("outcomePrices"))]
        if len(outcomes) != len(prices) or not prices or max(prices) < 0.99:
            return None
        winner = outcomes[prices.index(max(prices))]
        return winner if winner in {"UP", "DOWN"} else None
    except Exception:
        return None


def reconcile(position: dict[str, Any], stream, gamma_base: str, resolved_at: str) -> Optional[dict[str, Any]]:
    window = int(position.get("resolution_window_s") or 60)
    end_ts = float(position["market_end_ts"])
    close = stream.price_near(end_ts, window, tolerance_sec=10.0)
    ptb = float(position["price_to_beat"])
    if close is not None:
        cp = float(close["price"])
        outcome = "UP" if cp >= ptb else "DOWN"
        return resolve_position(position, outcome, resolved_at, close_price=cp, resolution_method=f"chainlink_twap_{window}s")
    outcome = gamma_outcome(gamma_base, str(position.get("slug") or ""))
    if outcome:
        return resolve_position(position, outcome, resolved_at, resolution_method="polymarket_resolved_outcome")
    return None
