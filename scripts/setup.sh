#!/bin/bash
set -e

CONFIG_DIR="$HOME/.fetch-ads-data"
VENV="$CONFIG_DIR/venv"
CONFIG="$CONFIG_DIR/config.json"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLUGIN_ROOT="$(dirname "$SCRIPT_DIR")"

echo "=== Ad Analytics Plugin Setup ==="
echo ""

# 1. Create config directory
mkdir -p "$CONFIG_DIR"

# 2. Create / refresh venv (installs requirements.txt; no-op when already up to date)
echo "Ensuring Python virtual environment at $VENV..."
bash "$SCRIPT_DIR/ensure-venv.sh"
echo "Done."

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

# 7. Microsoft Advertising (Bing Ads) credentials
MS_CREDS="$CONFIG_DIR/microsoft-ads.json"
echo ""
echo "--- Microsoft Advertising (Bing Ads) ---"
if [ ! -f "$MS_CREDS" ]; then
    echo "Creating credentials template at $MS_CREDS"
    cp "$PLUGIN_ROOT/templates/microsoft-ads.json.template" "$MS_CREDS"
    echo "Fill in client_id and developer_token in $MS_CREDS, then run:"
    echo "  $VENV/bin/python $SCRIPT_DIR/microsoft_ads/get_token.py"
    echo "(See skills/microsoft-ads/references/setup.md for Azure app + developer token steps.)"
else
    echo "Microsoft Advertising credentials found at $MS_CREDS"
fi

# 8. Google Tag Manager credentials
GTM_CREDS="$CONFIG_DIR/google-tagmanager.json"
echo ""
echo "--- Google Tag Manager ---"
if [ -f "$GTM_CREDS" ]; then
    echo "GTM credentials found at $GTM_CREDS"
else
    echo "No GTM credentials found."
    echo "To set up GTM access, run:"
    echo "  $VENV/bin/python $SCRIPT_DIR/google_tag_manager/get_token.py"
fi

# 9. G2 Digital Markets credentials
G2_CREDS="$CONFIG_DIR/g2-digital-markets.json"
echo ""
echo "--- G2 Digital Markets (Capterra / GetApp / Software Advice) ---"
if [ -f "$G2_CREDS" ]; then
    echo "G2 Digital Markets credentials found at $G2_CREDS"
else
    echo "Creating credentials template at $G2_CREDS"
    cp "$PLUGIN_ROOT/templates/g2-digital-markets.json.template" "$G2_CREDS"
    echo "Paste the API key (from your G2DM account manager) into $G2_CREDS"
fi

# 10. DataForSEO credentials (env vars or credential file)
DFS_CREDS="$CONFIG_DIR/dataforseo.json"
echo ""
echo "--- DataForSEO (keyword volume + SERP) ---"
if [ -n "$DATAFORSEO_LOGIN" ] && [ -n "$DATAFORSEO_PASSWORD" ]; then
    echo "Using DATAFORSEO_LOGIN / DATAFORSEO_PASSWORD from the environment"
elif [ -f "$DFS_CREDS" ]; then
    echo "DataForSEO credentials found at $DFS_CREDS"
else
    echo "Creating credentials template at $DFS_CREDS"
    cp "$PLUGIN_ROOT/templates/dataforseo.json.template" "$DFS_CREDS"
    chmod 600 "$DFS_CREDS"
    echo "Paste your API login/password (https://app.dataforseo.com/api-access) into $DFS_CREDS,"
    echo "or set DATAFORSEO_LOGIN / DATAFORSEO_PASSWORD instead."
fi
echo "Daily spend cap defaults to \$1.00 — change dataforseo.daily_cap_usd in $CONFIG."

# 11. Discover accounts
echo ""
echo "--- Discovering accounts ---"
echo ""
echo "Google Ads accounts:"
"$VENV/bin/python" "$SCRIPT_DIR/google_ads/list_accounts.py" 2>/dev/null || echo "  (could not list — check credentials)"

echo ""
echo "LinkedIn Ads accounts:"
"$VENV/bin/python" "$SCRIPT_DIR/linkedin_ads/list_li_accounts.py" 2>/dev/null || echo "  (could not list — check credentials)"

echo ""
echo "Google Tag Manager accounts:"
"$VENV/bin/python" "$SCRIPT_DIR/google_tag_manager/list_accounts.py" 2>/dev/null || echo "  (could not list — check credentials)"

echo ""
echo "G2 Digital Markets API:"
"$VENV/bin/python" "$SCRIPT_DIR/g2_digital_markets/query_g2.py" --action verify 2>/dev/null || echo "  (could not verify — add your API key to $G2_CREDS)"

echo ""
echo "DataForSEO API:"
"$VENV/bin/python" "$SCRIPT_DIR/dataforseo/verify.py" 2>/dev/null || echo "  (could not verify — add your API login/password to $DFS_CREDS)"

echo ""
echo "Microsoft Advertising accounts:"
"$VENV/bin/python" "$SCRIPT_DIR/microsoft_ads/list_accounts.py" 2>/dev/null || echo "  (could not list — check credentials)"

echo ""
echo "=== Setup complete ==="
echo "Edit $CONFIG to configure your default accounts and property IDs."
