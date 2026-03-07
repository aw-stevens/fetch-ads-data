# Google Ads — Setup

Run the plugin setup script:

```bash
bash ${CLAUDE_PLUGIN_ROOT}/scripts/setup.sh
```

Or use the `/ad-analytics-setup` command.

The script will:
1. Create a Python venv at `~/.ad-analytics/venv`
2. Install the `google-ads` and `mcp` packages
3. Copy credentials template to `~/.ad-analytics/google-ads.yaml` if no credentials file exists
4. Verify by listing accessible Google Ads accounts

## Credentials

The skill requires `~/.ad-analytics/google-ads.yaml` with your developer token and OAuth2 credentials.
See `templates/google-ads.yaml.template` for the required format.

To obtain credentials, contact whoever manages the Google Ads API project,
or follow the [Google Ads API quickstart](https://developers.google.com/google-ads/api/docs/get-started/introduction).
