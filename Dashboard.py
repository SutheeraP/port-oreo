import json
import numpy as np
from datetime import date as date_type, datetime, timedelta, timezone
from pathlib import Path
from perf_engine import (
    build_master_history,
    build_holdings,
    compute_scoped_irr,
    compute_tax_summary,
    tx_split_factor,
)

import fetch_prices
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="Portfolio", page_icon="📈", layout="wide")

PORTFOLIO = Path("portfolio.json")
PRICES    = Path("prices.json")

TICKER_PALETTE = ["#00d4a0", "#ff6b35", "#7c3aed", "#3b82f6", "#f59e0b", "#ec4899", "#06b6d4", "#84cc16"]


PORTFOLIO_SAMPLE = Path("portfolio.sample.json")

@st.cache_data(ttl=300)
def load_data():
    portfolio_path = PORTFOLIO if PORTFOLIO.exists() else PORTFOLIO_SAMPLE
    if not PRICES.exists():
        fetch_prices.main()
    portfolio  = json.loads(portfolio_path.read_text())
    prices_raw = json.loads(PRICES.read_text())
    return portfolio, prices_raw


# ── load ──────────────────────────────────────────────────────────────────────
portfolio_data, prices_raw = load_data()
prices        = prices_raw["prices"]
split_history = prices_raw.get("split_history", {})
sectors       = prices_raw.get("sectors", {})
fetched_at    = prices_raw.get("fetched_at", "")
df            = build_holdings(portfolio_data, prices, split_history, sectors)

total_cost    = df["Cost"].sum()
total_value   = df["Value"].dropna().sum()
total_pnl     = total_value - total_cost
total_pnl_pct = total_pnl / total_cost * 100 if total_cost else 0
best_row      = df[df["P&L %"].notna()].sort_values("P&L %", ascending=False).iloc[0]
tax_summary   = compute_tax_summary(portfolio_data)

try:
    time_str = datetime.fromisoformat(fetched_at).astimezone(timezone.utc).strftime("%I:%M %p UTC")
except Exception:
    time_str = fetched_at

n_prices = sum(1 for v in prices.values() if v is not None)

# ── header ────────────────────────────────────────────────────────────────────
h_col, b_col = st.columns([6, 1])
h_col.header("Portfolio Dashboard")
st.caption(f"● {n_prices} prices loaded · {time_str}")

with b_col:
    if st.button("↻ Refresh", width="stretch"):
        with st.spinner("Fetching…"):
            try:
                fetch_prices.main()
                st.cache_data.clear()
                st.rerun()
            except Exception as e:
                st.error(str(e))

# ── metrics ───────────────────────────────────────────────────────────────────
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Total Value", f"${total_value:,.2f}", border=True, height="stretch")
c2.metric("Invested",    f"${total_cost:,.2f}", border=True, height="stretch")
c3.metric("Total P&L",  f"${total_pnl:+,.2f}", f"{total_pnl_pct:+.2f}%", border=True, height="stretch")
c4.metric("Positions",  len(df), f"best: {best_row['Ticker']} {best_row['P&L %']:+.1f}%", border=True, height="stretch")
st.metric("Tax P&L (THB)", f"฿{tax_summary['realized_pnl_thb']:+,.2f}",
          f"realized · {tax_summary['total_proceeds_thb']:,.0f} proceeds", border=True, height="stretch")

st.divider()

# ── performance chart ─────────────────────────────────────────────────────────
hist = build_master_history(json.dumps(portfolio_data), json.dumps(prices_raw))
mdf  = hist["df"]

scope = st.session_state.get("perf_scope", "ALL") or "ALL"

perf_head, mode_col = st.columns([9, 3])
perf_head.subheader("Performance")

with mode_col:
    view_mode = st.segmented_control(
        "view_mode",
        ["Value", "TWR", "MWR"],
        default="TWR",
        selection_mode="single",
        label_visibility="collapsed",
        key="perf_view",
        width="stretch"
    )
view_mode = view_mode or "TWR"

today_d = date_type.today()
if scope == "7D":
    scope_start = today_d - timedelta(days=7)
elif scope == "MTD":
    scope_start = today_d - timedelta(days=31)
elif scope == "YTD":
    scope_start = today_d.replace(month=1, day=1)
