# Google Search Console Fields Reference

Search Console API — Search Analytics endpoint.

---

## Sites

Configured in `~/.ad-analytics/config.json` under `google_search_console.sites`.
Run `query_gsc.py --action list-sites` to discover accessible sites.

---

## Dimensions

Dimensions control how data is grouped. You can combine multiple dimensions.

| Dimension | Description |
|---|---|
| `query` | Search query text (default) |
| `page` | Landing page URL |
| `country` | 3-letter country code (e.g. USA, GBR, FRA) |
| `device` | DESKTOP, MOBILE, or TABLET |
| `date` | Date (YYYY-MM-DD) — useful for trends |
| `searchAppearance` | Special search result types (e.g. richResults) |

**Multi-dimension examples:**
- `query page` — which page ranks for which query
- `query country` — query performance by country
- `query device` — query performance by device type
- `date device` — daily trend by device

---

## Metrics

Every query returns these four metrics:

| Metric | Description |
|---|---|
| `clicks` | Number of clicks from search results |
| `impressions` | Number of times the site appeared in results |
| `ctr` | Click-through rate (clicks / impressions) |
| `position` | Average ranking position (1 = top) |

---

## Search Types

| Type | Description |
|---|---|
| `web` | Standard Google Search (default) |
| `image` | Google Images |
| `video` | Google Videos |
| `news` | Google News |
| `discover` | Google Discover feed |
| `googleNews` | news.google.com |

---

## Date Range

| Shorthand | Resolves to |
|---|---|
| `today` | Most recent available data (~3 days ago) |
| `yesterday` | Same as today (auto-adjusted for lag) |
| `7daysAgo` | 7 days back from latest available |
| `30daysAgo` | 30 days back (default start) |
| `90daysAgo` | 90 days back |

Or use YYYY-MM-DD format. Dates are automatically capped to the latest available data.

**Important:** Search Console data has a ~3 day lag. The most recent data is typically from 3 days ago.

---

## Tips

- Data is sorted by clicks (descending) by default
- Maximum 25,000 rows per query
- Combine `query` + `page` to see which pages rank for specific terms
- Use `date` dimension for trend analysis
- Country codes follow ISO 3166-1 alpha-3 (USA, GBR, FRA, DEU, etc.)
- Position 1.0 = first result; lower is better
- High impressions + low CTR may indicate titles/descriptions need improvement
- High position (e.g. 8+) with clicks may indicate opportunity for optimization
