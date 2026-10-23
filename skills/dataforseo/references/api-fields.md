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
| `query_ads_search.py --mode standard/priority` | `POST /v3/serp/google/ads_search/task_post` | Yes — per task per 40 ads |
| | `GET /v3/serp/google/ads_search/task_get/advanced/{id}` | No |
| `query_ads_search.py --mode live` | `POST /v3/serp/google/ads_search/live/advanced` | Yes — per task per 40 ads |
| `query_ads_advertisers.py --mode standard/priority` | `POST /v3/serp/google/ads_advertisers/task_post` | Yes — per task |
| | `GET /v3/serp/google/ads_advertisers/task_get/advanced/{id}` | No |
| `query_ads_advertisers.py --mode live` | `POST /v3/serp/google/ads_advertisers/live/advanced` | Yes — per task |
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

For ads by advertiser (rather than by query), use `query_ads_search.py` (Ads Transparency
Center data, below).

## Ads search (Ads Transparency) — request fields

| Script flag | API field | Notes |
|---|---|---|
| positional domain | `target` | One task per domain |
| positional `AR…` IDs | `advertiser_ids` | Up to 25 per task; the script groups them |
| `--location-code` / `--all-locations` | `location_code` | Omitted = ads shown in any location. Codes: `GET /v3/serp/google/ads_search/locations` (free) |
| `--platform` | `platform` | `all`, `google_search`, `youtube`, `google_play`, `google_maps`, `google_shopping` (sent only when not `all`) |
| `--ad-format` | `format` | `all`, `text`, `image`, `video` (sent only when not `all`) |
| `--date-from` / `--date-to` | `date_from` / `date_to` | `YYYY-MM-DD`, both or neither, 2018-05-31 to today |
| `--depth` | `depth` | Default 40; max 700 (task_post) / 120 (live). Billed per 40 |
| `--mode priority` | `priority: 2` | High priority, about 2x price |

Results are desktop only. Up to 100 tasks per `task_post`; Live takes one task per call.

## Ads search — output fields

Per target: `target` (domain, or `ids:AR…,AR…`), `advertiser_ids_requested`,
`location_code` (null = all locations), `platform`, `ad_format`, `date_from`, `date_to`,
`depth`, `fetched_at`, `ads_returned`, `may_have_more` (result filled `depth`), plus:

**advertisers**: `advertiser_id`, `name`, `verified`, `ads` (count in this result)

**ads**

| Field | API field | Description |
|---|---|---|
| `rank` | `rank_group` | Order in the Transparency Center listing |
| `advertiser_id` | `advertiser_id` | Advertiser account (`AR…`) |
| `advertiser_name` | `title` | Advertiser's legal/display name |
| `verified` | `verified` | Advertiser verified by Google |
| `creative_id` | `creative_id` | Ad ID (`CR…`) |
| `format` | `format` | `text`, `image`, or `video` |
| `first_shown` / `last_shown` | same | `YYYY-MM-DD hh:mm:ss +00:00` (UTC) |
| `transparency_url` | `url` | The ad on adstransparency.google.com |
| `preview_url` | `preview_url` | Ad preview link (often null for text ads) |
| `preview_image_url`, `preview_image_width`, `preview_image_height` | `preview_image` | Rendered preview image |

Ads are listed most recently shown first. A `target` domain matches ads that point to that
domain, so other advertisers (resellers, agencies, affiliates) can appear in `advertisers`
next to the domain owner. No ad copy, impressions, spend, or targeting is returned. A task with no ads returns
`40102 No Search Results`, which the script reports as zero ads, not an error.

## Advertiser lookup — fields

Request: `keyword` (≤700 characters), optional `location_code` (omitted with
`--all-locations`), `priority`. Billed per task, regardless of how many advertisers match.

Matching is loose: advertisers and domains that only contain the keyword are included.

Per keyword: `keyword`, `location_code`, `fetched_at`, `domains` (from `ads_domain` items),
and `advertisers`:

| Field | Description |
|---|---|
| `rank` | Rank within its type (`rank_group`) |
| `kind` | `multi_account` (API `ads_multi_account_advertiser`: one brand, several accounts) or `advertiser` (`ads_advertiser`) |
| `name` | Advertiser name (`title`) |
| `location` | Country code |
| `verified` | Single account: as returned. Multi-account: true if every account is verified, false if none, null if mixed (table: `mixed`) |
| `approx_ads_count` | Approximate ads across all Google platforms |
| `advertiser_ids` | IDs to pass to `query_ads_search.py` |
| `accounts` | Per account: `advertiser_id`, `location`, `verified`, `approx_ads_count` |

CSV output is one row per account (`keyword, rank, kind, name, advertiser_id, location,
verified, approx_ads_count`) plus one `kind=domain` row per domain.

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
