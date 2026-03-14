---
name: google-analytics
description: Query and analyze Google Analytics 4 (GA4) data. Use when asked about website traffic, sessions, pageviews, bounce rate, engagement, user acquisition, traffic sources, top pages, conversions, device breakdown, geographic data, or any GA4 metrics for configured properties.
---

# Google Analytics

## Prerequisites

First-time setup required per machine. Run `/fetch-ads-data-setup` or `bash ${CLAUDE_PLUGIN_ROOT}/scripts/setup.sh`.

**Python**: `~/.fetch-ads-data/venv/bin/python`

**Properties**: Configured in `~/.fetch-ads-data/config.json` under `google_analytics.properties`.
Run `list_properties.py` to verify access.

---

## Workflow

1. Identify which property the user is asking about (default from config)
2. Determine dimensions, metrics, date range — consult `references/ga4-fields.md` if needed
3. Run `query_ga.py`
4. Interpret and present results

---

## Running Queries

```bash
~/.fetch-ads-data/venv/bin/python \
  ${CLAUDE_PLUGIN_ROOT}/scripts/google_analytics/query_ga.py \
  --property <ID> \
  --dimensions sessionSource sessionMedium \
  --metrics sessions newUsers engagementRate \
  --start 30daysAgo --end today \
  --limit 20 \
  --format table
```

**Args:**
- `--property` — property ID (defaults to config `google_analytics.default_property`)
- `--dimensions` — space-separated dimension names (optional)
- `--metrics` — space-separated metric names (required)
- `--start` / `--end` — date range (default: `30daysAgo` / `today`)
- `--limit` — row limit (default: 100)
- `--format` — `table` (default), `csv`, `json`
- `--realtime` — query last 30 minutes of live traffic instead of historical data

---

## Quick Examples

**Traffic by source:**
```bash
--dimensions sessionSource sessionMedium --metrics sessions newUsers engagementRate
```

**Top pages:**
```bash
--dimensions pagePath --metrics screenPageViews averageSessionDuration bounceRate --limit 25
```

**Daily trend:**
```bash
--dimensions date --metrics sessions activeUsers --start 90daysAgo --limit 90
```

**Device breakdown:**
```bash
--dimensions deviceCategory --metrics sessions engagementRate bounceRate
```

**Live traffic (realtime):**
```bash
--realtime --dimensions city --metrics activeUsers --limit 20
```

---

## GA4 Reference

See `references/ga4-fields.md` for:
- All dimension and metric names (GA4 names differ from Universal Analytics)
- Date range formats
- Example commands per property
- Common gotchas (e.g. use `totalUsers` not `users`, `screenPageViews` not `pageviews`)
