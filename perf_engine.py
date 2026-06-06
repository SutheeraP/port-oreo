"""
perf_engine.py — portfolio performance calculation engine.

Public API used by Dashboard.py:
    build_master_history(portfolio_json_str, prices_json_str) -> dict
    compute_scoped_irr(mdf, idx0, portfolio_data, today_d) -> float
    get_historical_prices(...)
    get_historical_index_prices(...)
"""
import json
from datetime import date as date_type, datetime, timedelta

import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf



def _xirr(cashflows: list, dates: list) -> float:
    """Newton-Raphson XIRR. cashflows: negative=outflow, positive=inflow."""
    try:
        if len(cashflows) < 2:
            return 0.0
        base = dates[0]

        def npv(r: float) -> float:
            return sum(cf / (1.0 + r) ** ((d - base).days / 365.0)
                       for cf, d in zip(cashflows, dates))

        def d_npv(r: float) -> float:
            return sum(
                -((d - base).days / 365.0) * cf / (1.0 + r) ** ((d - base).days / 365.0 + 1.0)
                for cf, d in zip(cashflows, dates)
            )

        r = 0.1
        for _ in range(100):
            f  = npv(r)
            df = d_npv(r)
            if abs(df) < 1e-12:
                break
            r_new = r - f / df
            if abs(r_new - r) < 1e-8:
                return r_new
            r = max(-0.9999, r_new)
        return r
    except Exception:
        return 0.0


# ── public price fetchers (swap bodies for real API calls) ────────────────────

def get_historical_prices(
    ticker: str,
    start_date: date_type,
    end_date: date_type,
    portfolio_data: list,
    prices: dict,
    split_history: dict,
) -> pd.DataFrame:
    raw = yf.download(ticker, start=start_date,
                      end=end_date + timedelta(days=1),
                      auto_adjust=True, progress=False)
    if isinstance(raw.columns, pd.MultiIndex):
        raw = raw.droplevel(level=1, axis=1)
    return raw[["Close"]].rename(columns={"Close": "close"})


def get_historical_index_prices(
    start_date: date_type,
    end_date: date_type,
) -> tuple:
    sp_raw = yf.download("^GSPC", start=start_date,
                          end=end_date + timedelta(days=1),
                          auto_adjust=True, progress=False)
    nq_raw = yf.download("^IXIC", start=start_date,
                          end=end_date + timedelta(days=1),
                          auto_adjust=True, progress=False)
    for df in (sp_raw, nq_raw):
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.droplevel(1)
    sp = sp_raw["Close"].squeeze().rename("sp500")
    nq = nq_raw["Close"].squeeze().rename("nasdaq")
    return sp, nq


# ── public computation functions ──────────────────────────────────────────────

@st.cache_data(ttl=300)
def build_master_history(portfolio_json_str: str, prices_json_str: str) -> dict:
    """Returns {"df": pd.DataFrame, "irr": float}. DataFrame indexed by daily Timestamps."""
    pdata = json.loads(portfolio_json_str)
    praw  = json.loads(prices_json_str)
    p     = praw["prices"]
    sh    = praw.get("split_history", {})
    today = date_type.today()

    tx_dates = [datetime.strptime(tx["date"], "%Y-%m-%d").date() for tx in pdata]
    start    = min(tx_dates)
    full_idx = pd.date_range(pd.Timestamp(start), pd.Timestamp(today), freq="D")

    ticker_dfs = {t: get_historical_prices(t, start, today, pdata, p, sh) for t in p}

    # Shares held per ticker — always post-split units (consistent with price series)
    portfolio_value = pd.Series(0.0, index=full_idx, dtype=float)
    for ticker, price_df in ticker_dfs.items():
        splits_t    = sh.get(ticker, [])
        ticker_txs  = [tx for tx in pdata if tx["ticker"] == ticker]
        shares_held = np.zeros(len(full_idx))
        for tx in ticker_txs:
            tx_pos    = full_idx.searchsorted(pd.Timestamp(tx["date"]))
            sf        = 1.0
            for s in splits_t:
                if s["date"] > tx["date"]:
                    sf *= s["ratio"]
            shares_held[tx_pos:] += float(tx["shares"]) * sf
        portfolio_value += shares_held * price_df["close"].reindex(full_idx, method="ffill").values

    # Daily deposits and cumulative sum
    deposits = pd.Series(0.0, index=full_idx, dtype=float)
    for tx in pdata:
        deposits[pd.Timestamp(tx["date"])] += float(tx["shares"]) * float(tx["price"])
    cum_deposits = deposits.cumsum()

    # Time-Weighted Return via Modified-Dietz sub-period chaining
    pv  = portfolio_value.values
    dep = deposits.values
    twr = np.zeros(len(full_idx))
    for i in range(1, len(full_idx)):
        denom  = pv[i - 1] + dep[i]
        twr[i] = (1.0 + twr[i - 1]) * (pv[i] / denom) - 1.0 if denom > 0 else twr[i - 1]

    sp500_s, nasdaq_s = get_historical_index_prices(start, today)

    master_df = pd.DataFrame({
        "portfolio_value": portfolio_value,
        "deposits":        deposits,
        "cum_deposits":    cum_deposits,
        "twr":             pd.Series(twr, index=full_idx),
        "sp500":           sp500_s.reindex(full_idx, method="ffill"),
        "nasdaq":          nasdaq_s.reindex(full_idx, method="ffill"),
    }, index=full_idx)

    # Full-history IRR (used by MWR mode when scope == ALL)
    sorted_txs = sorted(pdata, key=lambda x: x["date"])
    irr_cf = [-float(tx["shares"]) * float(tx["price"]) for tx in sorted_txs]
    irr_dt = [datetime.strptime(tx["date"], "%Y-%m-%d").date() for tx in sorted_txs]
    irr_cf.append(float(pv[-1]))
    irr_dt.append(today)

    return {"df": master_df, "irr": _xirr(irr_cf, irr_dt)}


def compute_scoped_irr(
    mdf: pd.DataFrame,
    idx0: int,
    portfolio_data: list,
    today_d: date_type,
) -> float:
    """
    XIRR for a scoped window: treats the portfolio value at idx0 as the
    initial outflow, then adds subsequent deposits, then the terminal value.
    """
    pv_at_start      = float(mdf["portfolio_value"].iloc[idx0])
    scope_start_date = mdf.index[idx0].date()
    mwr_cf, mwr_dt   = [], []

    if pv_at_start > 0:
        mwr_cf.append(-pv_at_start)
        mwr_dt.append(scope_start_date)

    for tx in portfolio_data:
        tx_dt = datetime.strptime(tx["date"], "%Y-%m-%d").date()
        if tx_dt >= scope_start_date:
            mwr_cf.append(-float(tx["shares"]) * float(tx["price"]))
            mwr_dt.append(tx_dt)

    mwr_cf.append(float(mdf["portfolio_value"].iloc[-1]))
    mwr_dt.append(today_d)
    return _xirr(mwr_cf, mwr_dt)
