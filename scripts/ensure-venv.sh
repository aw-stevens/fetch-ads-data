#!/bin/bash
VENV="$HOME/.ad-analytics/venv"
[ -d "$VENV" ] && exit 0
python3 -m venv "$VENV"
"$VENV/bin/pip" install -q google-ads google-analytics-data google-analytics-admin requests "mcp[cli]"
