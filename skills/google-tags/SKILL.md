---
name: google-tags
description: Query Google Tags and GA4 property configuration. Use when asked about measurement IDs, data streams, conversion events, key events, custom dimensions, custom metrics, Google Ads account linking, or tag setup for any configured GA4 property.
---

# Google Tags

## Prerequisites

First-time setup required per machine. Run `/fetch-ads-data-setup` or `bash ${CLAUDE_PLUGIN_ROOT}/scripts/setup.sh`.

**Python**: `~/.fetch-ads-data/venv/bin/python`

**Properties**: Uses the same GA4 properties configured in `~/.fetch-ads-data/config.json` under `google_analytics.properties`.

---

## Workflow

1. Identify which property the user is asking about (default from config)
2. Choose the right action — consult `references/admin-api-fields.md` if needed
3. Run `query_google_tags.py`
4. Interpret and present results

---

## Running Queries

```bash
~/.fetch-ads-data/venv/bin/python \
  ${CLAUDE_PLUGIN_ROOT}/scripts/google_tags/query_google_tags.py \
  --action <ACTION> \
  --property <ID> \
  --format table
```

**Actions:**
- `list-streams` — Data streams with measurement IDs (G-XXXXX)
- `list-key-events` — Conversion/key events configured for the property
- `list-custom-dimensions` — Custom event-scoped and user-scoped dimensions
- `list-custom-metrics` — Custom metrics with units
- `list-ads-links` — Linked Google Ads accounts

**Args:**
- `--property` — GA4 property ID (defaults to first default from config)
- `--format` — `table` (default), `csv`, `json`

---

## Quick Examples

**List all measurement IDs (Google Tags):**
```bash
--action list-streams
```

**See which events are marked as conversions:**
```bash
--action list-key-events --property 123456789
```

**Audit custom dimensions:**
```bash
--action list-custom-dimensions
```

**Check which Google Ads accounts are linked:**
```bash
--action list-ads-links --property 123456789
```

---

## Reference

See `references/admin-api-fields.md` for:
- All available actions and their output columns
- Property ID lookup
- Common use cases
