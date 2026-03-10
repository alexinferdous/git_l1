"""
Market data fetcher using yfinance for US stocks.
"""

import logging
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


def get_price_history(ticker: str, days: int = 250) -> pd.DataFrame:
    """
    Fetch historical daily closing prices for a ticker.

    Args:
        ticker: Stock symbol (e.g. 'AAPL')
        days: Number of calendar days of history to fetch (default 250 covers ~200 trading days)

    Returns:
        DataFrame with columns: Open, High, Low, Close, Volume
        Index is DatetimeIndex.
    """
    end = datetime.today()
    start = end - timedelta(days=days)
    try:
        df = yf.download(ticker, start=start.strftime("%Y-%m-%d"),
                         end=end.strftime("%Y-%m-%d"), progress=False, auto_adjust=True)
        if df.empty:
            raise ValueError(f"No data returned for ticker '{ticker}'")
        logger.debug("Fetched %d rows for %s", len(df), ticker)
        return df
    except Exception as exc:
        logger.error("Failed to fetch price history for %s: %s", ticker, exc)
        raise


def get_current_price(ticker: str) -> float:
    """Return the most recent closing price for a ticker."""
    df = get_price_history(ticker, days=5)
    return float(df["Close"].iloc[-1])
