# G2 Digital Markets — Setup

Run the plugin setup script:

```bash
bash ${CLAUDE_PLUGIN_ROOT}/scripts/setup.sh
```

Or use the `/fetch-ads-data-setup` command.

## Credentials

The Click Report API uses a single **API key** (no OAuth). Request the key from your
G2 Digital Markets account manager, then store it at:

```
~/.fetch-ads-data/g2-digital-markets.json
```

```json
{
  "api_key": "YOUR_API_KEY"
}
```

The setup script drops a template at this path if one doesn't exist — just paste the key in.

## Config

Endpoint and auth settings live in `~/.fetch-ads-data/config.json`:

```json
{
  "g2_digital_markets": {
    "credentials": "~/.fetch-ads-data/g2-digital-markets.json",
    "base_url": "https://public-api.capterra.com/v2",
    "auth_in": "header",
    "auth_param": "Authorization"
  }
}
```

- `base_url` — Click Report API base (default `https://public-api.capterra.com/v2`).
- `auth_in` — how the key is sent: `header` (default) or `query`.
- `auth_param` — the header/param name for the key. The Click Report API expects the key
  in a raw `Authorization` header (no `Bearer` prefix), so the default is `Authorization`.
  These settings exist so you can adapt if G2DM changes their auth scheme.

## Verifying

```bash
~/.fetch-ads-data/venv/bin/python \
  ${CLAUDE_PLUGIN_ROOT}/scripts/g2_digital_markets/query_g2.py --action verify
```

A successful run prints `OK — G2 Digital Markets API key works.` If you see a `401`/`403`,
double-check the key, and confirm `auth_param` is `Authorization` with `auth_in` set to
`header` in config.json.

## Rate limits

1000 requests/minute. The query script paginates with a cursor and stays well under this
for normal date ranges; very large ranges are capped by `--max-pages` (default 100).
