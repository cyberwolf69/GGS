from __future__ import annotations

import argparse
import datetime as dt
import os
import time
from pathlib import Path
from typing import Any

import yaml

from .analytics.performance import compute_metrics
from .fusion.decision_engine import decide
from .market.discovery import discover_active_market
from .market.polymarket_clob import fetch_book
from .market.reference_price import TwapStream
from .market.source_lock import lock_price_to_beat
from .paper.executor import execute_paper
from .live.executor import LiveUnavailable, execute_live, execute_shadow
from .live.client import get_live_client
from .paper.resolver import reconcile
from .risk.risk_engine import can_open
from .state import EVENTS_FILE, PENDING_FILE, STATE_FILE, TRADES_FILE, LIVE_STATUS_FILE, LIVE_ORDERS_FILE, append_jsonl, get_control, get_settings, load_json, load_jsonl, save_json

UTC = dt.timezone.utc
ROOT = Path(os.environ.get("GGS_ROOT", Path(__file__).resolve().parents[1]))
MODE = os.environ.get("GGS_MODE", "PAPER").strip().upper() or "PAPER"
CONFIG_FILE = ROOT / "config" / ("paper.yaml" if MODE == "PAPER" else "live.yaml")


def iso_now() -> str:
    return dt.datetime.now(UTC).isoformat().replace("+00:00", "Z")


def load_config() -> dict[str, Any]:
    return yaml.safe_load(CONFIG_FILE.read_text(encoding="utf-8"))


def event(event_type: str, message: str, **extra: Any) -> None:
    append_jsonl(EVENTS_FILE, {"ts": iso_now(), "type": event_type, "message": message, **extra})


def _balance(cfg: dict[str, Any]) -> float:
    return float(cfg["account"]["starting_balance"]) + sum(float(x.get("pnl", 0.0)) for x in load_jsonl(TRADES_FILE) if x.get("status") == "RESOLVED")


def _position_from_state() -> dict[str, Any] | None:
    old = load_json(STATE_FILE, {})
    p = old.get("position") if isinstance(old, dict) else None
    return dict(p) if isinstance(p, dict) and p.get("status") == "OPEN" else None


def _pending_from_disk() -> list[dict[str, Any]]:
    x = load_json(PENDING_FILE, [])
    return [dict(v) for v in x if isinstance(v, dict)] if isinstance(x, list) else []


def _compact_decision(d: dict[str, Any]) -> dict[str, Any]:
    # State is public/local dashboard data; keep raw book payloads out.
    return {k: v for k, v in d.items() if k not in {"raw"}}


