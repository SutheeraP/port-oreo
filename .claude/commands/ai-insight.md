---
description: Analyze portfolio.json + prices.json and write comprehensive analysis to insights.html
---

Analyze the user's portfolio and write a fresh `insights.html`.

## Steps

1. Read `portfolio.json` and `prices.json`.

2. Use WebSearch to gather current context for each active holding and the broader market. Run these searches:
   - `"S&P 500 performance YTD 2026"` — benchmark comparison
   - `"US market macro outlook 2026"` — market context
   - For each active ticker in the portfolio: `"{TICKER} stock news earnings 2026"` — one search per ticker (also gather each ticker's next confirmed/expected earnings date)

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

4. Read `.claude/commands/ai-insight-template.html`. It's the static page shell — copy it as-is and only fill in the placeholders described below (each appears once in the shell, wrapped in `{CURLY_BRACES}`). Do not change the CSS or the surrounding markup.

**Simple placeholders (header):**

- `{DATE}` — today's date, e.g. `July 14, 2026` (used in both `<title>` and the subdate line)
- `{FETCHED_AT_TIME}` — time portion of `fetched_at` from prices.json, e.g. `14:51 UTC`
- `{TOTAL_PNL_PCT}` — e.g. `+13.2%` (prefix `+` if positive)
- `{BENCHMARK_YTD_PCT}` — S&P 500 YTD return from web search, e.g. `+9.8%`
- `{PERF_PILL_CLASS}` — empty string if `total_pnl_pct` is positive, `neg` if negative (controls the pill's red/green styling)

**`{STAT_CARDS}`** — exactly 4 `.stat-card` divs, in this order:
1. Top performer — best `pnl_pct` position
2. Biggest laggard — worst `pnl_pct` position (skip only if every position is positive; in that case use the smallest gainer instead)
3. A concentration stat — e.g. combined weight of the largest holding(s) or asset class (ETFs vs single stocks)
4. A thematic exposure stat — e.g. sector/theme weight (tech, healthcare, etc.) derived from what the holdings actually are

Each card:
```html
<div class="stat-card">
  <div class="stat-label">Top performer</div>
  <div class="stat-value" style="color:var(--success)">UNH +48.6%</div>
  <div class="stat-sub">reports in 2 days</div>
</div>
```
Use `style="color:var(--success)"` for positive values and `style="color:var(--destructive)"` for negative ones on cards 1–2; cards 3–4 have no color override. `.stat-sub` is one short clause of context (earnings timing, cost basis, what makes up the weight, etc.).

**Market context:**
- `{MARKET_CONTEXT_SUMMARY}` — one line naming the dominant market narrative right now, e.g. `Market context — narrow AI-led rally, thin risk premium`
- `{MARKET_CONTEXT_BODY}` — 2–3 `<p>` tags of macro prose (Fed policy, sector trends, earnings-season context, anything from web search relevant to these specific holdings)

**`{TIMELINE_ITEMS}`** — one `.tl-item` per holding that has a known or estimated next earnings date, sorted chronologically (soonest first):
```html
<div class="tl-item">
  <div class="tl-dot"></div>
  <div class="tl-date">Jul 28</div>
  <div class="tl-ticker">GOOGL</div>
</div>
```
If a date falls on today ({DATE}), add `today` to the item's class (`<div class="tl-item today">`) — this is the signature red marker. Omit ETFs/positions with no single earnings print unless they have a notable related event.

**`{HOLDINGS}`** — one `.holding` block per active position, sorted by `pnl_pct` descending:
```html
<div class="holding">
  <details>
    <summary class="holding-row">
      <div><div class="ticker">UNH</div><div class="cost-basis">$54</div></div>
      <div class="ret pos">▲ 48.6%</div>
      <div class="badge yes">Thesis intact</div>
      <div class="next-earn">Reports <strong>Jul 16</strong></div>
      <span class="chev">▶</span>
    </summary>
    <div class="holding-detail">
      <div class="detail-block"><h4>Earnings</h4><p>...</p></div>
      <div class="detail-block"><h4>Price action</h4><p>...</p></div>
      <div class="detail-block"><h4>News / sentiment</h4><p>...</p></div>
      <div class="detail-block flag"><h4>Red flags</h4><p>...</p></div>
    </div>
  </details>
</div>
```
- `cost-basis` is the rounded `avg_cost`, e.g. `$54`
- `.ret` uses class `pos` + `▲` for positive `pnl_pct`, `neg` + `▼` for negative
- `.badge` reflects overall thesis status: `yes` = "Thesis intact", `watch` = "Watch" (mixed signals, upcoming catalyst risk, early/small position), `no` = "Thesis broken" (use sparingly, only for a clear deterioration)
- `.next-earn` shows the next confirmed/estimated earnings date (`Reports <strong>{date}</strong>`), or `No date set` / `Tracks index` / `Tracks holdings` for ETFs
- The 4 `detail-block`s are always Earnings, Price action, News / sentiment, Red flags in that order — 1–2 sentences each, grounded in the web search results and the computed P&L numbers. Give the "Red flags" block `class="detail-block flag"`; write "None at this time" if there's genuinely nothing to flag.

**`{ACTION_ITEMS}`** — 3–5 items, ordered by urgency/soonest catalyst first:
```html
<div class="action-item urgent">
  <div class="action-num">1</div>
  <div class="action-text"><strong>UNH reports Jul 16</strong> — hold through the print; Street wants $4.85 EPS after FY26 guidance was raised to >$18.25 EPS.</div>
</div>
```
Add `urgent` to `action-item`'s class only for items tied to a catalyst within the next ~7 days; leave it off otherwise. Number `.action-num` sequentially starting at 1. Each `.action-text` names the ticker in `<strong>`, states a concrete action, and gives the reason.

5. Write the complete HTML to `insights.html`, overwriting any previous version.
