"""
fetch_fx.py — fetch historical THB/USD exchange rate via Yahoo Finance.

Used to fill fx_rate for USD-funded transactions where no THB appears on
the slip. Uses USDTHB=X (Yahoo Finance) as a close approximation to the
Bank of Thailand TT reference rate.
"""
import pandas as pd
import yfinance as yf
from datetime import date, timedelta


def get_thb_usd_rate(transaction_date: str) -> float:
    """Return THB per 1 USD on the given date, falling back to nearest prior trading day."""
    d = date.fromisoformat(transaction_date)
    start = d - timedelta(days=7)
    end = d + timedelta(days=2)
    raw = yf.download("USDTHB=X", start=start, end=end, progress=False, auto_adjust=True)
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = raw.columns.droplevel(1)
    if raw.empty:
        raise ValueError(f"No FX rate available for {transaction_date}")
    target = pd.Timestamp(d)
    available = raw.index[raw.index <= target]
    if available.empty:
        available = raw.index
    return round(float(raw["Close"].loc[available[-1]]), 4)
