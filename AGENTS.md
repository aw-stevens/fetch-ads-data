# Ad Analytics Plugin

## Overview

Claude Code plugin providing Google Ads, Google Analytics (GA4), Google Tags, Google Tag Manager, Google Search Console, LinkedIn Ads, G2 Digital Markets, and Microsoft Advertising (Bing Ads) querying via 8 skills and 16 MCP tools. Installed as a marketplace from `aw-stevens/fetch-ads-data`.

## Architecture

```
.claude-plugin/marketplace.json  — Marketplace + plugin manifest
.mcp.json                        — MCP server config (uses ${CLAUDE_PLUGIN_ROOT})
skills/                          — 8 skills (SKILL.md + references/)
scripts/                         — Python scripts called by MCP tools
  config.py                      — Shared config loader (all scripts import this)
  google_ads/                    — query_ads.py, list_accounts.py
  google_analytics/              — query_ga.py, list_properties.py
  google_tags/                   — query_google_tags.py, get_token.py
  google_tag_manager/            — query_gtm.py, list_accounts.py, get_token.py
  google_search_console/         — query_gsc.py, get_token.py
  linkedin_ads/                  — query_li_ads.py, list_li_accounts.py, auth.py, get_token.py
  g2_digital_markets/            — query_g2.py (Click Report; API-key auth)
  microsoft_ads/                 — query_ms_ads.py, list_accounts.py, auth.py, get_token.py
mcp/server.py                    — Single FastMCP server, all 16 tools (subprocess pattern)
hooks/hooks.json                 — SessionStart hook to ensure venv exists
commands/                        — /fetch-ads-data-setup slash command
templates/                       — Config and credential templates
```

## Key Design Decisions

- **Single MCP server** — All 16 tools in one FastMCP process. Tools call scripts via subprocess.
- **Config-driven** — All account IDs, credential paths, and defaults live in `~/.fetch-ads-data/config.json`, not hardcoded.
- **Stable venv** — Python venv at `~/.fetch-ads-data/venv/` persists across plugin updates. Scripts reference it by absolute path.
- **`${CLAUDE_PLUGIN_ROOT}`** — Used in SKILL.md and .mcp.json to resolve paths within the plugin cache (changes on update). Never used for the venv or config paths.

## Runtime Paths

| What | Path |
|------|------|
| Config | `~/.fetch-ads-data/config.json` |
| Venv | `~/.fetch-ads-data/venv/` |
| Google Ads creds | `~/.fetch-ads-data/google-ads.yaml` |
| LinkedIn creds | `~/.fetch-ads-data/linkedin-ads.json` |
| GA4 creds (ADC) | `~/.config/gcloud/application_default_credentials.json` |
| GSC creds | `~/.fetch-ads-data/google-search-console.json` |
| GTM creds | `~/.fetch-ads-data/google-tagmanager.json` |
| G2DM creds | `~/.fetch-ads-data/g2-digital-markets.json` |
| Microsoft Ads creds | `~/.fetch-ads-data/microsoft-ads.json` |

## Development

### Adding a new tool

1. Create the script in `scripts/<service>/`
2. Import `config` for credentials and defaults: `sys.path.insert(0, str(Path(__file__).parent.parent)); import config`
3. Add the MCP tool wrapper in `mcp/server.py` (subprocess pattern)
4. Update the skill's SKILL.md and references if needed
5. Update `templates/config.template.json` if the new service needs config entries

### Adding a new service

1. Create `scripts/<service>/` with query and list scripts
2. Create `skills/<service>/SKILL.md` and `references/`
3. Add service config section to `templates/config.template.json`
4. Add MCP tools to `mcp/server.py`
5. Update `scripts/setup.sh` to handle the new service's credentials
6. Update marketplace.json version

### Testing changes

```bash
# Test a script directly
~/.fetch-ads-data/venv/bin/python scripts/google_ads/query_ads.py "SELECT campaign.name FROM campaign LIMIT 1"

# Test MCP server loads
~/.fetch-ads-data/venv/bin/python -c "
import importlib.util
spec = importlib.util.spec_from_file_location('srv', 'mcp/server.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
print('Server loaded:', mod.mcp.name)
"
```

### Publishing updates

After committing and pushing to `main`, users pick up changes on next session start (marketplace auto-updates). Bump the version in `marketplace.json` for significant changes.

## Style

- Scripts are standalone CLI tools with argparse — testable outside MCP
- MCP tools are thin subprocess wrappers, no business logic
- `config.py` is the only shared module — keep it minimal
- Skills reference `${CLAUDE_PLUGIN_ROOT}` for script paths, `~/.fetch-ads-data/` for runtime paths
- No hardcoded account IDs anywhere except `~/.fetch-ads-data/config.json`
