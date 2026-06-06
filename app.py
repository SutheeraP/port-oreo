import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="Portfolio", page_icon="📈", layout="wide")

PORTFOLIO = Path("portfolio.json")
PRICES    = Path("prices.json")
INSIGHTS  = Path("insights.md")



TICKER_PALETTE = ["#00d4a0", "#ff6b35", "#7c3aed", "#3b82f6", "#f59e0b", "#ec4899", "#06b6d4", "#84cc16"]


@st.cache_data(ttl=300)
def load_data():
    portfolio  = json.loads(PORTFOLIO.read_text())
    prices_raw = json.loads(PRICES.read_text())
    return portfolio, prices_raw


def build_holdings(portfolio, prices):
    rows = {}
    for tx in portfolio:
        t, shares = tx["ticker"], float(tx["shares"])
        if t not in rows:
            rows[t] = {"shares": 0.0, "cost": 0.0}
        rows[t]["shares"] += shares
        rows[t]["cost"]   += shares * float(tx["price"])

    records = []
    for t, r in rows.items():
        cp  = prices.get(t)
        cv  = r["shares"] * cp if cp else None
        avg = r["cost"] / r["shares"] if r["shares"] else 0
        pnl = cv - r["cost"] if cv is not None else None
        pct = pnl / r["cost"] * 100 if pnl is not None and r["cost"] else None
        records.append({
            "Ticker":   t,
            "Sector":   SECTORS.get(t, "Other"),
            "Shares":   round(r["shares"], 4),
            "Avg Cost": round(avg, 2),
            "Price":    cp,
            "Cost":     round(r["cost"], 2),
            "Value":    round(cv, 2) if cv else None,
            "P&L $":    round(pnl, 2) if pnl is not None else None,
            "P&L %":    round(pct, 2) if pct is not None else None,
        })
    return pd.DataFrame(records).sort_values("Value", ascending=False)


# ── load ──────────────────────────────────────────────────────────────────────
portfolio_data, prices_raw = load_data()
prices     = prices_raw["prices"]
fetched_at = prices_raw.get("fetched_at", "")
df         = build_holdings(portfolio_data, prices)

total_cost    = df["Cost"].sum()
total_value   = df["Value"].dropna().sum()
total_pnl     = total_value - total_cost
total_pnl_pct = total_pnl / total_cost * 100 if total_cost else 0
best_row      = df[df["P&L %"].notna()].sort_values("P&L %", ascending=False).iloc[0]

try:
    time_str = datetime.fromisoformat(fetched_at).astimezone(timezone.utc).strftime("%I:%M %p UTC")
except Exception:
    time_str = fetched_at

n_prices = sum(1 for v in prices.values() if v is not None)

# ── header ────────────────────────────────────────────────────────────────────
h_col, s_col, b_col = st.columns([3, 3, 1])
h_col.subheader("Portfolio Dashboard")
s_col.caption(f"● {n_prices} prices loaded · {time_str}")

with b_col:
    if st.button("↻ Refresh", use_container_width=True):
        with st.spinner("Fetching…"):
            result = subprocess.run(["python3", "fetch_prices.py"], capture_output=True, text=True)
        if result.returncode == 0:
            st.cache_data.clear()
            st.rerun()
        else:
            st.error(result.stderr)

# ── metrics ───────────────────────────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Value", f"${total_value:,.2f}")
c2.metric("Invested",    f"${total_cost:,.2f}")
c3.metric("Total P&L",  f"${total_pnl:+,.2f}", f"{total_pnl_pct:+.2f}%")
c4.metric("Positions",  len(df), f"best: {best_row['Ticker']} {best_row['P&L %']:+.1f}%")

st.divider()

# ── main layout ───────────────────────────────────────────────────────────────
left, right = st.columns([3, 2], gap="large")

with left:
    st.subheader("Holdings")

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
    st.dataframe(styled, use_container_width=True, hide_index=True)

with right:
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
        font=dict(color="#8b949e", size=12),
        height=280, margin=dict(t=0, b=0, l=0, r=0),
        legend=dict(orientation="h", x=0, y=-0.05, font=dict(size=11)),
    )
    st.plotly_chart(fig_pie, use_container_width=True)

    st.subheader("Sector Exposure")
    sector_vals: dict = {}
    for _, row in alloc_df.iterrows():
        s = SECTORS.get(row["Ticker"], "Other")
        sector_vals[s] = sector_vals.get(s, 0) + row["Value"]

    s_total  = sum(sector_vals.values())
    s_sorted = sorted(sector_vals.items(), key=lambda x: -x[1])
    s_names  = [x[0] for x in s_sorted]
    s_pcts   = [x[1] / s_total * 100 for x in s_sorted]

    fig_sector = go.Figure(go.Bar(
        x=s_pcts, y=s_names, orientation="h",
        marker_color=[SECTOR_COLORS.get(n, "#8b949e") for n in s_names],
        text=[f"{p:.1f}%" for p in s_pcts],
        textposition="outside",
        textfont=dict(color="#8b949e", size=11),
    ))
    fig_sector.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#8b949e", size=12),
        height=max(140, len(s_names) * 45),
        margin=dict(t=0, b=0, l=0, r=50),
        showlegend=False,
        xaxis=dict(visible=False, range=[0, max(s_pcts) * 1.35]),
        yaxis=dict(tickfont=dict(color="#c9d1d9", size=12), gridcolor="rgba(0,0,0,0)"),
        bargap=0.45,
    )
    st.plotly_chart(fig_sector, use_container_width=True)

# ── AI insights ───────────────────────────────────────────────────────────────
st.divider()
st.subheader("AI Insights")
if INSIGHTS.exists():
    st.markdown(INSIGHTS.read_text())
else:
    st.info("No insights yet. Ask Claude to analyze `portfolio.json` + `prices.json` and write to `insights.md`.")
