# fetch-ads-data

Pull live data from your ad platforms via API — works with any MCP-compatible client or agent harness. Skills and bundled scripts for Claude Code; MCP server for Claude Desktop or any MCP host. A lightweight alternative to token-heavy official MCPs.

## Install

```
/plugin add aw-stevens/fetch-ads-data
```

## Quick Setup

```
/fetch-ads-data-setup
```

Or manually:

```bash
bash ~/.claude/plugins/cache/aw-stevens/fetch-ads-data/*/scripts/setup.sh
```

The setup script creates a Python venv at `~/.fetch-ads-data/venv/`, copies config templates, and walks you through credential setup for each service.

## What You Get

### Skills (6)

| Skill | Description |
|---|---|
| **google-ads** | Query Google Ads with GAQL. Campaigns, keywords, search terms, PMax, etc. |
| **google-analytics** | Query GA4 properties. Traffic, pages, devices, realtime. |
| **google-tags** | GA4 property config — data streams, conversion events, custom dimensions, Ads links. |
| **google-tag-manager** | GTM container inspection — tags, triggers, variables, versions. |
| **google-search-console** | Organic search performance — queries, rankings, CTR, landing pages. |
| **linkedin-ads** | LinkedIn Ads analytics. Campaigns, demographics, spend, conversions. |
| **g2-digital-markets** | G2 Digital Markets Click Report — PPC clicks, cost, conversions, CPL across Capterra, GetApp, Software Advice. |

### MCP Tools (14)

| Tool | Description |
|---|---|
| `google_ads_query` | Run GAQL queries |
| `google_ads_list_accounts` | List accessible Google Ads accounts |
| `google_analytics_query` | Run GA4 reports |
| `google_analytics_realtime` | GA4 realtime data (last 30 minutes) |
| `google_tags_query` | Query GA4 property configuration |
| `google_tags_list_streams` | List data streams / measurement IDs |
| `gtm_query` | Query GTM container configuration (tags, triggers, variables) |
| `gtm_list_accounts` | List GTM accounts and containers |
| `google_search_console_query` | Search analytics — queries, pages, CTR, position |
| `google_search_console_list_sites` | List accessible Search Console sites |
| `linkedin_ads_query` | Query LinkedIn Ads analytics |
| `linkedin_ads_list_accounts` | List LinkedIn ad accounts |
| `g2_digital_markets_query` | Query the G2DM Click Report (raw or aggregated by month/channel/vendor) |
| `g2_digital_markets_verify` | Verify the G2 Digital Markets API key |

Skills trigger automatically in Claude Code based on what you ask. MCP tools are available in both Claude Code and Claude Desktop.

## Configuration

All config lives in `~/.fetch-ads-data/`:

```
~/.fetch-ads-data/
├── config.json                  # Account IDs, credential paths, defaults
├── venv/                        # Python virtual environment
├── google-ads.yaml              # Google Ads API credentials
├── google-search-console.json   # Search Console OAuth tokens
├── google-tagmanager.json       # Google Tag Manager OAuth tokens
├── linkedin-ads.json            # LinkedIn OAuth tokens
└── g2-digital-markets.json      # G2 Digital Markets API key

```

Edit `config.json` to set default accounts/properties and add or remove entries. The `default_accounts` / `default_properties` arrays control which accounts are queried when no specific ID is passed.

