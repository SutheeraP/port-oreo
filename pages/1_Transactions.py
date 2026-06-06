import json
from pathlib import Path

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Transactions", page_icon="📋", layout="wide")

PORTFOLIO = Path(__file__).parent.parent / "portfolio.json"


@st.cache_data(ttl=300)
def load_transactions() -> pd.DataFrame:
    raw = json.loads(PORTFOLIO.read_text())
    df = pd.DataFrame(raw)
    df["shares"] = df["shares"].astype(float)
    df["price"] = df["price"].astype(float)
    df["thb"] = df["thb"].astype(float)
    df["total_usd"] = df["shares"] * df["price"]
    df["date"] = pd.to_datetime(df["date"]).dt.date
    df = df.sort_values("date", ascending=False).reset_index(drop=True)
    return df.rename(columns={
        "date": "Date",
        "ticker": "Ticker",
        "shares": "Shares",
        "price": "Price (USD)",
        "thb": "THB",
        "total_usd": "Total (USD)",
        "exchange": "Exchange",
    })[["Date", "Ticker",  "Shares", "Price (USD)", "THB", "Total (USD)", "Exchange"]]


st.subheader("Transactions")

df = load_transactions()

col1, col2 = st.columns(2)
col1.metric("Total Transactions", len(df), border=True)
col2.metric("Total Invested (THB)", f"${df['THB'].sum():,.2f}", border=True)

styled = (
    df.style
    .map(lambda _: "color: #45556e", subset=["Exchange"])
    .map(lambda _: "color: #00d4a0", subset=["Total (USD)"])
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
