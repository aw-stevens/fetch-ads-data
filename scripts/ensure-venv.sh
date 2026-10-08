#!/bin/bash
# Create or refresh the plugin's Python venv at ~/.fetch-ads-data/venv.
#
# Safe to re-run (it's the SessionStart hook): installs only when the venv is new, a
# previous install was interrupted, or requirements.txt has changed. Completion is
# recorded in a stamp file written only after pip succeeds.
set -e

VENV="$HOME/.fetch-ads-data/venv"
REQS="$(cd "$(dirname "$0")/.." && pwd)/requirements.txt"
STAMP="$VENV/.requirements.sha256"

if command -v sha256sum >/dev/null 2>&1; then
    want="$(sha256sum "$REQS" | cut -d' ' -f1)"
else
    want="$(shasum -a 256 "$REQS" | cut -d' ' -f1)"
fi

if [ -f "$STAMP" ] && [ "$(cat "$STAMP")" = "$want" ]; then
    exit 0
fi

[ -x "$VENV/bin/python" ] || python3 -m venv "$VENV"
"$VENV/bin/pip" install -q --prefer-binary -r "$REQS"
echo "$want" > "$STAMP"
