from __future__ import annotations
from typing import Any, Optional


def _change(history: list[dict[str, Any]], current: float, now_ts: float, seconds: float) -> Optional[float]:
    target = now_ts - seconds
    older = [x for x in history if float(x.get("t", 0.0)) <= target]
    if not older:
        return None
    ref = max(older, key=lambda x: float(x.get("t", 0.0)))
    return current - float(ref["p"])


def score_momentum(*, side: str, current_price: float, price_to_beat: float, seconds_left: float, history: list[dict[str, Any]], up_ask: float | None, down_ask: float | None, cfg: dict[str, Any], now_ts: float) -> dict[str, Any]:
    sign = 1.0 if side == "UP" else -1.0
    delta = current_price - price_to_beat
    d_dir = delta * sign
    stronger = None
    if up_ask is not None and down_ask is not None:
        stronger = "UP" if up_ask >= down_ask else "DOWN"
    skew_aligned = stronger == side

    move_ref = max(1.0, float(cfg.get("repo_btc_move_usd_reference", 70.0)))
    impulse_progress = min(1.0, max(0.0, d_dir / move_ref))
    target = float(cfg.get("repo_entry_target_seconds_left", 120.0))
    tol = max(1.0, float(cfg.get("repo_entry_tolerance_seconds", 90.0)))
    time_alignment = max(0.0, 1.0 - abs(seconds_left - target) / tol)

    m5 = _change(history, current_price, now_ts, 5.0)
    m15 = _change(history, current_price, now_ts, 15.0)
    short_aligned = ((m5 is not None and m5 * sign > 0) or (m15 is not None and m15 * sign > 0))
    direction_aligned = d_dir >= 0

    score = 0.0
    score += 30.0 if direction_aligned else 0.0
    score += 25.0 if skew_aligned else 0.0
    score += 20.0 if short_aligned else 0.0
    score += 15.0 * impulse_progress
    score += 10.0 * time_alignment

    return {
        "score": round(score, 2),
        "direction_aligned": direction_aligned,
        "skew_aligned": skew_aligned,
        "short_momentum_aligned": short_aligned,
        "stronger_side": stronger,
        "btc_delta": delta,
        "momentum_5s": m5,
        "momentum_15s": m15,
        "impulse_progress": impulse_progress,
        "time_alignment": time_alignment,
    }
