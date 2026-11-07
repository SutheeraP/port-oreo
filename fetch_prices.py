#!/usr/bin/env python3
"""Fetch current prices for all tickers in portfolio.json and save to prices.json."""
import json
import warnings
from datetime import datetime, timedelta, timezone
from pathlib import Path

warnings.filterwarnings("ignore")
import pandas as pd
import yfinance as yf

PORTFOLIO = Path("portfolio.json")
PORTFOLIO_SAMPLE = Path("portfolio.sample.json")
PRICES_OUT = Path("prices.json")
MAX_PRICE_AGE_MINUTES = 15


def get_tickers(portfolio: list) -> list:
    return sorted({tx["ticker"] for tx in portfolio})


def is_stale(prices_data, tickers: list, max_age_minutes: int = MAX_PRICE_AGE_MINUTES, now=None) -> bool:
    """True if prices are missing, too old, or don't cover every ticker."""
    if not prices_data:
        return True
    prices = prices_data.get("prices", {})
    if any(prices.get(ticker) is None for ticker in tickers):
        return True
    now = now or datetime.now(timezone.utc)
    try:
        age = now - datetime.fromisoformat(prices_data["fetched_at"])
    except (KeyError, TypeError, ValueError):
        return True
    return age > timedelta(minutes=max_age_minutes)


def read_prices():
    """Return the saved prices file, or None if it's missing or unreadable."""
    try:
        return json.loads(PRICES_OUT.read_text())
    except (OSError, ValueError):
        return None


def fetch_price(ticker: str):
    tk = yf.Ticker(ticker)
    try:
        price = tk.fast_info.get("last_price") or tk.fast_info.get("previous_close")
        if price:
            return round(float(price), 4)
    except Exception:
        pass
    try:
        hist = tk.history(period="5d")
        if not hist.empty:
            return round(float(hist["Close"].dropna().iloc[-1]), 4)
    except Exception:
        pass
    return None


def fetch_sector(ticker: str) -> str:
    try:
        info = yf.Ticker(ticker).info
        if info.get("quoteType") == "ETF":
            return "ETF"
        sector = info.get("sector", "")
        return sector if sector else "Other"
    except Exception:
        return "Other"


def fetch_split_history(ticker: str, since: str) -> list:
    """List of {date, ratio} for each split on or after the first purchase date."""
    tk = yf.Ticker(ticker)
    try:
        splits = tk.splits
        if splits.empty:
            return []
        since_dt = pd.Timestamp(since, tz="UTC")
        relevant = splits[splits.index >= since_dt]
        return [
            {"date": idx.strftime("%Y-%m-%d"), "ratio": float(ratio)}
            for idx, ratio in relevant.items()
        ]
    except Exception:
        return []


def main(portfolio=None):
    """Fetch and save prices. A failed fetch never replaces good saved data."""
    if portfolio is None:
        portfolio_path = PORTFOLIO if PORTFOLIO.exists() else PORTFOLIO_SAMPLE
        portfolio = json.loads(portfolio_path.read_text())
    tickers = get_tickers(portfolio)
    previous = read_prices() or {}
    previous_prices = previous.get("prices", {})
    previous_splits = previous.get("split_history", {})
    previous_sectors = previous.get("sectors", {})

    earliest = {}
    for tx in portfolio:
        t, d = tx["ticker"], tx["date"]
        if t not in earliest or d < earliest[t]:
            earliest[t] = d

    print(f"Fetching prices for: {', '.join(tickers)}")
    prices = {}
    for ticker in tickers:
        price = fetch_price(ticker)
        prices[ticker] = price
        status = f"${price}" if price else "FAILED"
        print(f"  {ticker}: {status}")

    if previous_prices and not any(prices.values()):
        print("\nNo prices fetched. Keeping the saved prices.")
        return

    # Keep the last known price for any ticker that failed this time.
    for ticker in tickers:
        if prices[ticker] is None:
            prices[ticker] = previous_prices.get(ticker)

    print("Fetching split history...")
    split_history = {}
    for ticker in tickers:
        history = fetch_split_history(ticker, earliest.get(ticker, "2000-01-01"))
        # Splits never disappear, so an empty result here means the fetch failed.
        split_history[ticker] = history or previous_splits.get(ticker, [])
        if history:
            print(f"  {ticker}: {len(history)} split(s) — " + ", ".join(f"{s['date']} {s['ratio']}x" for s in history))

    print("Fetching sectors...")
    sectors = {}
    for ticker in tickers:
        sector = fetch_sector(ticker)
        if sector == "Other":
            sector = previous_sectors.get(ticker, sector)
        sectors[ticker] = sector
        print(f"  {ticker}: {sector}")

    output = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "prices": prices,
        "split_history": split_history,
        "sectors": sectors,
    }
    PRICES_OUT.write_text(json.dumps(output, indent=2))
    print(f"\nSaved to {PRICES_OUT}")


if __name__ == "__main__":
    main()
