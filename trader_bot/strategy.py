"""
Moving Average Crossover strategy.

Signal logic:
  BUY  — short-term MA crosses ABOVE long-term MA (Golden Cross)
  SELL — short-term MA crosses BELOW long-term MA (Death Cross)
  HOLD — no crossover detected
"""

from dataclasses import dataclass
from enum import Enum
import logging
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class Signal(Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


@dataclass
class StrategyResult:
    ticker: str
    signal: Signal
    short_ma: float
    long_ma: float
    prev_short_ma: float
    prev_long_ma: float
    current_price: float


def compute_ma_crossover(
    df: pd.DataFrame,
    ticker: str,
    short_window: int = 50,
    long_window: int = 200,
) -> StrategyResult:
    """
    Evaluate the MA crossover strategy on price history.

    Args:
        df:           DataFrame with a 'Close' column (from market_data.get_price_history)
        ticker:       Stock symbol, for logging/reporting
        short_window: Period for the short-term MA (default 50)
        long_window:  Period for the long-term MA (default 200)

    Returns:
        StrategyResult with the current signal and MA values.

    Raises:
        ValueError: if there isn't enough data to compute the long MA.
    """
    close = df["Close"].squeeze()  # handle MultiIndex columns from yfinance

    if len(close) < long_window + 1:
        raise ValueError(
            f"Not enough data for {ticker}: need at least {long_window + 1} rows, "
            f"got {len(close)}"
        )

    ma_short = close.rolling(window=short_window).mean()
    ma_long = close.rolling(window=long_window).mean()

    # Current and previous values (drop NaN tails)
    valid_idx = ma_long.dropna().index
    if len(valid_idx) < 2:
        raise ValueError(f"Not enough non-NaN MA values for {ticker}")

    curr_short = float(ma_short.loc[valid_idx[-1]])
    curr_long = float(ma_long.loc[valid_idx[-1]])
    prev_short = float(ma_short.loc[valid_idx[-2]])
    prev_long = float(ma_long.loc[valid_idx[-2]])
    current_price = float(close.iloc[-1])

    # Detect crossover
    prev_above = prev_short > prev_long
    curr_above = curr_short > curr_long

    if not prev_above and curr_above:
        signal = Signal.BUY      # Golden Cross
    elif prev_above and not curr_above:
        signal = Signal.SELL     # Death Cross
    else:
        signal = Signal.HOLD

    result = StrategyResult(
        ticker=ticker,
        signal=signal,
        short_ma=curr_short,
        long_ma=curr_long,
        prev_short_ma=prev_short,
        prev_long_ma=prev_long,
        current_price=current_price,
    )

    logger.info(
        "[%s] Price=%.2f  MA%d=%.2f  MA%d=%.2f  → %s",
        ticker,
        current_price,
        short_window,
        curr_short,
        long_window,
        curr_long,
        signal.value,
    )
    return result
