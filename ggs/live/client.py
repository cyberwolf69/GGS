from __future__ import annotations

import os
import time
from dataclasses import asdict, dataclass
from decimal import Decimal
from typing import Any


class LiveUnavailable(RuntimeError):
    pass


@dataclass
class LiveReadiness:
    sdk_available: bool = False
    private_key_present: bool = False
    wallet_present: bool = False
    wallet_matches_signer: bool | None = None
    client_connected: bool = False
    wallet: str | None = None
    signer: str | None = None
    wallet_type: str | None = None
    balance_usd: float | None = None
    allowance_ready: bool | None = None
    live_enabled: bool = False
    withdrawals_enabled: bool = False
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class LiveClient:
    """Lazy wrapper around Polymarket's official unified Python SDK.

    Secrets are read only from process environment. They are never written to
    runtime JSON or returned by public status methods.
    """

    def __init__(self) -> None:
        self._client: Any | None = None
        self._last_status_at = 0.0
        self._readiness = LiveReadiness(
            private_key_present=bool(os.getenv("POLYMARKET_PRIVATE_KEY", "").strip()),
            wallet_present=bool(os.getenv("POLYMARKET_WALLET_ADDRESS", "").strip()),
            live_enabled=os.getenv("GGS_LIVE_ENABLED", "false").lower() == "true",
            withdrawals_enabled=os.getenv("GGS_LIVE_WITHDRAWALS_ENABLED", "false").lower() == "true",
        )

    @property
    def live_enabled(self) -> bool:
        return self._readiness.live_enabled

    def _imports(self):
        try:
            from eth_account import Account
            from polymarket import SecureClient
        except Exception as exc:  # pragma: no cover - exercised on machines without live deps
            raise LiveUnavailable(
                "LIVE dependencies unavailable. Run: pip install -r requirements.txt"
            ) from exc
        return Account, SecureClient

    def connect(self) -> LiveReadiness:
        private_key = os.getenv("POLYMARKET_PRIVATE_KEY", "").strip()
        wallet = os.getenv("POLYMARKET_WALLET_ADDRESS", "").strip()
        r = self._readiness
        if not private_key:
            r.error = "POLYMARKET_PRIVATE_KEY_MISSING"
            return r
        if not wallet:
            r.error = "POLYMARKET_WALLET_ADDRESS_MISSING"
            return r
        try:
            Account, SecureClient = self._imports()
            r.sdk_available = True
            signer = Account.from_key(private_key).address
            r.signer = signer
            r.wallet = wallet
            r.wallet_matches_signer = signer.lower() == wallet.lower()
            if not r.wallet_matches_signer:
                r.error = "METAMASK_WALLET_DOES_NOT_MATCH_PRIVATE_KEY"
                return r
            if self._client is None:
                self._client = SecureClient.create(private_key=private_key, wallet=wallet)
            r.client_connected = True
            r.wallet_type = str(getattr(self._client, "wallet_type", "EOA"))
            bal = self._client.get_balance_allowance(asset_type="COLLATERAL")
            r.balance_usd = float(Decimal(int(bal.balance)) / Decimal(1_000_000))
            r.allowance_ready = bool(bal.allowances) and all(int(v) > 0 for v in bal.allowances.values())
            r.error = None
            self._last_status_at = time.time()
        except Exception as exc:
            r.client_connected = False
            r.error = f"{type(exc).__name__}: {exc}"
        return r

    def readiness(self, refresh: bool = False) -> dict[str, Any]:
        if refresh or not self._readiness.client_connected or time.time() - self._last_status_at >= 5.0:
            self.connect()
        return self._readiness.to_dict()

    def setup_trading_approvals(self) -> dict[str, Any]:
        if self._client is None:
            self.connect()
        if self._client is None:
            raise LiveUnavailable(self._readiness.error or "LIVE client unavailable")
        handle = self._client.setup_trading_approvals()
        try:
            handle.wait()
        except Exception:
            pass
        return self.readiness(refresh=True)

    def preview_buy(self, *, token_id: str, stake_usd: float, max_price: float) -> dict[str, Any]:
        return {
            "mode": "SHADOW",
            "token_id": str(token_id),
            "side": "BUY",
            "stake_usd": float(stake_usd),
            "max_price": float(max_price),
            "order_type": "FAK",
            "submitted": False,
        }

    def place_buy(self, *, token_id: str, stake_usd: float, max_price: float) -> dict[str, Any]:
        if not self.live_enabled:
            raise LiveUnavailable("GGS_LIVE_ENABLED is false")
        if self._client is None:
            self.connect()
        if self._client is None or not self._readiness.client_connected:
            raise LiveUnavailable(self._readiness.error or "LIVE client unavailable")
        if self._readiness.wallet_matches_signer is not True:
            raise LiveUnavailable("Signer/wallet mismatch")
        response = self._client.place_market_order(
            token_id=str(token_id),
            side="BUY",
            amount=Decimal(str(stake_usd)),
            max_spend=Decimal(str(stake_usd)),
            max_price=Decimal(str(max_price)),
            order_type="FAK",
        )
        ok = bool(getattr(response, "ok", False))
        if not ok:
            return {
                "ok": False,
                "code": str(getattr(response, "code", "unknown")),
                "message": str(getattr(response, "message", "order rejected")),
            }
        spend = float(getattr(response, "making_amount", 0) or 0)
        shares = float(getattr(response, "taking_amount", 0) or 0)
        return {
            "ok": True,
            "order_id": str(getattr(response, "order_id", "")),
            "status": str(getattr(response, "status", "accepted")),
            "spend_usd": spend,
            "shares": shares,
            "avg_entry": (spend / shares) if shares > 0 else None,
            "trade_ids": [str(x) for x in getattr(response, "trade_ids", ())],
            "tx_hashes": [str(x) for x in getattr(response, "transactions_hashes", ())],
        }

    def withdraw_collateral(self, *, recipient: str, amount_usd: float) -> dict[str, Any]:
        if not self._readiness.withdrawals_enabled:
            raise LiveUnavailable("GGS_LIVE_WITHDRAWALS_ENABLED is false")
        if self._client is None:
            self.connect()
        if self._client is None or not self._readiness.client_connected:
            raise LiveUnavailable(self._readiness.error or "LIVE client unavailable")
        if amount_usd <= 0:
            raise LiveUnavailable("Withdrawal amount must be positive")
        status = self.readiness(refresh=True)
        bal = float(status.get("balance_usd") or 0.0)
        if amount_usd > bal:
            raise LiveUnavailable(f"Insufficient collateral balance: ${bal:.2f}")
        token = os.getenv("POLYMARKET_COLLATERAL_TOKEN", "0xC011a7E12a19f7B1f670d46F03B03f3342E82DFB").strip()
        amount_base = int(round(float(amount_usd) * 1_000_000))
        handle = self._client.transfer_erc20(
            token_address=token, recipient_address=recipient, amount=amount_base,
            metadata=f"GGS withdrawal {amount_usd:.6f} pUSD",
        )
        receipt = handle.wait()
        return {
            "ok": True, "amount_usd": float(amount_usd), "recipient": recipient,
            "result": str(receipt),
        }


_GLOBAL_CLIENT: LiveClient | None = None


def get_live_client() -> LiveClient:
    global _GLOBAL_CLIENT
    if _GLOBAL_CLIENT is None:
        _GLOBAL_CLIENT = LiveClient()
    return _GLOBAL_CLIENT
