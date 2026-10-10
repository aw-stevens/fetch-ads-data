# Security Policy

## Reporting a vulnerability

Please **don't open a public issue** for security problems. Report them privately via
[GitHub's private vulnerability reporting](https://github.com/aw-stevens/fetch-ads-data/security/advisories/new)
(the **Security** tab → **Report a vulnerability**). I'll acknowledge reports as soon as I can.

## Never share credentials

This plugin works with OAuth refresh tokens, developer tokens and API keys stored under
`~/.fetch-ads-data/`. When filing any issue — security-related or not — **never paste the
contents of those files, `config.json` values you consider private, or command output that
includes tokens.** Redact them first. If you think a credential has leaked, revoke it with the
issuing provider (Google, LinkedIn, Microsoft, G2) right away.

## Scope

The plugin runs locally with your own credentials and only makes read-only API calls. Reports
about how it stores or transmits credentials, the local OAuth callback flows in
`scripts/*/get_token.py`, or the MCP server in `mcp/server.py` are all in scope.
