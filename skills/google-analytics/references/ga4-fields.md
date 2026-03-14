# GA4 Dimensions & Metrics Reference

Full API schema: https://developers.google.com/analytics/devguides/reporting/data/v1/api-schema

---

## Properties

Configured in `~/.fetch-ads-data/config.json` under `google_analytics.properties`.
Run `list_properties.py` to verify access to all properties.

---

## Common Dimensions

### Traffic & Source
| Dimension | Description |
|---|---|
| `sessionSource` | Traffic source (google, direct, etc.) |
| `sessionMedium` | Medium (organic, cpc, referral, email, etc.) |
| `sessionCampaignName` | Campaign name |
| `sessionDefaultChannelGroup` | Default channel grouping (Organic Search, Paid Search, Direct, etc.) |
| `firstUserSource` | Source that acquired the user |
| `firstUserMedium` | Medium that acquired the user |

### Pages & Content
| Dimension | Description |
|---|---|
| `pagePath` | Page path (e.g., /pricing) |
| `pageTitle` | Page title |
| `landingPage` | First page of session |
| `exitPage` | Last page of session |
| `contentGroup` | Content group if configured |

### Geography
| Dimension | Description |
|---|---|
| `country` | Country name |
| `region` | Region/state |
| `city` | City name |

### Device & Platform
| Dimension | Description |
|---|---|
| `deviceCategory` | desktop, mobile, tablet |
| `operatingSystem` | Windows, macOS, iOS, Android, etc. |
| `browser` | Chrome, Safari, Firefox, etc.) |

### Time
| Dimension | Description |
|---|---|
| `date` | YYYYMMDD format |
| `week` | Week number |
| `month` | Month number (01-12) |
| `year` | Year |
| `dayOfWeek` | 0=Sunday, 6=Saturday |
| `hour` | 00-23 |

### Users
| Dimension | Description |
|---|---|
| `newVsReturning` | new, returning |
| `userAgeBracket` | 18-24, 25-34, etc. |
| `userGender` | male, female |

### Events
| Dimension | Description |
|---|---|
| `eventName` | GA4 event name |

---

## Common Metrics

### Users & Sessions
| Metric | Description |
|---|---|
| `sessions` | Number of sessions |
| `totalUsers` | Total users (use instead of `users`) |
| `newUsers` | New users |
| `activeUsers` | Active users |
| `sessionsPerUser` | Sessions per user |

### Engagement
| Metric | Description |
|---|---|
| `screenPageViews` | Total page views |
| `screenPageViewsPerSession` | Pages per session |
| `engagedSessions` | Sessions with engagement >=10s or conversion |
| `engagementRate` | Engaged sessions / sessions |
| `averageSessionDuration` | Avg session duration in seconds |
| `bounceRate` | Bounce rate (decimal, e.g. 0.45 = 45%) |
| `userEngagementDuration` | Total engaged time in seconds |

### Conversions & Events
| Metric | Description |
|---|---|
| `conversions` | Total conversion events |
| `eventCount` | Total event count |
| `eventCountPerUser` | Events per user |

### Revenue (if ecommerce configured)
| Metric | Description |
|---|---|
| `totalRevenue` | Total revenue |
| `purchaseRevenue` | Revenue from purchases |
| `transactions` | Number of transactions |

---

## Date Formats

```
Named:   today, yesterday, 7daysAgo, 28daysAgo, 30daysAgo, 60daysAgo, 90daysAgo
Custom:  YYYY-MM-DD  (e.g. 2025-01-01)
```

---

## Example Commands

**Traffic by source (last 30 days):**
```bash
python query_ga.py \
  --dimensions sessionSource sessionMedium \
  --metrics sessions newUsers engagementRate \
  --start 30daysAgo --end today --limit 20
```

**Top pages by views:**
```bash
python query_ga.py \
  --dimensions pagePath pageTitle \
  --metrics screenPageViews averageSessionDuration bounceRate \
  --start 30daysAgo --end today --limit 25
```

**Daily sessions trend:**
```bash
python query_ga.py \
  --dimensions date \
  --metrics sessions activeUsers \
  --start 90daysAgo --end today --limit 90
```

**Device breakdown:**
```bash
python query_ga.py \
  --dimensions deviceCategory \
  --metrics sessions engagementRate bounceRate averageSessionDuration \
  --start 30daysAgo --end today
```

---

## Notes

- GA4 metric names differ from Universal Analytics. Key changes:
  - `users` -> use `totalUsers` or `activeUsers`
  - `pageviews` -> `screenPageViews`
  - `bounceRate` is now engagement-based (lower than UA bounce rate)
- `bounceRate` is returned as a decimal (0.45 = 45%) -- multiply by 100 if displaying as %
- `averageSessionDuration` is in seconds
- Cannot combine all dimensions/metrics -- incompatible combinations return errors
