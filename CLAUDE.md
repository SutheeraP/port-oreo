# Portfolio Dashboard

Streamlit-based personal stock portfolio tracker.

## Key files
- `dashboard.py` — main Streamlit app
- `portfolio.json` — holdings and transactions
- `prices.json` — cached price history
- `perf_engine.py` — IRR and performance calculations
- `fetch_prices.py` — price data fetcher
- `insights.html` — AI-generated analysis output

## Run
```
make dev
```

## Skills
- `/read-slip` — parse transaction slip images into `portfolio.json`
- `/ai-insight` — generate analysis into `insights.html`
