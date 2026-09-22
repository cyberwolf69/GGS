from __future__ import annotations

import datetime as dt
import json
import time
from typing import Any, Optional

import certifi
import requests

UTC = dt.timezone.utc


def bucket_5m(ts: int) -> int:
    return ts - (ts % 300)


def _json_list(v: Any) -> list[Any]:
    if isinstance(v, list):
        return v
    if isinstance(v, str):
        try:
            x = json.loads(v)
            return x if isinstance(x, list) else []
        except Exception:
            return []
    return []


def _parse_end_ts(market: dict[str, Any], fallback_start: int) -> float:
    end_iso = str(market.get("endDate") or market.get("endDateIso") or "")
    try:
        return dt.datetime.fromisoformat(end_iso.replace("Z", "+00:00")).timestamp()
    except Exception:
        return float(fallback_start + 300)


def resolution_window_s(market: dict[str, Any]) -> int:
    cfg = market.get("cryptoMarketConfig") or {}
    if isinstance(cfg, str):
        try:
            cfg = json.loads(cfg)
        except Exception:
            cfg = {}
    if isinstance(cfg, dict):
        try:
            n = int(cfg.get("twapLookbackSeconds"))
            if n in (30, 60):
                return n
        except Exception:
            pass
    blob = " ".join(str(market.get(k) or "") for k in ("description", "rules", "resolutionSource", "resolution_source", "question")).lower()
    if "30-second twap" in blob or "twap-30s" in blob or "twap_thirty" in blob:
        return 30
    if "60-second twap" in blob or "twap-60s" in blob or "twap_sixty" in blob:
        return 60
    return 60


def discover_active_market(gamma_base: str, now_ts: Optional[int] = None, timeout: float = 6.0) -> Optional[dict[str, Any]]:
    now = int(now_ts or time.time())
    start = bucket_5m(now)
    slug = f"btc-updown-5m-{start}"
    r = requests.get(f"{gamma_base.rstrip('/')}/events", params={"slug": slug}, timeout=timeout, verify=certifi.where(), headers={"User-Agent": "GGS/1.0"})
    r.raise_for_status()
    arr = r.json()
    event = arr[0] if isinstance(arr, list) and arr else None
    if not event:
        return None
    markets = event.get("markets") or []
    if not markets:
        return None
    market = dict(markets[0])
    if market.get("closed") is True or market.get("active") is False:
        return None
    end_ts = _parse_end_ts(market, start)
    seconds_left = end_ts - time.time()
    if seconds_left <= 0:
        return None
    outcomes = [str(x).upper() for x in _json_list(market.get("outcomes"))]
    tokens = [str(x) for x in _json_list(market.get("clobTokenIds"))]
    if len(outcomes) != len(tokens) or not tokens:
        return None
    mapping = dict(zip(outcomes, tokens))
    if "UP" not in mapping or "DOWN" not in mapping:
        return None
    market.update({
        "_slug": slug,
        "_start_ts": start,
        "_end_ts": end_ts,
        "_seconds_left": seconds_left,
        "_up_token": mapping["UP"],
        "_down_token": mapping["DOWN"],
        "_resolution_window_s": resolution_window_s(market),
    })
    return market
