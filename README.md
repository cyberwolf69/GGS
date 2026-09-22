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

**Powered by web3rai**

---

## Overview

GGS evaluates Polymarket **BTC 5-Minute UP / DOWN** markets using multiple independent layers before an entry is allowed.

```text
BTC Reference Feed
        |
        v
Active BTC 5m Market
        |
        v
Price To Beat Source Lock
        |
        +-------------------------+
        |                         |
        v                         v
Probability Engine        Momentum / Skew Engine
        |                         |
        +------------+------------+
                     |
                     v
              Net Edge Engine
                     |
                     v
          Payout Gate 1.50–1.80x
                     |
                     v
      Spread / Freshness / Latency Guards
                     |
                     v
               Decision Engine
                     |
       +-------------+-------------+
       |             |             |
       v             v             v
    BUY UP        BUY DOWN      NO TRADE
       |             |
       +------+------+ 
              |
      +-------+------------------+
      |                          |
      v                          v
 PAPER Executor             LIVE Executor
                             |
                   READ ONLY / SHADOW / REAL
```

`NO_TRADE` is a valid decision. Missing, stale, low-quality, or economically unattractive setups are rejected rather than guessed.

---

## Current Market Profile

| Setting | Default |
| --- | ---: |
| Asset | BTC |
| Market | UP / DOWN |
| Duration | 5 minutes |
| Minimum effective payout | **1.50x** |
| Maximum effective payout | **1.80x** |
| Base minimum net edge | **4%** |
| Adaptive confidence gate | **Enabled** |
| Max active position | **1 / market** |
| Exit model | **Hold to resolution** |
| Martingale | **OFF** |

The payout gate uses estimated effective cost rather than only the raw displayed price. GGS also applies a stricter confidence requirement around lower-payout entries.

---

## Features

| Feature | Description |
| --- | --- |
| Market Discovery | Tracks the current BTC 5-minute Polymarket market. |
| Price To Beat Lock | Keeps entry and resolution context aligned to the same round. |
| Reference Price Engine | Normalizes and validates BTC reference data. |
| Probability Engine | Estimates directional probability using price distance, volatility, and time remaining. |
| Momentum Engine | Adds BTC movement, stronger-side, timing, and market-skew context. |
| Net Edge Engine | Evaluates probability edge after modeled costs and latency buffers. |
| Adaptive Payout Gate | Accepts only effective payout in the configured **1.50x–1.80x** range. |
| Risk Guards | Spread, liquidity, freshness, latency, balance, pause, and position limits. |
| PAPER Mode | Simulated entries and hold-to-resolution accounting. |
| LIVE READ-ONLY | Connects MetaMask/Polymarket without submitting orders. |
| LIVE SHADOW | Produces real-market order previews but sends nothing. |
| LIVE REAL | Price-protected, gated order submission using the official Polymarket Python SDK. |
| Telegram Control | Monitoring, mode switching, settings, pause/resume, and gated withdrawal. |
| Dashboard | Terminal-style monitoring at `127.0.0.1:6969`. |
| Persistent Settings | Runtime operator settings survive restart. |
| Cross-platform Launchers | macOS/Linux, Windows PowerShell, and Linux VPS/systemd. |

---

## PAPER / LIVE Modes

GGS uses **one strategy core**. PAPER and LIVE do not have separate signal logic.

```text
Decision Engine
      |
      +--------------------------+
      |                          |
      v                          v
PAPER Executor              LIVE Executor
      |                          |
Simulated fills      MetaMask + Polymarket SDK
```

Available operator modes:

```text
PAPER
LIVE_READONLY
LIVE_SHADOW
LIVE
```

### PAPER

No real orders or withdrawals.

### LIVE READ-ONLY

Connects the configured MetaMask EOA and authenticated Polymarket client, then reads wallet/collateral readiness. No entry is submitted.

### LIVE SHADOW

The real market decision is converted into an order preview containing side, token, stake, and maximum accepted price. The order is **not sent**.

### LIVE REAL

Real entry submission is available only when:

```env
GGS_LIVE_ENABLED=true
```

The live BUY uses a **FAK market order with `max_spend` and `max_price` protection**. GGS therefore does not intentionally chase an outcome price above the decision price.

LIVE remains fail-closed when the wallet, signer, CLOB connection, balance, or other required checks are not ready.

---

## MetaMask LIVE Setup

The current LIVE connector is designed for a **MetaMask EOA** where the configured wallet address belongs to the configured private key.

