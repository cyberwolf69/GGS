from __future__ import annotations
import json, time, datetime as dt
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
rt=ROOT/'runtime'/'paper'; rt.mkdir(parents=True,exist_ok=True)
now=time.time(); ptb=81455.69
hist=[]
for i in range(90):
    t=now-89+i; p=ptb-10+i*.58+(3 if i>55 else 0)
    hist.append({"t":t,"p":p})
state={
 "status":"RUNNING","name":"GGS","full_name":"Ganteng-Ganteng Signature","mode":"PAPER",
 "market":{"slug":"btc-updown-5m-fixture","seconds_left":96,"resolution_window_s":60,"price_to_beat":ptb,"current_price":81500.21,"price_delta":44.52,"ptb_locked":True,"reference_ready":True,"reference_age_ms":230,"reference_source":"Polymarket market rules · Chainlink BTC/USD TWAP 60s","rtds_connected":True,"up_bid":.61,"up_ask":.62,"down_bid":.37,"down_ask":.38,"book_latency_ms":48},
 "price_history":hist,
 "decision":{"decision":"BUY_UP","reason":"FUSION_CONFIRMED","reasons":["PROBABILITY_EDGE","MOMENTUM_ALIGNED","PAYOUT_ELIGIBLE","RISK_OK"],"side":"UP","entry_price":.62,"p_up":.78,"p_down":.22,"p_side":.78,"confidence_pct":78,"payout_multiple":1/.62,"momentum":{"score":78,"btc_delta":44.52,"skew_aligned":True},"edge":{"raw_edge":.16,"estimated_cost":.024,"uncertainty_buffer":.02,"net_edge":.116}},
 "position":{"status":"OPEN","slug":"btc-updown-5m-fixture","side":"UP","entry_price":.62,"stake_usd":6,"shares":9.6774,"potential_payout":9.6774,"potential_profit":3.6774,"payout_multiple":1/.62,"currently_winning":True},
 "metrics":{"starting_balance":60,"balance":76.32,"net_pnl":16.32,"peak_pnl":19.40,"peak_balance":79.40,"roi_pct":27.2,"closed_trades":18,"wins":14,"losses":4,"wr_pct":77.8,"avg_win":3.24,"avg_loss":-6,"expectancy":.9067,"profit_factor":1.89,"avg_payout_multiple":1.58,"current_drawdown_usd":3.08,"current_drawdown_pct":3.88,"max_drawdown_usd":8.52,"max_drawdown_pct":11.4,"open_exposure":6},
 "config_public":{"starting_balance":60,"stake_usd":6,"min_payout_multiple":1.5,"max_entry_price":.6666667,"min_net_edge":.04,"min_confidence_pct":65},"latency_ms":54,"updated_at":dt.datetime.now(dt.timezone.utc).isoformat().replace('+00:00','Z')}
(rt/'state.json').write_text(json.dumps(state,indent=2))
events=[
 {"ts":"2026-09-19T15:42:01Z","type":"PAPER_ENTRY","message":"UP @ 0.620 | $6.00 | payout 1.61x | edge +0.116"},
 {"ts":"2026-09-19T15:41:59Z","type":"SCAN","message":"FUSION_CONFIRMED"},
 {"ts":"2026-09-19T15:41:50Z","type":"SCAN","message":"PAYOUT_TOO_LOW"},
 {"ts":"2026-09-19T15:40:00Z","type":"WATCH","message":"new market btc-updown-5m-fixture"},
]
(rt/'events.jsonl').write_text('\n'.join(json.dumps(x) for x in events)+'\n')
tr=[]
for i,(side,entry,res,pnl) in enumerate([('UP',.64,'WIN',3.375),('DOWN',.65,'LOSS',-6),('UP',.61,'WIN',3.836),('DOWN',.66,'WIN',3.091)]):
 tr.append({"status":"RESOLVED","resolved_at":f"2026-09-19T15:{30+i*5:02d}:00Z","side":side,"entry_price":entry,"payout_multiple":1/entry,"result":res,"pnl":pnl,"decision_snapshot":{"confidence_pct":74+i,"edge":{"net_edge":.06+i*.01}}})
(rt/'trades.jsonl').write_text('\n'.join(json.dumps(x) for x in tr)+'\n')
print('FIXTURE_WRITTEN')