```json
{
  "google_ads": {
    "credentials": "~/.fetch-ads-data/google-ads.yaml",
    "default_accounts": ["123-456-7890"],
    "accounts": {
      "123-456-7890": "My Company"
    }
  },
  "google_analytics": {
    "credentials": "~/.config/gcloud/application_default_credentials.json",
    "default_properties": ["properties/123456789"],
    "properties": {
      "properties/123456789": "My Website"
    }
  },
  "linkedin_ads": {
    "credentials": "~/.fetch-ads-data/linkedin-ads.json",
    "default_accounts": ["123456789"],
    "accounts": {
      "123456789": "My Company"
    }
  },
  "google_search_console": {
    "credentials": "~/.fetch-ads-data/google-search-console.json",
    "default_site": "https://example.com/",
    "sites": {
      "https://example.com/": "My Website"
    }
  },
  "google_tag_manager": {
    "credentials": "~/.fetch-ads-data/google-tagmanager.json",
    "default_account": "123456",
    "default_container": "789012",
    "accounts": {
      "123456": "My GTM Account"
    }
  },
  "g2_digital_markets": {
    "credentials": "~/.fetch-ads-data/g2-digital-markets.json",
    "base_url": "https://public-api.capterra.com/v2",
    "auth_in": "header",
    "auth_param": "Authorization"
  }
}
```

## Credential Setup by Service

Each service requires its own credentials. You don't need all seven — set up only the ones you use.

### Google Ads

**What you need:** A Google Ads developer token, an OAuth2 client (client ID + secret), and a refresh token.

