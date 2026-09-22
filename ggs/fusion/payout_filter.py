from __future__ import annotations


def evaluate(
    entry_price: float,
    *,
    min_multiple: float,
    max_multiple: float,
    max_entry_price: float,
    min_entry_price: float,
    taker_fee_per_share: float = 0.0,
    slippage_per_share: float = 0.0,
) -> dict:
    entry = float(entry_price)
    gross_multiple = 1.0 / entry if entry > 0 else 0.0
    effective_unit_cost = entry + max(0.0, float(taker_fee_per_share)) + max(0.0, float(slippage_per_share))
    net_multiple = 1.0 / effective_unit_cost if effective_unit_cost > 0 else 0.0
    if entry > float(max_entry_price) or net_multiple < float(min_multiple):
        reason = "PAYOUT_TOO_LOW"
        ok = False
    elif entry < float(min_entry_price) or net_multiple > float(max_multiple):
        reason = "PAYOUT_TOO_HIGH"
        ok = False
    else:
        reason = "OK"
        ok = True
    return {
        "ok": ok,
        "gross_payout_multiple": gross_multiple,
        "payout_multiple": net_multiple,
        "effective_unit_cost": effective_unit_cost,
        "reason": reason,
    }
