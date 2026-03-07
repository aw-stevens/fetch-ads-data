# GAQL Fields Reference

GAQL (Google Ads Query Language) is SQL-like. Structure:
```
SELECT field1, field2 FROM resource WHERE conditions ORDER BY field LIMIT n
```

## Accounts

Configured in `~/.ad-analytics/config.json` under `google_ads.accounts`.
Run `list_accounts.py` to discover all accessible accounts.

---

## Resources & Key Fields

### `campaign` — Campaign-level data

```sql
SELECT
  campaign.id,
  campaign.name,
  campaign.status,                    -- ENABLED, PAUSED, REMOVED
  campaign.advertising_channel_type,  -- SEARCH, DISPLAY, PERFORMANCE_MAX, VIDEO, SHOPPING
  campaign.bidding_strategy_type,     -- TARGET_CPA, TARGET_ROAS, MAXIMIZE_CONVERSIONS, etc.
  campaign.campaign_budget,
  metrics.impressions,
  metrics.clicks,
  metrics.cost_micros,                -- divide by 1,000,000 for dollars (done automatically)
  metrics.conversions,
  metrics.conversions_value,
  metrics.ctr,
  metrics.average_cpc,
  metrics.search_impression_share,
  metrics.search_top_impression_share
FROM campaign
WHERE segments.date DURING LAST_30_DAYS
  AND campaign.status = 'ENABLED'
ORDER BY metrics.cost_micros DESC
LIMIT 50
```

### `ad_group` — Ad group-level data

```sql
SELECT
  campaign.name,
  ad_group.id,
  ad_group.name,
  ad_group.status,
  ad_group.type,                -- SEARCH_STANDARD, DISPLAY_STANDARD, etc.
  metrics.impressions,
  metrics.clicks,
  metrics.cost_micros,
  metrics.conversions,
  metrics.average_cpc,
  metrics.ctr
FROM ad_group
WHERE segments.date DURING LAST_30_DAYS
  AND ad_group.status = 'ENABLED'
ORDER BY metrics.cost_micros DESC
LIMIT 100
```

### `keyword_view` — Keyword performance

```sql
SELECT
  campaign.name,
  ad_group.name,
  ad_group_criterion.keyword.text,
  ad_group_criterion.keyword.match_type,  -- EXACT, PHRASE, BROAD
  ad_group_criterion.status,
  ad_group_criterion.quality_info.quality_score,
  metrics.impressions,
  metrics.clicks,
  metrics.cost_micros,
  metrics.conversions,
  metrics.average_cpc,
  metrics.ctr,
  metrics.search_impression_share
FROM keyword_view
WHERE segments.date DURING LAST_30_DAYS
  AND ad_group_criterion.status = 'ENABLED'
ORDER BY metrics.impressions DESC
LIMIT 200
```

### `search_term_view` — Actual search queries that triggered ads

```sql
SELECT
  campaign.name,
  ad_group.name,
  search_term_view.search_term,
  search_term_view.status,         -- ADDED, EXCLUDED, NONE
  metrics.impressions,
  metrics.clicks,
  metrics.cost_micros,
  metrics.conversions,
  metrics.ctr
FROM search_term_view
WHERE segments.date DURING LAST_30_DAYS
ORDER BY metrics.impressions DESC
LIMIT 200
```

### `ad_group_ad` — Individual ad performance

```sql
SELECT
  campaign.name,
  ad_group.name,
  ad_group_ad.ad.id,
  ad_group_ad.ad.type,
  ad_group_ad.status,
  ad_group_ad.ad.responsive_search_ad.headlines,
  metrics.impressions,
  metrics.clicks,
  metrics.cost_micros,
  metrics.conversions,
  metrics.ctr
FROM ad_group_ad
WHERE segments.date DURING LAST_30_DAYS
  AND ad_group_ad.status = 'ENABLED'
ORDER BY metrics.impressions DESC
LIMIT 100
```

### `asset_group` — Performance Max asset groups

PMax campaigns use asset groups instead of ad groups/keywords. Use `campaign.advertising_channel_type = 'PERFORMANCE_MAX'` to filter.

```sql
-- PMax campaign performance (campaign level)
SELECT
  campaign.id,
  campaign.name,
  campaign.status,
  metrics.impressions,
  metrics.clicks,
  metrics.cost_micros,
  metrics.conversions,
  metrics.conversions_value
FROM campaign
WHERE campaign.advertising_channel_type = 'PERFORMANCE_MAX'
  AND segments.date DURING LAST_30_DAYS
```

```sql
-- PMax asset groups
SELECT
  campaign.name,
  asset_group.id,
  asset_group.name,
  asset_group.status,
  asset_group.final_urls,
  metrics.impressions,
  metrics.clicks,
  metrics.cost_micros,
  metrics.conversions
FROM asset_group
WHERE segments.date DURING LAST_30_DAYS
```

**PMax limitations**: Keywords, search terms, and placement data are not available for PMax campaigns. Performance breakdown by channel is not available.

### `geographic_view` — Performance by location

```sql
SELECT
  geographic_view.country_criterion_id,
  geographic_view.location_type,
  campaign.name,
  metrics.impressions,
  metrics.clicks,
  metrics.cost_micros,
  metrics.conversions
FROM geographic_view
WHERE segments.date DURING LAST_30_DAYS
ORDER BY metrics.cost_micros DESC
```

---

## Common Segments

Segments split metrics by a dimension. Add to SELECT and WHERE:

| Segment | Values |
|---|---|
| `segments.date` | `'2025-01-01'` or ranges |
| `segments.week` | Week starting date |
| `segments.month` | Month as date |
| `segments.device` | `DESKTOP`, `MOBILE`, `TABLET` |
| `segments.day_of_week` | `MONDAY`, `TUESDAY`, etc. |
| `segments.hour` | 0-23 |
| `segments.ad_network_type` | `SEARCH`, `SEARCH_PARTNERS`, `CONTENT` |
| `segments.conversion_action_name` | Name of specific conversion action |

---

## Date Range Filters

```sql
-- Named ranges (use in WHERE segments.date DURING ...)
LAST_7_DAYS
LAST_14_DAYS
LAST_30_DAYS
LAST_BUSINESS_WEEK
LAST_WEEK_SUN_SAT
THIS_MONTH
LAST_MONTH
THIS_YEAR

-- Custom range
WHERE segments.date BETWEEN '2025-01-01' AND '2025-01-31'
```

---

## Common WHERE Conditions

```sql
AND campaign.status = 'ENABLED'           -- ENABLED, PAUSED, REMOVED
AND ad_group.status = 'ENABLED'
AND ad_group_criterion.status = 'ENABLED'
AND campaign.advertising_channel_type = 'SEARCH'   -- or PERFORMANCE_MAX, DISPLAY, VIDEO
AND metrics.impressions > 0
AND metrics.cost_micros > 0
```

---

## Tips

- **Micros**: `metrics.cost_micros` is in millionths of the currency unit. The script automatically converts to dollars.
- **Segmenting**: Adding `segments.date` to SELECT will return one row per day per entity.
- **Resource limits**: Each resource type has allowed field combinations. If you get an error about incompatible fields, try a different resource.
- **PMax**: PMax campaigns appear in `campaign` queries but don't support keyword/search term resources.
