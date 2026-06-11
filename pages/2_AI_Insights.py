from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="AI Insights", page_icon="🤖", layout="wide")

INSIGHTS = Path("insights.html")

st.subheader("AI Insights")

if INSIGHTS.exists():
    components.html(INSIGHTS.read_text(), height=700, scrolling=True)
else:
    st.info("No insights yet. Ask Claude to analyze `portfolio.json` + `prices.json` and write to `insights.html`.")
