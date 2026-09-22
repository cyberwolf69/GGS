---
name: ggs-fusion-1_5x
description: GGS (Ganteng-Ganteng Signature) PAPER/LIVE fusion engine for Polymarket BTC 5-minute Up/Down. Combines source-locked Chainlink TWAP settlement, the Novals83 momentum/skew strategy concepts, and a cost-aware diffusion probability/edge model. Targets effective payout 1.50x–1.80x and emits BUY_UP, BUY_DOWN, or NO_TRADE.
metadata:
  mode: PAPER_LIVE
  port: 6969
  starting_balance: 60
  stake_usd: 6
---

# GGS — Ganteng-Ganteng Signature

GGS is a paper-first fusion engine with gated LIVE READ-ONLY, SHADOW, and REAL execution. Profitability is the objective; win rate is a descriptive output, not a target that can force trades.

## Sources fused

1. **Novals83/5min-btc-polymarket**
   - Current runner behavior: CLOB best-ask threshold/stronger-side logic.
   - Strategy reference: momentum follow-through into close, target around 120s remaining, meaningful BTC move reference around $70-$100, market-skew preference, spread/liquidity/risk guards.
   - In GGS these become momentum/context features rather than a hard `>=0.70` entry rule, because a 0.70 entry cannot satisfy the GGS 1.50x payout floor.

2. **User-provided `BTC 5min.zip` skill**
   - Settlement TWAP is the state variable.
   - Diffusion baseline: `p_up = Phi((S_t-K)/(sigma*sqrt(tau)))`.
   - Decision is model probability versus executable CLOB ask after fee, slippage, latency and uncertainty.
   - `NO_TRADE` is first-class and critical data failures fail closed.

3. **SAMARUK lessons/fixes**
   - Price-to-beat and resolution are source-locked to the same applicable Chainlink TWAP stream.
   - `twapLookbackSeconds` is read per market when available.
   - Expired unresolved positions move to a pending queue so stale state cannot block future markets.
   - Paper accounting is persistent.

## Hard GGS rules

- PAPER is the default. LIVE READ-ONLY and SHADOW are available after local MetaMask setup. LIVE REAL requires the explicit `GGS_LIVE_ENABLED=true` safety gate.
- Starting paper balance: `$60`.
- Fixed paper stake: `$6`.
- Effective payout range after modeled taker fee + slippage buffer: `1.50x–1.80x`.
- Raw entry band: approximately `0.5555556–0.6666667`; the cost-aware filter enforces the effective 1.50x–1.80x range.
- Base minimum model confidence: `68%`, with an adaptive gate (`73%` around 1.50–1.59x, `70%` around 1.60–1.69x, `68%` around 1.70–1.80x).
- Minimum net edge after modeled costs/buffer: `4%`.
- Maximum candidate spread: `4%`.
- Maximum reference-data age: `1500 ms`.
- Maximum CLOB latency: `400 ms`.
- One position per market.
- Hold to resolution. No stop loss, no early exit, no martingale.

## Decision pipeline

`MARKET TRUTH -> PROBABILITY -> MOMENTUM -> EDGE -> PAYOUT -> RISK -> BUY_UP/BUY_DOWN/NO_TRADE`

### Market truth

- Current BTC 5m slug: `btc-updown-5m-<floor(now/300)*300>`.
- Discover from Gamma.
- Read `cryptoMarketConfig.twapLookbackSeconds` when present.
- Subscribe to matching RTDS TWAP stream (30s or 60s).
- Capture Price To Beat from that same stream at the market boundary.
- If the boundary print was missed, do not trade the current round.

### Probability

MVP uses the user-provided diffusion model on the settlement TWAP. Sigma is estimated from recent TWAP innovations and clamped using the provided min/max bps configuration.

### Momentum

Momentum is a confirmation score informed by the GitHub strategy reference:
- direction of current TWAP versus Price To Beat,
- Polymarket stronger-side skew,
- short-term TWAP momentum,
- progress toward the repo's ~$70 meaningful-move reference,
- proximity to the repo's ~120s target timing.

Momentum does **not** overwrite the probability model. It gates a trade.

### Edge

For the predicted side:

`raw_edge = p_side - executable_ask`

`net_edge = raw_edge - taker_fee - slippage_buffer - latency_cost - uncertainty_buffer`

Crypto taker fee model follows the supplied skill:

`fee/share = 0.07 * p * (1-p)`

### Payout discipline

Any candidate with entry price above `0.6666667` is rejected even if probability is high.

### Fail closed

Examples of NO_TRADE reason codes:
- `SOURCE_LOCK_NOT_READY`
- `OUTSIDE_ENTRY_WINDOW`
- `CLOB_UNAVAILABLE`
- `REFERENCE_FEED_STALE`
- `LATENCY_TOO_HIGH`
- `SPREAD_TOO_WIDE`
- `LIQUIDITY_TOO_LOW`
- `PAYOUT_TOO_LOW`
- `PAYOUT_TOO_HIGH`
- `MOMENTUM_NOT_CONFIRMED`
- `CONFIDENCE_TOO_LOW`
- `EDGE_TOO_SMALL`
- `ROUND_ALREADY_USED`
- `POSITION_ALREADY_OPEN`

## Success criteria

Do not declare the strategy successful from a short hot streak. Evaluate after a meaningful paper sample using:
- Net PnL
- balance growth / ROI
- expectancy per trade
- profit factor
- average payout multiple
- current and maximum drawdown
- win rate

The design goal is to test whether GGS can combine effective payout 1.50x–1.80x with positive expectancy; `70%+ WR` is an observed target, not a hard input.