def run(poll_sec: float = 0.75) -> None:
    cfg = load_config()
    endpoints = cfg["endpoints"]
    stream = TwapStream(str(endpoints["rtds"]))
    position = _position_from_state()
    pending = _pending_from_disk()
    seen = {str(t.get("slug")) for t in load_jsonl(TRADES_FILE) if t.get("slug")}
    if position and position.get("slug"):
        seen.add(str(position["slug"]))
    for p in pending:
        if p.get("slug"):
            seen.add(str(p["slug"]))

    event("BOOT", "GGS PAPER engine started · probability × momentum × edge")
    last_market_slug = None
    last_scan_reason = None

    while True:
        loop_started = time.perf_counter()
        now = time.time()
        state: dict[str, Any] = load_json(STATE_FILE, {})
        try:
            # Telegram/runtime overrides are reloaded every loop so settings apply to the next entry.
            runtime_settings = get_settings()
            cfg["account"]["starting_balance"] = float((runtime_settings.get("paper") or {}).get("starting_balance", cfg["account"]["starting_balance"]))
            cfg["account"]["stake_usd"] = float((runtime_settings.get("execution") or {}).get("stake_usd", cfg["account"]["stake_usd"]))
            cfg["account"]["max_positions_per_market"] = int((runtime_settings.get("execution") or {}).get("max_positions_per_market", cfg["account"].get("max_positions_per_market", 1)))
            cfg["fusion"]["min_payout_multiple"] = float((runtime_settings.get("fusion") or {}).get("min_payout_multiple", cfg["fusion"]["min_payout_multiple"]))
            cfg["fusion"]["max_payout_multiple"] = float((runtime_settings.get("fusion") or {}).get("max_payout_multiple", cfg["fusion"].get("max_payout_multiple", 1.80)))
            cfg["fusion"]["min_net_edge"] = float((runtime_settings.get("fusion") or {}).get("min_net_edge", cfg["fusion"]["min_net_edge"]))
            cfg["fusion"]["min_confidence_pct"] = float((runtime_settings.get("fusion") or {}).get("min_confidence_pct", cfg["fusion"]["min_confidence_pct"]))
            cfg["market"]["max_spread"] = float((runtime_settings.get("market") or {}).get("max_spread", cfg["market"]["max_spread"]))
            # Never let an expired unresolved position block the next market.
            if position is not None and now >= float(position["market_end_ts"]):
                resolved = reconcile(position, stream, str(endpoints["gamma"]), iso_now())
                if resolved is not None:
                    append_jsonl(TRADES_FILE, resolved)
                    event("RESOLVE_WIN" if resolved["result"] == "WIN" else "RESOLVE_LOSS",
                          f"{resolved['side']} {resolved['result']} | PnL {resolved['pnl']:+.2f} | {resolved['resolution_method']}",
                          slug=resolved.get("slug"), pnl=resolved.get("pnl"))
                else:
                    queued = dict(position)
                    queued["pending_since"] = iso_now()
                    if not any(str(x.get("slug")) == str(queued.get("slug")) for x in pending):
                        pending.append(queued)
                        event("PENDING_RESOLUTION", "Expired market moved to pending; active slot released", slug=queued.get("slug"))
                position = None
                save_json(PENDING_FILE, pending)

            if pending:
                remaining = []
                for p in pending:
                    resolved = reconcile(p, stream, str(endpoints["gamma"]), iso_now())
                    if resolved is None:
                        remaining.append(p)
                        continue
                    append_jsonl(TRADES_FILE, resolved)
                    event("RESOLVE_WIN" if resolved["result"] == "WIN" else "RESOLVE_LOSS",
                          f"pending {resolved['side']} {resolved['result']} | PnL {resolved['pnl']:+.2f} | {resolved['resolution_method']}",
                          slug=resolved.get("slug"), pnl=resolved.get("pnl"))
                pending = remaining
                save_json(PENDING_FILE, pending)

            market = discover_active_market(str(endpoints["gamma"]))
            if market is None:
                state.update({"status": "WAIT_MARKET", "updated_at": iso_now(), "position": position, "pending_resolutions": pending})
                save_json(STATE_FILE, state)
                time.sleep(poll_sec)
                continue

            slug = str(market["_slug"])
            if slug != last_market_slug:
                event("WATCH", f"new market {slug}", slug=slug)
                last_market_slug = slug

            window_s = int(market["_resolution_window_s"])
            feed = stream.snapshot(window_s)
            boundary = lock_price_to_beat(stream, market, tolerance_sec=3.0)
            ptb = float(boundary["price"]) if boundary else None
            current_price = float(feed["current"]) if feed.get("current") is not None else None
            age_ms = float(feed["age_ms"]) if feed.get("age_ms") is not None else None
            reference_ready = bool(feed.get("connected")) and ptb is not None and current_price is not None
            seconds_left = max(0.0, float(market["_end_ts"]) - time.time())
            history = stream.history(window_s, seconds=330.0)

            up_book: dict[str, Any] = {}
            down_book: dict[str, Any] = {}
            book_error = None
            try:
                up_book = fetch_book(str(endpoints["clob"]), str(market["_up_token"]))
                down_book = fetch_book(str(endpoints["clob"]), str(market["_down_token"]))
            except Exception as exc:
                book_error = f"{type(exc).__name__}: {exc}"

            decision: dict[str, Any]
            if not reference_ready:
                decision = {"decision": "NO_TRADE", "reason": "SOURCE_LOCK_NOT_READY", "reasons": ["SOURCE_LOCK_NOT_READY"]}
            elif book_error:
                decision = {"decision": "NO_TRADE", "reason": "CLOB_UNAVAILABLE", "reasons": ["CLOB_UNAVAILABLE"], "error": book_error}
            else:
                decision = decide(
                    current_price=current_price,
                    price_to_beat=ptb,
                    seconds_left=seconds_left,
                    price_history=history,
                    up_book=up_book,
                    down_book=down_book,
                    reference_age_ms=age_ms,
                    fusion_cfg=cfg["fusion"],
                    market_cfg=cfg["market"],
                    model_cfg=cfg["model"],
                    costs_cfg=cfg["costs"],
                    now_ts=time.time(),
                )

            metrics = compute_metrics(load_jsonl(TRADES_FILE), float(cfg["account"]["starting_balance"]))
            paused = bool(get_control().get("paused", False))
            risk_ok, risk_reason = can_open(
                balance=float(metrics["balance"]),
                stake=float(cfg["account"]["stake_usd"]),
                open_position=position,
                seen_market=slug in seen,
            )
            if decision.get("decision", "NO_TRADE") != "NO_TRADE" and paused:
                decision = {**decision, "decision": "NO_TRADE", "reason": "PAUSED_BY_OWNER", "reasons": ["PAUSED_BY_OWNER"]}
            elif decision.get("decision", "NO_TRADE") != "NO_TRADE" and not risk_ok:
                decision = {**decision, "decision": "NO_TRADE", "reason": risk_reason, "reasons": [risk_reason]}

            scan_reason = str(decision.get("reason") or "NO_REASON")
            if scan_reason != last_scan_reason:
                event("SCAN", scan_reason, slug=slug, decision=decision.get("decision"))
                last_scan_reason = scan_reason

            active_mode = str(runtime_settings.get("mode", "PAPER")).upper()
            if position is None and decision.get("decision") in {"BUY_UP", "BUY_DOWN"}:
                side = str(decision["side"])
                token = str(market["_up_token"] if side == "UP" else market["_down_token"])
                stake = float(cfg["account"]["stake_usd"])
                if active_mode == "PAPER":
                    position = execute_paper(
                        decision=decision, slug=slug, token_id=token, stake_usd=stake,
                        market_start_ts=int(market["_start_ts"]), market_end_ts=int(market["_end_ts"]),
                        price_to_beat=float(ptb), resolution_window_s=window_s, opened_at=iso_now(),
                    )
                    seen.add(slug)
                    event("PAPER_ENTRY", f"{side} @ {position['entry_price']:.3f} | ${position['stake_usd']:.2f} | payout {position['payout_multiple']:.2f}x", slug=slug, side=side)
                elif active_mode == "LIVE_SHADOW":
                    preview = execute_shadow(decision=decision, token_id=token, stake_usd=stake)
                    append_jsonl(LIVE_ORDERS_FILE, {"ts": iso_now(), "slug": slug, "side": side, **preview})
                    seen.add(slug)
                    event("LIVE_SHADOW", f"would BUY {side} @ max {preview['max_price']:.3f} | ${stake:.2f}", slug=slug, side=side)
                elif active_mode == "LIVE":
                    try:
                        result = execute_live(decision=decision, token_id=token, stake_usd=stake)
                        append_jsonl(LIVE_ORDERS_FILE, {"ts": iso_now(), "slug": slug, "side": side, **result})
                        seen.add(slug)
                        event("LIVE_ORDER" if result.get("ok") else "LIVE_REJECTED", f"{side} | {result}", slug=slug, side=side)
                    except LiveUnavailable as exc:
                        decision = {**decision, "decision": "NO_TRADE", "reason": "LIVE_NOT_READY", "reasons": [str(exc)]}
                elif active_mode == "LIVE_READONLY":
                    decision = {**decision, "decision": "NO_TRADE", "reason": "LIVE_READONLY", "reasons": ["LIVE_READONLY"]}

            metrics = compute_metrics(load_jsonl(TRADES_FILE), float(cfg["account"]["starting_balance"]))
            metrics["open_pnl"] = 0.0
            if position is not None:
                metrics["open_exposure"] = float(position["stake_usd"])
                mark_bid = up_book.get("best_bid") if position.get("side") == "UP" else down_book.get("best_bid")
                if mark_bid is not None:
                    metrics["open_pnl"] = float(position["shares"]) * float(mark_bid) - float(position["stake_usd"])
            else:
                metrics["open_exposure"] = 0.0

            market_state = {
                "slug": slug,
                "start_ts": int(market["_start_ts"]),
                "end_ts": int(market["_end_ts"]),
                "seconds_left": seconds_left,
                "resolution_window_s": window_s,
                "price_to_beat": ptb,
                "current_price": current_price,
                "price_delta": None if ptb is None or current_price is None else current_price - ptb,
                "ptb_locked": ptb is not None,
                "reference_ready": reference_ready,
                "reference_age_ms": age_ms,
                "reference_source": f"Polymarket market rules · Chainlink BTC/USD TWAP {window_s}s",
                "rtds_connected": bool(feed.get("connected")),
                "rtds_last_error": feed.get("last_error"),
                "up_bid": up_book.get("best_bid"), "up_ask": up_book.get("best_ask"),
                "down_bid": down_book.get("best_bid"), "down_ask": down_book.get("best_ask"),
                "up_spread": up_book.get("spread"), "down_spread": down_book.get("spread"),
                "book_latency_ms": max(float(up_book.get("latency_ms") or 0), float(down_book.get("latency_ms") or 0)) if up_book and down_book else None,
            }

            dashboard_position = None
            if position is not None:
                dashboard_position = dict(position)
                current_outcome = None if market_state["price_delta"] is None else ("UP" if market_state["price_delta"] >= 0 else "DOWN")
                dashboard_position["currently_winning"] = current_outcome == position.get("side") if current_outcome else None

            live_status = {}
            if str(runtime_settings.get("mode", "PAPER")).upper().startswith("LIVE"):
                try:
                    live_status = get_live_client().readiness(refresh=False)
                except Exception as exc:
                    live_status = {"error": f"{type(exc).__name__}: {exc}"}
                save_json(LIVE_STATUS_FILE, live_status)

            state = {
                "status": "RUNNING",
                "name": "GGS",
                "full_name": "Ganteng-Ganteng Signature",
                "mode": str(runtime_settings.get("mode", MODE)).upper(),
                "paused": paused,
                "market": market_state,
                "price_history": history[-330:],
                "decision": _compact_decision(decision),
                "position": dashboard_position,
                "metrics": metrics,
                "pending_resolutions": pending,
                "live": live_status,
                "config_public": {
                    "starting_balance": cfg["account"]["starting_balance"],
                    "stake_usd": cfg["account"]["stake_usd"],
                    "min_payout_multiple": cfg["fusion"]["min_payout_multiple"],
                    "max_payout_multiple": cfg["fusion"].get("max_payout_multiple", 1.80),
                    "max_entry_price": cfg["fusion"]["max_entry_price"],
                    "min_net_edge": cfg["fusion"]["min_net_edge"],
                    "min_confidence_pct": cfg["fusion"]["min_confidence_pct"],
                },
                "latency_ms": round((time.perf_counter() - loop_started) * 1000.0, 1),
                "updated_at": iso_now(),
            }
            save_json(STATE_FILE, state)
        except Exception as exc:
            state.update({"status": "ERROR", "last_error": f"{type(exc).__name__}: {exc}", "updated_at": iso_now(), "position": position, "pending_resolutions": pending})
            save_json(STATE_FILE, state)
            event("ERROR", state["last_error"])
        time.sleep(max(0.25, poll_sec))


def main() -> None:
    ap = argparse.ArgumentParser(description="GGS paper engine")
    ap.add_argument("--poll-sec", type=float, default=0.75)
    args = ap.parse_args()
    run(args.poll_sec)


if __name__ == "__main__":
    main()