elif scope == "1Y":
    try:
        scope_start = today_d.replace(year=today_d.year - 1)
    except ValueError:
        scope_start = today_d - timedelta(days=365)
else:
    scope_start = mdf.index[0].date()

idx0      = int(mdf.index.searchsorted(pd.Timestamp(scope_start)))
idx0      = max(0, min(idx0, len(mdf) - 1))
df_scoped = mdf.iloc[idx0:]

_CHART_BASE = dict(
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#8b949e"), height=300,
    margin=dict(t=10, b=30, l=0, r=0),
    xaxis=dict(showgrid=False, zeroline=False, tickfont=dict(color="#8b949e", size=11)),
    legend=dict(orientation="h", x=0, y=1.12, font=dict(color="#abb2b9", size=12),
                bgcolor="rgba(0,0,0,0)"),
    hovermode="x unified",
)

if view_mode == "Value":
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df_scoped.index, y=df_scoped["portfolio_value"],
        mode="lines", name="Portfolio Value",
        line=dict(color="#00d4a0", width=2.5),
        hovertemplate="$%{y:,.2f}<extra>Portfolio Value</extra>",
    ))
    fig.add_trace(go.Scatter(
        x=df_scoped.index, y=df_scoped["cum_deposits"],
        mode="lines", name="Cumulative Deposits",
        line=dict(color="#3b82f6", width=1.5, dash="dash"),
        hovertemplate="$%{y:,.2f}<extra>Cumulative Deposits</extra>",
    ))
    fig.update_layout(
        **_CHART_BASE,
        yaxis=dict(showgrid=True, gridcolor="#1f2937", zeroline=False,
                   tickfont=dict(color="#8b949e", size=11),
                   tickprefix="$", tickformat=",.2f"),
    )
    st.plotly_chart(fig, use_container_width=True)

elif view_mode == "TWR":
    twr_base = 1.0 + float(mdf["twr"].iloc[idx0])
    twr_pct  = ((1.0 + df_scoped["twr"].values) / twr_base - 1.0) * 100.0

    sp_base  = float(mdf["sp500"].iloc[idx0])
    nq_base  = float(mdf["nasdaq"].iloc[idx0])
    sp_pct   = (df_scoped["sp500"].values  / sp_base - 1.0) * 100.0 if sp_base else np.zeros(len(df_scoped))
    nq_pct   = (df_scoped["nasdaq"].values / nq_base - 1.0) * 100.0 if nq_base else np.zeros(len(df_scoped))

    fig = go.Figure()
    fig.add_hline(y=0, line=dict(color="#374151", width=1, dash="dot"))
    fig.add_trace(go.Scatter(
        x=df_scoped.index, y=twr_pct,
        mode="lines", name="Portfolio TWR",
        line=dict(color="#00d4a0", width=2.5),
        hovertemplate="%{y:,.2f}%<extra>Portfolio TWR</extra>",
    ))
    fig.add_trace(go.Scatter(
        x=df_scoped.index, y=sp_pct,
        mode="lines", name="S&P 500 ✦",
        line=dict(color="#3b82f6", width=1.5, dash="dot"),
        hovertemplate="%{y:,.2f}%<extra>S&P 500</extra>",
    ))
    fig.add_trace(go.Scatter(
        x=df_scoped.index, y=nq_pct,
        mode="lines", name="Nasdaq ✦",
        line=dict(color="#f59e0b", width=1.5, dash="dot"),
        hovertemplate="%{y:,.2f}%<extra>Nasdaq</extra>",
    ))
    fig.update_layout(
        **_CHART_BASE,
        yaxis=dict(showgrid=True, gridcolor="#1f2937", zeroline=False,
                   tickfont=dict(color="#8b949e", size=11),
                   ticksuffix="%", tickformat=".1f"),
    )
    st.plotly_chart(fig, use_container_width=True)

