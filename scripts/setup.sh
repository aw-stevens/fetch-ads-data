#!/bin/bash
set -e

CONFIG_DIR="$HOME/.ad-analytics"
VENV="$CONFIG_DIR/venv"
CONFIG="$CONFIG_DIR/config.json"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLUGIN_ROOT="$(dirname "$SCRIPT_DIR")"

echo "=== Ad Analytics Plugin Setup ==="
echo ""

# 1. Create config directory
mkdir -p "$CONFIG_DIR"

# 2. Create venv
if [ ! -d "$VENV" ]; then
    echo "Creating Python virtual environment at $VENV..."
    python3 -m venv "$VENV"
    echo "Installing packages..."
    "$VENV/bin/pip" install -q google-ads google-analytics-data requests "mcp[cli]"
    echo "Done."
else
    echo "Virtual environment already exists at $VENV"
fi

# 3. Config file
if [ ! -f "$CONFIG" ]; then
    echo ""
    echo "Creating config template at $CONFIG"
    cp "$PLUGIN_ROOT/templates/config.template.json" "$CONFIG"
    echo "Edit $CONFIG to add your account IDs and credentials paths."
else
    echo "Config already exists at $CONFIG"
fi

# 4. Google Ads credentials
GADS_YAML="$CONFIG_DIR/google-ads.yaml"
if [ ! -f "$GADS_YAML" ]; then
    echo ""
    echo "--- Google Ads ---"
    if [ -f "$HOME/google-ads.yaml" ]; then
        echo "Found existing ~/google-ads.yaml — copying to $GADS_YAML"
        cp "$HOME/google-ads.yaml" "$GADS_YAML"
    else
        echo "Creating credentials template at $GADS_YAML"
        cp "$PLUGIN_ROOT/templates/google-ads.yaml.template" "$GADS_YAML"
        echo "Fill in your API credentials in $GADS_YAML"
    fi
fi

# 5. Google Analytics ADC
ADC="$HOME/.config/gcloud/application_default_credentials.json"
echo ""
echo "--- Google Analytics ---"
if [ -f "$ADC" ]; then
    echo "Application Default Credentials found at $ADC"
else
    echo "No ADC found. Run: gcloud auth application-default login"
fi

# 6. LinkedIn Ads credentials
LI_CREDS="$CONFIG_DIR/linkedin-ads.json"
echo ""
echo "--- LinkedIn Ads ---"
if [ ! -f "$LI_CREDS" ]; then
    if [ -f "$HOME/.linkedin-ads.json" ]; then
        echo "Found existing ~/.linkedin-ads.json — copying to $LI_CREDS"
        cp "$HOME/.linkedin-ads.json" "$LI_CREDS"
    else
        echo "No LinkedIn credentials found."
        echo "Create $LI_CREDS with client_id and client_secret, then run:"
        echo "  $VENV/bin/python $SCRIPT_DIR/linkedin_ads/get_token.py"
    fi
else
    echo "LinkedIn credentials found at $LI_CREDS"
fi

# 7. Discover accounts
echo ""
echo "--- Discovering accounts ---"
echo ""
echo "Google Ads accounts:"
"$VENV/bin/python" "$SCRIPT_DIR/google_ads/list_accounts.py" 2>/dev/null || echo "  (could not list — check credentials)"

echo ""
echo "LinkedIn Ads accounts:"
"$VENV/bin/python" "$SCRIPT_DIR/linkedin_ads/list_li_accounts.py" 2>/dev/null || echo "  (could not list — check credentials)"

echo ""
echo "=== Setup complete ==="
echo "Edit $CONFIG to configure your default accounts and property IDs."
