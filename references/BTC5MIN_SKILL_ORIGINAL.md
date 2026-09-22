---
name: polymarket-btc-5m-predictor
description: Analyze live Polymarket BTC 5-minute Up/Down markets, estimate P(UP) from Chainlink TWAP and microstructure, compare model probability to CLOB prices, and emit UP, DOWN, or NO_TRADE in paper-trading mode. Use when the user mentions Polymarket BTC 5m, bitcoin 5-minute up/down, prediction-market edge, or wants a reusable autonomous trading skill for these windows.
metadata:
  type: workflow
  version: "0.1.0"
  default_mode: PAPER_TRADING
  asset: BTC
  window: 5m
---

# polymarket-btc-5m-predictor

Analyze one active BTC 5-minute Polymarket market at a time. Decide only from model probability versus executable market price after costs. Default is paper trading. Fail closed. Never force a trade.

## Purpose

Identify probabilistically favorable UP/DOWN opportunities in Polymarket BTC 5-minute markets. The decision is not "will BTC go up." The decision is whether `P(UP)` differs from the executable CLOB price by more than spread, fees, slippage, latency, and calibration error.

## Default mode

`PAPER_TRADING`

Do not enable live auto-execution from this skill. `APPROVAL_REQUIRED` is the only optional next mode. `REAL_AUTO` is out of scope until paper EV is proven out of sample.

## Non-negotiable rules

- Do not invent sources, PnL, or win rates.
- Do not use martingale or increase size after losses.
- Do not trade every window. `NO_TRADE` is a first-class output.
- Separate prediction accuracy from trading profitability.
- Resolve against the market's own Chainlink TWAP config, never Binance last, Coinbase last, or a reconstructed TWAP from 1 Hz ticks.
- Read `cryptoMarketConfig.twapLookbackSeconds` per market. Do not hardcode 30 or 60.
- If critical data is missing, stale, or conflicting, output `NO_TRADE`.

## Official market mechanics (must be re-read live)

- Series slug `btc-up-or-down-5m`. Market slug `btc-updown-5m-<unix_window_start_utc>`.
- Outcomes are `Up` and `Down`. Winning shares redeem at $1.
- Resolution language (current TWAP era). The market resolves to Up if the Chainlink TWAP of BTC at the end of the titled window is greater than or equal to the TWAP at the beginning of that window. Otherwise Down. Ties go Up.
- Settlement source is Chainlink Data Streams, not spot exchanges. Both price-to-beat and close come from the same applicable TWAP feed.
- Regime history that invalidates naive backtests
  - Before 2026-08-07 00:00 UTC instantaneous Chainlink snapshot.
  - 2026-08-07 through ~2026-08-14 5m used 30s TWAP.
  - From 2026-08-14/15 5m markets use 60s TWAP. Confirm on the live market object.
- Markets are created about 24 hours before the window. Trading can continue until close; the book often collapses near expiry.
- Crypto taker fee `fee = shares * 0.07 * p * (1-p)`. Makers pay 0. Read the live market fee fields; do not assume fee-free.
- Typical constraints seen on these markets `orderMinSize` around 5, tick size 0.01 or 0.001. Always read book `min_order_size` and `tick_size`. Tick size can change near extremes.

## Workflow

1. Discover the currently active window.
   - Compute `window_start = floor(now_utc / 300) * 300`.
   - Fetch Gamma `https://gamma-api.polymarket.com/markets?slug=btc-updown-5m-<window_start>`.
   - Confirm `active`, not `closed`, `cryptoMarketConfig`, `clobTokenIds`, `outcomes` order, `resolutionSource`.
2. Snapshot resolution rules from the market object. Store `price_to_beat` only from the settlement TWAP at window open. If the open print was missed and cannot be recovered from a trusted store, `NO_TRADE`.
3. Collect synchronized clocks
   - Settlement TWAP via RTDS `crypto_prices_twap_sixty` and/or `crypto_prices_twap_thirty` matching `twapLookbackSeconds`.
   - Instantaneous Chainlink `crypto_prices_chainlink` as a leading indicator only.
   - Optional venue tapes Binance/Coinbase/Bybit/OKX for lead-lag research, never for resolution.
   - CLOB market websocket for UP/DOWN bid/ask/depth/trades.
4. Compute features from data that existed at the decision timestamp. No future bars.
5. Estimate `p_up` and `p_down = 1 - p_up` from the MVP diffusion model, then optional residual adjustments that were validated out of sample.
6. Read executable Polymarket prices. For buying UP use best ask on UP (or walk the book). For buying DOWN use best ask on DOWN.
7. Compute
   - `raw_edge = p_model - entry_price` for the chosen side
   - `estimated_cost = taker_fee + half_spread_or_slippage + latency_buffer`
   - `uncertainty_buffer` from model variance, data age, and calibration error
   - `net_edge = raw_edge - estimated_cost - uncertainty_buffer`
8. Apply hard no-trade filters and risk limits.
9. Emit `UP`, `DOWN`, or `NO_TRADE` with confidence and reason codes.
10. Record the decision before resolution. Never edit after the fact.
11. After settlement, score Brier, log loss, PnL, and calibration. Update performance memory as descriptive stats only. Memory must not override current evidence.

