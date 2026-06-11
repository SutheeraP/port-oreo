---
description: Analyze portfolio.json + prices.json and write comprehensive analysis to insights.html
---

Analyze the user's portfolio and write a fresh `insights.html`.

## Steps

1. Read `portfolio.json` and `prices.json`.

2. Use WebSearch to gather current context for each active holding and the broader market. Run these searches:
   - `"S&P 500 performance YTD 2026"` — benchmark comparison
   - `"US market macro outlook 2026"` — Current Situation context
   - For each active ticker in the portfolio: `"{TICKER} stock news earnings 2026"` — one search per ticker

3. Run this Python script via Bash to compute accurate position metrics:

```python
import json
from collections import defaultdict

portfolio = json.load(open('portfolio.json'))
prices_data = json.load(open('prices.json'))
prices = prices_data['prices']
split_history = prices_data.get('split_history', {})

def tx_split_factor(tx_date, history):
    factor = 1.0
    for s in history:
        if s['date'] > tx_date:
            factor *= s['ratio']
    return factor

positions = defaultdict(lambda: {'shares': 0.0, 'usd_invested': 0.0, 'thb_invested': 0.0, 'dates': []})

for t in portfolio:
    ticker = t['ticker']
    shares = float(t['shares'])
    sf = tx_split_factor(t['date'], split_history.get(ticker, []))
    positions[ticker]['shares'] += shares * sf
    positions[ticker]['usd_invested'] += shares * float(t['price'])
    positions[ticker]['thb_invested'] += float(t['thb'])
    positions[ticker]['dates'].append(t['date'])

results = []
for ticker, pos in positions.items():
    adj_shares = pos['shares']
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

4. Use the computed numbers and web search results to write `insights.html` with **today's date** in the title. Use this HTML structure as your template — fill in all placeholder values with real, substantive analysis:

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Portfolio Insights — {DATE}</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; color: #e2e8f0; padding: 2rem; line-height: 1.6; }
  h1 { font-size: 1.6rem; color: #38bdf8; margin-bottom: 0.25rem; }
  .date { color: #64748b; font-size: 0.85rem; margin-bottom: 2rem; }
  h2 { font-size: 0.75rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.08em; color: #64748b; margin-bottom: 1rem; }
  .card { background: #1e293b; border-radius: 12px; padding: 1.5rem; margin-bottom: 1.5rem; border: 1px solid #334155; }
  .commentary { font-size: 0.9rem; color: #cbd5e1; line-height: 1.7; }
  .commentary p { margin-bottom: 0.6rem; }
  .commentary p:last-child { margin-bottom: 0; }
  .stock-block { margin-bottom: 1.2rem; padding-bottom: 1.2rem; border-bottom: 1px solid #334155; }
  .stock-block:last-child { border-bottom: none; margin-bottom: 0; padding-bottom: 0; }
  .position-label { font-weight: 700; color: #38bdf8; font-size: 1rem; margin-bottom: 0.5rem; }
  .pos { color: #4ade80; font-weight: 600; }
  .neg { color: #f87171; font-weight: 600; }
  ul { padding-left: 1.2rem; }
  ul li { color: #cbd5e1; font-size: 0.9rem; margin-bottom: 0.4rem; line-height: 1.6; }
  .steps ol { padding-left: 1.2rem; }
  .steps ol li { color: #cbd5e1; font-size: 0.9rem; margin-bottom: 0.6rem; line-height: 1.6; }
  .snapshot-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 0.75rem; }
  .snapshot-item { background: #0f172a; border-radius: 8px; padding: 0.9rem 1rem; }
  .snapshot-label { font-size: 0.7rem; color: #64748b; text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 0.3rem; }
  .snapshot-value { font-size: 0.9rem; color: #f1f5f9; line-height: 1.5; }
  .footer { font-size: 0.75rem; color: #475569; }
  code { background: #0f172a; color: #38bdf8; padding: 1px 5px; border-radius: 3px; font-family: monospace; }
</style>
</head>
<body>

<h1>Portfolio AI Insights</h1>
<div class="date">{DATE}</div>

<div class="card">
  <h2>Current Situation</h2>
  <div class="commentary">
    {CURRENT_SITUATION}
  </div>
</div>

<div class="card">
  <h2>Individual Stock Deep Dive</h2>
  {STOCK_BLOCKS}
</div>

<div class="card steps">
  <h2>Action Items</h2>
  <ol>
    {ACTION_ITEMS}
  </ol>
</div>

<div class="card">
  <h2>Portfolio Snapshot</h2>
  <div class="snapshot-grid">
    <div class="snapshot-item">
      <div class="snapshot-label">vs Benchmark</div>
      <div class="snapshot-value">{PORTFOLIO_VS_BENCHMARK}</div>
    </div>
    <div class="snapshot-item">
      <div class="snapshot-label">Top Performers</div>
      <div class="snapshot-value">{TOP_PERFORMERS}</div>
    </div>
    <div class="snapshot-item">
      <div class="snapshot-label">Laggards</div>
      <div class="snapshot-value">{WORST_PERFORMERS}</div>
    </div>
    <div class="snapshot-item">
      <div class="snapshot-label">Concentration Risk</div>
      <div class="snapshot-value">{CONCENTRATION_NOTE}</div>
    </div>
  </div>
</div>

</body>
</html>
```

**Filling in placeholders:**

- `{DATE}` — today's date (e.g. "June 10, 2026")
- `{FETCHED_AT}` — timestamp from prices.json

- `{CURRENT_SITUATION}` — 3–5 sentences of prose covering: what is happening in the broader market or macro environment right now that is relevant to these holdings. Mention any notable sector trends, economic events, Fed policy, geopolitical factors, or earnings season context. Draw on web search results.

- `{STOCK_BLOCKS}` — one `.stock-block` div per active holding, sorted by P&L % descending. Each block:
```html
<div class="stock-block">
  <div class="position-label">TICKER &nbsp;<span class="pos|neg">+X.X% · $X,XXX</span></div>
  <ul>
    <li><strong>Earnings:</strong> [recent results or next expected date and what to watch for]</li>
    <li><strong>Price action:</strong> [is it near a key level, breaking out, consolidating, or breaking down?]</li>
    <li><strong>News / sentiment:</strong> [any analyst upgrades/downgrades, notable news, sentiment shift]</li>
    <li><strong>Thesis intact?</strong> [yes/no/watch — brief reason]</li>
    <li><strong>Red flags:</strong> [any concerns, or "None at this time"]</li>
  </ul>
</div>
```
Use `class="pos"` on the span for positive P&L, `class="neg"` for negative. Prefix positive P&L with `+`.

- `{ACTION_ITEMS}` — 3–5 `<li>` items with concrete, specific actions: which ticker, what to do, and why. Flag urgency where relevant (e.g. "Before next earnings on X date…").

- `{PORTFOLIO_VS_BENCHMARK}` — one-line comparison, e.g. "Portfolio +12.3% vs S&P 500 +8.1% YTD — outperforming by ~4.2 pp"
- `{TOP_PERFORMERS}` — inline list of top 2–3 winners with their P&L %, e.g. "UNH +43.2%, VGT +19.7%"
- `{WORST_PERFORMERS}` — inline list of bottom 2–3 laggards with their P&L %, e.g. "KTOS −32.2%, MSFT −0.1%"
- `{CONCENTRATION_NOTE}` — one sentence flagging any sector or single-name concentration worth noting, e.g. "Tech exposure (VGT + GOOGL + MSFT + DDOG) is ~65% of portfolio"

5. Write the complete HTML to `insights.html`, overwriting any previous version.
