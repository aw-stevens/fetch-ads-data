#!/bin/bash
VENV="$HOME/.fetch-ads-data/venv"
[ -d "$VENV" ] && exit 0
python3 -m venv "$VENV"
"$VENV/bin/pip" install -q google-ads google-analytics-data google-analytics-admin google-api-python-client requests "mcp[cli]"
