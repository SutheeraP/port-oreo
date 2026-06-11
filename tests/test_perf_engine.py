"""Unit tests for pure functions in perf_engine.py."""
import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from perf_engine import _xirr, build_holdings, compute_tax_summary, tx_split_factor


# ── _xirr ─────────────────────────────────────────────────────────────────────

class TestXirr:
    """
    XIRR (Extended Internal Rate of Return) answers: given these cash flows on these exact
    dates, what annual growth rate explains them? Unlike regular IRR, XIRR works when
    investments happen at irregular intervals.

    cf   = cash flows: negative = money you paid out (invested), positive = money you received.
    dt   = dates: one datetime.date per cash flow entry, matching position-for-position with cf.
    1e-4 = 0.0001 — floating-point math can't produce a perfect answer, so tests accept any
           error smaller than 0.0001 (a tenth of a percent) as "close enough".
    
    Assert Pattern: abs(actual - expected) < tolerance
    """

    def test_zero_return(self):
        """Buy and sell at same price → IRR ≈ 0."""
        cf = [-1000.0, 1000.0]
        dt = [date(2024, 1, 1), date(2025, 1, 1)]
        assert abs(_xirr(cf, dt)) < 1e-4

    def test_known_positive_rate(self):
        """
        Double money in exactly one year (non-leap) → IRR ≈ 100%.
        abs(result - 1.0) < 1e-4 means: result ≈ 1.0, i.e. 100% annual return. 
        """
        cf = [-1000.0, 2000.0]
        dt = [date(2023, 1, 1), date(2024, 1, 1)]  # 365 days
        assert abs(_xirr(cf, dt) - 1.0) < 1e-4

    def test_known_negative_rate(self):
        """
        Lose half in exactly one year (non-leap) → IRR ≈ -50%.
        abs(result - (-0.5)) < 1e-4 means: result ≈ -0.5, i.e. -50% annual return.
        """
        cf = [-1000.0, 500.0]
        dt = [date(2023, 1, 1), date(2024, 1, 1)]  # 365 days
        assert abs(_xirr(cf, dt) - (-0.5)) < 1e-4

    def test_multiple_cashflows(self):
        """
        Two deposits and a terminal value should converge without error.
        Sanity check: -1 = lower bound (can't lose more than everything invested)
        """
        cf = [-500.0, -500.0, 1200.0]
        dt = [date(2024, 1, 1), date(2024, 7, 1), date(2025, 1, 1)]
        result = _xirr(cf, dt)
        assert isinstance(result, float)
        assert -1.0 < result < 10.0

    def test_fewer_than_two_cashflows_returns_zero(self):
        """Edge case: single cashflow → 0.0 (no rate to compute)."""
        assert _xirr([-1000.0], [date(2024, 1, 1)]) == 0.0

    def test_empty_cashflows_returns_zero(self):
        assert _xirr([], []) == 0.0


# ── compute_tax_summary ───────────────────────────────────────────────────────

