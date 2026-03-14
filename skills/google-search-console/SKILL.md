---
name: google-search-console
description: Query Google Search Console data. Use when asked about organic search performance, search queries, keyword rankings, click-through rates, impressions, average position, top landing pages, search appearance, or SEO data.
---

# Google Search Console

## Prerequisites

First-time setup required per machine. Run `/fetch-ads-data-setup` or `bash ${CLAUDE_PLUGIN_ROOT}/scripts/setup.sh`.

**Python**: `~/.fetch-ads-data/venv/bin/python`

**Sites**: Configured in `~/.fetch-ads-data/config.json` under `google_search_console.sites`.
Run `query_gsc.py --action list-sites` to discover accessible sites.

---

## Workflow

1. Identify which site the user is asking about (default from config)
2. Determine dimensions, date range, search type — consult `references/gsc-fields.md` if needed
3. Run `query_gsc.py`
4. Interpret and present results

---

## Running Queries

```bash
~/.fetch-ads-data/venv/bin/python \
  ${CLAUDE_PLUGIN_ROOT}/scripts/google_search_console/query_gsc.py \
  --site "https://example.com/" \
  --dimensions query \
  --start 30daysAgo --end today \
  --limit 25 \
  --format table
```

**Args:**
- `--site` — site URL (defaults to config `google_search_console.default_site`)
- `--dimensions` — space-separated: `query`, `page`, `country`, `device`, `date`, `searchAppearance`
- `--start` / `--end` — date range (default: `30daysAgo` / `today`). Data has ~3 day lag.
- `--search-type` — `web` (default), `image`, `video`, `news`, `discover`, `googleNews`
- `--limit` — row limit (default: 25, max: 25000)
- `--format` — `table` (default), `csv`, `json`
- `--action list-sites` — list all accessible sites instead of querying

---

## Quick Examples

**Top search queries:**
```bash
--dimensions query --limit 20
```

**Top landing pages:**
```bash
--dimensions page --limit 20
```

**Daily search trend:**
```bash
--dimensions date --start 30daysAgo
```

**Queries by country:**
```bash
--dimensions query country --limit 20
```

**Device breakdown:**
```bash
--dimensions device
```

**Query + page combinations (which page ranks for which query):**
```bash
--dimensions query page --limit 20
```

**Image search performance:**
```bash
--dimensions query --search-type image --limit 10
```

---

## GSC Reference

See `references/gsc-fields.md` for:
- All dimensions and metrics
- Search type options
- Date range handling and data lag
- Common analysis patterns
