# Architecture

```
polymarket-btc-5m-predictor/
├── SKILL.md
├── config.yaml
├── references/
├── scripts/
│   ├── market_discovery.py
│   ├── polymarket_client.py
│   ├── btc_market_data.py
│   ├── orderbook_engine.py
│   ├── feature_engine.py
│   ├── probability_model.py
│   ├── edge_engine.py
│   ├── signal_engine.py
│   ├── risk_engine.py
│   ├── execution_engine.py
│   ├── paper_trader.py
│   ├── performance_memory.py
│   ├── backtester.py
│   └── logger.py
└── tests/
```

Layers

1. DATA — discovery, Gamma, CLOB, RTDS, venue tapes
2. FEATURES — causal features only
3. MODEL — P(UP)
4. EDGE — raw, cost, buffer, net
5. DECISION — UP / DOWN / NO_TRADE
6. RISK — caps, fail-closed
7. EXECUTION — paper first
8. MEMORY — descriptive buckets, no override
9. MONITORING — logs, latency, gaps

MVP loop

```
while true:
  market = discover_active()
  if not market.ok: record NO_TRADE; continue
  data = ingest()
  if data.stale: record NO_TRADE; continue
  feats = features(data)
  p = model(feats, market)
  edge = edge_engine(p, book, fees)
  risk = risk_engine(edge, portfolio)
  signal = signal_engine(edge, risk)
  paper_trader.apply(signal)
  on_resolve(score)
```