### 1. Start GGS once

macOS/Linux:

```bash
./start.sh
```

Windows:

```powershell
.\start.ps1
```

This creates the virtual environment and installs dependencies.

### 2. Configure the signer locally

**Never send your private key to Telegram, ChatGPT, GitHub, or a public log.**

macOS/Linux:

```bash
./setup-live.sh
```

Windows:

```powershell
.\setup-live.ps1
```

The setup asks for:

```text
MetaMask address
MetaMask private key (hidden input)
```

GGS verifies locally that the private key belongs to the address and stores it only in the gitignored local `.env` file.

The setup intentionally leaves:

```env
GGS_LIVE_ENABLED=false
GGS_LIVE_WITHDRAWALS_ENABLED=false
```

### 3. Check LIVE connection

```bash
./live-check.sh
```

or Windows:

```powershell
.\live-check.ps1
```

Review wallet match, authenticated client status, collateral balance, and allowance readiness.

If trading approvals are missing, they can be submitted explicitly:

```bash
./live-check.sh --approve
```

For an EOA, this can broadcast Polygon approval transactions and may require network gas.

### 4. Test READ-ONLY

Telegram:

```text
/mode
```

Then choose:

```text
LIVE → READ ONLY
```

Confirm that the wallet shown by GGS matches your MetaMask address and the balance is correct.

### 5. Test SHADOW

Choose:

```text
LIVE → SHADOW
```

GGS will continue evaluating live markets but only record what it **would** submit.

### 6. Enable real entries

Only after READ-ONLY and SHADOW have been validated, change the local `.env`:

```env
GGS_LIVE_ENABLED=true
```

Restart GGS and select:

```text
/mode → LIVE → LIVE REAL
```

For the first real test, use a small Bet / Entry value from `/settings`.

---

## LIVE Order Protection

A valid strategy signal is not enough to force an order.

For every live BUY, GGS provides:

```text
amount     = configured Bet / Entry
max_spend  = configured Bet / Entry
max_price  = strategy decision entry price
order_type = FAK
```

If acceptable liquidity is no longer available under the protected price, the order may be rejected or only fill according to the exchange's FAK behavior rather than intentionally chasing a worse price.

Live order results are stored separately under `runtime/` and can include accepted/rejected status, order ID, fill amounts, trade IDs, and settlement transaction hashes returned by the SDK.

---

## Telegram Owner Control

Send:

```text
/start
```

Main panel:

```text
[ Status ]        [ Market ]
[ Position ]      [ Performance ]
[ Modules ]       [ Last Trade ]
[ Balance ]       [ Withdrawal ]
[ Pause ]         [ Resume ]
[             MODE             ]
[           SETTINGS           ]
```

GGS also registers a Telegram command menu automatically:

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

Monitoring pages use inline **Refresh** buttons that edit the existing message rather than spamming new messages.

### `/settings`

Bet / Entry can be changed from Telegram:

```text
[ $2 ] [ $4 ] [ $6 ]
[ $8 ] [ $10 ] [ Custom ]
```

Changes apply to the **next entry** and do not resize an existing position.

Signal settings display the current payout range, confidence, edge, and market guards.

---

## Withdrawal

Withdrawal is disabled unless all of these are true:

```text
Mode = LIVE
GGS_LIVE_WITHDRAWALS_ENABLED=true
Valid MetaMask signer
Sufficient collateral balance
Owner Telegram authorization
```

Telegram flow:

```text
Withdrawal
    |
Destination address
    |
Amount
    |
Preview
    |
[ Confirm ] [ Cancel ]
```

The confirmation state expires and is cleared before transaction submission to reduce accidental duplicate execution.

Withdrawal uses the configured Polymarket collateral token on Polygon and the authenticated local signer. Keep withdrawal disabled until real entry execution has been validated.

---

## Dashboard

Open:

```text
http://127.0.0.1:6969
```

The dashboard includes:

- Price To Beat
- Actual BTC reference price
- UP / DOWN ask
- countdown
- decision and reason
- payout
- confidence
- net edge
- momentum
- execution tape
- PAPER performance metrics
- LIVE collateral balance when a LIVE mode is active
- runtime activity bars

Activity bars represent module activity level rather than decorative blinking.

---

## Telegram Setup

### 1. Create a bot

Open **@BotFather** in Telegram:

```text
/newbot
```

Follow the prompts and copy the Bot Token.

