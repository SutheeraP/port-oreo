from pathlib import Path

import streamlit as st

st.set_page_config(page_title="AI Insights", page_icon="🤖", layout="wide")

INSIGHTS = Path("insights.md")

st.subheader("AI Insights")

if INSIGHTS.exists():
    st.markdown(INSIGHTS.read_text())
else:
    st.info("No insights yet. Ask Claude to analyze `portfolio.json` + `prices.json` and write to `insights.md`.")
