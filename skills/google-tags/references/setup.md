# Google Tags — Setup

No additional setup required beyond Google Analytics.

Google Tags uses the GA4 Admin API, which shares the same Application Default Credentials as the GA4 Data API. If Google Analytics is working, Google Tags will work too.

## Credentials

Same as Google Analytics — uses ADC:

```bash
gcloud auth application-default login
```

Your account needs at least Viewer access to the GA4 properties.

## Verifying

```bash
~/.fetch-ads-data/venv/bin/python ${CLAUDE_PLUGIN_ROOT}/scripts/google_tags/query_google_tags.py \
  --action list-streams
```

This should list your data streams with measurement IDs (G-XXXXX).
