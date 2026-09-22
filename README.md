# GGS — Ganteng-Ganteng Signature

![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)
![Polymarket](https://img.shields.io/badge/Polymarket-Prediction%20Markets-5B5BD6)
![BTC](https://img.shields.io/badge/Market-BTC%205m-F7931A?logo=bitcoin&logoColor=white)
![Modes](https://img.shields.io/badge/Modes-PAPER%20%7C%20LIVE-22C55E)
![Payout](https://img.shields.io/badge/Payout-1.50x--1.80x-0EA5E9)
![Telegram](https://img.shields.io/badge/Telegram-Remote%20Control-26A5E4?logo=telegram&logoColor=white)
![Dashboard](https://img.shields.io/badge/Dashboard-Port%206969-0EA5E9)
![Platform](https://img.shields.io/badge/Platform-macOS%20%7C%20Linux%20%7C%20Windows-64748B)

**BTC 5-minute Polymarket prediction and trading infrastructure with PAPER, LIVE READ-ONLY, LIVE SHADOW, and gated LIVE execution.**

GGS combines probability modeling, momentum context, cost-aware edge, payout filtering, market-quality guards, Telegram owner control, and a real-time dashboard in one codebase.



---

## Overview

```text
BTC Reference Feed
        │
        ▼
Active BTC 5m Market
        │
        ▼
Price To Beat Source Lock
        │
        ▼
Probability Engine
        │
        ├──────────────► Momentum / Skew Engine
        │
        ▼
Net Edge Engine
        │
        ▼
Payout Gate
   1.50x — 1.80x
        │
        ▼
Spread / Freshness / Latency Guards
        │
        ▼
Decision Engine
        │
        ├──────────────► BUY UP
        ├──────────────► BUY DOWN
        └──────────────► NO TRADE
                              │
                ┌─────────────┴─────────────┐
                ▼                           ▼
          PAPER Executor             LIVE Executor
                │                           │
                ▼                           ▼
              PAPER              READ ONLY / SHADOW / REAL
```

`NO_TRADE` is a valid decision.

Missing, stale, low-quality, or economically unattractive setups are rejected instead of being forced into a trade.

---

## Current Market Profile

| Parameter | Value |
|---|---|
| Asset | BTC |
| Market | UP / DOWN |
| Duration | 5 minutes |
| Minimum effective payout | 1.50x |
| Maximum payout | 1.80x |
| Base minimum net edge | 4% |
| Adaptive confidence | Enabled |
| Maximum active position | 1 / market |
| Exit | Hold to resolution |
| Martingale | OFF |

---

## Features

| Feature | Description |
|---|---|
| Market Discovery | Finds the active BTC 5-minute prediction market |
| Price To Beat Lock | Locks the correct reference source for the active market |
| Reference Price Engine | Tracks the BTC reference price used by the strategy |
| Probability Engine | Estimates UP / DOWN probability |
| Momentum Engine | Uses momentum and market skew context |
| Net Edge Engine | Evaluates economic edge after cost considerations |
| Adaptive Payout Gate | Filters opportunities within the configured payout range |
| Risk Guards | Spread, freshness, latency, liquidity, and market-quality protection |
| PAPER | Simulated execution without real orders |
| LIVE READ-ONLY | Connects and checks live wallet readiness without entering |
| LIVE SHADOW | Previews live execution without sending an order |
| LIVE REAL | Protected real execution behind explicit environment gates |
| Telegram Control | Remote owner-only control |
| Dashboard | Real-time market, signal, position, and execution monitoring |
| Persistent Settings | Stores runtime trading settings |
| Cross-platform Launchers | macOS, Linux, and Windows support |

---

## PAPER / LIVE Modes

GGS supports four runtime modes:

### PAPER

Fully simulated trading.

- No real orders
- No real withdrawals
- Uses the same strategy core
- Suitable for development and validation

### LIVE READ-ONLY

Connects to the configured MetaMask EOA and authenticated Polymarket client.

- Reads wallet status
- Reads collateral readiness
- Checks live connectivity
- Does not enter positions
- Does not send trading orders

### LIVE SHADOW

Uses the live market environment while keeping execution simulated.

- Reads real market conditions
- Builds the real order decision
- Previews the intended order
- Does not send the order

### LIVE REAL

Real trading execution.

Real entries are only permitted when:

```text
GGS_LIVE_ENABLED=true
```

The execution path uses:

- FAK market orders
- `max_spend` protection
- `max_price` protection
- Wallet/signer validation
- Collateral and readiness checks
- Fail-closed behavior when required conditions are not ready

---

## Changing Mode

The runtime mode can be changed from Telegram using:

```text
/mode
```

Available modes:

```text
PAPER
LIVE READ-ONLY
LIVE SHADOW
LIVE
```

Changing the runtime mode does **not** bypass the environment safety gate.

Real execution still requires:

```text
GGS_LIVE_ENABLED=true
```

The default configuration keeps real trading disabled.

---

## Default Configuration

The default environment is intentionally conservative:

```env
GGS_MODE=PAPER
GGS_LIVE_ENABLED=false
GGS_LIVE_WITHDRAWALS_ENABLED=false
```

Default application settings:

```text
Dashboard : http://127.0.0.1:6969
Asset     : BTC
Market    : BTC Up / Down
Duration  : 5 minutes
Payout    : 1.50x — 1.80x
Martingale: OFF
Exit      : Hold to resolution
```

---

## MetaMask LIVE Setup

GGS can connect to a MetaMask EOA for authenticated Polymarket operations.

### 1. Start GGS

macOS / Linux:

```bash
./start.sh
```

Windows PowerShell:

```powershell
.\start.ps1
```

### 2. Configure LIVE

macOS / Linux:

```bash
./setup-live.sh
```

Windows PowerShell:

```powershell
.\setup-live.ps1
```

The setup asks for:

- MetaMask wallet address
- Private key

The private key is entered locally and stored only in the gitignored `.env` file.

**Never commit `.env` to GitHub.**

After setup, the default safety state remains:

```env
GGS_LIVE_ENABLED=false
GGS_LIVE_WITHDRAWALS_ENABLED=false
```

### 3. Check LIVE Readiness

macOS / Linux:

```bash
./live-check.sh
```

Windows PowerShell:

```powershell
.\live-check.ps1
```

Optional approval setup:

```bash
./live-check.sh --approve
```

Approval setup may broadcast an on-chain approval transaction and requires gas.

### 4. Validate the Runtime

Start with:

```text
PAPER
```

Then use Telegram:

```text
/mode
```

Move to:

```text
LIVE READ-ONLY
```

Then:

```text
LIVE SHADOW
```

Only after the live environment has been independently verified should real execution be enabled:

```env
GGS_LIVE_ENABLED=true
```

Then select:

```text
/mode → LIVE
```

---

## Telegram Setup

GGS supports owner-only Telegram control.

### 1. Create a Telegram Bot

Open **BotFather** in Telegram:

https://t.me/BotFather

Send:

```text
/newbot
```

Follow the instructions and copy the bot token provided by BotFather.

Set it in `.env`:

```env
TELEGRAM_BOT_TOKEN=YOUR_BOT_TOKEN
```

### 2. Get Telegram Owner ID / Chat ID

Start a conversation with your bot and send:

```text
/start
```

Then open the Telegram Bot API `getUpdates` endpoint using your bot token:

```text
https://api.telegram.org/botYOUR_BOT_TOKEN/getUpdates
```

Look for:

```json
"chat": {
  "id": 123456789
}
```

The number inside `chat.id` is your Telegram Owner ID / Chat ID.

Set:

```env
TELEGRAM_OWNER_ID=123456789
```

Replace `123456789` with your actual Telegram ID.

The owner ID is used to restrict control commands to the authorized Telegram account.

---

## Telegram Commands

Available commands include:

```text
/start
/status
/market
/position
/performance
/modules
/last
/balance
/mode
/settings
/pause
/resume
/withdrawal
/help
```

### `/mode`

Switch between:

```text
PAPER
LIVE READ-ONLY
LIVE SHADOW
LIVE
```

### `/settings`

Controls trading settings such as Bet / Entry.

Available choices:

```text
$2
$4
$6
$8
$10
Custom
```

Changes apply to the next entry.

Signal settings also display:

- Payout
- Confidence
- Net edge
- Market guards

---

## LIVE Order Protection

LIVE REAL execution uses protected market-order parameters.

Conceptually:

```text
amount     = configured Bet / Entry
max_spend  = configured Bet / Entry
max_price  = strategy decision entry price
order_type = FAK
```

The order may be rejected if sufficient liquidity is not available under the protected price.

Execution results are stored in the runtime state.

---

## Withdrawal

Withdrawals are separately gated and disabled by default.

Withdrawals require:

```env
GGS_LIVE_WITHDRAWALS_ENABLED=true
```

Additional requirements include:

- LIVE mode
- Valid signer
- Sufficient collateral
- Authorized Telegram owner
- Explicit confirmation

The Telegram withdrawal flow is:

```text
Destination
    ↓
Amount
    ↓
Preview
    ↓
Confirm / Cancel
```

Withdrawals are not part of normal trading execution.

---

## Dashboard

Dashboard:

```text
http://127.0.0.1:6969
```

The dashboard provides real-time visibility into:

- Price To Beat
- Actual BTC reference price
- UP ask
- DOWN ask
- Countdown
- Decision
- Decision reason
- Payout
- Confidence
- Net edge
- Momentum
- Execution tape
- PAPER metrics
- LIVE collateral
- Runtime activity

---

## Installation

### Clone

```bash
git clone https://github.com/cyberwolf69/GGS.git
cd GGS
```

### macOS / Linux

```bash
./start.sh
```

### Windows

```powershell
.\start.ps1
```

Dashboard:

```text
http://127.0.0.1:6969
```

---

## Configuration

Main configuration files:

```text
config/paper.yaml
runtime/settings.json
.env
```

Important environment variables:

```env
GGS_MODE=PAPER
GGS_PORT=6969

TELEGRAM_BOT_TOKEN=
TELEGRAM_OWNER_ID=

POLYMARKET_PRIVATE_KEY=
POLYMARKET_WALLET_ADDRESS=

GGS_LIVE_ENABLED=false
GGS_LIVE_WITHDRAWALS_ENABLED=false

POLYGON_RPC_URL=https://polygon.drpc.org
CHAIN_ID=137

POLYMARKET_COLLATERAL_TOKEN=0xC011a7E12a19f7B1f670d46F03B03f3342E82DFB

WITHDRAW_CONFIRM_TIMEOUT=60
MAX_WITHDRAW_USD=500
```

Never commit real credentials, private keys, bot tokens, or `.env` files.

---

## Safety

GGS is designed around explicit execution gates.

The default state is:

```text
PAPER
```

Real trading requires the explicit environment gate:

```env
GGS_LIVE_ENABLED=true
```

Real withdrawals require a separate gate:

```env
GGS_LIVE_WITHDRAWALS_ENABLED=true
```

Private keys and credentials must remain local and must never be committed to GitHub.

LIVE execution should only be enabled after the wallet, signer, collateral, approvals, market connectivity, and execution behavior have been independently verified.

---

## Disclaimer

GGS is experimental trading infrastructure for Polymarket prediction markets.

Trading prediction markets involves financial risk. Market prices, liquidity, execution, network conditions, and model outputs can change rapidly.

Nothing in this repository constitutes financial, investment, or trading advice.

Use PAPER and READ-ONLY modes to validate the system before enabling real execution.

The user is responsible for configuring, operating, and securing the system.

---

<p align="center">
  <b>GGS — Ganteng-Ganteng Signature</b><br>
  BTC 5-Minute Prediction & Trading Infrastructure<br><br>
  Powered by web3rai
</p>