class TestComputeTaxSummary:
    """
    PnL (Profit and Loss) = total proceeds from selling minus what those shares cost you.
    FIFO (First In, First Out) = when selling, the oldest shares you bought are matched first.
    """

    def test_no_sells_zero_realized_pnl(self):
        # Three buys, no sells → nothing realized yet; invested total = 3500 + 2100 + 2800
        portfolio = [
            {"ticker": "AAPL", "type": "buy", "shares": "10", "price": "100.00", "date": "2024-01-01", "thb": "3500.00"},
            {"ticker": "AAPL", "type": "buy", "shares": "5",  "price": "120.00", "date": "2024-03-01", "thb": "2100.00"},
            {"ticker": "MSFT", "type": "buy", "shares": "2",  "price": "200.00", "date": "2024-02-01", "thb": "2800.00"},
        ]
        result = compute_tax_summary(portfolio)
        assert result["realized_pnl_thb"] == 0.0
        assert result["total_proceeds_thb"] == 0.0
        assert result["total_invested_thb"] == pytest.approx(3500.0 + 2100.0 + 2800.0)

    def test_full_exit_positive_pnl(self):
        # Buy 10 shares, cost = ฿3500 total. Sell all 10 later for ฿5250 total.
        # Gain = ฿5250 - ฿3500 = ฿1750
        portfolio = [
            {"ticker": "AAPL", "type": "buy",  "shares": "10", "price": "100.00", "date": "2024-01-01", "thb": "3500.00"},
            {"ticker": "AAPL", "type": "sell", "shares": "10", "price": "150.00", "date": "2024-06-01", "thb": "5250.00"},
        ]
        result = compute_tax_summary(portfolio)
        assert result["total_proceeds_thb"] == pytest.approx(5250.0)
        assert result["realized_pnl_thb"] == pytest.approx(5250.0 - 3500.0)

    def test_partial_fifo_sell(self):
        # Buy 10 shares for ฿3500 total (฿350 each in THB).
        # Sell 4 shares → FIFO cost = 4 × ฿350 = ฿1400; proceeds = ฿2100; gain = ฿700
        portfolio = [
            {"ticker": "AAPL", "type": "buy",  "shares": "10", "price": "100.00", "date": "2024-01-01", "thb": "3500.00"},
            {"ticker": "AAPL", "type": "sell", "shares": "4",  "price": "150.00", "date": "2024-06-01", "thb": "2100.00"},
        ]
        result = compute_tax_summary(portfolio)
        assert result["total_proceeds_thb"] == pytest.approx(2100.0)
        assert result["realized_pnl_thb"] == pytest.approx(2100.0 - 1400.0)

    def test_multi_lot_fifo_ordering(self):
        """Sell 12 shares across two lots (10 @ ฿100 + 5 @ ฿200). FIFO: first lot fully consumed."""
        portfolio = [
            {"ticker": "X", "type": "buy",  "shares": "10", "price": "100", "date": "2024-01-01", "thb": "1000"},
            {"ticker": "X", "type": "buy",  "shares": "5",  "price": "200", "date": "2024-02-01", "thb": "500"},
            {"ticker": "X", "type": "sell", "shares": "12", "price": "300", "date": "2024-12-01", "thb": "3600"},
        ]
        result = compute_tax_summary(portfolio)
        # Cost of 12 shares FIFO: 10 * (1000/10) + 2 * (500/5) = 1000 + 200 = 1200
        expected_cost = 1000 + 200
        assert result["realized_pnl_thb"] == pytest.approx(3600.0 - expected_cost)


# ── tx_split_factor ───────────────────────────────────────────────────────────

class TestTxSplitFactor:
    def test_no_splits_returns_one(self):
        assert tx_split_factor("2024-01-01", []) == 1.0

    def test_split_after_tx_applies_ratio(self):
        """Split on 2024-06-01 affects shares bought 2024-01-01."""
        history = [{"date": "2024-06-01", "ratio": 2.0}]
        assert tx_split_factor("2024-01-01", history) == 2.0

    def test_split_on_exact_same_date_ignored(self):
        history = [{"date": "2024-06-01", "ratio": 3.0}]
        assert tx_split_factor("2024-06-01", history) == 1.0

    def test_multiple_splits_compound(self):
        """Two splits after tx: 2x then 3x → factor = 6."""
        history = [
            {"date": "2024-06-01", "ratio": 2.0},
            {"date": "2025-01-01", "ratio": 3.0},
        ]
        assert tx_split_factor("2024-01-01", history) == pytest.approx(6.0)

    def test_only_future_splits_compound(self):
        """One past split (ignored) and one future split (applied)."""
        history = [
            {"date": "2023-01-01", "ratio": 4.0},
            {"date": "2025-01-01", "ratio": 2.0},
        ]
        assert tx_split_factor("2024-01-01", history) == pytest.approx(2.0)


# ── build_holdings ────────────────────────────────────────────────────────────

