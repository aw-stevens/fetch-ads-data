#!/usr/bin/env python3
"""
LinkedIn OAuth2 token generation.

Prerequisites:
  - ~/.fetch-ads-data/linkedin-ads.json exists with client_id, client_secret, redirect_uri
  - redirect_uri is registered in your LinkedIn Developer app
    (https://www.linkedin.com/developers/apps)

Run: python get_token.py
"""

import json
import sys
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

import requests

sys.path.insert(0, str(Path(__file__).parent.parent))
import config

AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
SCOPES = "r_ads r_ads_reporting"


def _creds_file() -> Path:
    path = config.credentials_path("linkedin_ads")
    if path:
        return Path(path)
    return Path.home() / ".fetch-ads-data" / "linkedin-ads.json"


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
                b"<html><body><h1>Authorization successful!</h1>"
                b"<p>You can close this tab.</p></body></html>"
            )
        elif "error" in params:
            _CallbackHandler.error = params.get("error_description", ["unknown"])[0]
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"<html><body><h1>Authorization failed.</h1></body></html>")

    def log_message(self, format, *args):
        pass  # suppress server logs


def main():
    creds_file = _creds_file()
    if not creds_file.exists():
        print(f"Error: {creds_file} not found. Create it with client_id and client_secret.")
        sys.exit(1)

    creds = json.loads(creds_file.read_text())
    client_id = creds.get("client_id") or input("client_id: ").strip()
    client_secret = creds.get("client_secret") or input("client_secret: ").strip()
    redirect_uri = creds.get("redirect_uri", "http://localhost:8080/callback")

    # Parse port from redirect_uri
    parsed_redirect = urlparse(redirect_uri)
    port = parsed_redirect.port or 8080

    auth_params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": SCOPES,
        "state": "linkedin_ads_auth",
    }
    auth_url = f"{AUTH_URL}?{urlencode(auth_params)}"

    print(f"\nOpening browser for LinkedIn authorization...")
    print(f"If the browser doesn't open, visit:\n  {auth_url}\n")
    webbrowser.open(auth_url)

    print(f"Waiting for callback on {redirect_uri} ...")
    server = HTTPServer(("localhost", port), _CallbackHandler)
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
            "redirect_uri": redirect_uri,
            "client_id": client_id,
            "client_secret": client_secret,
        },
    )
    if not resp.ok:
        print(f"Token exchange failed: {resp.status_code} {resp.text}", file=sys.stderr)
        sys.exit(1)

    token_data = resp.json()
    creds.update(
        {
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "access_token": token_data["access_token"],
            "refresh_token": token_data.get("refresh_token", ""),
        }
    )
    creds_file.write_text(json.dumps(creds, indent=2))
    creds_file.chmod(0o600)

    expires_in = token_data.get("expires_in", "unknown")
    print(f"\nTokens saved to {creds_file}")
    print(f"Access token valid for: {expires_in} seconds (~{int(expires_in)//86400} days)")


if __name__ == "__main__":
    main()
