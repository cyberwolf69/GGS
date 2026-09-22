from __future__ import annotations

def drawdown(peak: float, current: float) -> tuple[float, float]:
    usd = max(0.0, float(peak) - float(current))
    pct = (usd / float(peak) * 100.0) if peak > 0 else 0.0
    return usd, pct
