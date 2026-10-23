---
name: dataforseo
description: Look up Google keyword search volume and live Google search results pages via DataForSEO. Use when asked about keyword search volume, monthly search trends, keyword CPC or competition, keyword research or sizing, who ranks organically for a query, which advertisers and ad copy appear on a search term (sampled — see ad coverage caveats), People Also Ask questions, related searches, SERP features, or what ads a specific advertiser or domain runs on Google (Ads Transparency Center: formats, first/last shown dates, advertiser IDs). Paid API — every call is checked against a daily spend cap.
---

# DataForSEO (Keyword Volume, SERP, Ads Transparency)

Market-level search data for any keyword or query — not tied to your own ad accounts or site.

| Need | Tool / script |
|---|---|
| Search volume, CPC, competition, monthly trend for keywords | `dataforseo_keyword_volume` / `query_volume.py` |
| Who ranks organically, PAA, related searches, SERP features | `dataforseo_serp` / `query_serp.py` |
| Sample which ads appear on a query (advertiser, copy, top/bottom) | `dataforseo_serp` with `ads_test` / `query_serp.py --ads-test` |
| Ads a given advertiser/domain runs (format, first/last shown, preview link) | `dataforseo_ads_search` / `query_ads_search.py` |
| Advertiser IDs and domains for a brand name or keyword | `dataforseo_ads_advertisers` / `query_ads_advertisers.py` |
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
| Ads search — standard / priority / live | per domain (or ≤25-ID group) per 40 ads | ~$0.0006 / $0.0012 / $0.002 |
| Advertiser lookup — standard / priority / live | per keyword | ~$0.0006 / $0.0012 / $0.002 |

\*Rates change — check https://dataforseo.com/pricing. Recorded spend uses the actual `cost`
the API returns, so the tally stays accurate even if these projections drift.

Guidelines:
- **Batch keywords** into one volume call — 1 keyword costs the same as 700.
- Keep SERP `depth` at 10 unless the user needs more; each extra 10 is billed again.
- Keep ads search `depth` at 40 unless the user needs more; each extra 40 is billed again.
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
- `--ads-test` — capture paid ads more reliably (same price); organic `url`/`domain` come back empty. See below.
- `--depth` — 10–100 results (default 10)
- `--location-code`, `--language-code` — as above
- `--poll-interval` / `--timeout` — queued modes (defaults 10 s / 300 s)
- `--task-ids ID ...` — collect results of tasks that timed out earlier (free; IDs are printed on timeout)
- `--dry-run`, `--format`

Returns per query:
- **organic** — `position`, `domain`, `title`, `url`, `description` (`domain`/`url` empty in ads test mode)
- **paid** — any ads captured: `position` (ad rank), `placement` (`top`/`bottom`, derived from where the ad sits relative to the first organic result), `domain`, `title`, `description`, `url`, `breadcrumb`, `sitelinks` count
- **people_also_ask** — question strings
- **related_searches** — query strings
- **serp_features** — other blocks (featured snippet, AI overview, local pack, video, etc.) with absolute rank
- `item_types`, `total_results`, `ads_test`

### Ad coverage — set expectations

DataForSEO's crawler is frequently served **no ads**, even on heavily advertised queries, so a
normal fetch usually returns an empty `paid` list. This is how Google serves ads to automated
requests, not a parsing problem.

- For "who is advertising on X" questions, use **ads test mode** (`ads_test` / `--ads-test`). It
  sends Google's `adtest=on` flag, which records no real ad impressions and captures ads more
  often — but still not every time.
- Ads test mode strips `url`/`domain` from organic results. If the user needs both, make two
  calls: one normal (organic) and one in ads test mode (ads).
- Every SERP is one sample; ads rotate by time, location, device, and budget. **Never report
  "no one advertises on X"** from an empty result — say no ads were captured in that fetch.
  For a fuller picture, sample a few times, on both devices, and report which advertisers
  appeared and how often.
- Google Shopping ads show up as a `shopping` SERP feature, not in `paid`.

---

## Ads by advertiser (Ads Transparency Center)

Answers "what ads does example.com run" from Google's Ads Transparency Center: every ad the
advertiser ran in the chosen location/platform/date range, not a sample of one search page.

```bash
~/.fetch-ads-data/venv/bin/python \
  ${CLAUDE_PLUGIN_ROOT}/scripts/dataforseo/query_ads_search.py \
  example.com --platform google_search --mode live
```

**Args:**
- positional targets: advertiser domains (`example.com`; scheme, path and `www.` are stripped) and/or advertiser IDs (`AR` + digits). Each domain is one task; IDs are grouped into one task per 25, so a brand's accounts share one result list.
- `--mode` — `standard` (default), `priority`, `live`, as for SERPs
- `--location-code` — where the ads were shown; default config or `2840`. `--all-locations` sends no location.
- `--platform` — `all` (default), `google_search`, `youtube`, `google_play`, `google_maps`, `google_shopping`
- `--ad-format` — `all` (default), `text`, `image`, `video`
- `--date-from` / `--date-to` — YYYY-MM-DD, both or neither; earliest 2018-05-31
- `--depth` — max ads per task, default 40 (≤700 queued, ≤120 live)
- `--poll-interval`, `--timeout`, `--task-ids`, `--dry-run`, `--format` — as for SERPs

Returns per target: `advertisers` (accounts found, with ad counts in this result) and `ads`:
`rank`, `advertiser_id`, `advertiser_name`, `verified`, `creative_id`, `format`,
`first_shown`, `last_shown`, `transparency_url` (the ad on adstransparency.google.com),
`preview_url`, `preview_image_url` (+ width/height). `may_have_more` is true when the result
filled `depth`. Ads come back most recently shown first.

**A domain search is not just the domain owner's ads.** It returns ads that point to that
domain, so resellers, agencies, and affiliates can appear alongside the owner's own accounts.
Check the `advertisers` summary and filter by `advertiser_id` when the user wants only the
owner's ads (or search by the owner's advertiser IDs instead).

**What it does not give:** ad copy text (open the Transparency Center link or preview image),
impressions, spend, or keywords. Ads are matched to a domain by Google, so a domain can
return nothing while the brand still advertises under accounts not tied to it. Then look up
its IDs:

```bash
~/.fetch-ads-data/venv/bin/python \
  ${CLAUDE_PLUGIN_ROOT}/scripts/dataforseo/query_ads_advertisers.py "example brand" --mode live
```

`query_ads_advertisers.py` takes keywords (and `--file`), `--mode`, `--location-code` /
`--all-locations`, `--task-ids`, `--dry-run`, `--format`. Returns `advertisers` (`name`,
`kind` = `advertiser` or `multi_account`, `location`, `verified`, `approx_ads_count`,
`advertiser_ids`, per-account `accounts`) and `domains` (advertiser domains matching the
keyword). Pass a brand's `advertiser_ids` (or a domain) to `query_ads_search.py`. Matching
is loose: unrelated advertisers and domains that merely contain the keyword are included,
so confirm the right account by name, verification, and ad count.

---

## Quick examples

**Size a keyword list:**
```bash
query_volume.py --file keywords.txt --format csv
```

**Sample which ads appear on these terms (desktop and mobile):**
```bash
query_serp.py "crm software" "sales pipeline software" --mode live --ads-test
query_serp.py "crm software" "sales pipeline software" --mode live --ads-test --device mobile
```

**Which video ads did an advertiser run on YouTube in January?**
```bash
query_ads_search.py example.com --platform youtube --ad-format video --date-from 2026-01-01 --date-to 2026-01-31
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
