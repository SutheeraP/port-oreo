---
description: Read transaction slip images from a slips subfolder and add them to portfolio.json
---

The user wants to import transaction slips from this folder: $ARGUMENTS

Follow these steps exactly:

1. Use Bash to list all PNG files in `slips/$ARGUMENTS/`.
   Command: `ls slips/$ARGUMENTS/*.PNG slips/$ARGUMENTS/*.png 2>/dev/null`

2. For each PNG file, use the Read tool to view the image. Extract these 6 fields:
   - `ticker`: the stock symbol from the "Buy XXXX" header
   - `exchange`: the exchange name shown in the badge (e.g. "NYSE Arca", "NASDAQ", "NYSE")
   - `price`: the number from "Executed Price" row (USD, digits and decimal only, no currency symbol)
   - `shares`: the number from "Shares" row (digits and decimal only)
   - `date`: the date from "Completion Date" formatted as YYYY-MM-DD
   - `thb`: the number from "Stock Amount" row in THB (digits and decimal only, no currency symbol)
   All values must be strings.

3. Read portfolio.json using the Read tool.

4. Parse the JSON array. For each extracted entry, check if an entry with the same `ticker`, `date`, and `shares` already exists. Skip duplicates.

5. Append only the new entries to the array and write the updated array back to portfolio.json using the Write tool. Preserve the existing entries exactly — only add to the end.

6. Report a summary: total slips read, entries added, entries skipped as duplicates.
