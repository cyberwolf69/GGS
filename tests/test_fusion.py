from __future__ import annotations

import math
import time

from ggs.analytics.performance import compute_metrics
from ggs.fusion.decision_engine import decide
from ggs.paper.accounting import open_position, resolve_position

FUSION = {
    "min_payout_multiple": 1.50,
    "max_entry_price": 2/3,
    "min_net_edge": 0.04,
    "min_confidence_pct": 65,
    "min_momentum_score": 55,
    "repo_btc_move_usd_reference": 70,
    "repo_entry_target_seconds_left": 120,
    "repo_entry_tolerance_seconds": 90,
}
MARKET = {"max_spread": 0.04, "max_data_age_ms": 1500, "max_latency_ms": 400, "min_seconds_remaining": 20, "max_seconds_remaining": 180, "min_liquidity_shares": 5}
MODEL = {"vol_shrinkage": 0.5, "min_sigma_bps_per_sqrt_sec": 0.4, "max_sigma_bps_per_sqrt_sec": 8.0, "min_uncertainty_buffer": 0.02, "calibration_error_prior": 0.02}
COSTS = {"taker_fee_rate": 0.07, "slippage_bps_buffer": 20, "latency_edge_buffer_max": 0.01}


def hist_up(now: float, base=10000.0):
    return [{"t": now - (20-i), "p": base + i*2.0} for i in range(21)]


def hist_down(now: float, base=10050.0):
    return [{"t": now - (20-i), "p": base - i*2.0} for i in range(21)]


def book(bid, ask, latency=50, size=100):
    return {"best_bid": bid, "best_ask": ask, "best_ask_size": size, "latency_ms": latency, "spread": ask-bid}


def test_buy_up():
    now=time.time(); h=hist_up(now)
    d=decide(current_price=10050,price_to_beat=10000,seconds_left=90,price_history=h,up_book=book(.61,.62),down_book=book(.37,.38),reference_age_ms=200,fusion_cfg=FUSION,market_cfg=MARKET,model_cfg=MODEL,costs_cfg=COSTS,now_ts=now)
    assert d["decision"]=="BUY_UP", d
    assert d["payout_multiple"]>=1.5
    assert d["confidence_pct"]>=65
    assert d["edge"]["net_edge"]>=.04


def test_buy_down():
    now=time.time(); h=hist_down(now)
    d=decide(current_price=9990,price_to_beat=10040,seconds_left=90,price_history=h,up_book=book(.37,.38),down_book=book(.61,.62),reference_age_ms=180,fusion_cfg=FUSION,market_cfg=MARKET,model_cfg=MODEL,costs_cfg=COSTS,now_ts=now)
    assert d["decision"]=="BUY_DOWN", d


def test_reject_payout():
    now=time.time(); h=hist_up(now)
    d=decide(current_price=10050,price_to_beat=10000,seconds_left=90,price_history=h,up_book=book(.69,.70),down_book=book(.29,.30),reference_age_ms=100,fusion_cfg=FUSION,market_cfg=MARKET,model_cfg=MODEL,costs_cfg=COSTS,now_ts=now)
    assert d["decision"]=="NO_TRADE" and d["reason"]=="PAYOUT_TOO_LOW", d


def test_reject_gross_1_5_but_net_below_after_costs():
    now=time.time(); h=hist_up(now)
    d=decide(current_price=10050,price_to_beat=10000,seconds_left=90,price_history=h,up_book=book(.65,.66),down_book=book(.33,.34),reference_age_ms=100,fusion_cfg=FUSION,market_cfg=MARKET,model_cfg=MODEL,costs_cfg=COSTS,now_ts=now)
    assert d["decision"]=="NO_TRADE" and d["reason"]=="PAYOUT_TOO_LOW", d
    assert d["gross_payout_multiple"] > 1.5 and d["payout_multiple"] < 1.5


def test_reject_stale():
    now=time.time(); h=hist_up(now)
    d=decide(current_price=10050,price_to_beat=10000,seconds_left=90,price_history=h,up_book=book(.61,.62),down_book=book(.37,.38),reference_age_ms=2000,fusion_cfg=FUSION,market_cfg=MARKET,model_cfg=MODEL,costs_cfg=COSTS,now_ts=now)
    assert d["reason"]=="REFERENCE_FEED_STALE", d


def test_reject_spread():
    now=time.time(); h=hist_up(now)
    d=decide(current_price=10050,price_to_beat=10000,seconds_left=90,price_history=h,up_book=book(.55,.62),down_book=book(.37,.38),reference_age_ms=100,fusion_cfg=FUSION,market_cfg=MARKET,model_cfg=MODEL,costs_cfg=COSTS,now_ts=now)
    assert d["reason"]=="SPREAD_TOO_WIDE", d


def test_accounting_and_metrics():
    p=open_position(slug="x",side="UP",token_id="1",entry_price=.60,stake_usd=6,market_start_ts=1,market_end_ts=301,price_to_beat=100,resolution_window_s=60,decision={"confidence_pct":75,"edge":{"net_edge":.08}},opened_at="x")
    assert math.isclose(p["potential_payout"],10.0)
    w=resolve_position(p,"UP","y")
    l=resolve_position({**p,"slug":"z"},"DOWN","y")
    assert math.isclose(w["pnl"],4.0) and math.isclose(l["pnl"],-6.0)
    m=compute_metrics([w,l],60)
    assert m["balance"]==58.0 and m["peak_balance"]==64.0 and m["max_drawdown_usd"]==6.0


def main():
    for fn in [test_buy_up,test_buy_down,test_reject_payout,test_reject_gross_1_5_but_net_below_after_costs,test_reject_stale,test_reject_spread,test_accounting_and_metrics]:
        fn(); print("PASS",fn.__name__)
    print("FUSION_TEST_PASS")

if __name__=="__main__": main()
