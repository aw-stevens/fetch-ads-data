# DataForSEO — Endpoints and Fields

Base URL: `https://api.dataforseo.com`. Auth: HTTP Basic (API login + API password).
Docs: https://docs.dataforseo.com/v3/

## Endpoints used

| Script | Endpoint | Billed? |
|---|---|---|
| `query_volume.py` | `POST /v3/keywords_data/google_ads/search_volume/live` | Yes — per request (≤1,000 keywords; the script sends 700) |
| `query_serp.py --mode standard/priority` | `POST /v3/serp/google/organic/task_post` | Yes — per task per 10 results |
| | `GET /v3/serp/google/organic/task_get/advanced/{id}` | No |
| `query_serp.py --mode live` | `POST /v3/serp/google/organic/live/advanced` | Yes — per task per 10 results |
| `verify.py` | `GET /v3/appendix/user_data` | No |

Rate limits: Google Ads Live endpoints (keyword volume) allow **12 requests/minute** — the
script spaces multi-chunk runs ~5 s apart. `task_post` takes up to 100 tasks per request.
Standard-queue results are kept for retrieval for a limited time (see DataForSEO docs), so
collect timed-out task IDs promptly.

## Keyword volume — output fields

| Field | Description |
|---|---|
| `keyword` | Keyword as returned (lower-cased by Google) |
| `search_volume` | Average monthly searches over the last 12 months |
| `cpc` | Average cost per click (USD) |
| `competition` | `LOW` / `MEDIUM` / `HIGH` — advertiser competition in Google Ads |
| `competition_index` | 0–100 version of `competition` |
| `low_top_of_page_bid` / `high_top_of_page_bid` | Top-of-page bid range (USD) |
| `monthly_searches` | `[{year, month, search_volume}]`, oldest → newest (table/CSV: `YYYY-MM:N ...`) |

Null metrics mean Google has too little data for the keyword. Google Ads groups close
variants, so near-duplicate keywords can return identical volumes.

## SERP — output fields

Per query: `query`, `location_code`, `language_code`, `device`, `total_results`,
`item_types` (every block type on the page, in order), plus:

**paid** (ads — often empty; see "Ad coverage" below)

| Field | Description |
|---|---|
| `position` | Ad rank among ads on the page (`rank_group`) |
| `rank_absolute` | Position among all page elements |
| `placement` | `top` if above the first organic result on its page, else `bottom` (`unknown` if the page has no organic results). Derived — not an API field. |
| `page` | SERP page number |
| `domain`, `url`, `breadcrumb` | Advertiser domain and display / landing URL |
| `title`, `description` | Ad copy |
| `sitelinks` | Number of sitelink extensions |

**organic**: `position`, `rank_absolute`, `domain`, `title`, `url`, `description`
(`domain`/`url` are null in ads test mode)

`ads_test` is `true` when the result was fetched with `adtest=on`.

**people_also_ask**: question titles. **related_searches**: query strings.

**serp_features**: every other block (`featured_snippet`, `ai_overview`, `local_pack`,
`video`, `images`, `top_stories`, `knowledge_graph`, …) with `type`, `rank_absolute`, and
`title`/`domain`/`url` where present.

CSV output is one row per element: `query, section, position, rank_absolute, placement,
domain, title, url, description` where `section` is `paid`, `organic`, `people_also_ask`,
`related_search`, or a feature type.

## Ad coverage

Google often serves no ads to DataForSEO's crawler, so `paid` is frequently empty even on
queries that show several ads to people. `--ads-test` / `ads_test` adds
`"search_param": "adtest=on"` to the task — Google's test-ad flag, which logs no real
impressions and returns ads more often (same price). Side effects: organic items come back
without `url`/`domain`, `total_results` is unreliable, and some other SERP features may be
incomplete. DataForSEO also
suggests narrowing location to a city, though that did not reliably surface ads in testing.

Background: https://dataforseo.com/help-center/getting-more-consistent-ad-results-in-google-serp-api

For ads by advertiser (rather than by query), DataForSEO's separate Google Ads Search API
(Ads Transparency Center data) is the better source; it is not wrapped by this plugin.

## Common location codes

| Code | Location |
|---|---|
| 2840 | United States |
| 2826 | United Kingdom |
| 2124 | Canada |
| 2036 | Australia |
| 2276 | Germany |
| 2250 | France |
| 2356 | India |

Full list (free): `GET /v3/serp/google/locations` or
https://docs.dataforseo.com/v3/serp/google/locations/. Cities and regions have their own codes.

## Status codes

| Code | Meaning |
|---|---|
| 20000 | OK |
| 20100 | Task created (queued) |
| 40601 / 40602 | Task handed / in queue — still polling |
| 40100 (or HTTP 401) | Not authorized — check API login/password |
| 40102 | No search results for the query / keywords |
| 40200 / 40210 | Payment required / insufficient funds — top up the balance |
| 40202 / 40209 | Rate limit per minute / too many simultaneous requests |
| 40501 | Invalid field in the request |

Full list: https://docs.dataforseo.com/v3/appendix/errors/
