---
description: Analyze portfolio.json + prices.json and write comprehensive analysis to insights.html
---

Analyze the user's portfolio and write a fresh `insights.html`.

**Tone**: every piece of prose (market context, holding details, DCA reasons, action items) is simple, beginner-friendly Thai for a novice DCA investor — short sentences, no dense analyst jargon. Briefly explain any unavoidable English financial term on first use, e.g. "IRR (ผลตอบแทนเฉลี่ยต่อปี)". Tickers, company names, numbers, and dates stay as-is.

## Steps

1. Read `portfolio.json` and `prices.json`.

2. Use WebSearch for context:
   - `"S&P 500 performance YTD 2026"` — benchmark comparison
   - `"US market macro outlook 2026"` — market context
   - `"{TICKER} stock news earnings 2026"` for each active ticker — also gather its next confirmed/expected earnings date

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
    'cash_reserve_estimate': round(total_invested * 0.20, 2),
    'fetched_at': prices_data['fetched_at'],
}, indent=2))
```

`cash_reserve_estimate` is a working assumption (the user keeps roughly 20% of invested capital as standby cash) — there's no real cash field in the data, so treat it as a number to reason with, not a tracked balance. Only positions with `adj_shares > 0` are active; a fully-exited ticker (e.g. one sold down to zero) must never appear in `{HOLDINGS}`, `{TIMELINE_ITEMS}`, or `{DCA_PLAN}`.

4. Read `.claude/commands/ai-insight-template.html` and copy it as-is, filling only the `{PLACEHOLDER}` tokens. **The template has an HTML comment next to every placeholder showing its exact markup pattern and mechanical rules (sorting, class names, thresholds) — follow those precisely, then delete all instructional comments from your output**, so none of them leak into `insights.html`. The content judgment below goes beyond what those comments cover:

- **Stat cards, market context, holdings** — ground everything in the actual computed numbers and the web search results for these specific holdings; avoid generic commentary.
- **`{DCA_PLAN}`** — the part that most needs care:
  - This is a rebalancing-aware read of where the portfolio sits *today* (via each position's `allocation`), not a fixed monthly split. ETF weight staying near ~50% of the whole portfolio is the anchor; no single business theme should quietly become an oversized bet.
  - **Judge real concentration yourself — don't take `prices.json`'s `sectors` field literally.** It's a rough label (e.g. GOOGL is tagged "Communication Services") and trusting it mechanically produces silly conclusions — GOOGL is very much an AI/tech-exposed business and belongs in the same mental bucket as VGT/MSFT/RBRK. Reason about what each holding actually *is and does*, like an informed investor would.
  - Tickers with a strong, still-underweight thesis get a larger share of this round's money. Tickers that are already a large position, or sit in a theme the portfolio is already heavy in, get a smaller share — not a hard cap, just diminishing benefit from concentrating further. A weakening/broken thesis gets little, but not zero — staying consistent is the point of DCA.
  - **Writing `.dca-stock-reason` is the highest-value part of this whole skill.** Write like a thoughtful long-term investor explaining a decision to themselves: is this ticker's own thesis intact or weakening, is the price attractive relative to cost, is there a near-term reason to lean in or hold back. Never write a formulaic "สัดส่วนตอนนี้ X% เพดาน Y%" line — if concentration genuinely drives the call for a specific ticker, say so once in plain investing language, not as a formula repeated everywhere. If a position is simply fine and unremarkable, say that briefly instead of inventing an angle.
- **`{CASH_RESERVE_NOTE}`** — state the estimate (`cash_reserve_estimate`, ~20% of invested) and give a plain verdict on whether current conditions (market context + specific holdings) make now a good "จังหวะ" to deploy some of it beyond the regular DCA amount, or whether to just hold it and stay the course.

5. Write the complete HTML to `insights.html`, overwriting any previous version.
