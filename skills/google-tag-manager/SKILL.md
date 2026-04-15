---
name: google-tag-manager
description: Query Google Tag Manager container configuration. Use when asked about GTM tags, triggers, variables, container setup, tag audit, what tags are firing, trigger conditions, custom HTML tags, GA4 configuration tags, conversion tracking tags, or any GTM container inspection.
---

# Google Tag Manager

## Prerequisites

First-time setup required per machine. Run `/fetch-ads-data-setup` or `bash ${CLAUDE_PLUGIN_ROOT}/scripts/setup.sh`.

**Python**: `~/.fetch-ads-data/venv/bin/python`

**Credentials**: OAuth2 — requires `~/.fetch-ads-data/google-tagmanager.json`. See `references/setup.md`.

**Config**: GTM account and container IDs in `~/.fetch-ads-data/config.json` under `google_tag_manager`.

---

## Workflow

1. Identify which account/container the user is asking about (defaults from config)
2. Choose the right action — consult `references/gtm-api-fields.md` if needed
3. Run `query_gtm.py` (or `list_accounts.py` for discovery)
4. Interpret and present results

---

## Running Queries

```bash
~/.fetch-ads-data/venv/bin/python \
  ${CLAUDE_PLUGIN_ROOT}/scripts/google_tag_manager/query_gtm.py \
  --action <ACTION> \
  --account <ACCOUNT_ID> \
  --container <CONTAINER_ID> \
  --format table
```

**Actions:**
- `list-containers` — Containers in an account
- `list-workspaces` — Workspaces in a container
- `list-tags` — All tags with type, firing triggers, and key parameters
- `list-triggers` — All triggers with type and conditions
- `list-variables` — Custom variables
- `list-built-in-variables` — Enabled built-in variables
- `list-folders` — Tag folders
- `get-version` — Currently published (live) container version

**Args:**
- `--account` — GTM account ID (defaults from config)
- `--container` — GTM container ID (defaults from config)
- `--workspace` — Workspace ID (auto-detects default if not specified)
- `--format` — `table` (default), `csv`, `json`

---

## Quick Examples

**List all containers in an account:**
```bash
--action list-containers
```

**See all tags with their firing triggers:**
```bash
--action list-tags
```

**Audit trigger setup:**
```bash
--action list-triggers --format json
```

**Check custom variables:**
```bash
--action list-variables
```

**See what's currently published:**
```bash
--action get-version
```

**Discover all accounts and containers:**
```bash
~/.fetch-ads-data/venv/bin/python \
  ${CLAUDE_PLUGIN_ROOT}/scripts/google_tag_manager/list_accounts.py
```

---

## Reference

See `references/gtm-api-fields.md` for:
- All available actions and their output columns
- GTM entity hierarchy (Account > Container > Workspace)
- Common tag types, trigger types, variable types
- Common use cases