else:  # MWR
    if scope == "ALL":
        irr_scoped = hist["irr"]
    else:
        irr_scoped = compute_scoped_irr(mdf, idx0, portfolio_data, today_d)

    holding_days   = (today_d - mdf.index[idx0].date()).days
    total_invested = float(df_scoped["deposits"].sum())
    current_value  = float(mdf["portfolio_value"].iloc[-1])

    _, metric_col, _ = st.columns([1, 3, 1])
    with metric_col:
        st.metric("Annualized IRR (MWR)", f"{irr_scoped * 100:+.1f}%")
        if holding_days < 30:
            st.caption("Short holding period — annualized rate may appear large")
        st.markdown("<br>", unsafe_allow_html=True)
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Invested", f"${total_invested:,.2f}")
        m2.metric("Current Value",  f"${current_value:,.2f}")
        m3.metric("Holding Period", f"{holding_days}d")

_, scope_center, _ = st.columns([1, 1, 1])
with scope_center:
    st.segmented_control(
        "scope",
        ["7D", "MTD", "YTD", "1Y", "ALL"],
        default="ALL",
        selection_mode="single",
        label_visibility="collapsed",
        key="perf_scope",
        width="stretch"
    )

st.divider()

# ── main layout ───────────────────────────────────────────────────────────────
left, right = st.columns([1, 1], gap="large")


st.subheader("Holdings")
st.markdown("<style>.stDataFrame * { font-size: 14px !important; }</style>", unsafe_allow_html=True)

display_cols = ["Ticker", "Sector", "Shares", "Avg Cost", "Price", "Value", "P&L $", "P&L %"]

def _color_pnl(val):
    if isinstance(val, (int, float)) and val > 0:
        return "color: #00d4a0"
    if isinstance(val, (int, float)) and val < 0:
        return "color: #ff4560"
    return ""

styled = (
    df[display_cols].style
    .format({
        "Avg Cost": "${:,.2f}",
        "Price":    "${:,.2f}",
        "Value":    "${:,.2f}",
        "P&L $":    "${:+,.2f}",
        "P&L %":    "{:+.2f}%",
    }, na_rep="—")
    .map(_color_pnl, subset=["P&L $", "P&L %"])
)
st.dataframe(styled,  width="stretch", hide_index=True)

with left:
    st.subheader("Allocation")
    alloc_df = df[df["Value"].notna()].copy()
    total_v  = alloc_df["Value"].sum()
    colors   = [TICKER_PALETTE[i % len(TICKER_PALETTE)] for i in range(len(alloc_df))]

    fig_pie = go.Figure(go.Pie(
        labels=[f"{t}  {v/total_v*100:.1f}%" for t, v in zip(alloc_df["Ticker"], alloc_df["Value"])],
        values=alloc_df["Value"],
        hole=0.55,
        marker=dict(colors=colors, line=dict(color="#161b27", width=2)),
        textinfo="none",
        hovertemplate="<b>%{label}</b><br>$%{value:,.2f}<br>%{percent}<extra></extra>",
    ))
    fig_pie.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#8b949e", size=14),
        height=280, margin=dict(t=2, b=0, l=0, r=0),
        legend=dict(orientation="h", x=0, y=-0.05, font=dict(color="#abb2b9",size=14)),
    )
    st.plotly_chart(fig_pie, use_container_width=True)

with right:
    st.subheader("Sector Exposure")
    sector_vals: dict = {}
    for _, row in alloc_df.iterrows():
        s = sectors.get(row["Ticker"], "Other")
        sector_vals[s] = sector_vals.get(s, 0) + row["Value"]

    s_total  = sum(sector_vals.values())
    s_sorted = sorted(sector_vals.items(), key=lambda x: -x[1])
    s_labels = [f"{name}  {val/s_total*100:.1f}%" for name, val in s_sorted]
    s_values = [val for _, val in s_sorted]
    s_colors = [TICKER_PALETTE[i % len(TICKER_PALETTE)] for i in range(len(s_sorted))]

    fig_sector = go.Figure(go.Pie(
        labels=s_labels,
        values=s_values,
        hole=0.55,
        marker=dict(colors=s_colors, line=dict(color="#161b27", width=2)),
        textinfo="none",
        hovertemplate="<b>%{label}</b><br>$%{value:,.2f}<br>%{percent}<extra></extra>",
    ))
    fig_sector.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#8b949e", size=14),
        height=280, margin=dict(t=2, b=0, l=0, r=0),
        legend=dict(orientation="h", x=0, y=-0.05, font=dict(color="#abb2b9", size=14)),
    )
    st.plotly_chart(fig_sector, use_container_width=True)


