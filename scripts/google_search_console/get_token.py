#!/usr/bin/env python3
"""
Generate OAuth2 refresh token for Google Search Console API.

Uses the same OAuth client from your Google Ads credentials (~/.ad-analytics/google-ads.yaml)
but requests the webmasters.readonly scope.

Run: python get_token.py
"""

import json
import sys
import webbrowser
import yaml
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

import requests

SCOPES = "https://www.googleapis.com/auth/webmasters.readonly"
TOKEN_URL = "https://oauth2.googleapis.com/token"
AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_ADS_YAML = Path.home() / ".ad-analytics" / "google-ads.yaml"
GSC_CREDS_FILE = Path.home() / ".ad-analytics" / "google-search-console.json"
REDIRECT_URI = "http://localhost:8090/callback"


class _CallbackHandler(BaseHTTPRequestHandler):
    code = None
    error = None

    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        if "code" in params:
            _CallbackHandler.code = params["code"][0]
            self.send_response(200)
            self.end_headers()
            self.wfile.write(
                b"<html><body><h1>Search Console authorization successful!</h1>"
                b"<p>You can close this tab.</p></body></html>"
            )
        elif "error" in params:
            _CallbackHandler.error = params.get("error_description", ["unknown"])[0]
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"<html><body><h1>Authorization failed.</h1></body></html>")

    def log_message(self, format, *args):
        pass


def main():
    if not GOOGLE_ADS_YAML.exists():
        print(f"Error: {GOOGLE_ADS_YAML} not found. Need OAuth client_id and client_secret.")
        sys.exit(1)

    ads_creds = yaml.safe_load(GOOGLE_ADS_YAML.read_text())
    client_id = ads_creds["client_id"]
    client_secret = ads_creds["client_secret"]

    auth_params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPES,
        "access_type": "offline",
        "prompt": "consent",
    }
    auth_url = f"{AUTH_URL}?{urlencode(auth_params)}"

    print(f"\nOpening browser for Google Search Console authorization...")
    print(f"If the browser doesn't open, visit:\n  {auth_url}\n")
    webbrowser.open(auth_url)

    print(f"Waiting for callback on {REDIRECT_URI} ...")
    server = HTTPServer(("localhost", 8090), _CallbackHandler)
    server.handle_request()

    if _CallbackHandler.error:
        print(f"Authorization failed: {_CallbackHandler.error}", file=sys.stderr)
        sys.exit(1)
    if not _CallbackHandler.code:
        print("No authorization code received.", file=sys.stderr)
        sys.exit(1)

    # Exchange code for tokens
    resp = requests.post(
        TOKEN_URL,
        data={
            "grant_type": "authorization_code",
            "code": _CallbackHandler.code,
            "redirect_uri": REDIRECT_URI,
            "client_id": client_id,
            "client_secret": client_secret,
        },
    )
    if not resp.ok:
        print(f"Token exchange failed: {resp.status_code} {resp.text}", file=sys.stderr)
        sys.exit(1)

    token_data = resp.json()
    creds = {
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": token_data["refresh_token"],
        "token_uri": TOKEN_URL,
    }
    GSC_CREDS_FILE.write_text(json.dumps(creds, indent=2))
    GSC_CREDS_FILE.chmod(0o600)

    print(f"\nCredentials saved to {GSC_CREDS_FILE}")
    print("Search Console API access is now configured.")


if __name__ == "__main__":
    main()
