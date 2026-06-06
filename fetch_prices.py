#!/usr/bin/env python3
"""Fetch current prices for all tickers in portfolio.json and save to prices.json."""
import json
import warnings
from datetime import datetime, timezone
from pathlib import Path

warnings.filterwarnings("ignore")
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


def main():
    portfolio = json.loads(PORTFOLIO.read_text())
    tickers = get_tickers(portfolio)
    print(f"Fetching prices for: {', '.join(tickers)}")
    prices = {}
    for ticker in tickers:
        price = fetch_price(ticker)
        prices[ticker] = price
        status = f"${price}" if price else "FAILED"
        print(f"  {ticker}: {status}")

    output = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "prices": prices,
    }
    PRICES_OUT.write_text(json.dumps(output, indent=2))
    print(f"\nSaved to {PRICES_OUT}")


if __name__ == "__main__":
    main()