**GCP setup:**
1. Go to [Google Cloud Console](https://console.cloud.google.com/) and create or select a project
2. Enable the **Google Ads API**
3. Go to **APIs & Services > Credentials** and create an **OAuth 2.0 Client ID** (Desktop app type)
4. Note the `client_id` and `client_secret`

**Developer token:**
1. Log into [Google Ads](https://ads.google.com/)
2. Go to **Tools & Settings > API Center**
3. Apply for a developer token (test or production)

**Refresh token:**
1. Use the [Google OAuth Playground](https://developers.google.com/oauthplayground/) or the `google-ads` library's `generate_user_credentials.py` to generate a refresh token with the `https://www.googleapis.com/auth/adwords` scope

**Credential file:** `~/.fetch-ads-data/google-ads.yaml`
```yaml
developer_token: YOUR_DEVELOPER_TOKEN
client_id: YOUR_CLIENT_ID.apps.googleusercontent.com
client_secret: YOUR_CLIENT_SECRET
refresh_token: YOUR_REFRESH_TOKEN
use_proto_plus: True
# login_customer_id: YOUR_MCC_ID  # if using a manager account
```

### Google Analytics (GA4)

**What you need:** Google Application Default Credentials (ADC) with access to your GA4 properties.

**Setup:**
```bash
gcloud auth application-default login
```

That's it. Your Google account needs at least Viewer access to the GA4 properties you want to query. No API keys or OAuth clients needed — ADC handles everything.

**Credential file:** `~/.config/gcloud/application_default_credentials.json` (managed by gcloud)

### Google Tags (GA4 Admin API)

**What you need:** Uses the same ADC credentials as Google Analytics. No additional setup required.

The Google Tags tool queries GA4 property configuration (data streams, key events, custom dimensions, linked Ads accounts) via the GA4 Admin API, which uses the same `analytics.readonly` scope as the Data API.

### Google Tag Manager

**What you need:** An OAuth2 refresh token with the `tagmanager.readonly` scope. Reuses the same OAuth client as Google Ads.

**GCP setup:**
1. In the same GCP project as Google Ads, enable the **Tag Manager API**
2. In your OAuth consent screen, add `https://www.googleapis.com/auth/tagmanager.readonly` to the authorized scopes

**Generate token:**
```bash
~/.fetch-ads-data/venv/bin/python ~/.claude/plugins/cache/aw-stevens/fetch-ads-data/*/scripts/google_tag_manager/get_token.py
```

This opens a browser for OAuth consent and saves credentials to `~/.fetch-ads-data/google-tagmanager.json`. Your Google account needs at least Read access to the GTM containers you want to query.

**Credential file:** `~/.fetch-ads-data/google-tagmanager.json` (auto-generated by `get_token.py`)

### Google Search Console

**What you need:** An OAuth2 refresh token with the `webmasters.readonly` scope. Reuses the same OAuth client as Google Ads.

**GCP setup:**
1. In the same GCP project as Google Ads, enable the **Search Console API**
2. In your OAuth client's settings, add `https://www.googleapis.com/auth/webmasters.readonly` to the authorized scopes

**Generate token:**
```bash
~/.fetch-ads-data/venv/bin/python ~/.claude/plugins/cache/aw-stevens/fetch-ads-data/*/scripts/google_search_console/get_token.py
```

This opens a browser for OAuth consent and saves credentials to `~/.fetch-ads-data/google-search-console.json`. Your Google account needs to be a verified owner or user of the Search Console properties you want to query.

**Credential file:** `~/.fetch-ads-data/google-search-console.json` (auto-generated by `get_token.py`)

### LinkedIn Ads

**What you need:** A LinkedIn Developer app with Marketing API access, plus an OAuth2 refresh token.

**LinkedIn setup:**
1. Go to [LinkedIn Developers](https://www.linkedin.com/developers/apps) and create an app
2. Under **Products**, request access to **Marketing Developer Platform** (requires approval)
3. Under **Auth**, note the `client_id` and `client_secret`
4. Add `http://localhost:8080/callback` as an authorized redirect URL

**Generate token:**
1. Create the initial credential file at `~/.fetch-ads-data/linkedin-ads.json`:
   ```json
   {
     "client_id": "YOUR_CLIENT_ID",
     "client_secret": "YOUR_CLIENT_SECRET",
     "redirect_uri": "http://localhost:8080/callback"
   }
   ```
2. Run the OAuth flow:
   ```bash
   ~/.fetch-ads-data/venv/bin/python ~/.claude/plugins/cache/aw-stevens/fetch-ads-data/*/scripts/linkedin_ads/get_token.py
   ```
   This opens a browser, completes OAuth, and adds the `access_token` and `refresh_token` to the credential file.

**Credential file:** `~/.fetch-ads-data/linkedin-ads.json` (created manually, then updated by `get_token.py`)

### G2 Digital Markets

**What you need:** An API key for the G2 Digital Markets **Click Report API** (PPC across Capterra, GetApp, Software Advice). Request it from your G2DM account manager.

**Setup:**
1. Create `~/.fetch-ads-data/g2-digital-markets.json` with your key:
   ```json
   {
     "api_key": "YOUR_API_KEY"
   }
   ```
2. Verify it works:
   ```bash
   ~/.fetch-ads-data/venv/bin/python ~/.claude/plugins/cache/aw-stevens/fetch-ads-data/*/scripts/g2_digital_markets/query_g2.py --action verify
   ```

The endpoint and auth method are configured in `config.json` under `g2_digital_markets`. The key is sent as a raw `Authorization` header (no `Bearer` prefix) — this is what the Click Report API expects. The `auth_in` (`header`/`query`) and `auth_param` settings let you adjust this if G2DM changes their scheme.

**Credential file:** `~/.fetch-ads-data/g2-digital-markets.json` (created manually)

## Claude Desktop

The MCP server works in Claude Desktop without Claude Code. After completing credential setup above:

1. Run the setup script directly to create the venv and config:
   ```bash
   bash ~/.claude/plugins/cache/aw-stevens/fetch-ads-data/*/scripts/setup.sh
   ```
   Or clone the repo and run `bash scripts/setup.sh` from the repo root.

2. Add to your `claude_desktop_config.json`:
   ```json
   {
     "mcpServers": {
       "fetch-ads-data": {
         "command": "/Users/yourname/.fetch-ads-data/venv/bin/python",
         "args": ["/path/to/fetch-ads-data/mcp/server.py"]
       }
     }
   }
   ```

3. Restart Claude Desktop.

Note: Skills are Claude Code–only. In Claude Desktop you get the 14 MCP tools directly.

## Requirements

- Python 3.10+
- `gcloud` CLI (for Google Analytics ADC)
- A GCP project with the relevant APIs enabled (Google Ads, Search Console)
- A LinkedIn Developer app (for LinkedIn Ads)

## Development

See `AGENTS.md` for project conventions and how to add new tools or services.
