# Google Ads — Setup

Run the plugin setup script:

```bash
bash ${CLAUDE_PLUGIN_ROOT}/scripts/setup.sh
```

Or use the `/fetch-ads-data-setup` command.

The script will:
1. Create a Python venv at `~/.fetch-ads-data/venv`
2. Install the `google-ads` and `mcp` packages
3. Copy credentials template to `~/.fetch-ads-data/google-ads.yaml` if no credentials file exists
4. Verify by listing accessible Google Ads accounts

## Credentials

### 1. GCP Project Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/) and create or select a project
2. Enable the **Google Ads API** (APIs & Services > Library)
3. Go to **APIs & Services > Credentials**
4. Create an **OAuth 2.0 Client ID** with application type **Desktop app**
5. Note the `client_id` and `client_secret`

This same OAuth client can be reused for Search Console and Google Tags by adding their scopes.

### 2. Developer Token

1. Log into [Google Ads](https://ads.google.com/)
2. Go to **Tools & Settings > API Center** (under Setup)
3. Apply for a developer token
4. A test token works for read-only queries against your own accounts

### 3. Refresh Token

Generate a refresh token with the `adwords` scope using one of:

- **OAuth Playground**: Use [developers.google.com/oauthplayground](https://developers.google.com/oauthplayground/) with your client ID/secret and the scope `https://www.googleapis.com/auth/adwords`
- **google-ads library**: Run `generate_user_credentials.py` from the google-ads Python package

### 4. Credential File

Save to `~/.fetch-ads-data/google-ads.yaml`:

```yaml
developer_token: YOUR_DEVELOPER_TOKEN
client_id: YOUR_CLIENT_ID.apps.googleusercontent.com
client_secret: YOUR_CLIENT_SECRET
refresh_token: YOUR_REFRESH_TOKEN
use_proto_plus: True
```

If you access accounts through a Manager (MCC) account, add:
```yaml
login_customer_id: YOUR_MCC_ID
```

### 5. Config

Add your accounts to `~/.fetch-ads-data/config.json`:

```json
{
  "google_ads": {
    "credentials": "~/.fetch-ads-data/google-ads.yaml",
    "default_accounts": ["1234567890"],
    "accounts": {
      "1234567890": "My Account",
      "0987654321": "Other Account"
    }
  }
}
```

## Verifying

```bash
~/.fetch-ads-data/venv/bin/python ${CLAUDE_PLUGIN_ROOT}/scripts/google_ads/list_accounts.py
```
