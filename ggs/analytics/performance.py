from __future__ import annotations
from typing import Any


def compute_metrics(trades: list[dict[str, Any]], starting_balance: float) -> dict[str, Any]:
    closed = [t for t in trades if t.get("status") == "RESOLVED"]
    pnls = [float(t.get("pnl", 0.0)) for t in closed]
    wins = [x for x in pnls if x > 0]
    losses = [x for x in pnls if x < 0]
    net = sum(pnls)
    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))
    balance = float(starting_balance)
    peak_balance = balance
    max_drawdown_usd = 0.0
    max_drawdown_pct = 0.0
    for pnl in pnls:
        balance += pnl
        peak_balance = max(peak_balance, balance)
        dd = peak_balance - balance
        max_drawdown_usd = max(max_drawdown_usd, dd)
        if peak_balance > 0:
            max_drawdown_pct = max(max_drawdown_pct, dd / peak_balance * 100.0)
    current_drawdown_usd = peak_balance - balance
    current_drawdown_pct = (current_drawdown_usd / peak_balance * 100.0) if peak_balance > 0 else 0.0
    payouts = [float(t.get("payout_multiple", 0.0)) for t in closed if t.get("payout_multiple")]
    return {
        "starting_balance": starting_balance,
        "balance": starting_balance + net,
        "net_pnl": net,
        "peak_pnl": peak_balance - starting_balance,
        "peak_balance": peak_balance,
        "roi_pct": (net / starting_balance * 100.0) if starting_balance else 0.0,
        "closed_trades": len(closed),
        "wins": len(wins),
        "losses": len(losses),
        "wr_pct": (len(wins) / len(closed) * 100.0) if closed else None,
        "avg_win": (sum(wins) / len(wins)) if wins else None,
        "avg_loss": (sum(losses) / len(losses)) if losses else None,
        "expectancy": (net / len(closed)) if closed else None,
        "profit_factor": (gross_profit / gross_loss) if gross_loss > 0 else None,
        "avg_payout_multiple": (sum(payouts) / len(payouts)) if payouts else None,
        "current_drawdown_usd": current_drawdown_usd,
        "current_drawdown_pct": current_drawdown_pct,
        "max_drawdown_usd": max_drawdown_usd,
        "max_drawdown_pct": max_drawdown_pct,
    }
