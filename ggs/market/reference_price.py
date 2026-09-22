from __future__ import annotations

import json
import ssl
import threading
import time
from collections import deque
from typing import Any, Optional

import certifi
import websocket


def _f(v: Any) -> Optional[float]:
    try:
        if v is None:
            return None
        return float(v)
    except Exception:
        return None


def _normalize_btc_usd_price(value: Any, payload: Optional[dict[str, Any]] = None) -> Optional[float]:
    """Normalize Polymarket/Chainlink RTDS BTC/USD values to ordinary USD.

    Some RTDS TWAP frames expose ``full_accuracy_value`` as a fixed-point integer
    with 18 decimals (for example ~8.16e22 for ~$81.6k). Other frames already
    expose a normal decimal USD value. Prefer an explicit decimals/precision field
    when supplied; otherwise apply the observed 1e18 fixed-point scale only to
    obviously oversized BTC/USD values. Fail closed if the normalized result is
    outside a broad BTC/USD sanity range.
    """
    raw = _f(value)
    if raw is None or raw <= 0:
        return None

    payload = payload or {}
    decimals = None
    for key in ("decimals", "decimal", "precision", "scale"):
        v = payload.get(key)
        try:
            if v is not None:
                iv = int(v)
                if 0 <= iv <= 30:
                    decimals = iv
                    break
        except Exception:
            pass

    price = raw
    if decimals is not None and raw > 10_000_000:
        price = raw / (10 ** decimals)
    elif raw >= 1_000_000_000_000:
        # Chainlink Streams full-accuracy fixed-point representation observed by
        # Polymarket RTDS for BTC/USD.  Do not repeatedly divide heuristically.
        price = raw / 1e18

    # Broad sanity guard: catches unscaled fixed-point values and malformed frames
    # without hard-coding today's BTC price.
    if not (100.0 <= price <= 10_000_000.0):
        return None
    return float(price)


class TwapStream:
    def __init__(self, endpoint: str):
        self.endpoint = endpoint
        self._lock = threading.Lock()
        self._feeds: dict[int, dict[str, Any]] = {
            30: {"current": None, "source_ts": None, "recv_ts": None, "connected": False, "last_error": None, "ticks": deque(maxlen=1800)},
            60: {"current": None, "source_ts": None, "recv_ts": None, "connected": False, "last_error": None, "ticks": deque(maxlen=1800)},
        }
        for window, topic in ((30, "crypto_prices_twap_thirty"), (60, "crypto_prices_twap_sixty")):
            threading.Thread(target=self._loop, args=(window, topic), daemon=True, name=f"ggs-twap-{window}").start()

    def snapshot(self, window: int) -> dict[str, Any]:
        w = 30 if int(window) == 30 else 60
        with self._lock:
            f = self._feeds[w]
            age_ms = None if f["recv_ts"] is None else max(0.0, (time.time() - float(f["recv_ts"])) * 1000.0)
            return {"current": f["current"], "source_ts": f["source_ts"], "age_ms": age_ms, "connected": f["connected"], "last_error": f["last_error"], "window_s": w}

    def price_near(self, target_ts: float, window: int, tolerance_sec: float = 3.0) -> Optional[dict[str, Any]]:
        w = 30 if int(window) == 30 else 60
        with self._lock:
            ticks = list(self._feeds[w]["ticks"])
        if not ticks:
            return None
        best = min(ticks, key=lambda x: abs(float(x["source_ts"]) - float(target_ts)))
        offset = float(best["source_ts"]) - float(target_ts)
        if abs(offset) > tolerance_sec:
            return None
        return {"price": float(best["price"]), "source_ts": float(best["source_ts"]), "offset_sec": offset}

    def history(self, window: int, seconds: float = 330.0) -> list[dict[str, float]]:
        w = 30 if int(window) == 30 else 60
        cutoff = time.time() - seconds
        with self._lock:
            return [{"t": float(x["source_ts"]), "p": float(x["price"])} for x in self._feeds[w]["ticks"] if float(x["source_ts"]) >= cutoff]

    def _store(self, window: int, value: Any, source_ts: Any) -> None:
        price = _f(value)
        ts = _f(source_ts)
        if price is None or price <= 0:
            return
        if ts is None:
            ts = time.time()
        if ts > 10_000_000_000:
            ts /= 1000.0
        now = time.time()
        with self._lock:
            f = self._feeds[window]
            f["current"] = price
            f["source_ts"] = ts
            f["recv_ts"] = now
            f["connected"] = True
            f["last_error"] = None
            if not f["ticks"] or f["ticks"][-1]["source_ts"] != ts or f["ticks"][-1]["price"] != price:
                f["ticks"].append({"source_ts": ts, "price": price, "recv_ts": now})

    def _handle(self, msg: Any, window: int) -> None:
        if isinstance(msg, list):
            for x in msg:
                self._handle(x, window)
            return
        if not isinstance(msg, dict):
            return
        if msg.get("message") and not msg.get("payload"):
            with self._lock:
                self._feeds[window]["last_error"] = str(msg.get("message"))[:240]
            return
        payload = msg.get("payload", msg)
        if not isinstance(payload, dict):
            return
        symbol = str(payload.get("symbol") or "").lower()
        if symbol and symbol != "btc/usd":
            return
        value = payload.get("full_accuracy_value") or payload.get("value") or payload.get("price")
        price = _normalize_btc_usd_price(value, payload)
        ts = payload.get("timestamp") or payload.get("ts") or msg.get("timestamp")
        self._store(window, price, ts)

    def _loop(self, window: int, topic: str) -> None:
        def on_open(ws):
            # RTDS currently requires filters to be a compact JSON STRING for TWAP topics.
            frame = {"action": "subscribe", "subscriptions": [{"topic": topic, "type": "update", "filters": "{\"symbol\":\"btc/usd\"}"}]}
            ws.send(json.dumps(frame, separators=(",", ":")))
            with self._lock:
                self._feeds[window]["connected"] = True
                self._feeds[window]["last_error"] = None

        def on_message(_ws, message):
            try:
                self._handle(json.loads(message), window)
            except Exception as exc:
                with self._lock:
                    self._feeds[window]["last_error"] = f"parse:{type(exc).__name__}:{exc}"[:240]

        def on_error(_ws, error):
            with self._lock:
                self._feeds[window]["connected"] = False
                self._feeds[window]["last_error"] = str(error)[:240]

        def on_close(_ws, _code, _reason):
            with self._lock:
                self._feeds[window]["connected"] = False

        while True:
            try:
                ws = websocket.WebSocketApp(self.endpoint, on_open=on_open, on_message=on_message, on_error=on_error, on_close=on_close)
                ws.run_forever(ping_interval=20, ping_timeout=10, sslopt={"cert_reqs": ssl.CERT_REQUIRED, "ca_certs": certifi.where()})
            except Exception as exc:
                with self._lock:
                    self._feeds[window]["connected"] = False
                    self._feeds[window]["last_error"] = f"{type(exc).__name__}: {exc}"[:240]
            time.sleep(2)