## Probability model (MVP)

Treat the settlement TWAP as the state variable `S_t`. Let `K` be the open TWAP (price to beat). Let `tau` be seconds remaining until window end. Let `sigma` be a shrinkage estimator of short-horizon TWAP innovation volatility.

Under a driftless Gaussian diffusion on the settlement series

`p_up = Phi((S_t - K) / (sigma * sqrt(tau)))`

with a small tie-to-up adjustment only if the live rule is still `>=`.

This is the minimum-MSE random-walk baseline. It will not call a large move from a standing start. Tradeable information, if any, is disagreement versus the book after costs.

Do not ship RSI/EMA soup in MVP. Experimental residuals (order-flow, cross-exchange lead, Polymarket lag) may adjust `p_up` only after a walk-forward test beats this baseline on EV per trade, not win rate.

## Edge calculation

```
side = UP if p_up >= 0.5 else DOWN
entry = ask_up if side == UP else ask_down
p_side = p_up if side == UP else p_down
raw_edge = p_side - entry
taker_fee = 0.07 * entry * (1 - entry)   # per share, crypto category
slippage = expected_walk_cost(size, book)
latency_cost = f(data_age_ms, book_velocity)
estimated_cost = taker_fee + slippage + latency_cost
uncertainty_buffer = max(min_buffer, k * se(p_side) + calib_error)
net_edge = raw_edge - estimated_cost - uncertainty_buffer
```

Enter only if `net_edge >= MIN_EDGE` and `confidence >= MIN_CONFIDENCE` and no hard filter fires.

Optional complement arb is a separate family. If `ask_up + ask_down < 1 - fees - slippage`, that is inventory-neutral harvest, not a directional call. Record it under strategy family `PAIR_ARB`.

## Time-to-expiry regimes

Evaluate and gate separately

- 300-180s research only unless edge is extreme
- 180-60s main directional window for residual models
- 60-20s late confirmation; TWAP damping matters
- 20-5s only if remaining move >> residual TWAP vol
- <5s default `NO_TRADE` unless maker-only and already filled

After the 60s TWAP change, last-second spot sniping is weaker than under snapshot resolution. Do not copy pre-August-2026 bot logic blindly.

## Hard no-trade conditions

Fail closed if any of these hold

- spread on the candidate side above `MAX_SPREAD`
- executable size below `MIN_LIQUIDITY` or `orderMinSize`
- `net_edge < MIN_EDGE`
- TWAP or CLOB data older than `MAX_DATA_AGE_MS`
- websocket disconnected or sequence gap
- missing price-to-beat
- conflicting venue returns beyond configured tolerance when a residual model depends on them
- realized vol above `MAX_VOL_Z` without a validated high-vol model
- API latency above `MAX_ALLOWED_LATENCY_MS`
- seconds remaining below `MIN_SECONDS_REMAINING`
- model confidence below `MIN_CONFIDENCE`
- detected clock skew
- probability already inside cost band (`abs(p_model - mid) < estimated_cost + buffer`)
- daily loss, consecutive loss, or exposure caps hit
- market not the current window or already resolving

## Risk

Configurable caps in `config.yaml`

- `MAX_RISK_PER_MARKET`
- `MAX_DAILY_LOSS`
- `MAX_CONSECUTIVE_LOSSES`
- `MAX_TOTAL_EXPOSURE`
- `MIN_EDGE`
- `MIN_CONFIDENCE`
- `MIN_LIQUIDITY`
- `MAX_SPREAD`
- `MAX_ALLOWED_LATENCY_MS`

Size with fractional Kelly on `net_edge`, then clip to `MAX_RISK_PER_MARKET`. After a loss, do not increase size. Optional soft size-down after a loss streak. Never martingale.

## Decision payload

Every cycle must emit JSON with at least

```json
{
  "market_id": "",
  "slug": "",
  "timestamp": "",
  "seconds_remaining": 0,
  "btc_reference_price": 0,
  "btc_current_twap": 0,
  "polymarket_up_bid": 0,
  "polymarket_up_ask": 0,
  "polymarket_down_bid": 0,
  "polymarket_down_ask": 0,
  "p_up": 0,
  "p_down": 0,
  "raw_edge": 0,
  "estimated_cost": 0,
  "uncertainty_buffer": 0,
  "net_edge": 0,
  "signal": "NO_TRADE",
  "confidence": 0,
  "reasons": []
}
```

## Architecture

See `references/architecture.md` for module boundaries and `config.yaml` for defaults. Keep DATA, FEATURES, MODEL, EDGE, DECISION, RISK, EXECUTION, MEMORY, MONITORING separate.

## Implementation priority

- MVP. Market discovery, TWAP+CLOB ingest, diffusion `p_up`, edge vs ask, no-trade filters, paper fills, settlement scoring.
- V2. Order-flow residuals, maker posting, complement arb, walk-forward calibration.
- V3. Cross-exchange lead-lag, full book reconstruction, online calibration, approval-mode live.

Do not add features that have not beaten the diffusion baseline on EV per trade.

## References

- `references/mechanics.md` official rules and endpoints
- `references/features.md` ranked feature table
- `references/architecture.md` modules and tests
- `config.yaml` conservative paper-trading defaults
