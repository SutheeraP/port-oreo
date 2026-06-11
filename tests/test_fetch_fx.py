"""Unit tests for fetch_fx.get_thb_usd_rate (yfinance calls are mocked)."""
import sys
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from fetch_fx import get_thb_usd_rate


def _make_df(dates: list[str], closes: list[float]) -> pd.DataFrame:
    idx = pd.DatetimeIndex([pd.Timestamp(d) for d in dates])
    return pd.DataFrame({"Close": closes}, index=idx)


class TestGetThbUsdRate:
    def test_returns_rate_for_exact_date(self):
        """When the target date exists in the data, return its closing rate."""
        mock_data = _make_df(["2024-05-10", "2024-05-13"], [35.50, 36.00])
        with patch("fetch_fx.yf.download", return_value=mock_data):
            rate = get_thb_usd_rate("2024-05-13")
        assert rate == pytest.approx(36.00)

    def test_falls_back_to_nearest_prior_trading_day(self):
        """When the exact date is missing (weekend/holiday), use the last available date before it."""
        mock_data = _make_df(["2024-05-10"], [35.50])
        with patch("fetch_fx.yf.download", return_value=mock_data):
            # 2024-05-11 is a Saturday — not in the data
            rate = get_thb_usd_rate("2024-05-11")
        assert rate == pytest.approx(35.50)

    def test_raises_value_error_when_no_data(self):
        """Empty DataFrame → ValueError with the date in the message."""
        empty = pd.DataFrame({"Close": []}, index=pd.DatetimeIndex([]))
        with patch("fetch_fx.yf.download", return_value=empty):
            with pytest.raises(ValueError, match="2024-05-11"):
                get_thb_usd_rate("2024-05-11")

    def test_handles_multiindex_columns(self):
        """yfinance sometimes returns a MultiIndex; the function must flatten it."""
        idx = pd.DatetimeIndex([pd.Timestamp("2024-05-10")])
        mi = pd.MultiIndex.from_tuples([("Close", "USDTHB=X")])
        mock_data = pd.DataFrame([[35.50]], index=idx, columns=mi)
        with patch("fetch_fx.yf.download", return_value=mock_data):
            rate = get_thb_usd_rate("2024-05-10")
        assert rate == pytest.approx(35.50)

    def test_result_is_rounded_to_4_decimals(self):
        mock_data = _make_df(["2024-05-10"], [35.123456789])
        with patch("fetch_fx.yf.download", return_value=mock_data):
            rate = get_thb_usd_rate("2024-05-10")
        assert rate == round(rate, 4)
