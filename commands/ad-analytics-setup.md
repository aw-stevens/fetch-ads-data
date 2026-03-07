---
name: ad-analytics-setup
description: Set up the ad-analytics plugin (credentials, venv, accounts)
---

Run the ad-analytics setup script to configure credentials and discover accounts:

```bash
bash ${CLAUDE_PLUGIN_ROOT}/scripts/setup.sh
```

This will:
1. Create/verify the Python virtual environment at `~/.ad-analytics/venv`
2. Install required packages (google-ads, google-analytics-data, requests, mcp)
3. Set up credential files for each service
4. Discover and list available accounts/properties
5. Create `~/.ad-analytics/config.json` if it doesn't exist

After setup, edit `~/.ad-analytics/config.json` to set your default accounts and property IDs.
