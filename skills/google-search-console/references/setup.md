# Google Search Console — Setup

Run the plugin setup script:

```bash
bash ${CLAUDE_PLUGIN_ROOT}/scripts/setup.sh
```

Or use the `/ad-analytics-setup` command.

## Credentials

Search Console requires a dedicated OAuth2 token because its scope (`webmasters.readonly`) isn't included in standard ADC. The setup reuses the same OAuth client from Google Ads.

### Prerequisites

1. A GCP project with the **Search Console API** enabled
2. An OAuth 2.0 client (Desktop type) — the same one used for Google Ads works
3. The `webmasters.readonly` scope added to the OAuth client's authorized scopes

### Enable the API

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Select your project
3. Go to **APIs & Services > Library**
4. Search for "Google Search Console API" and enable it

### Add the scope to your OAuth client

1. Go to **APIs & Services > OAuth consent screen**
2. Under **Scopes**, add `https://www.googleapis.com/auth/webmasters.readonly`
3. Save

### Generate the token

```bash
~/.ad-analytics/venv/bin/python ${CLAUDE_PLUGIN_ROOT}/scripts/google_search_console/get_token.py
```

This opens a browser for OAuth consent and saves credentials to `~/.ad-analytics/google-search-console.json`.

### Config

Add your sites to `~/.ad-analytics/config.json`:

```json
{
  "google_search_console": {
    "credentials": "~/.ad-analytics/google-search-console.json",
    "default_site": "https://example.com/",
    "sites": {
      "https://example.com/": "My Site"
    }
  }
}
```

**Important:** Site URLs must match exactly what Search Console shows — including the trailing slash.

## Verifying

```bash
~/.ad-analytics/venv/bin/python ${CLAUDE_PLUGIN_ROOT}/scripts/google_search_console/query_gsc.py \
  --action list-sites
```

This should list all Search Console properties your account has access to.
