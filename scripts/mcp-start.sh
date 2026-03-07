#!/bin/bash
exec "$HOME/.ad-analytics/venv/bin/python" "$(dirname "$0")/../mcp/server.py"
