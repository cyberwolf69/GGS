from __future__ import annotations

import argparse
import json

from .client import LiveUnavailable, get_live_client


def main() -> None:
    ap = argparse.ArgumentParser(description="GGS MetaMask / Polymarket LIVE readiness check")
    ap.add_argument("--approve", action="store_true", help="submit missing trading approvals on Polygon")
    args = ap.parse_args()
    client = get_live_client()
    status = client.readiness(refresh=True)
    safe = {k: v for k, v in status.items() if k not in {"private_key"}}
    print(json.dumps(safe, indent=2))
    if not status.get("client_connected"):
        raise SystemExit(2)
    if status.get("wallet_matches_signer") is not True:
        raise SystemExit(3)
    if args.approve:
        try:
            print("[GGS] Submitting only missing Polymarket trading approvals...")
            approved = client.setup_trading_approvals()
            print(json.dumps(approved, indent=2))
        except LiveUnavailable as exc:
            raise SystemExit(str(exc)) from exc


if __name__ == "__main__":
    main()
