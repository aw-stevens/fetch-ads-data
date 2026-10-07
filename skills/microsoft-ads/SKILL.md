---
name: microsoft-ads
description: Query and analyze Microsoft Advertising (Bing Ads) performance data. Use when asked about Bing Ads / Microsoft Advertising campaigns, spend, clicks, impressions, conversions, CTR, CPC, or monthly Bing ad performance. Pulls Account- and Campaign-PerformanceReports for connected accounts via the Microsoft Advertising REST Reporting API.
---

# Microsoft Advertising (Bing Ads)

## Prerequisites

First-time setup required per machine. Run `/fetch-ads-data-setup` or `bash ${CLAUDE_PLUGIN_ROOT}/scripts/setup.sh`.

**Python**: `~/.fetch-ads-data/venv/bin/python`. Calls the Microsoft Advertising **REST** API (v13)
directly with `requests` — no `bingads` SDK needed (the SOAP API it wraps is fully deprecated
on 2027-01-31).

**Accounts**: Configured in `~/.fetch-ads-data/config.json` under `microsoft_ads.accounts`.
Run `list_accounts.py` to discover available accounts.

See `references/setup.md` for Azure app registration, developer token, and OAuth.

---

## Workflow

1. Understand what the user wants (metric, entity, time range, aggregation)
2. Choose `--report-type` (campaign or account), `--aggregation`, and date range
3. Run `query_ms_ads.py` with the appropriate parameters
4. Interpret and present results

Bing has no query language — this tool mirrors the *shape* of `google_ads_query` /
`linkedin_ads_query` (entity + metrics + time + format), not a literal query string.
Under the hood it submits a report (`GenerateReport/Submit`), polls until ready
(`GenerateReport/Poll`, usually a few seconds), and downloads the zipped CSV.

---

## Running Queries

```bash
~/.fetch-ads-data/venv/bin/python \
  ${CLAUDE_PLUGIN_ROOT}/scripts/microsoft_ads/query_ms_ads.py \
  --account-id <ID> \
  --report-type campaign \
  --aggregation Summary \
  --start 30daysAgo --end yesterday \
  --format table
```

**Args:**
- `--account-id` — Microsoft Advertising account ID (defaults to config `microsoft_ads.default_accounts`)
- `--report-type` — `campaign` (default, per-campaign rows) or `account` (account totals)
- `--aggregation` — `Summary` (default), `Daily`, `Weekly`, `Monthly`, `Yearly`
- `--start` / `--end` — date range (YYYY-MM-DD or 7daysAgo/30daysAgo/90daysAgo/yesterday/today)
- `--columns` — comma-separated report columns (default depends on report type)
- `--format` — `table` (default), `csv`, `json`

---

## Quick Examples

**Campaign performance last 30 days:**
```bash
--report-type campaign --start 30daysAgo --end yesterday
```

**Monthly account spend (e.g. May 2026):**
```bash
--report-type account --aggregation Monthly --start 2026-05-01 --end 2026-05-31
```
Sum the `Spend` column for the month's total.

**Daily campaign spend trend:**
```bash
--report-type campaign --aggregation Daily --start 30daysAgo --end yesterday
```

---

## API Reference

See `references/report-fields.md` for report types, available columns, aggregation, and
date-range details.

---

## Listing Accounts

```bash
~/.fetch-ads-data/venv/bin/python \
  ${CLAUDE_PLUGIN_ROOT}/scripts/microsoft_ads/list_accounts.py
```

Uses Customer Management (`CustomersInfo/Query` → `AccountsInfo/Query` per customer).

---

## Errors

API faults are printed as `Error: HTTP <status>: <ErrorCode> (<code>): <message> (TrackingId …)`.
Common ones:
- `InvalidCustomDateRangeEnd (2010)` / `InvalidCustomDateRangeStart` — the range is outside data retention
  (Daily/Weekly data is kept ~36 months) or `--end` is before `--start`.
- `OAuth token request failed (invalid_grant …)` — the refresh token was revoked/expired;
  re-run `get_token.py` (see `references/setup.md`).
