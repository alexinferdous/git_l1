"""
Wealthsimple Trade API client wrapper.

Uses the unofficial Wealthsimple-API-Python library.
Set WS_PAPER_TRADE=true in .env to run in simulation mode (no real orders placed).

Authentication:
    WS_EMAIL        — your Wealthsimple login email
    WS_PASSWORD     — your Wealthsimple login password
    WS_OTP_SECRET   — base32 TOTP secret from your 2FA setup (optional but required
                      for unattended/scheduled operation)

Rate limit note: Wealthsimple Trade rejects more than ~7 orders per hour.
"""

import logging
import os
from typing import Optional

import pyotp

logger = logging.getLogger(__name__)

# Lazy-import so the bot still runs in paper-trade mode if the library is absent
try:
    import wealthsimple as _ws_lib
    _WS_AVAILABLE = True
except ImportError:
    _WS_AVAILABLE = False
    logger.warning(
        "Wealthsimple-API-Python not installed. Live trading disabled. "
        "Install with: pip install Wealthsimple-API-Python"
    )


class WealthsimpleClient:
    """Thin wrapper around the Wealthsimple Trade API."""

    def __init__(
        self,
        email: str,
        password: str,
        otp_secret: Optional[str] = None,
        paper_trade: bool = False,
    ):
        self.paper_trade = paper_trade
        self._ws = None

        if paper_trade:
            logger.info("Paper-trade mode: no real orders will be placed.")
            return

        if not _WS_AVAILABLE:
            raise RuntimeError(
                "Wealthsimple-API-Python is not installed. "
                "Run: pip install Wealthsimple-API-Python"
            )

        otp_code = pyotp.TOTP(otp_secret).now() if otp_secret else None

        logger.info("Logging in to Wealthsimple Trade as %s …", email)
        if otp_code:
            self._ws = _ws_lib.WS(email, password, otp_secret)
        else:
            # Interactive 2FA prompt — suitable for manual runs
            self._ws = _ws_lib.WSTrade(
                email,
                password,
                two_factor_callback=lambda: input("Enter your 2FA code: "),
            )
        logger.info("Login successful.")

    # ------------------------------------------------------------------
    # Account helpers
    # ------------------------------------------------------------------

    def get_account_id(self) -> str:
        """Return the first non-TFSA/RRSP personal account ID."""
        if self.paper_trade:
            return "PAPER-ACCOUNT"
        accounts = self._ws.get_accounts()
        for acct in accounts.get("results", []):
            if acct.get("account_type") == "ca_non_registered":
                return acct["id"]
        # Fall back to first account
        return accounts["results"][0]["id"]

    def get_positions(self) -> dict:
        """Return current positions keyed by ticker symbol."""
        if self.paper_trade:
            return {}
        account_id = self.get_account_id()
        raw = self._ws.get_positions(account_id)
        positions = {}
        for pos in raw.get("results", []):
            symbol = pos["stock"]["symbol"]
            positions[symbol] = {
                "quantity": float(pos["quantity"]),
                "book_value": float(pos["book_value"]["amount"]),
            }
        return positions

    def get_buying_power(self) -> float:
        """Return available cash (CAD) in the account."""
        if self.paper_trade:
            return 10_000.0  # simulated balance
        account_id = self.get_account_id()
        acct = self._ws.get_account(account_id)
        return float(acct["buying_power"]["amount"])

    # ------------------------------------------------------------------
    # Order placement
    # ------------------------------------------------------------------

    def place_market_buy(self, ticker: str, quantity: int) -> dict:
        """Place a market buy order for `quantity` shares of `ticker`."""
        if quantity <= 0:
            raise ValueError(f"Quantity must be positive, got {quantity}")

        if self.paper_trade:
            logger.info("[PAPER] BUY %d shares of %s", quantity, ticker)
            return {"status": "simulated", "ticker": ticker, "quantity": quantity, "side": "buy"}

        account_id = self.get_account_id()
        order = self._ws.place_order(
            account_id=account_id,
            ticker=ticker,
            quantity=quantity,
            order_type="buy_quantity",
            order_sub_type="market",
        )
        logger.info("BUY order placed: %s", order)
        return order

    def place_market_sell(self, ticker: str, quantity: int) -> dict:
        """Place a market sell order for `quantity` shares of `ticker`."""
        if quantity <= 0:
            raise ValueError(f"Quantity must be positive, got {quantity}")

        if self.paper_trade:
            logger.info("[PAPER] SELL %d shares of %s", quantity, ticker)
            return {"status": "simulated", "ticker": ticker, "quantity": quantity, "side": "sell"}

        account_id = self.get_account_id()
        order = self._ws.place_order(
            account_id=account_id,
            ticker=ticker,
            quantity=quantity,
            order_type="sell_quantity",
            order_sub_type="market",
        )
        logger.info("SELL order placed: %s", order)
        return order
