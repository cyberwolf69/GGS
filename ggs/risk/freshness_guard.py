from __future__ import annotations


def evaluate(*, data_age_ms: float | None, latency_ms: float | None, max_data_age_ms: float, max_latency_ms: float) -> tuple[bool, str]:
    if data_age_ms is None:
        return False, "REFERENCE_FEED_MISSING"
    if data_age_ms > max_data_age_ms:
        return False, "REFERENCE_FEED_STALE"
    if latency_ms is None:
        return False, "CLOB_LATENCY_MISSING"
    if latency_ms > max_latency_ms:
        return False, "LATENCY_TOO_HIGH"
    return True, "OK"
