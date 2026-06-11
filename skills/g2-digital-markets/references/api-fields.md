# G2 Digital Markets Click Report — API Reference

`GET {base_url}/clicks` — historical click data across G2DM channels, categories, and countries.
Base URL: `https://public-api.capterra.com/v2`. Auth: API key sent in a raw `Authorization` header (no `Bearer` prefix).

## Request parameters

| Param | Type | Notes |
|-------|------|-------|
| `start_date` | string | Date of the first click. `YYYY-MM-DD`. |
| `end_date` | string | Date of the last click. `YYYY-MM-DD`. |
| `category` | string | Category where the click occurred. |
| `country` | string | Country where the click occurred. |
| `channel` | string | Site where the click occurred. One of: `capterra`, `getapp`, `software advice`. |
| `page_size` | string | Number of results per request/page. |
| `cursor` | string | Pagination cursor. First request omits it; the response returns the next page URL in `meta.next`. |
| `include_conversion_type` | boolean | When `true`, adds `conversions_by_type` (e.g. `bookDemo`, `freeTrial`, `other`). Default `false`. |

The `query_g2.py` script maps these to flags: `--start`, `--end`, `--category`, `--country`,
`--channel`, `--page-size`, `--include-conversion-type`. The `cursor` is handled automatically.

## Response

```json
{
  "clicks": [
    {
      "date_of_report": "2026-06-11",
      "campaign_name": "string",
      "product_name": "string",
      "category": "string",
      "avg_cpc": 0,
      "avg_position": 0,
      "clicks": 0,
      "conversions": 0,
      "conversion_rate": 0,
      "cost": 0,
      "cpl": 0,
      "channel": "string",
      "country": "string",
      "campaign_id": 0,
      "landing_page": "https://www.mywebsite.com/?utm_source=capterra",
      "conversions_by_type": { "bookDemo": 5, "freeTrial": 2, "other": 3 }
    }
  ],
  "meta": { "next": "https://public-api.capterra.com/v2/clicks?cursor=cursor" }
}
```

### Per-record fields

`date_of_report`, `vendor_name`, `product_name`, `campaign_name`, `category`, `avg_cpc`,
`avg_position`, `clicks`, `conversions`, `conversion_rate`, `cost`, `cpl`, `channel`,
`country`, `email`, `vendor_id`, `campaign_id`, `landing_page`, and (when requested)
`conversions_by_type`.

The exact field set varies by account/version. The script passes through every field the
API returns and orders the known ones first.

## Aggregation (`--group-by`)

When `--group-by` is set, records are grouped by the given keys and:

- **Summed:** `clicks`, `conversions`, `cost` (and each `conversions_by_type` entry).
- **Recomputed** from the sums (raw per-record averages are *not* summed):
  - `avg_cpc` = `cost / clicks`
  - `conversion_rate` = `conversions / clicks`
  - `cpl` = `cost / conversions`
  - `avg_position` = clicks-weighted average of per-record `avg_position`

Grouping keys: `month` (derived from `date_of_report` → `YYYY-MM`), `channel`, `country`,
`category`, `product_name`, `vendor_name`, `campaign_name`. Combine with commas, e.g.
`month,channel`.

## Status codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 400 | Invalid parameters |
| 401 / 403 | API key rejected — check the key and that `auth_param` is `Authorization` (`auth_in: header`) |
| 404 | Not found |
| 500 | G2 internal server error |

## Limits & caveats

- **Rate limit:** 1000 requests/minute.
- **Not final until invoiced:** a month-end review can lower click counts, so this report
  may read higher than the monthly invoice. Surface this caveat when reporting spend.
