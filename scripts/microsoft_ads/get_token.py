#!/usr/bin/env python3
"""
Microsoft Advertising OAuth2 token generation (desktop/native app flow).

Prerequisites:
  - ~/.fetch-ads-data/microsoft-ads.json exists with at least:
      { "client_id": "...", "developer_token": "..." }
  - The client_id is a registered application at
    https://apps.dev.microsoft.com / https://portal.azure.com (App registrations),
    configured as a "Mobile and desktop application" with the redirect URI
    https://login.microsoftonline.com/common/oauth2/nativeclient
  - A Microsoft Advertising developer token (production) — request one in the
    Microsoft Advertising UI under Account settings > Developer settings.

Unlike the LinkedIn flow, the Microsoft desktop grant uses a fixed native-client
redirect, so there is no localhost callback server: the browser lands on a page
whose URL contains ?code=..., and you paste that full URL back here.

Run: python get_token.py
"""

import json
import sys
import webbrowser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import config

sys.path.insert(0, str(Path(__file__).parent))
from auth import ENVIRONMENT, _creds_file, build_oauth

from bingads.authorization import AuthorizationData
from bingads.service_client import ServiceClient


def _fetch_customer_id(creds: dict, oauth) -> str:
    """Look up the authenticated user's CustomerId via Customer Management."""
    try:
        auth_data = AuthorizationData(
            authentication=oauth,
            developer_token=creds["developer_token"],
        )
        customer_service = ServiceClient(
            service="CustomerManagementService",
            version=13,
            authorization_data=auth_data,
            environment=ENVIRONMENT,
        )
        user = customer_service.GetUser(UserId=None).User
        return str(getattr(user, "CustomerId", "") or "")
    except Exception as exc:  # noqa: BLE001 — best-effort convenience lookup
        print(f"  (could not auto-detect customer_id: {exc})", file=sys.stderr)
        return ""


def main():
    creds_file = _creds_file()
    if not creds_file.exists():
        print(
            f"Error: {creds_file} not found.\n"
            f"Create it with client_id and developer_token first.",
            file=sys.stderr,
        )
        sys.exit(1)

    creds = json.loads(creds_file.read_text())
    if not creds.get("client_id"):
        creds["client_id"] = input("client_id: ").strip()
    if not creds.get("developer_token"):
        creds["developer_token"] = input("developer_token: ").strip()

    oauth = build_oauth(creds)
    auth_endpoint = oauth.get_authorization_endpoint()

    print("\nOpening browser for Microsoft Advertising authorization...")
    print(f"If the browser doesn't open, visit:\n  {auth_endpoint}\n")
    webbrowser.open(auth_endpoint)

    print(
        "After granting consent your browser will redirect to a (likely blank) page at\n"
        "  https://login.microsoftonline.com/common/oauth2/nativeclient?code=...\n"
        "Copy that page's FULL URL from the address bar and paste it below.\n"
    )
    response_uri = input("Paste the full redirect URL here: ").strip()

    oauth.request_oauth_tokens_by_response_uri(response_uri)
    tokens = oauth.oauth_tokens

    creds["refresh_token"] = tokens.refresh_token
    customer_id = _fetch_customer_id(creds, oauth)
    if customer_id:
        creds["customer_id"] = customer_id

    creds_file.write_text(json.dumps(creds, indent=2))
    creds_file.chmod(0o600)

    print(f"\nTokens saved to {creds_file}")
    if customer_id:
        print(f"Detected customer_id: {customer_id}")
    print(
        "Refresh token valid up to 90 days. Next: run list_accounts.py to discover "
        "account IDs, then add them to ~/.fetch-ads-data/config.json."
    )


if __name__ == "__main__":
    main()
