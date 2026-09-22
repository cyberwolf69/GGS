from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

ROOT = Path(os.environ.get("GGS_ROOT", Path(__file__).resolve().parents[1]))
MODE = os.environ.get("GGS_MODE", "PAPER").strip().upper() or "PAPER"
GLOBAL_RUNTIME = ROOT / "runtime"
RUNTIME = GLOBAL_RUNTIME / MODE.lower()
STATE_FILE = RUNTIME / "state.json"
EVENTS_FILE = RUNTIME / "events.jsonl"
TRADES_FILE = RUNTIME / "trades.jsonl"
PENDING_FILE = RUNTIME / "pending_resolution.json"
CONTROL_FILE = GLOBAL_RUNTIME / "control.json"
SETTINGS_FILE = GLOBAL_RUNTIME / "settings.json"
WALLETS_FILE = GLOBAL_RUNTIME / "wallets.json"
TELEGRAM_SESSION_FILE = GLOBAL_RUNTIME / "telegram_session.json"
TELEGRAM_OFFSET_FILE = GLOBAL_RUNTIME / "telegram_offset.json"
LIVE_STATUS_FILE = GLOBAL_RUNTIME / "live_status.json"
LIVE_ORDERS_FILE = GLOBAL_RUNTIME / "live_orders.jsonl"

DEFAULT_SETTINGS: dict[str, Any] = {
    "mode": "PAPER",
    "paper": {"starting_balance": 60.0},
    "execution": {"stake_usd": 6.0, "max_positions_per_market": 1},
    "fusion": {"min_payout_multiple": 1.50, "max_payout_multiple": 1.80, "min_net_edge": 0.04, "min_confidence_pct": 68.0},
    "market": {"max_spread": 0.04},
}


def ensure_runtime() -> None:
    GLOBAL_RUNTIME.mkdir(parents=True, exist_ok=True)
    RUNTIME.mkdir(parents=True, exist_ok=True)


def append_jsonl(path: Path, obj: dict[str, Any]) -> None:
    ensure_runtime()
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, separators=(",", ":"), ensure_ascii=False) + "\n")


def load_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def save_json(path: Path, value: Any) -> None:
    ensure_runtime()
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    out: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            row = json.loads(line)
            if isinstance(row, dict):
                out.append(row)
        except Exception:
            pass
    return out


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = dict(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(result.get(k), dict):
            result[k] = _deep_merge(result[k], v)
        else:
            result[k] = v
    return result


def get_control() -> dict[str, Any]:
    value = load_json(CONTROL_FILE, {"paused": False})
    return value if isinstance(value, dict) else {"paused": False}


def set_paused(paused: bool) -> dict[str, Any]:
    control = get_control()
    control["paused"] = bool(paused)
    save_json(CONTROL_FILE, control)
    return control


def get_settings() -> dict[str, Any]:
    value = load_json(SETTINGS_FILE, {})
    if not isinstance(value, dict):
        value = {}
    return _deep_merge(DEFAULT_SETTINGS, value)


def update_settings(patch: dict[str, Any]) -> dict[str, Any]:
    settings = _deep_merge(get_settings(), patch)
    save_json(SETTINGS_FILE, settings)
    return settings


def reset_settings() -> dict[str, Any]:
    save_json(SETTINGS_FILE, DEFAULT_SETTINGS)
    return get_settings()


def get_wallets() -> dict[str, Any]:
    value = load_json(WALLETS_FILE, {"watch": [], "active": None})
    return value if isinstance(value, dict) else {"watch": [], "active": None}


def add_watch_wallet(address: str) -> dict[str, Any]:
    wallets = get_wallets()
    items = list(wallets.get("watch") or [])
    if address not in items:
        items.append(address)
    wallets["watch"] = items
    wallets["active"] = address
    save_json(WALLETS_FILE, wallets)
    return wallets
