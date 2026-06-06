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

    print("Fetching split history...")
    split_history = {}
    for ticker in tickers:
        history = fetch_split_history(ticker, earliest.get(ticker, "2000-01-01"))
        split_history[ticker] = history
        if history:
            print(f"  {ticker}: {len(history)} split(s) — " + ", ".join(f"{s['date']} {s['ratio']}x" for s in history))

    print("Fetching sectors...")
    sectors = {}
    for ticker in tickers:
        sector = fetch_sector(ticker)
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
