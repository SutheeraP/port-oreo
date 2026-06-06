# Portfolio Dashboard — Project Plan

## Goal
A local app that shows a portfolio dashboard with AI analytics at zero extra cost.

## Stack

| Need           | Tool                        | Cost      |
|----------------|-----------------------------|-----------|
| Read slips     | Claude Code (already paying) | $0 extra |
| Store data     | Local JSON files             | $0        |
| Current prices | `yfinance` Python library    | $0        |
| Dashboard      | Streamlit (Python)           | $0        |
| AI analytics   | Claude Code writes to file   | $0 extra  |

---

## Project Structure

```
/portfolio-app
  /slips/          ← drop transaction slip images here
  portfolio.json   ← Claude extracts & stores transactions
  prices.json      ← auto-fetched via yfinance
  insights.md      ← Claude writes AI analysis here
  app.py           ← Streamlit dashboard reads all 3
```

---

## Workflow

1. Drop transaction slip images into `/slips/`
2. Ask Claude Code → reads images → updates `portfolio.json`
3. Python script runs `yfinance` → fetches live prices → `prices.json`
4. Ask Claude Code → analyzes both files → writes `insights.md`
5. Streamlit dashboard displays everything

---

## Key Insight: Free AI Analytics

Instead of calling the Claude API (paid), use Claude Code itself as the analyst:
- Ask Claude Code to analyze `portfolio.json` + `prices.json`
- Claude writes the analysis to `insights.md`
- Dashboard just displays that file — no API calls, no extra cost

---

## Dashboard Features
- Holdings overview (quantity, avg cost, current value)
- Gain/Loss per position (unrealized P&L)
- Portfolio allocation chart
- Current price vs. buy price comparison
- AI insights panel (from `insights.md`)

---

## Notes
- Fully local, no cloud database
- `yfinance` supports stocks, ETFs, and crypto
- Easy to extend with more analytics later
