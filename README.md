# Ad Analytics Plugin for Claude Code

Query and analyze ad performance across Google Ads, Google Analytics (GA4), and LinkedIn Ads — all from Claude Code.

## Install

```
/plugin add aw-stevens/ad-analytics
```

## Setup

```
/ad-analytics-setup
```

Or manually:

```bash
bash ~/.claude/plugins/cache/aw-stevens/ad-analytics/*/scripts/setup.sh
```

## What you get

### Skills (3)
- **google-ads** — Query Google Ads with GAQL. Campaigns, keywords, search terms, PMax, etc.
- **google-analytics** — Query GA4 properties. Traffic, pages, devices, realtime.
- **linkedin-ads** — Query LinkedIn Ads analytics. Campaigns, demographics, spend.

### MCP Tools (6)
- `google_ads_query` — Run GAQL queries
- `google_ads_list_accounts` — List accessible Google Ads accounts
- `google_analytics_query` — Run GA4 reports
- `google_analytics_realtime` — GA4 realtime data
- `linkedin_ads_query` — Query LinkedIn Ads analytics
- `linkedin_ads_list_accounts` — List LinkedIn ad accounts

## Configuration

All config lives in `~/.ad-analytics/`:

```
~/.ad-analytics/
├── config.json          # Account IDs, credential paths, defaults
├── venv/                # Python virtual environment
├── google-ads.yaml      # Google Ads API credentials
└── linkedin-ads.json    # LinkedIn OAuth tokens
```

Edit `config.json` to set default accounts and add/remove properties.

## Requirements

- Python 3.10+
- Google Ads API credentials (developer token + OAuth2)
- Google Cloud ADC for GA4 (`gcloud auth application-default login`)
- LinkedIn Developer app with Marketing API access
