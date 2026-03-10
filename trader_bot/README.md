# Wealthsimple MA Crossover Trader Bot

A Python bot that trades US stocks on your Wealthsimple account using a
**Moving Average Crossover** strategy (Golden Cross / Death Cross).

## How it works

| Signal | Condition | Action |
|---|---|---|
| **Golden Cross** (BUY) | Short MA crosses **above** Long MA | Buy up to `MAX_POSITION_USD` worth of shares |
| **Death Cross** (SELL) | Short MA crosses **below** Long MA | Sell entire held position |
| **HOLD** | No crossover | Do nothing |

Default settings: `SHORT_MA=50`, `LONG_MA=200` (classic strategy).

## Quick start

```bash
cd trader_bot

# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure credentials and settings
cp .env.example .env
# Edit .env — fill in WS_EMAIL, WS_PASSWORD, (optionally WS_OTP_SECRET)
# Keep WS_PAPER_TRADE=true until you've verified the bot works correctly

# 3. Run
python trader.py
```

## Files

```
trader_bot/
├── trader.py        Main bot — scheduler + order logic
├── strategy.py      MA crossover signal computation
├── market_data.py   Price history fetcher (yfinance)
├── ws_client.py     Wealthsimple Trade API wrapper
├── requirements.txt Python dependencies
├── .env.example     Configuration template
└── README.md        This file
```

## Configuration

Copy `.env.example` → `.env` and set these values:

| Variable | Default | Description |
|---|---|---|
| `WS_EMAIL` | — | Your Wealthsimple email |
| `WS_PASSWORD` | — | Your Wealthsimple password |
| `WS_OTP_SECRET` | *(blank)* | Base32 TOTP secret for unattended 2FA |
| `WS_PAPER_TRADE` | `true` | `true` = simulate only, `false` = live trading |
| `TICKERS` | `AAPL,MSFT,NVDA,AMZN,GOOGL` | Stocks to watch |
| `SHORT_MA_WINDOW` | `50` | Short-term MA period |
| `LONG_MA_WINDOW` | `200` | Long-term MA period |
| `MAX_POSITION_USD` | `500` | Max USD per BUY order |
| `MAX_DAILY_TRADES` | `5` | Max orders per day |
| `CHECK_INTERVAL_MIN` | `60` | Minutes between signal checks |

## 2FA setup (for unattended operation)

`WS_OTP_SECRET` is the **base32 secret key** you received when setting up 2FA
(the string you typed/scanned before your authenticator app showed codes for the
first time). It is **not** the 6-digit rotating code.

If you leave `WS_OTP_SECRET` blank, the bot will prompt you to type the 6-digit
code each time it starts — suitable for manual runs.

## Disclaimer

This bot uses an **unofficial, community-maintained** Wealthsimple API library
and is not affiliated with or endorsed by Wealthsimple. Trading involves
financial risk. Use paper-trade mode first. The authors are not responsible for
any financial losses.

Wealthsimple Trade rate-limits orders to approximately **7 per hour**.
`MAX_DAILY_TRADES` is set conservatively by default.
