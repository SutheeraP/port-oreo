---
description: Read transaction slip images from a slips subfolder and add them to portfolio.json
---

The user wants to import transaction slips from this folder: $ARGUMENTS

Follow these steps exactly:

1. Use Bash to list all PNG files in `slips/$ARGUMENTS/`.
   Command: `ls slips/$ARGUMENTS/*.PNG slips/$ARGUMENTS/*.png 2>/dev/null`

2. For each PNG file, use the Read tool to view the image. Extract these fields:
   - `ticker`: the stock symbol from the header (e.g. "Buy XXXX" or "Sell XXXX")
   - `type`: `"buy"` if the header says "Buy XXXX", `"sell"` if it says "Sell XXXX"
   - `exchange`: the exchange name shown in the badge (e.g. "NYSE Arca", "NASDAQ", "NYSE")
   - `price`: the number from "Executed Price" row (USD, digits and decimal only, no currency symbol)
   - `shares`: the number from "Shares" row (digits and decimal only)
   - `date`: the date from "Completion Date" formatted as YYYY-MM-DD
   - `thb`: determine as follows:
     - If the slip shows a THB amount (e.g. "Stock Amount" row in ฿): use that number (digits and decimal only). Set `thb_source` to `"slip"`.
     - If the slip shows no THB (USD-funded buy — money came from USD account balance): call `fetch_fx.get_thb_usd_rate(date)` to get the BOT-approximate rate, then compute `thb = round(float(shares) * float(price) * rate, 2)`. Set `thb_source` to `"bot_rate"`.
   - `fx_rate`: determine as follows:
     - If `thb_source` is `"slip"`: compute `fx_rate = round(float(thb) / (float(shares) * float(price)), 4)` as a string.
     - If `thb_source` is `"bot_rate"`: use the rate returned by `fetch_fx.get_thb_usd_rate(date)` as a string.
   All values must be strings.

3. Read portfolio.json using the Read tool.

4. Parse the JSON array. For each extracted entry, check if an entry with the same `ticker`, `type`, `date`, and `shares` already exists. Skip duplicates.

5. Append only the new entries to the array and write the updated array back to portfolio.json using the Write tool. Preserve the existing entries exactly — only add to the end. Each entry must include: `ticker`, `type`, `shares`, `price`, `date`, `exchange`, `thb`, `fx_rate`, `thb_source`.

6. Report a summary: total slips read, entries added, entries skipped as duplicates. For any `bot_rate` entries, note the FX rate used.
