# LinkedIn Ads API Fields Reference

LinkedIn Marketing API v202602 — Ad Analytics endpoint.

---

## Accounts

Configured in `~/.ad-analytics/config.json` under `linkedin_ads.accounts`.
Run `list_li_accounts.py` to discover all accessible accounts.

---

## Pivot Dimensions

The `--pivot` parameter determines how data is grouped:

| Pivot | Description |
|---|---|
| `ACCOUNT` | Aggregate by ad account |
| `CAMPAIGN` | By individual campaign (default) |
| `CAMPAIGN_GROUP` | By campaign group |
| `CREATIVE` | By individual creative/ad |
| `MEMBER_COMPANY` | By viewer's company |
| `MEMBER_INDUSTRY` | By viewer's industry |
| `MEMBER_SENIORITY` | By viewer's seniority level |
| `MEMBER_JOB_TITLE` | By viewer's job title |
| `MEMBER_COUNTRY_V2` | By viewer's country |

---

## Available Metrics (--fields)

### Core Metrics
| Field | Description |
|---|---|
| `impressions` | Number of times ads were shown |
| `clicks` | Total clicks |
| `costInLocalCurrency` | Spend in account currency |
| `costInUsd` | Spend in USD |

### Engagement
| Field | Description |
|---|---|
| `externalWebsiteConversions` | Off-LinkedIn conversions |
| `externalWebsitePostClickConversions` | Post-click conversions |
| `externalWebsitePostViewConversions` | Post-view conversions |
| `likes` | Likes/reactions |
| `comments` | Comments |
| `shares` | Shares |
| `follows` | Follows from ads |
| `otherEngagements` | Other engagement actions |
| `totalEngagements` | Sum of all engagements |

### Video
| Field | Description |
|---|---|
| `videoViews` | Video views (2+ seconds) |
| `videoFirstQuartileCompletions` | Viewed 25% |
| `videoMidpointCompletions` | Viewed 50% |
| `videoThirdQuartileCompletions` | Viewed 75% |
| `videoCompletions` | Viewed 100% |
| `videoStarts` | Video play starts |

### Lead Gen
| Field | Description |
|---|---|
| `leadGenerationMailContactInfoShares` | Lead form submissions |
| `oneClickLeads` | One-click lead submissions |

### Common Combined Fields
| Field | Description |
|---|---|
| `dateRange` | Date range for the row (always include) |
| `pivotValues` | Pivot entity URNs (always include) |

---

## Date Range Shortcuts

| Shorthand | Resolves to |
|---|---|
| `today` | Current date |
| `yesterday` | Previous day |
| `7daysAgo` | 7 days back |
| `30daysAgo` | 30 days back |
| `90daysAgo` | 90 days back |

Or use YYYY-MM-DD format.

---

## Granularity

| Value | Description |
|---|---|
| `ALL` | Aggregate entire date range (default) |
| `DAILY` | One row per day per pivot entity |
| `MONTHLY` | One row per month per pivot entity |

---

## Tips

- Always include `dateRange` and `pivotValues` in `--fields` for readable output
- `costInLocalCurrency` is in the account's configured currency (check with `list_li_accounts.py`)
- Demographic pivots (MEMBER_*) only show data for users who have that profile attribute
- The API returns URNs in `pivotValues` — the script extracts the readable ID portion
