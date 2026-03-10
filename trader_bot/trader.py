"""
Wealthsimple Moving-Average-Crossover Trader Bot
=================================================

Runs on a schedule and checks each watched ticker for a MA crossover signal.
On a BUY signal  → buys a position sized by MAX_POSITION_USD.
On a SELL signal → sells the entire held position.

Environment variables (see .env.example):
    WS_EMAIL            Wealthsimple login email
    WS_PASSWORD         Wealthsimple login password
    WS_OTP_SECRET       Base32 TOTP secret (optional; needed for unattended 2FA)
    WS_PAPER_TRADE      "true" to simulate trades (default: true)
    TICKERS             Comma-separated list of US stock symbols, e.g. "AAPL,MSFT,NVDA"
    SHORT_MA_WINDOW     Short-term MA period (default: 50)
    LONG_MA_WINDOW      Long-term MA period (default: 200)
    MAX_POSITION_USD    Max USD per position (default: 500)
    MAX_DAILY_TRADES    Max total trades per calendar day (default: 5)
    CHECK_INTERVAL_MIN  How often to re-check signals in minutes (default: 60)
"""

import logging
import os
import sys
import time
from datetime import date, datetime

import schedule
from dotenv import load_dotenv

from market_data import get_price_history, get_current_price
from strategy import compute_ma_crossover, Signal
from ws_client import WealthsimpleClient

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("trader_bot.log"),
    ],
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
load_dotenv()

EMAIL = os.environ["WS_EMAIL"]
PASSWORD = os.environ["WS_PASSWORD"]
OTP_SECRET = os.getenv("WS_OTP_SECRET")
PAPER_TRADE = os.getenv("WS_PAPER_TRADE", "true").lower() == "true"

TICKERS = [t.strip().upper() for t in os.getenv("TICKERS", "AAPL,MSFT,NVDA").split(",") if t.strip()]
SHORT_MA = int(os.getenv("SHORT_MA_WINDOW", "50"))
LONG_MA = int(os.getenv("LONG_MA_WINDOW", "200"))
MAX_POSITION_USD = float(os.getenv("MAX_POSITION_USD", "500"))
MAX_DAILY_TRADES = int(os.getenv("MAX_DAILY_TRADES", "5"))
CHECK_INTERVAL_MIN = int(os.getenv("CHECK_INTERVAL_MIN", "60"))

# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------
_daily_trade_count = 0
_last_trade_date: date = date.min


def _reset_daily_counter():
    global _daily_trade_count, _last_trade_date
    today = date.today()
    if today != _last_trade_date:
        _daily_trade_count = 0
        _last_trade_date = today


def _can_trade() -> bool:
    _reset_daily_counter()
    if _daily_trade_count >= MAX_DAILY_TRADES:
        logger.warning("Daily trade limit (%d) reached. Skipping until tomorrow.", MAX_DAILY_TRADES)
        return False
    return True


def _increment_trade():
    global _daily_trade_count
    _reset_daily_counter()
    _daily_trade_count += 1


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def run_strategy(client: WealthsimpleClient):
    """Evaluate each ticker and act on crossover signals."""
    logger.info("=== Running strategy check (%d tickers) ===", len(TICKERS))

    positions = {}
    try:
        positions = client.get_positions()
    except Exception as exc:
        logger.error("Could not fetch positions: %s", exc)

    for ticker in TICKERS:
        try:
            df = get_price_history(ticker, days=LONG_MA * 2 + 50)
            result = compute_ma_crossover(df, ticker, short_window=SHORT_MA, long_window=LONG_MA)
        except Exception as exc:
            logger.error("[%s] Strategy error: %s", ticker, exc)
            continue

        if result.signal == Signal.BUY:
            if not _can_trade():
                break

            try:
                price = result.current_price
                shares = max(1, int(MAX_POSITION_USD / price))
                logger.info("[%s] Golden Cross — buying %d share(s) @ ~%.2f", ticker, shares, price)
                client.place_market_buy(ticker, shares)
                _increment_trade()
            except Exception as exc:
                logger.error("[%s] BUY failed: %s", ticker, exc)

        elif result.signal == Signal.SELL:
            held_qty = int(positions.get(ticker, {}).get("quantity", 0))
            if held_qty <= 0:
                logger.info("[%s] Death Cross but no position held — skip SELL.", ticker)
                continue

            if not _can_trade():
                break

            try:
                logger.info("[%s] Death Cross — selling %d share(s)", ticker, held_qty)
                client.place_market_sell(ticker, held_qty)
                _increment_trade()
            except Exception as exc:
                logger.error("[%s] SELL failed: %s", ticker, exc)

        else:
            logger.info("[%s] HOLD — no crossover detected.", ticker)

    logger.info("=== Check complete. Trades today: %d/%d ===", _daily_trade_count, MAX_DAILY_TRADES)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    logger.info("Starting Wealthsimple MA Crossover Bot")
    logger.info("  Tickers       : %s", ", ".join(TICKERS))
    logger.info("  MA windows    : %d / %d", SHORT_MA, LONG_MA)
    logger.info("  Max pos USD   : %.2f", MAX_POSITION_USD)
    logger.info("  Max daily tr. : %d", MAX_DAILY_TRADES)
    logger.info("  Check interval: %d min", CHECK_INTERVAL_MIN)
    logger.info("  Paper trade   : %s", PAPER_TRADE)

    client = WealthsimpleClient(
        email=EMAIL,
        password=PASSWORD,
        otp_secret=OTP_SECRET,
        paper_trade=PAPER_TRADE,
    )

    # Run once immediately, then on schedule
    run_strategy(client)

    schedule.every(CHECK_INTERVAL_MIN).minutes.do(run_strategy, client=client)
    logger.info("Scheduler started — checking every %d minutes.", CHECK_INTERVAL_MIN)

    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    main()
