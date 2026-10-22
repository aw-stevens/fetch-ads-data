---
name: dataforseo
description: Look up Google keyword search volume and live Google search results pages via DataForSEO. Use when asked about keyword search volume, monthly search trends, keyword CPC or competition, keyword research or sizing, who is advertising on a search term, competitor ads and ad copy on Google, who ranks organically for a query, People Also Ask questions, related searches, or SERP features. Paid API — every call is checked against a daily spend cap.
---

# DataForSEO (Keyword Volume + SERP)

Market-level search data for any keyword or query — not tied to your own ad accounts or site.

| Need | Tool / script |
|---|---|
| Search volume, CPC, competition, monthly trend for keywords | `dataforseo_keyword_volume` / `query_volume.py` |
| Who advertises on a query (ads, copy, top/bottom), who ranks organically, PAA, related searches, SERP features | `dataforseo_serp` / `query_serp.py` |
| Check credentials, account balance, today's spend vs cap | `dataforseo_verify` / `verify.py` |

**Use another skill instead** for your own performance data: your site's organic queries and
rankings → `google-search-console`; your own ad spend/clicks per keyword → `google-ads` /
`microsoft-ads`.

## Prerequisites

First-time setup required per machine. Run `/fetch-ads-data-setup` or `bash ${CLAUDE_PLUGIN_ROOT}/scripts/setup.sh`.

**Python**: `~/.fetch-ads-data/venv/bin/python`

**Credentials**: DataForSEO API login + password (from https://app.dataforseo.com/api-access),
via `DATAFORSEO_LOGIN` / `DATAFORSEO_PASSWORD` env vars or `~/.fetch-ads-data/dataforseo.json`.
See `references/setup.md`. Confirm with `verify.py` (free).

---

## Cost — read before calling

DataForSEO charges a prepaid balance per request. Every billed call is projected against a
**daily spend cap** (default **$1.00/day**, UTC) and refused if it would exceed it. Successful
output ends with a cost line (this call / today's total / cap).

| Call | Billing unit | Approx. rate* |
|---|---|---|
| Keyword volume (Live) | per request of up to 700 keywords | ~$0.09 / request |
| SERP — standard queue | per query per 10 results | ~$0.0006 |
| SERP — priority queue | per query per 10 results | ~$0.0012 |
| SERP — live | per query per 10 results | ~$0.002 |

\*Rates change — check https://dataforseo.com/pricing. Recorded spend uses the actual `cost`
the API returns, so the tally stays accurate even if these projections drift.

Guidelines:
- **Batch keywords** into one volume call — 1 keyword costs the same as 700.
- Keep SERP `depth` at 10 unless the user needs more; each extra 10 is billed again.
- For large or unclear requests, run with `dry_run` / `--dry-run` first and tell the user the
  projected cost.
- If a call is refused by the cap, tell the user — don't split it up to get around the cap.

---

## Keyword volume

```bash
~/.fetch-ads-data/venv/bin/python \
  ${CLAUDE_PLUGIN_ROOT}/scripts/dataforseo/query_volume.py \
  "crm software" "email marketing tool" --format table
```

**Args:**
- positional keywords, and/or `--file keywords.txt` (one per line). Max 80 chars / 10 words each, 10,000 per run. Case-insensitive duplicates are dropped.
- `--location-code` — default config or `2840` (US). See `references/api-fields.md` for common codes.
- `--language-code` — default config or `en`
- `--dry-run` — print request bodies + projected cost, no API call
- `--format` — `table` (default), `csv`, `json`

Returns per keyword: `search_volume` (avg monthly, last 12 months), `cpc` (USD), `competition`
(LOW/MEDIUM/HIGH — paid competition, not SEO difficulty), `competition_index` (0–100),
`low_top_of_page_bid` / `high_top_of_page_bid`, and `monthly_searches` (oldest → newest).
Keywords with too little volume come back with null metrics.

## SERP results

```bash
~/.fetch-ads-data/venv/bin/python \
  ${CLAUDE_PLUGIN_ROOT}/scripts/dataforseo/query_serp.py \
  "crm software" --mode standard --device desktop
```

**Args:**
- positional queries and/or `--file`. Up to 100 per run.
- `--mode` — `standard` (default, cheapest; queued, often a few minutes), `priority` (~2x, usually <1 min), `live` (~3x, seconds). Prefer `live` or `priority` when the user is waiting on one or two queries.
- `--device` — `desktop` (default) or `mobile`; ads and layout differ by device
- `--depth` — 10–100 results (default 10)
- `--location-code`, `--language-code` — as above
- `--poll-interval` / `--timeout` — queued modes (defaults 10 s / 300 s)
- `--task-ids ID ...` — collect results of tasks that timed out earlier (free; IDs are printed on timeout)
- `--dry-run`, `--format`

Returns per query:
- **paid** — `position` (ad rank), `placement` (`top`/`bottom`, derived from where the ad sits relative to the first organic result), `domain`, `title`, `description`, `url`, `breadcrumb`, `sitelinks` count
- **organic** — `position`, `domain`, `title`, `url`, `description`
- **people_also_ask** — question strings
- **related_searches** — query strings
- **serp_features** — other blocks (featured snippet, AI overview, local pack, video, etc.) with absolute rank
- `item_types`, `total_results`

A SERP is a single snapshot: ads rotate by time, location, and device, so "no ads" on one
fetch doesn't mean nobody bids on the term. Say so when reporting advertiser presence.

---

## Quick examples

**Size a keyword list:**
```bash
query_volume.py --file keywords.txt --format csv
```

**Who advertises on these terms, on mobile, right now:**
```bash
query_serp.py "crm software" "sales pipeline software" --mode live --device mobile
```

**Content brief inputs (PAA + related searches) for a topic, as JSON:**
```bash
query_serp.py "how to choose a crm" --format json
```

**Check what a run would cost:**
```bash
query_volume.py --file keywords.txt --dry-run
```

## Reference

- `references/api-fields.md` — endpoints, response fields, location codes, status codes
- `references/setup.md` — credentials, config, spend cap
