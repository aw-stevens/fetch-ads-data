# Google Tag Manager — Setup

GTM uses OAuth2 credentials (separate from GA4's Application Default Credentials).

## 1. Enable the Tag Manager API

In your GCP project:
1. Go to APIs & Services > Library
2. Search "Tag Manager API"
3. Click **Enable**

## 2. Add the GTM scope

If your OAuth consent screen doesn't already include the GTM scope:
1. Go to APIs & Services > OAuth consent screen
2. Under Scopes, add: `https://www.googleapis.com/auth/tagmanager.readonly`

This uses the same OAuth client ID/secret from `~/.fetch-ads-data/google-ads.yaml`.

## 3. Generate credentials

```bash
~/.fetch-ads-data/venv/bin/python ${CLAUDE_PLUGIN_ROOT}/scripts/google_tag_manager/get_token.py
```

This opens a browser for authorization and saves credentials to `~/.fetch-ads-data/google-tagmanager.json`.

## 4. Configure accounts

Discover your accounts:
```bash
~/.fetch-ads-data/venv/bin/python ${CLAUDE_PLUGIN_ROOT}/scripts/google_tag_manager/list_accounts.py
```

Then add to `~/.fetch-ads-data/config.json`:
```json
"google_tag_manager": {
  "credentials": "~/.fetch-ads-data/google-tagmanager.json",
  "default_account": "YOUR_ACCOUNT_ID",
  "default_container": "YOUR_CONTAINER_ID",
  "accounts": {
    "YOUR_ACCOUNT_ID": "Friendly Name"
  }
}
```

## Verifying

```bash
~/.fetch-ads-data/venv/bin/python ${CLAUDE_PLUGIN_ROOT}/scripts/google_tag_manager/query_gtm.py \
  --action list-containers
```

This should list your GTM containers.
