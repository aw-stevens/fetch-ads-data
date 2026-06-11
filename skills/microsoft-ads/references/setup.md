# Microsoft Advertising (Bing Ads) — Setup

Run the plugin setup script:

```bash
bash ${CLAUDE_PLUGIN_ROOT}/scripts/setup.sh
```

Or use the `/fetch-ads-data-setup` command.

The script will:
1. Create a Python venv at `~/.fetch-ads-data/venv`
2. Install the `bingads`, `requests`, and `mcp` packages
3. Check for Microsoft Advertising credentials at `~/.fetch-ads-data/microsoft-ads.json`
4. Point you at the OAuth flow to generate a refresh token

## What you need

Microsoft's API requires **two** distinct credentials:

1. **A registered application (client_id)** — for OAuth user authorization.
2. **A developer token** — a separate key that authorizes API access for your account.

### 1. Register an application (Azure / Microsoft Entra)

1. Go to the [Azure portal → App registrations](https://portal.azure.com) (or
   https://apps.dev.microsoft.com) and **New registration**.
2. Account types: choose multi-tenant + personal Microsoft accounts (or match your org).
3. Under **Authentication → Add a platform → Mobile and desktop applications**, add the
   redirect URI:
   ```
   https://login.microsoftonline.com/common/oauth2/nativeclient
   ```
   This native/desktop flow needs **no client secret**.
4. Under **API permissions**, add delegated permission for Microsoft Advertising
   (`https://ads.microsoft.com/msads.manage` + `offline_access`).
5. Copy the **Application (client) ID**.

### 2. Get a developer token

1. Sign in to [Microsoft Advertising](https://ads.microsoft.com) with an account that has
   access to the ad accounts you want to query.
2. Account settings → **Developer settings** → request/copy a **production developer token**.
   (The universal **sandbox** token `BBD37VB98` works only against the sandbox environment.)

### 3. Create the credentials file

Create `~/.fetch-ads-data/microsoft-ads.json` (the setup script copies a template):

```json
{
  "client_id": "YOUR_AZURE_APP_CLIENT_ID",
  "developer_token": "YOUR_MICROSOFT_ADVERTISING_DEVELOPER_TOKEN",
  "tenant": "common"
}
```

### 4. Authenticate (one-time, generates a refresh token)

```bash
~/.fetch-ads-data/venv/bin/python ${CLAUDE_PLUGIN_ROOT}/scripts/microsoft_ads/get_token.py
```

The desktop flow opens a browser for consent. Because it uses Microsoft's fixed
native-client redirect (not a localhost server), the browser lands on a page whose URL
contains `?code=...`. **Copy that full URL and paste it back into the terminal.** The script
then stores a `refresh_token` (valid up to 90 days, auto-refreshed on use) and auto-detects
your `customer_id`.

### 5. Discover accounts and configure defaults

```bash
~/.fetch-ads-data/venv/bin/python ${CLAUDE_PLUGIN_ROOT}/scripts/microsoft_ads/list_accounts.py
```

Add the account IDs you care about to `~/.fetch-ads-data/config.json`:

```json
"microsoft_ads": {
  "credentials": "~/.fetch-ads-data/microsoft-ads.json",
  "default_accounts": ["1234567"],
  "accounts": { "1234567": "My Company Bing" }
}
```

## Re-authenticating

If a refresh token expires (90-day max, or the user changed their password / revoked
consent), re-run `get_token.py`.
