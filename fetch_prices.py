#!/usr/bin/env python3
"""Fetch current prices for all tickers in portfolio.json and save to prices.json."""
import json
import warnings
from datetime import datetime, timezone
from pathlib import Path

warnings.filterwarnings("ignore")
import pandas as pd
import yfinance as yf

PORTFOLIO = Path("portfolio.json")
PRICES_OUT = Path("prices.json")


def get_tickers(portfolio: list) -> list:
    return sorted({tx["ticker"] for tx in portfolio})


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


def fetch_split_factor(ticker: str, since: str) -> float:
    """Cumulative split ratio for all splits on or after the first purchase date."""
    tk = yf.Ticker(ticker)
    try:
        splits = tk.splits
        if splits.empty:
            return 1.0
        since_dt = pd.Timestamp(since, tz="UTC")
        relevant = splits[splits.index >= since_dt]
        factor = 1.0
        for ratio in relevant:
            factor *= ratio
        return round(factor, 6)
    except Exception:
        return 1.0


def main():
    portfolio = json.loads(PORTFOLIO.read_text())
    tickers = get_tickers(portfolio)

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

    print("Fetching split factors...")
    split_factors = {}
    for ticker in tickers:
        sf = fetch_split_factor(ticker, earliest.get(ticker, "2000-01-01"))
        split_factors[ticker] = sf
        if sf != 1.0:
            print(f"  {ticker}: split factor {sf}x")

    output = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "prices": prices,
        "split_factors": split_factors,
    }
    PRICES_OUT.write_text(json.dumps(output, indent=2))
    print(f"\nSaved to {PRICES_OUT}")


if __name__ == "__main__":
    main()
