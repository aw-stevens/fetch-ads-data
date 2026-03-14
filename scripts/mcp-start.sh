#!/bin/bash
exec "$HOME/.fetch-ads-data/venv/bin/python" "$(dirname "$0")/../mcp/server.py"
