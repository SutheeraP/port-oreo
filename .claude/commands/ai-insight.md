---
description: Analyze portfolio.json + prices.json and write comprehensive analysis to insights.html
---

Analyze the user's portfolio and write a fresh `insights.html`.

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

3. Use the computed numbers to write `insights.html` with **today's date** in the title. Use this HTML structure as your template — fill in all placeholder values with real computed data:

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Portfolio Insights — {DATE}</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: #0f172a; color: #e2e8f0; padding: 2rem; line-height: 1.6; }
  h1 { font-size: 1.6rem; color: #38bdf8; margin-bottom: 0.25rem; }
  .date { color: #64748b; font-size: 0.85rem; margin-bottom: 2rem; }
  h2 { font-size: 0.75rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.08em; color: #64748b; margin-bottom: 1rem; }
  .card { background: #1e293b; border-radius: 12px; padding: 1.5rem; margin-bottom: 1.5rem; border: 1px solid #334155; }
  .summary-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 1rem; }
  .stat { background: #0f172a; border-radius: 8px; padding: 1rem; text-align: center; }
  .stat-label { font-size: 0.7rem; color: #64748b; text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 0.4rem; }
  .stat-value { font-size: 1.4rem; font-weight: 700; color: #f1f5f9; }
  .stat-value.pos { color: #4ade80; }
  .stat-value.neg { color: #f87171; }
  table { width: 100%; border-collapse: collapse; font-size: 0.88rem; }
  th { color: #64748b; text-align: left; padding: 0.5rem 0.75rem; border-bottom: 1px solid #334155; font-weight: 500; font-size: 0.75rem; text-transform: uppercase; }
  td { padding: 0.6rem 0.75rem; border-bottom: 1px solid #1e293b; }
  tr:last-child td { border-bottom: none; }
  .ticker { font-weight: 700; color: #38bdf8; }
  .pos { color: #4ade80; font-weight: 600; }
  .neg { color: #f87171; font-weight: 600; }
  .sector-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 0.75rem; }
  .sector-card { background: #0f172a; border-radius: 8px; padding: 0.9rem 1rem; border-left: 3px solid #334155; }
  .sector-card.risk { border-left-color: #f59e0b; }
  .sector-name { font-size: 0.8rem; font-weight: 600; color: #94a3b8; margin-bottom: 0.25rem; }
  .sector-alloc { font-size: 1.2rem; font-weight: 700; color: #f1f5f9; }
  .sector-tickers { font-size: 0.72rem; color: #64748b; margin-top: 0.2rem; }
  .risk-badge { display: inline-block; background: #78350f; color: #fbbf24; padding: 1px 7px; border-radius: 4px; font-size: 0.65rem; font-weight: 700; text-transform: uppercase; margin-left: 6px; }
  .commentary { font-size: 0.9rem; color: #cbd5e1; line-height: 1.7; }
  .winner-block, .loser-block { margin-bottom: 1rem; padding-bottom: 1rem; border-bottom: 1px solid #334155; }
  .winner-block:last-child, .loser-block:last-child { border-bottom: none; margin-bottom: 0; padding-bottom: 0; }
  .position-label { font-weight: 700; color: #38bdf8; margin-bottom: 0.3rem; }
  ul { padding-left: 1.2rem; }
  ul li { color: #cbd5e1; font-size: 0.9rem; margin-bottom: 0.4rem; }
  .steps ol { padding-left: 1.2rem; }
  .steps ol li { color: #cbd5e1; font-size: 0.9rem; margin-bottom: 0.6rem; }
  .footer { font-size: 0.75rem; color: #475569; }
  code { background: #0f172a; color: #38bdf8; padding: 1px 5px; border-radius: 3px; font-family: monospace; }
</style>
</head>
<body>

<h1>Portfolio AI Insights</h1>
<div class="date">{DATE}</div>

<div class="card">
  <h2>Portfolio Summary</h2>
  <div class="summary-grid">
    <div class="stat">
      <div class="stat-label">Positions</div>
      <div class="stat-value">{TOTAL_POSITIONS}</div>
    </div>
    <div class="stat">
      <div class="stat-label">Invested (USD)</div>
      <div class="stat-value">${TOTAL_INVESTED}</div>
    </div>
    <div class="stat">
      <div class="stat-label">Invested (THB)</div>
      <div class="stat-value">&#3647;{TOTAL_THB}</div>
    </div>
    <div class="stat">
      <div class="stat-label">Current Value</div>
      <div class="stat-value">${TOTAL_VALUE}</div>
    </div>
    <div class="stat">
      <div class="stat-label">Overall P&amp;L</div>
      <div class="stat-value {PNL_CLASS}">{PNL_SIGN}${TOTAL_PNL} ({PNL_SIGN}{TOTAL_PNL_PCT}%)</div>
    </div>
  </div>
</div>

<div class="card">
  <h2>Positions</h2>
  <table>
    <thead>
      <tr>
        <th>Ticker</th><th>Shares</th><th>Avg Cost</th><th>Price</th>
        <th>Invested</th><th>Value</th><th>P&amp;L (USD)</th><th>P&amp;L %</th><th>Alloc %</th>
      </tr>
    </thead>
    <tbody>
      {POSITIONS_ROWS}
    </tbody>
  </table>
</div>

<div class="card">
  <h2>Sector Breakdown</h2>
  <div class="sector-grid">
    {SECTOR_CARDS}
  </div>
</div>

<div class="card">
  <h2>Winners &amp; Underperformers</h2>
  <div class="commentary">
    {WINNERS_AND_UNDERPERFORMERS}
  </div>
</div>

<div class="card">
  <h2>Key Risks</h2>
  <ul>
    {KEY_RISKS}
  </ul>
</div>

<div class="card steps">
  <h2>Suggested Next Steps</h2>
  <ol>
    {NEXT_STEPS}
  </ol>
</div>

<div class="card">
  <div class="footer">
    Prices fetched: {FETCHED_AT} &nbsp;&middot;&nbsp; To refresh: run <code>python3 fetch_prices.py</code> then <code>/ai-insight</code>
  </div>
</div>

</body>
</html>
```

**Filling in placeholders:**

- `{DATE}` — today's date (e.g. "June 6, 2026")
- `{TOTAL_POSITIONS}` — count of tickers
- `{TOTAL_INVESTED}`, `{TOTAL_VALUE}`, `{TOTAL_THB}`, `{TOTAL_PNL}`, `{TOTAL_PNL_PCT}` — computed totals
- `{PNL_CLASS}` — `pos` if total P&L > 0, else `neg`
- `{PNL_SIGN}` — `+` if positive, empty string if negative (the number carries its own `-`)
- `{POSITIONS_ROWS}` — one `<tr>` per position: apply `class="pos"` to P&L cells for gains, `class="neg"` for losses; `class="ticker"` on ticker cell; prefix P&L values with `+` for gains
- `{SECTOR_CARDS}` — one `.sector-card` div per group; add `class="sector-card risk"` and `<span class="risk-badge">Concentration Risk</span>` if group allocation > 50%; sector tickers: Broad ETFs (VOO, VGT), Tech (DDOG, GOOGL, MSFT), Defense/GovTech (KTOS, AXON), Healthcare (UNH)
- `{WINNERS_AND_UNDERPERFORMERS}` — `.winner-block` / `.loser-block` divs with `.position-label` header and 2–3 sentence commentary
- `{KEY_RISKS}` — 3 `<li>` items
- `{NEXT_STEPS}` — 3–5 `<li>` items with concrete actions
- `{FETCHED_AT}` — timestamp from prices.json

4. Write the complete HTML to `insights.html`, overwriting any previous version.