class TestBuildHoldings:
    def test_basic_pnl(self):
        """Two AAPL lots + one MSFT → correct shares, cost, value, P&L."""
        portfolio = [
            {"ticker": "AAPL", "type": "buy", "shares": "10", "price": "100.00", "date": "2024-01-01", "thb": "3500.00"},
            {"ticker": "AAPL", "type": "buy", "shares": "5",  "price": "120.00", "date": "2024-03-01", "thb": "2100.00"},
            {"ticker": "MSFT", "type": "buy", "shares": "2",  "price": "200.00", "date": "2024-02-01", "thb": "2800.00"},
        ]
        prices = {"AAPL": 130.0, "MSFT": 250.0}
        df = build_holdings(portfolio, prices, {}, {})

        aapl = df[df["Ticker"] == "AAPL"].iloc[0]
        assert aapl["Shares"] == pytest.approx(15.0)       # 10 + 5
        assert aapl["Cost"]   == pytest.approx(1600.0)     # 10*100 + 5*120 = 1600 usd
        assert aapl["Value"]  == pytest.approx(1950.0)     # 15*130 = 1950 usd
        assert aapl["P&L $"]  == pytest.approx(350.0)      # 1950 - 1600

    def test_sell_reduces_shares_fifo(self):
        """Selling 4 shares leaves 6 remaining with correct FIFO cost."""
        portfolio = [
            {"ticker": "AAPL", "type": "buy",  "shares": "10", "price": "100.00", "date": "2024-01-01", "thb": "3500.00"},
            {"ticker": "AAPL", "type": "sell", "shares": "4",  "price": "150.00", "date": "2024-06-01", "thb": "2100.00"},
        ]
        prices = {"AAPL": 130.0}
        df = build_holdings(portfolio, prices, {}, {})

        aapl = df[df["Ticker"] == "AAPL"].iloc[0]
        assert aapl["Shares"] == pytest.approx(6.0)    # 10 - 4
        assert aapl["Cost"]   == pytest.approx(600.0)  # 6 remaining * 100 FIFO cost

    def test_fully_sold_position_excluded(self):
        """Ticker with zero remaining shares must not appear in the result."""
        portfolio = [
            {"ticker": "AAPL", "type": "buy",  "shares": "10", "price": "100.00", "date": "2024-01-01", "thb": "3500.00"},
            {"ticker": "AAPL", "type": "sell", "shares": "10", "price": "150.00", "date": "2024-06-01", "thb": "5250.00"},
        ]
        prices = {"AAPL": 130.0}
        df = build_holdings(portfolio, prices, {}, {})
        assert "AAPL" not in df["Ticker"].values

    def test_split_adjusts_shares(self):
        """A 2-for-1 split doubles the share count for pre-split buys."""
        portfolio = [{"ticker": "AAPL", "type": "buy", "shares": "10", "price": "100", "date": "2024-01-01", "thb": "3500.00"}]
        prices = {"AAPL": 130.0}
        split_history = {"AAPL": [{"date": "2024-06-01", "ratio": 2.0}]}
        df = build_holdings(portfolio, prices, split_history, {})

        aapl = df[df["Ticker"] == "AAPL"].iloc[0]
        assert aapl["Shares"] == pytest.approx(20.0)  # 10 * 2

    def test_sector_assigned(self):
        portfolio = [
            {"ticker": "AAPL", "type": "buy", "shares": "10", "price": "100.00", "date": "2024-01-01", "thb": "3500.00"},
            {"ticker": "MSFT", "type": "buy", "shares": "2",  "price": "200.00", "date": "2024-02-01", "thb": "2800.00"},
        ]
        prices = {"AAPL": 130.0, "MSFT": 250.0}
        sectors = {"AAPL": "Technology", "MSFT": "Technology"}
        df = build_holdings(portfolio, prices, {}, sectors)
        assert (df["Sector"] == "Technology").all()

    def test_sorted_by_value_descending(self):
        portfolio = [
            {"ticker": "AAPL", "type": "buy", "shares": "10", "price": "100.00", "date": "2024-01-01", "thb": "3500.00"},
            {"ticker": "MSFT", "type": "buy", "shares": "2",  "price": "200.00", "date": "2024-02-01", "thb": "2800.00"},
        ]
        prices = {"AAPL": 130.0, "MSFT": 250.0}
        # AAPL value = 10*130 = 1300, MSFT value = 2*250 = 500 → descending: [1300, 500]
        df = build_holdings(portfolio, prices, {}, {})
        values = df["Value"].dropna().tolist()
        assert values == sorted(values, reverse=True)
