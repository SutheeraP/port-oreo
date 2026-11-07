"""Unit tests for pure functions in fetch_prices.py."""
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

import fetch_prices
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


NOW = datetime(2026, 11, 7, 12, 0, tzinfo=timezone.utc)


def saved(minutes_old=0, prices=None):
    return {
        "fetched_at": (NOW - timedelta(minutes=minutes_old)).isoformat(),
        "prices": {"AAPL": 100.0} if prices is None else prices,
    }


class TestIsStale:
    def test_fresh_prices(self):
        assert not fetch_prices.is_stale(saved(5), ["AAPL"], now=NOW)

    def test_old_prices(self):
        assert fetch_prices.is_stale(saved(16), ["AAPL"], now=NOW)

    def test_custom_age_limit(self):
        assert not fetch_prices.is_stale(saved(30), ["AAPL"], 60, now=NOW)

    def test_missing_file(self):
        assert fetch_prices.is_stale(None, ["AAPL"], now=NOW)

    def test_new_ticker_not_covered(self):
        assert fetch_prices.is_stale(saved(1), ["AAPL", "VOO"], now=NOW)

    def test_null_price(self):
        assert fetch_prices.is_stale(saved(1, {"AAPL": None}), ["AAPL"], now=NOW)

    def test_bad_timestamps(self):
        for value in (None, "not a date", "2026-11-07T12:00:00"):
            data = {"fetched_at": value, "prices": {"AAPL": 100.0}}
            assert fetch_prices.is_stale(data, ["AAPL"], now=NOW)


PORTFOLIO = [
    {"ticker": "AAPL", "date": "2025-01-01"},
    {"ticker": "NVDA", "date": "2024-01-01"},
]


@pytest.fixture
def prices_file(tmp_path, monkeypatch):
    path = tmp_path / "prices.json"
    monkeypatch.setattr(fetch_prices, "PRICES_OUT", path)
    monkeypatch.setattr(fetch_prices, "fetch_sector", lambda t: "Other")
    monkeypatch.setattr(fetch_prices, "fetch_split_history", lambda t, since: [])
    return path


class TestMainFailedFetches:
    PREVIOUS = {
        "fetched_at": "2026-11-01T00:00:00+00:00",
        "prices": {"AAPL": 100.0, "NVDA": 200.0},
        "split_history": {"NVDA": [{"date": "2024-06-10", "ratio": 10.0}]},
        "sectors": {"AAPL": "Technology"},
    }

    def test_total_failure_keeps_saved_file(self, prices_file, monkeypatch):
        prices_file.write_text(json.dumps(self.PREVIOUS))
        monkeypatch.setattr(fetch_prices, "fetch_price", lambda t: None)
        fetch_prices.main(PORTFOLIO)
        assert json.loads(prices_file.read_text()) == self.PREVIOUS

    def test_partial_failure_keeps_last_price(self, prices_file, monkeypatch):
        prices_file.write_text(json.dumps(self.PREVIOUS))
        monkeypatch.setattr(fetch_prices, "fetch_price", lambda t: 150.0 if t == "AAPL" else None)
        fetch_prices.main(PORTFOLIO)
        assert json.loads(prices_file.read_text())["prices"] == {"AAPL": 150.0, "NVDA": 200.0}

    def test_failed_split_and_sector_fetch_keeps_saved_values(self, prices_file, monkeypatch):
        prices_file.write_text(json.dumps(self.PREVIOUS))
        monkeypatch.setattr(fetch_prices, "fetch_price", lambda t: 1.0)
        fetch_prices.main(PORTFOLIO)
        result = json.loads(prices_file.read_text())
        assert result["split_history"]["NVDA"] == self.PREVIOUS["split_history"]["NVDA"]
        assert result["sectors"]["AAPL"] == "Technology"

    def test_first_run_failure_saves_nulls(self, prices_file, monkeypatch):
        monkeypatch.setattr(fetch_prices, "fetch_price", lambda t: None)
        fetch_prices.main(PORTFOLIO)
        assert json.loads(prices_file.read_text())["prices"] == {"AAPL": None, "NVDA": None}
