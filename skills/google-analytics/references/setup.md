# Google Analytics — Setup

Run the plugin setup script:

```bash
bash ${CLAUDE_PLUGIN_ROOT}/scripts/setup.sh
```

Or use the `/ad-analytics-setup` command.

The script will:
1. Create a Python venv at `~/.ad-analytics/venv`
2. Install the `google-analytics-data` and `mcp` packages
3. Check for Application Default Credentials and prompt you to authenticate if missing
4. Verify by running a test query

## Credentials

This skill uses Google Application Default Credentials (ADC). Authenticate with your Google account:

```bash
gcloud auth application-default login
```

Your account needs Viewer access to the GA4 properties. Ask a property administrator to grant it if you don't have it.
