# Toy Ticker

Happy Meal eBay price tracker.

Daily eBay prices for McDonald's Happy Meal collectibles: the current Pokémon TCG
cards plus the two toy series before it (Disney Villains Boo Buckets, SpongeBob × One Piece).

- **Site:** https://toy-ticker.github.io/ (one page per series: `?s=<series id>`)
- **Data:** asking prices of active eBay US Buy It Now listings (eBay Browse API), saved to `data/prices.json`.
  Each item keeps the median, 25th percentile and lowest ask plus the listing count; lots, sets,
  graded cards and multi-item listings are filtered out by title.
- **Series and items:** `data/config.json`. Add a series there to start tracking it.
- **Updates:** `.github/workflows/update-prices.yml` runs `scripts/fetch_prices.py` daily.
  Needs repo secrets `EBAY_CLIENT_ID` and `EBAY_CLIENT_SECRET` (eBay developer Production keyset).

Run locally:

```bash
EBAY_CLIENT_ID=... EBAY_CLIENT_SECRET=... python3 scripts/fetch_prices.py
python3 -m http.server 8765   # then open http://localhost:8765
```

## Backfilling past sold prices (Terapeak)

Daily data only goes back to when tracking began. To fill in a past series, export its sold listings from
eBay Seller Hub > Research > Product research (Sold tab), one search per item or one for the whole series,
and import them:

```bash
python3 scripts/import_terapeak.py boo-buckets-2026 ~/Downloads/terapeak-*.csv --report /tmp/report.txt
```

Rows go through the same title rules as the daily prices; check the report for what was skipped.
The result goes to `data/backfill/<series>.json` and shows as weekly sold medians on each item's chart.

## Toy sightings map

`sightings.html` lets visitors pick a McDonald's on a map and report which Happy Meal toys they got there.
There's no server: reports go to a Google Form, and the map reads the form's response sheet, published as CSV.
Until `data/sightings.json` has a form and a CSV link, the map shows stores but the Send button stays off.

One-time setup:

1. Create a Google Form with eight **Short answer** questions titled exactly:
   `store_id`, `store_name`, `address`, `lat`, `lon`, `series`, `toys`, `out`.
   In Settings, turn off "Collect email addresses" and any sign-in requirement.
2. Get the field IDs: ⋮ menu > **Get pre-filled link**, type the question's name in each box, **Get link**, copy it.
   The link holds `entry.123456=store_id&entry.789…=store_name…`; each `entry.N` goes into
   `form.fields` in `data/sightings.json`.
3. Set `form.action` to the form's link with `/viewform` swapped for `/formResponse`
   (`https://docs.google.com/forms/d/e/<form id>/formResponse`).
4. Responses tab > **Link to Sheets**. In the sheet: File > Share > **Publish to web**, pick the responses tab,
   **Comma-separated values (.csv)**, Publish. Put that link in `csv`.
5. Send one test report from the map and check it shows up in the sheet and, within ~5 minutes, on the map.

Reports older than `window_days` (14) drop off the map. To remove a bad report, delete its row in the sheet.

The restaurant list is `data/stores.json`, every US McDonald's on OpenStreetMap. Refresh it every month or so:

```bash
python3 scripts/fetch_stores.py
```
