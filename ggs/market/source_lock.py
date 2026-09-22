from __future__ import annotations
from typing import Any, Optional


def lock_price_to_beat(stream, market: dict[str, Any], tolerance_sec: float = 3.0) -> Optional[dict[str, Any]]:
    return stream.price_near(float(market["_start_ts"]), int(market["_resolution_window_s"]), tolerance_sec=tolerance_sec)
