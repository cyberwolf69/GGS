from __future__ import annotations

import getpass
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ENV = ROOT / ".env"


def _load(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if path.exists():
        for line in path.read_text().splitlines():
            if not line or line.lstrip().startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1); out[k.strip()] = v.strip()
    return out


def _write(values: dict[str, str]) -> None:
    template = (ROOT / ".env.example").read_text() if (ROOT / ".env.example").exists() else ""
    keys = []
    for line in template.splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            keys.append(line.split("=",1)[0].strip())
    for k in values:
        if k not in keys: keys.append(k)
    lines = []
    comments = [x for x in template.splitlines() if x.lstrip().startswith("#")]
    lines.extend(comments[:2])
    for k in keys:
        lines.append(f"{k}={values.get(k,'')}")
    ENV.write_text("\n".join(lines)+"\n")
    try: os.chmod(ENV, 0o600)
    except Exception: pass


def main() -> None:
    vals = _load(ENV)
    wallet = input("MetaMask address (0x...): ").strip()
    if not re.fullmatch(r"0x[a-fA-F0-9]{40}", wallet):
        raise SystemExit("Invalid wallet address")
    pk = getpass.getpass("MetaMask private key (hidden, local only): ").strip()
    if not re.fullmatch(r"(?:0x)?[a-fA-F0-9]{64}", pk):
        raise SystemExit("Invalid private key format")
    if not pk.startswith("0x"): pk = "0x" + pk
    try:
        from eth_account import Account
        derived = Account.from_key(pk).address
        if derived.lower() != wallet.lower():
            raise SystemExit(f"Private key belongs to {derived}, not {wallet}")
    except ImportError:
        print("[GGS] eth-account unavailable; address/key match will be verified at runtime.")
    vals.update({
        "POLYMARKET_PRIVATE_KEY": pk,
        "POLYMARKET_WALLET_ADDRESS": wallet,
        "GGS_LIVE_ENABLED": "false",
        "GGS_LIVE_WITHDRAWALS_ENABLED": "false",
    })
    _write(vals)
    print("\n[GGS] Live wallet saved locally to .env (chmod 600).")
    print("[GGS] Start GGS, choose LIVE READ ONLY first, then LIVE SHADOW.")
    print("[GGS] Set GGS_LIVE_ENABLED=true only after read-only/shadow checks pass.")

if __name__ == "__main__": main()
