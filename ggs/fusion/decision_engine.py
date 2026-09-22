from __future__ import annotations
from typing import Any

from .edge_engine import compute_edge
from .momentum_engine import score_momentum
from .payout_filter import evaluate as payout_evaluate
from .probability_engine import probability_snapshot
from ..risk.freshness_guard import evaluate as freshness_evaluate


def decide(*, current_price: float | None, price_to_beat: float | None, seconds_left: float, price_history: list[dict[str, Any]], up_book: dict[str, Any], down_book: dict[str, Any], reference_age_ms: float | None, fusion_cfg: dict[str, Any], market_cfg: dict[str, Any], model_cfg: dict[str, Any], costs_cfg: dict[str, Any], now_ts: float) -> dict[str, Any]:
    base = {"decision": "NO_TRADE", "reasons": []}
    if current_price is None or price_to_beat is None:
        return {**base, "reason": "SOURCE_LOCK_NOT_READY", "reasons": ["SOURCE_LOCK_NOT_READY"]}
    if seconds_left < float(market_cfg.get("min_seconds_remaining", 20)) or seconds_left > float(market_cfg.get("max_seconds_remaining", 180)):
        return {**base, "reason": "OUTSIDE_ENTRY_WINDOW", "reasons": ["OUTSIDE_ENTRY_WINDOW"]}

    up_ask, down_ask = up_book.get("best_ask"), down_book.get("best_ask")
    up_bid, down_bid = up_book.get("best_bid"), down_book.get("best_bid")
    if up_ask is None or down_ask is None:
        return {**base, "reason": "CLOB_MISSING", "reasons": ["CLOB_MISSING"]}

    probs = probability_snapshot(current_price, price_to_beat, seconds_left, price_history, model_cfg)
    side = "UP" if probs["p_up"] >= 0.5 else "DOWN"
    p_side = probs["p_up"] if side == "UP" else probs["p_down"]
    book = up_book if side == "UP" else down_book
    entry = float(book["best_ask"])
    bid = book.get("best_bid")
    spread = None if bid is None else entry - float(bid)
    liquidity = book.get("best_ask_size")
    latency_ms = max(float(up_book.get("latency_ms") or 0.0), float(down_book.get("latency_ms") or 0.0))

    out = {
        **base,
        "side": side,
        "entry_price": entry,
        "p_up": probs["p_up"],
        "p_down": probs["p_down"],
        "p_side": p_side,
        "confidence_pct": p_side * 100.0,
        "sigma": probs["sigma"],
        "spread": spread,
        "liquidity_shares": liquidity,
        "latency_ms": latency_ms,
    }

    fresh_ok, fresh_reason = freshness_evaluate(
        data_age_ms=reference_age_ms,
        latency_ms=latency_ms,
        max_data_age_ms=float(market_cfg.get("max_data_age_ms", 1500)),
        max_latency_ms=float(market_cfg.get("max_latency_ms", 400)),
    )
    if not fresh_ok:
        out.update({"reason": fresh_reason, "reasons": [fresh_reason]})
        return out
    if spread is None or spread > float(market_cfg.get("max_spread", 0.04)):
        out.update({"reason": "SPREAD_TOO_WIDE", "reasons": ["SPREAD_TOO_WIDE"]})
        return out
    if liquidity is not None and float(liquidity) < float(market_cfg.get("min_liquidity_shares", 5.0)):
        out.update({"reason": "LIQUIDITY_TOO_LOW", "reasons": ["LIQUIDITY_TOO_LOW"]})
        return out

    momentum = score_momentum(
        side=side,
        current_price=current_price,
        price_to_beat=price_to_beat,
        seconds_left=seconds_left,
        history=price_history,
        up_ask=up_ask,
        down_ask=down_ask,
        cfg=fusion_cfg,
        now_ts=now_ts,
    )
    out["momentum"] = momentum
    if momentum["score"] < float(fusion_cfg.get("min_momentum_score", 55.0)):
        out.update({"reason": "MOMENTUM_NOT_CONFIRMED", "reasons": ["MOMENTUM_NOT_CONFIRMED"]})
        return out

    edge = compute_edge(
        p_side=p_side,
        entry=entry,
        data_age_ms=float(reference_age_ms or 0.0),
        latency_ms=latency_ms,
        costs_cfg=costs_cfg,
        model_cfg=model_cfg,
        market_cfg=market_cfg,
    )
    out["edge"] = edge
    payout = payout_evaluate(
        entry,
        min_multiple=float(fusion_cfg.get("min_payout_multiple", 1.5)),
        max_multiple=float(fusion_cfg.get("max_payout_multiple", 1.8)),
        max_entry_price=float(fusion_cfg.get("max_entry_price", 2/3)),
        min_entry_price=float(fusion_cfg.get("min_entry_price", 1/1.8)),
        taker_fee_per_share=float(edge.get("taker_fee", 0.0)),
        slippage_per_share=float(edge.get("slippage", 0.0)),
    )
    out.update(
        payout_multiple=payout["payout_multiple"],
        gross_payout_multiple=payout["gross_payout_multiple"],
        effective_unit_cost=payout["effective_unit_cost"],
    )
    if not payout["ok"]:
        out.update({"reason": payout["reason"], "reasons": [payout["reason"]]})
        return out
    base_conf = float(fusion_cfg.get("min_confidence_pct", 68.0))
    adaptive = bool(fusion_cfg.get("adaptive_quality_gate", True))
    required_conf = base_conf
    if adaptive:
        multiple = float(payout["payout_multiple"])
        if multiple < 1.60:
            required_conf = max(required_conf, float(fusion_cfg.get("confidence_150_159", 73.0)))
        elif multiple < 1.70:
            required_conf = max(required_conf, float(fusion_cfg.get("confidence_160_169", 70.0)))
        else:
            required_conf = max(required_conf, float(fusion_cfg.get("confidence_170_180", 68.0)))
    out["required_confidence_pct"] = required_conf
    if p_side * 100.0 < required_conf:
        out.update({"reason": "CONFIDENCE_TOO_LOW", "reasons": ["CONFIDENCE_TOO_LOW"]})
        return out
    if edge["net_edge"] < float(fusion_cfg.get("min_net_edge", 0.04)):
        out.update({"reason": "EDGE_TOO_SMALL", "reasons": ["EDGE_TOO_SMALL"]})
        return out

    out.update({"decision": f"BUY_{side}", "reason": "FUSION_CONFIRMED", "reasons": ["PROBABILITY_EDGE", "MOMENTUM_ALIGNED", "PAYOUT_ELIGIBLE", "RISK_OK"]})
    return out
