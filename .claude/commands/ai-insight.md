---
description: Analyze portfolio.json + prices.json and write comprehensive analysis to insights.md
---

Analyze the user's portfolio and write a fresh `insights.md`.

## Steps

1. Read `portfolio.json` and `prices.json`.

2. Run this Python script via Bash to compute accurate position metrics:

```python
import json
from collections import defaultdict

portfolio = json.load(open('portfolio.json'))
prices_data = json.load(open('prices.json'))
prices = prices_data['prices']
splits = prices_data['split_factors']

positions = defaultdict(lambda: {'shares': 0.0, 'usd_invested': 0.0, 'thb_invested': 0.0, 'dates': []})

for t in portfolio:
    ticker = t['ticker']
    shares = float(t['shares'])
    price = float(t['price'])
    thb = float(t['thb'])
    positions[ticker]['shares'] += shares
    positions[ticker]['usd_invested'] += shares * price
    positions[ticker]['thb_invested'] += thb
    positions[ticker]['dates'].append(t['date'])

results = []
for ticker, pos in positions.items():
    split = splits.get(ticker, 1.0)
    adj_shares = pos['shares'] * split
    current_price = prices[ticker]
    current_value = adj_shares * current_price
    usd_invested = pos['usd_invested']
    pnl = current_value - usd_invested
    pnl_pct = (pnl / usd_invested) * 100
    avg_cost = usd_invested / adj_shares
    results.append({
        'ticker': ticker,
        'adj_shares': round(adj_shares, 4),
        'avg_cost': round(avg_cost, 2),
        'current_price': current_price,
        'usd_invested': round(usd_invested, 2),
        'thb_invested': round(pos['thb_invested'], 2),
        'current_value': round(current_value, 2),
        'pnl': round(pnl, 2),
        'pnl_pct': round(pnl_pct, 1),
        'first_buy': min(pos['dates']),
        'last_buy': max(pos['dates']),
    })

total_invested = sum(r['usd_invested'] for r in results)
total_value = sum(r['current_value'] for r in results)
total_thb = sum(r['thb_invested'] for r in results)
total_pnl = total_value - total_invested
total_pnl_pct = (total_pnl / total_invested) * 100

for r in results:
    r['allocation'] = round(r['current_value'] / total_value * 100, 1)

results.sort(key=lambda x: x['pnl_pct'], reverse=True)

print(json.dumps({
    'positions': results,
    'total_invested': round(total_invested, 2),
    'total_value': round(total_value, 2),
    'total_thb': round(total_thb, 2),
    'total_pnl': round(total_pnl, 2),
    'total_pnl_pct': round(total_pnl_pct, 1),
    'fetched_at': prices_data['fetched_at'],
}, indent=2))
```

3. Use the computed numbers to write `insights.md` with **today's date** at the top and these sections:

   **a. Portfolio Summary** — a table with: total positions, total USD invested, total THB invested, current value, overall P&L (USD and %).

   **b. Positions** — a markdown table with one row per ticker, sorted by P&L %:
   `Ticker | Shares | Avg Cost | Current Price | Invested (USD) | Value (USD) | P&L (USD) | P&L % | Allocation %`

   **c. Sector Breakdown** — group tickers into these categories and show total allocation per group:
   - Broad ETFs: VOO, VGT
   - Tech: DDOG, GOOGL, MSFT
   - Defense / GovTech: KTOS, AXON
   - Healthcare: UNH
   
   Flag any group exceeding 50% of the portfolio as a concentration risk.

   **d. Winners & Underperformers** — brief commentary (2–3 sentences each) on the top 2 gainers and any positions with negative P&L. Comment on whether the thesis still holds or if action is warranted.

   **e. Key Risks** — bullet list of the top 3 risks visible in the current data (e.g. sector concentration, individual position drawdowns, macro factors relevant to held sectors).

   **f. Suggested Next Steps** — 3–5 concrete, data-driven action items (e.g. "KTOS is down X% — set a stop-loss or decide on a thesis review date by [date]").

   **g. Footer** — include `prices fetched_at` timestamp and a one-liner on how to refresh.

4. Write the complete analysis to `insights.md`, overwriting any previous version.