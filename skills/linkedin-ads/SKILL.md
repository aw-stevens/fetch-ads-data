---
name: linkedin-ads
description: Query and analyze LinkedIn Ads performance data. Use when asked about LinkedIn Ads campaigns, impressions, clicks, spend, CTR, conversions, or professional demographic breakdowns (by company, industry, seniority, job title). Queries ad analytics for connected accounts via the LinkedIn Marketing API.
---

# LinkedIn Ads

## Prerequisites

First-time setup required per machine. Run `/fetch-ads-data-setup` or `bash ${CLAUDE_PLUGIN_ROOT}/scripts/setup.sh`.

**Python**: `~/.fetch-ads-data/venv/bin/python`

**Accounts**: Configured in `~/.fetch-ads-data/config.json` under `linkedin_ads.accounts`.
Run `list_li_accounts.py` to discover available accounts.

---

## Workflow

1. Understand what the user wants (metric, pivot/dimension, time range)
2. Choose pivot and fields — consult `references/api-fields.md` for options
3. Run `query_li_ads.py` with the appropriate parameters
4. Interpret and present results

---

## Running Queries

```bash
~/.fetch-ads-data/venv/bin/python \
  ${CLAUDE_PLUGIN_ROOT}/scripts/linkedin_ads/query_li_ads.py \
  --account-id <ID> \
  --pivot CAMPAIGN \
  --start 30daysAgo --end yesterday \
  --granularity ALL \
  --fields impressions,clicks,costInLocalCurrency,dateRange,pivotValues \
  --format table
```

**Args:**
- `--account-id` — sponsored account ID (defaults to config `linkedin_ads.default_account`)
- `--pivot` — grouping dimension: ACCOUNT, CAMPAIGN (default), CAMPAIGN_GROUP, CREATIVE, MEMBER_COMPANY, MEMBER_INDUSTRY, MEMBER_SENIORITY, MEMBER_JOB_TITLE, MEMBER_COUNTRY_V2
- `--start` / `--end` — date range (YYYY-MM-DD or 7daysAgo/30daysAgo/90daysAgo/yesterday/today)
- `--granularity` — DAILY, MONTHLY, or ALL (default)
- `--fields` — comma-separated metrics
- `--format` — `table` (default), `csv`, `json`

---

## Quick Examples

**Campaign performance last 30 days:**
```bash
--pivot CAMPAIGN --start 30daysAgo --end yesterday
```

**Daily spend trend:**
```bash
--pivot CAMPAIGN --granularity DAILY --start 30daysAgo --end yesterday
```

**Performance by industry:**
```bash
--pivot MEMBER_INDUSTRY --start 30daysAgo --end yesterday
```

**Performance by seniority:**
```bash
--pivot MEMBER_SENIORITY --start 30daysAgo --end yesterday
```

**Campaign group rollup:**
```bash
--pivot CAMPAIGN_GROUP --start 90daysAgo --end yesterday
```

---

## API Reference

See `references/api-fields.md` for:
- All available pivot dimensions
- All available metric fields
- Date range format details
- Granularity options

---

## Listing Accounts

```bash
~/.fetch-ads-data/venv/bin/python \
  ${CLAUDE_PLUGIN_ROOT}/scripts/linkedin_ads/list_li_accounts.py
```