### 2. Get your Telegram User ID

Send a message such as `/start` to your new bot, then run:

```bash
curl "https://api.telegram.org/botYOUR_BOT_TOKEN/getUpdates"
```

Find:

```json
"from": {
  "id": 123456789
}
```

Use that numeric value as `TELEGRAM_OWNER_ID`.

### 3. Configure `.env`

```bash
cp .env.example .env
```

Set:

```env
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_OWNER_ID=123456789
```

Restart GGS, then send `/start`.

Only the configured Telegram owner ID is authorized for control callbacks.

---

## Installation

Clone:

```bash
git clone https://github.com/cyberwolf69/GGS.git
cd GGS
```

### macOS / Linux

Requires **Python 3.11+**.

```bash
chmod +x start.sh stop.sh status.sh setup-live.sh live-check.sh
./start.sh
```

Status:

```bash
./status.sh
```

Stop:

```bash
./stop.sh
```

### Windows PowerShell

Requires **Python 3.11+**.

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\start.ps1
```

Status:

```powershell
.\status.ps1
```

Stop:

```powershell
.\stop.ps1
```

### Linux VPS

```bash
chmod +x deploy/*.sh
sudo ./deploy/install-systemd.sh
sudo systemctl status ggs
```

Logs:

```bash
journalctl -u ggs -f
```

The dashboard binds to localhost. To access it remotely without exposing port `6969` publicly:

```bash
ssh -L 6969:127.0.0.1:6969 user@YOUR_VPS_IP
```

Then open `http://127.0.0.1:6969` locally.

---

## Configuration

Strategy defaults:

```text
config/paper.yaml
```

Runtime owner settings:

```text
runtime/settings.json
```

Secrets:

```text
.env
```

`.env` and `runtime/` are ignored by Git.

Important LIVE variables:

```env
POLYMARKET_PRIVATE_KEY=
POLYMARKET_WALLET_ADDRESS=
GGS_LIVE_ENABLED=false
GGS_LIVE_WITHDRAWALS_ENABLED=false
POLYMARKET_COLLATERAL_TOKEN=0xC011a7E12a19f7B1f670d46F03B03f3342E82DFB
```

The official Polymarket SDK production environment supplies its Polygon chain and RPC configuration. `POLYGON_RPC_URL` in `.env.example` is reserved for a future custom-environment override and is not required by the current connector.

---

## Project Structure

```text
GGS/
├── ggs/
│   ├── market/
│   ├── fusion/
│   ├── risk/
│   ├── paper/
│   ├── live/
│   ├── telegram/
│   └── analytics/
├── dashboard/
├── config/
├── deploy/
├── tests/
├── setup-live.sh
├── live-check.sh
├── start.sh
├── stop.sh
├── status.sh
├── start.ps1
├── stop.ps1
├── status.ps1
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

---

## GitHub Safety

Before push:

```bash
git status --ignored
```

Never commit:

- `.env`
- wallet private keys
- Telegram Bot Token
- local wallet/keystore files
- runtime trading state containing sensitive data

Relevant patterns are included in `.gitignore`.

---

## Testing

```bash
pytest -q
```

The local suite covers strategy gates, payout range, paper accounting, source lock, settings persistence, Telegram controls, and fail-closed LIVE behavior without requiring a funded wallet.

Tests that would place real orders, approve tokens, or withdraw funds are **not** executed automatically.

---

## Safety Notes

- PAPER is the safe default.
- LIVE READ-ONLY and SHADOW should be validated before LIVE REAL.
- Private keys are accepted only through the local hidden-input setup script, never Telegram.
- Real execution requires explicit `GGS_LIVE_ENABLED=true`.
- Withdrawal requires a second explicit gate: `GGS_LIVE_WITHDRAWALS_ENABLED=true`.
- Strategy payout is restricted to **1.50x–1.80x** effective payout.
- A target win rate is not guaranteed by configuration.

---

## Disclaimer

GGS is experimental trading infrastructure. Prediction markets and cryptocurrency trading involve financial risk. PAPER performance does not guarantee LIVE results, and real execution can differ because of liquidity, latency, fees, order rejection, partial fills, settlement behavior, and market conditions.

Validate wallet configuration and use small amounts before increasing real exposure.

---

<p align="center">
  <b>GGS — Ganteng-Ganteng Signature</b><br>
  BTC 5-Minute Prediction & Trading Infrastructure<br><br>
  Powered by web3rai
</p>
