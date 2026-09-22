from __future__ import annotations

from math import erf, sqrt
from statistics import pstdev
from typing import Any


def _phi(x: float) -> float:
    return 0.5 * (1.0 + erf(x / sqrt(2.0)))


def estimate_sigma(price_history: list[dict[str, Any]], current_price: float, *, shrinkage: float, min_bps: float, max_bps: float) -> float:
    prices = [float(x["p"]) for x in price_history[-120:] if x.get("p") is not None]
    if len(prices) < 8:
        raw = current_price * (min_bps / 10000.0)
    else:
        diffs = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        raw = pstdev(diffs) if len(diffs) > 1 else 0.0
    min_sigma = current_price * (min_bps / 10000.0)
    max_sigma = current_price * (max_bps / 10000.0)
    shrunk = shrinkage * raw + (1.0 - shrinkage) * min_sigma
    return max(min_sigma, min(max_sigma, shrunk))


def p_up_diffusion(current_twap: float, price_to_beat: float, seconds_remaining: float, sigma: float) -> float:
    if sigma <= 0:
        return 1.0 if current_twap >= price_to_beat else 0.0
    tau = max(1.0, float(seconds_remaining))
    z = (float(current_twap) - float(price_to_beat)) / (float(sigma) * sqrt(tau))
    p = _phi(z)
    return min(max(p, 1e-6), 1.0 - 1e-6)


def probability_snapshot(current_twap: float, price_to_beat: float, seconds_remaining: float, history: list[dict[str, Any]], model_cfg: dict[str, Any]) -> dict[str, float]:
    sigma = estimate_sigma(
        history,
        current_twap,
        shrinkage=float(model_cfg.get("vol_shrinkage", 0.5)),
        min_bps=float(model_cfg.get("min_sigma_bps_per_sqrt_sec", 0.4)),
        max_bps=float(model_cfg.get("max_sigma_bps_per_sqrt_sec", 8.0)),
    )
    p_up = p_up_diffusion(current_twap, price_to_beat, seconds_remaining, sigma)
    return {"p_up": p_up, "p_down": 1.0 - p_up, "sigma": sigma}
