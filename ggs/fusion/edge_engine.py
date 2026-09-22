from __future__ import annotations
from typing import Any


def compute_edge(*, p_side: float, entry: float, data_age_ms: float, latency_ms: float, costs_cfg: dict[str, Any], model_cfg: dict[str, Any], market_cfg: dict[str, Any]) -> dict[str, float]:
    raw_edge = float(p_side) - float(entry)
    fee_rate = float(costs_cfg.get("taker_fee_rate", 0.07))
    taker_fee = fee_rate * entry * (1.0 - entry)
    slippage = float(costs_cfg.get("slippage_bps_buffer", 20.0)) / 10000.0
    max_data_age = max(1.0, float(market_cfg.get("max_data_age_ms", 1500)))
    max_latency = max(1.0, float(market_cfg.get("max_latency_ms", 400)))
    max_latency_buf = float(costs_cfg.get("latency_edge_buffer_max", 0.01))
    pressure = min(1.0, max(0.0, max(data_age_ms / max_data_age, latency_ms / max_latency)))
    latency_cost = max_latency_buf * pressure
    uncertainty = max(
        float(model_cfg.get("min_uncertainty_buffer", 0.02)),
        float(model_cfg.get("calibration_error_prior", 0.02)),
    )
    estimated_cost = taker_fee + slippage + latency_cost
    net_edge = raw_edge - estimated_cost - uncertainty
    return {
        "raw_edge": raw_edge,
        "taker_fee": taker_fee,
        "slippage": slippage,
        "latency_cost": latency_cost,
        "estimated_cost": estimated_cost,
        "uncertainty_buffer": uncertainty,
        "net_edge": net_edge,
    }
