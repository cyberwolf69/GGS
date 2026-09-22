from __future__ import annotations

import time
from typing import Any, Optional

import certifi
import requests


def _float(x: Any) -> Optional[float]:
    try:
        return float(x)
    except Exception:
        return None


def fetch_book(clob_base: str, token_id: str, timeout: float = 5.0) -> dict[str, Any]:
    t0 = time.perf_counter()
    r = requests.get(f"{clob_base.rstrip('/')}/book", params={"token_id": str(token_id)}, timeout=timeout, verify=certifi.where(), headers={"User-Agent": "GGS/1.0"})
    latency_ms = (time.perf_counter() - t0) * 1000.0
    r.raise_for_status()
    data = r.json()
    bids = data.get("bids") or []
    asks = data.get("asks") or []
    bid_rows = [(p, _float(p.get("price")), _float(p.get("size"))) for p in bids if isinstance(p, dict)]
    ask_rows = [(p, _float(p.get("price")), _float(p.get("size"))) for p in asks if isinstance(p, dict)]
    bid_rows = [x for x in bid_rows if x[1] is not None]
    ask_rows = [x for x in ask_rows if x[1] is not None]
    best_bid = max((x[1] for x in bid_rows), default=None)
    best_ask = min((x[1] for x in ask_rows), default=None)
    best_ask_size = None
    if best_ask is not None:
        sizes = [x[2] for x in ask_rows if x[1] == best_ask and x[2] is not None]
        best_ask_size = sum(sizes) if sizes else None
    return {
        "best_bid": best_bid,
        "best_ask": best_ask,
        "best_ask_size": best_ask_size,
        "spread": None if best_bid is None or best_ask is None else best_ask - best_bid,
        "tick_size": _float(data.get("tick_size") or data.get("min_tick_size")),
        "min_order_size": _float(data.get("min_order_size")),
        "latency_ms": latency_ms,
        "raw": data,
    }
