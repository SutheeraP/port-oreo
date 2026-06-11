"""Unit tests for pure functions in fetch_prices.py."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fetch_prices import get_tickers


class TestGetTickers:
    def test_deduplicates_tickers(self):
        portfolio = [
            {"ticker": "AAPL", "shares": "1", "price": "100", "date": "2024-01-01"},
            {"ticker": "AAPL", "shares": "2", "price": "110", "date": "2024-02-01"},
            {"ticker": "MSFT", "shares": "1", "price": "200", "date": "2024-01-01"},
        ]
        result = get_tickers(portfolio)
        assert result == ["AAPL", "MSFT"]

    def test_returns_sorted(self):
        portfolio = [
            {"ticker": "ZZZ", "shares": "1", "price": "100", "date": "2024-01-01"},
            {"ticker": "AAA", "shares": "1", "price": "100", "date": "2024-01-01"},
            {"ticker": "MMM", "shares": "1", "price": "100", "date": "2024-01-01"},
        ]
        result = get_tickers(portfolio)
        assert result == sorted(result)

    def test_single_ticker(self):
        portfolio = [{"ticker": "VOO", "shares": "1", "price": "600", "date": "2024-01-01"}]
        assert get_tickers(portfolio) == ["VOO"]

    def test_empty_portfolio(self):
        assert get_tickers([]) == []
