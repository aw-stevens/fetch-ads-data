---
name: g2-digital-markets
description: Query G2 Digital Markets Click Report data (PPC across Capterra, GetApp, Software Advice). Use when asked about G2DM / Capterra / GetApp / Software Advice paid clicks, spend/cost, conversions, CPL, CPC, conversion rate, average position, or monthly PPC performance by channel, vendor, product, category, or country.
---

# G2 Digital Markets (Click Report)

Query the G2 Digital Markets Click Report API for historical PPC performance across
**Capterra**, **GetApp**, and **Software Advice** — clicks, cost, conversions, CPL.

## Prerequisites

First-time setup required per machine. Run `/fetch-ads-data-setup` or `bash ${CLAUDE_PLUGIN_ROOT}/scripts/setup.sh`.

**Python**: `~/.fetch-ads-data/venv/bin/python`

**API key**: A single API key from your G2 Digital Markets account manager, stored in
`~/.fetch-ads-data/g2-digital-markets.json` as `{"api_key": "..."}`. Endpoint and auth
settings live in `~/.fetch-ads-data/config.json` under `g2_digital_markets`. See
`references/setup.md`.

Confirm connectivity first: `query_g2.py --action verify`.

---

## Workflow

1. Determine the date range (the API uses `YYYY-MM-DD`; shorthands like `30daysAgo` work too)
2. Decide on filters (channel / category / country) and grouping — consult `references/api-fields.md`
3. Run `query_g2.py`
4. Interpret and present results

**Click data is not final** until the monthly invoice is issued — month-end review may lower
totals, so this report can read slightly higher than the invoice. Note this when reporting.

---

## Running Queries

```bash
~/.fetch-ads-data/venv/bin/python \
  ${CLAUDE_PLUGIN_ROOT}/scripts/g2_digital_markets/query_g2.py \
  --start 2026-01-01 --end 2026-05-31 \
  --group-by month \
  --format table
```

**Args:**
- `--start` / `--end` — date range. `YYYY-MM-DD`, or `today`/`yesterday`/`7daysAgo`/`30daysAgo`/`90daysAgo` (default: `30daysAgo` → `today`)
- `--group-by` — comma-separated keys; sums clicks/conversions/cost and recomputes avg_cpc, conversion_rate, cpl, avg_position. Keys: `month`, `channel`, `country`, `category`, `product_name`, `vendor_name`, `campaign_name`. Empty = raw per-record rows.
- `--channel` — `capterra`, `getapp`, `software advice`
- `--category` — software category filter
- `--country` — country filter
- `--include-conversion-type` — add `conversions_by_type` breakdown (bookDemo, freeTrial, other)
- `--page-size` — records per page (default 1000); pagination is automatic
- `--format` — `table` (default), `csv`, `json`
- `--action verify` — test the API key instead of querying

---

## Quick Examples

**Monthly totals:**
```bash
--start 2026-01-01 --end 2026-05-31 --group-by month
```

**Monthly breakdown by channel:**
```bash
--start 2026-01-01 --end 2026-05-31 --group-by month,channel
```

**One channel, by product/vendor:**
```bash
--channel capterra --start 2026-05-01 --end 2026-05-31 --group-by product_name
```

**Conversion-type breakdown for a month:**
```bash
--start 2026-05-01 --end 2026-05-31 --group-by month --include-conversion-type
```

**Raw records (every click row) as JSON:**
```bash
--start 2026-05-01 --end 2026-05-31 --format json
```

---

## Monthly reporting

Use `--group-by month` to get one row per `YYYY-MM` with `cost`, `clicks`, `conversions`,
and `cpl` — convenient for feeding a monthly spend/CPL report.

---

## Reference

See `references/api-fields.md` for the full parameter list, response fields, channel values,
aggregation behavior, and rate limits.
