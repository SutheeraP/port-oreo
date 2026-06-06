# Port-Oreo

A personal DCA portfolio tracker with AI-powered transaction capture and portfolio analysis, built for someone new to the stock market who wants a clean, data-driven way to follow their investments over time.

## About

I started investing with a simple Dollar-Cost Averaging (DCA) strategy — making small, recurring purchases across a handful of stocks and ETFs. This tool helps me track everything in one place: how much I've put in (in both USD and Thai Baht), what it's worth now, and how my portfolio is performing relative to the broader market.

## Features


- **Performance charts**
  - **Value** — portfolio value vs. cumulative deposits over time
  - **TWR** (Time-Weighted Return) — your return vs. S&P 500 and Nasdaq benchmarks
  - **MWR** (Money-Weighted Return / IRR) — annualized return accounting for the timing of your deposits
- **Sector & allocation charts** — donut charts showing how capital is distributed across sectors
- **Holdings dashboard** — per-ticker view of shares held
- **Transactions page** — full history of all purchases
- **AI Insights page** — auto-generated HTML report with portfolio summary
- **Stock split handling** — split ratios are fetched and applied automatically
- **Live price refresh** — fetches current prices from Yahoo Finance on demand
- **Dual-currency tracking** — purchase costs tracked in both USD and THB

## Tech Stack

| Tool | Purpose |
|---|---|
| [Streamlit](https://streamlit.io) | Web app framework |
| [Pandas](https://pandas.pydata.org) | Data manipulation |
| [NumPy](https://numpy.org) | Numerical computations |
| [Plotly](https://plotly.com/python/) | Interactive charts |
| [yfinance](https://github.com/ranaroussi/yfinance) | Yahoo Finance price & split data |
| [Claude](https://claude.ai/code) (Claude Code) | AI slip parsing & portfolio analysis |
| Python 3 | Language runtime |

## Getting Started

**Prerequisites:** Python 3.8+

```bash
# Install dependencies
pip install streamlit pandas numpy plotly yfinance

# Run the app
make dev
```

The app opens at `http://localhost:8501`.

## How to Use

### Step 1 — Add transactions from receipt images

Drop your broker receipt screenshots (PNG) into `slips/YYYY-MM/` (e.g. `slips/2026-06/`), then run the Claude Code skill:

```
/read-slip
```

It reads each image, extracts the ticker, shares, price, date, and THB amount, deduplicates against existing entries, and appends new transactions to `portfolio.json`.

### Step 2 — Refresh prices

Click the **Refresh Prices** button on the dashboard, or run manually:

```bash
python3 fetch_prices.py
```

This fetches current prices and any new stock splits, then writes `prices.json`.

### Step 3 — View the dashboard

The main dashboard shows:
- **Holdings table** at the top — your current positions with P&L
- **Performance chart** below — switch between Value / TWR / MWR using the buttons, and filter by time scope (7D, MTD, YTD, 1Y, ALL)
- **Allocation charts** at the bottom — sector and per-ticker donut charts

### Step 4 — Browse transactions

Navigate to **Transactions** in the sidebar to see every purchase in a sortable table with total THB invested shown at the top.

### Step 5 — Generate AI Insights

Run the Claude Code skill to generate a full HTML report:

```
/ai-insight
```

Then open the **AI Insights** page in the sidebar to read the report — it includes an overall portfolio summary, per-position breakdown, sector concentration analysis, top winners and underperformers, key risks, and suggested next steps.

## Data Files

**`portfolio.json`** — array of transaction objects:
```json
{
  "ticker": "VOO",
  "shares": "0.0635",
  "price": "554.80",
  "date": "2026-01-08",
  "exchange": "NYSE Arca",
  "thb": "1180.00"
}
```

**`prices.json`** — latest prices and split history:
```json
{
  "fetched_at": "2026-06-06T13:47:00Z",
  "prices": { "VOO": 562.40, "NVDA": 131.50 },
  "split_history": {
    "NVDA": [{ "date": "2024-06-10", "ratio": 10.0 }]
  }
}
```
