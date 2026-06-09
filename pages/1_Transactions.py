import json
from pathlib import Path

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Transactions", page_icon="📋", layout="wide")

_ROOT = Path(__file__).parent.parent
PORTFOLIO = _ROOT / "portfolio.json"
PORTFOLIO_SAMPLE = _ROOT / "portfolio.sample.json"


@st.cache_data(ttl=300)
def load_transactions() -> pd.DataFrame:
    portfolio_path = PORTFOLIO if PORTFOLIO.exists() else PORTFOLIO_SAMPLE
    raw = json.loads(portfolio_path.read_text())
    df = pd.DataFrame(raw)
    df["type"] = df.get("type", pd.Series(["buy"] * len(df))).fillna("buy")
    df["shares"] = df["shares"].astype(float)
    df["price"] = df["price"].astype(float)
    df["thb"] = df["thb"].astype(float)
    df["total_usd"] = df["shares"] * df["price"]
    df["date"] = pd.to_datetime(df["date"]).dt.date
    df = df.sort_values("date", ascending=False).reset_index(drop=True)
    return df.rename(columns={
        "date": "Date",
        "ticker": "Ticker",
        "type": "Type",
        "shares": "Shares",
        "price": "Price (USD)",
        "thb": "THB",
        "total_usd": "Total (USD)",
        "exchange": "Exchange",
    })[["Date", "Ticker", "Type", "Shares", "Price (USD)", "THB", "Total (USD)", "Exchange"]]


st.subheader("Transactions")

df = load_transactions()

total_bought = df.loc[df["Type"] == "buy",  "THB"].sum()
total_sold   = df.loc[df["Type"] == "sell", "THB"].sum()
net_invested = total_bought - total_sold

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Transactions", len(df),                  border=True)
c2.metric("Total Bought (THB)", f"฿{total_bought:,.2f}",  border=True)
c3.metric("Total Sold (THB)",   f"฿{total_sold:,.2f}",    border=True)
c4.metric("Net Invested (THB)", f"฿{net_invested:,.2f}",  border=True)

def _color_type(val):
    return "color: #00d4a0" if val == "buy" else "color: #ff4560"

styled = (
    df.style
    .map(lambda _: "color: #45556e", subset=["Exchange"])
    .map(lambda _: "color: #00d4a0", subset=["Total (USD)"])
    .map(_color_type, subset=["Type"])
)

st.dataframe(
    styled,
    use_container_width=True,
    column_config={
        "Date": st.column_config.DateColumn("Date", format="YYYY-MM-DD"),
        "Shares": st.column_config.NumberColumn("Shares", format="%.6f"),
        "Price (USD)": st.column_config.NumberColumn("Price (USD)", format="$%.2f"),
        "THB": st.column_config.NumberColumn("THB (฿)", format="฿%.2f"),
        "Total (USD)": st.column_config.NumberColumn("Total (USD)", format="$%.2f"),
    },
    hide_index=True,
)
