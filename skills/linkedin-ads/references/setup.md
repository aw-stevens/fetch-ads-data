# LinkedIn Ads — Setup

Run the plugin setup script:

```bash
bash ${CLAUDE_PLUGIN_ROOT}/scripts/setup.sh
```

Or use the `/fetch-ads-data-setup` command.

The script will:
1. Create a Python venv at `~/.fetch-ads-data/venv`
2. Install the `requests` and `mcp` packages
3. Check for LinkedIn credentials at `~/.fetch-ads-data/linkedin-ads.json`
4. Optionally run the OAuth flow to generate tokens

## Credentials

1. Create a LinkedIn Developer app at https://www.linkedin.com/developers/apps
2. Enable the Marketing Developer Platform product
3. Create `~/.fetch-ads-data/linkedin-ads.json` with:
   ```json
   {
     "client_id": "YOUR_CLIENT_ID",
     "client_secret": "YOUR_CLIENT_SECRET",
     "redirect_uri": "http://localhost:8080/callback"
   }
   ```
4. Run the token generation script:
   ```bash
   ~/.fetch-ads-data/venv/bin/python ${CLAUDE_PLUGIN_ROOT}/scripts/linkedin_ads/get_token.py
   ```
