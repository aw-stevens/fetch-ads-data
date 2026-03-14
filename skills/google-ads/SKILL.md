---
name: google-ads
description: Query and analyze Google Ads data using GAQL (Google Ads Query Language). Use when asked about Google Ads performance, campaigns, keywords, ad groups, search terms, conversions, spend, impressions, clicks, CTR, PMax campaigns, or any Google Ads metrics. Runs read-only queries against connected Google Ads accounts via the google-ads Python library.
---

# Google Ads

## Prerequisites

First-time setup required per machine. Run `/fetch-ads-data-setup` or `bash ${CLAUDE_PLUGIN_ROOT}/scripts/setup.sh`.

**Python**: `~/.fetch-ads-data/venv/bin/python`

**Accounts**: Configured in `~/.fetch-ads-data/config.json` under `google_ads.accounts`.
Run `list_accounts.py` to discover available accounts.

---

## Workflow

1. Understand what the user wants (metric, dimension, time range, filters)
2. Write a GAQL query — consult `references/gaql-fields.md` for field names and resource types
3. Run `query_ads.py` with the query
4. Interpret and present results

---

## Running Queries

```bash
~/.fetch-ads-data/venv/bin/python \
  ${CLAUDE_PLUGIN_ROOT}/scripts/google_ads/query_ads.py \
  "<GAQL query>" \
  --customer-id <ID> \
  --format table   # or csv or json
```

- `--customer-id` — defaults to config `google_ads.default_account` if omitted
- `--format table` (default): human-readable aligned table
- `--format csv`: comma-separated, good for large result sets
- `--format json`: structured output

**Cost fields** (`metrics.cost_micros`) are automatically converted to dollars.

---

## Example Queries

**Campaign performance last 30 days:**
```sql
SELECT campaign.name, campaign.advertising_channel_type,
       metrics.impressions, metrics.clicks, metrics.cost_micros,
       metrics.conversions, metrics.ctr
FROM campaign
WHERE segments.date DURING LAST_30_DAYS
  AND campaign.status = 'ENABLED'
ORDER BY metrics.cost_micros DESC
LIMIT 20
```

**Top keywords by spend:**
```sql
SELECT campaign.name, ad_group.name,
       ad_group_criterion.keyword.text, ad_group_criterion.keyword.match_type,
       metrics.impressions, metrics.clicks, metrics.cost_micros, metrics.conversions
FROM keyword_view
WHERE segments.date DURING LAST_30_DAYS
  AND ad_group_criterion.status = 'ENABLED'
ORDER BY metrics.cost_micros DESC
LIMIT 50
```

**PMax campaign performance:**
```sql
SELECT campaign.name, asset_group.name, asset_group.status,
       metrics.impressions, metrics.clicks, metrics.cost_micros, metrics.conversions
FROM asset_group
WHERE segments.date DURING LAST_30_DAYS
```

**Daily spend trend:**
```sql
SELECT campaign.name, segments.date, metrics.cost_micros,
       metrics.impressions, metrics.clicks, metrics.conversions
FROM campaign
WHERE segments.date DURING LAST_30_DAYS
  AND campaign.status = 'ENABLED'
ORDER BY segments.date DESC, metrics.cost_micros DESC
```

---

## GAQL Reference

See `references/gaql-fields.md` for:
- All resource types (campaign, ad_group, keyword_view, search_term_view, asset_group, etc.)
- Available fields and metrics for each resource
- Date range options and WHERE clause patterns
- Segmentation options (device, day of week, network, etc.)
- PMax limitations

---

## Listing Accounts

```bash
~/.fetch-ads-data/venv/bin/python \
  ${CLAUDE_PLUGIN_ROOT}/scripts/google_ads/list_accounts.py
```
