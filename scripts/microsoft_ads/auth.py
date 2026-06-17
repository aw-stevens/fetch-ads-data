"""Microsoft Advertising (Bing Ads) credential management and SDK auth helpers.

Mirrors scripts/linkedin_ads/auth.py: credentials live in a JSON file pointed at by
config, OAuth refresh happens headlessly, and a rotated refresh token is persisted
back to disk automatically (Microsoft refresh tokens last up to 90 days).
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import config

from bingads.authorization import (
    AuthorizationData,
    GoogleOAuthDesktopMobileAuthCodeGrant,
    OAuthDesktopMobileAuthCodeGrant,
)

ENVIRONMENT = "production"
API_VERSION = 13


def _creds_file() -> Path:
    path = config.credentials_path("microsoft_ads")
    if path:
        return Path(path)
    return Path.home() / ".fetch-ads-data" / "microsoft-ads.json"


def load_creds() -> dict:
    creds_file = _creds_file()
    if not creds_file.exists():
        print(
            f"Error: credentials not found at {creds_file}\n"
            f"Run setup.sh, then authenticate with get_token.py.",
            file=sys.stderr,
        )
        sys.exit(1)
    return json.loads(creds_file.read_text())


def save_creds(creds: dict) -> None:
    creds_file = _creds_file()
    creds_file.write_text(json.dumps(creds, indent=2))
    creds_file.chmod(0o600)


def _google_client(creds: dict) -> tuple:
    """Return (client_id, client_secret) for the Google sign-in flow.

    Either set explicitly in microsoft-ads.json, or read at runtime from a Google
    OAuth client file (e.g. the plugin's google-ads.yaml) via "google_client_source".
    """
    cid, csec = creds.get("client_id"), creds.get("client_secret")
    if cid and csec:
        return cid, csec
    src = creds.get("google_client_source")
    if src:
        path = Path(src).expanduser()
        if not path.exists():
            print(f"Error: google_client_source not found at {path}", file=sys.stderr)
            sys.exit(1)
        text = path.read_text()
        try:
            import yaml  # available in the venv via google-ads
            data = yaml.safe_load(text) or {}
            cid = cid or data.get("client_id")
            csec = csec or data.get("client_secret")
        except Exception:
            import re
            cid = cid or (re.search(r"client_id:\s*(\S+)", text) or [None, None])[1]
            csec = csec or (re.search(r"client_secret:\s*(\S+)", text) or [None, None])[1]
    if not (cid and csec):
        print(
            "Error: Google identity requires a client_id and client_secret "
            "(set them in microsoft-ads.json or via google_client_source).",
            file=sys.stderr,
        )
        sys.exit(1)
    return cid, csec


def build_oauth(creds: dict):
    """Build the OAuth auth-code grant for the configured identity type.

    - identity "google" (default for Google-backed Bing users): GoogleOAuth...Grant,
      authenticates at accounts.google.com (redirect http://localhost). Needs a Google
      OAuth client id + secret.
    - identity "microsoft": OAuthDesktopMobileAuthCodeGrant (native app, no secret),
      Microsoft account sign-in.

    The returned object persists a rotated refresh_token back to the creds file via
    token_refreshed_callback, so unattended runs keep working across rotations.
    """
    identity = (creds.get("identity") or "microsoft").lower()
    if identity == "google":
        client_id, client_secret = _google_client(creds)
        oauth = GoogleOAuthDesktopMobileAuthCodeGrant(
            client_id=client_id,
            client_secret=client_secret,
            env=ENVIRONMENT,
        )
    else:
        if not creds.get("client_id"):
            print("Error: client_id missing from credentials.", file=sys.stderr)
            sys.exit(1)
        oauth = OAuthDesktopMobileAuthCodeGrant(
            client_id=creds["client_id"],
            env=ENVIRONMENT,
            tenant=creds.get("tenant", "common"),
        )

    def _on_refresh(oauth_tokens) -> None:
        # Google does not return a new refresh token on refresh — keep the old one.
        if getattr(oauth_tokens, "refresh_token", None):
            creds["refresh_token"] = oauth_tokens.refresh_token
            save_creds(creds)

    oauth.token_refreshed_callback = _on_refresh
    return oauth


def authorization_data(account_id: int = None) -> AuthorizationData:
    """Return an AuthorizationData ready for ServiceClient / ReportingServiceManager.

    Exchanges the stored refresh_token for fresh access/refresh tokens up front.
    """
    creds = load_creds()
    if not creds.get("refresh_token"):
        print(
            "Error: no refresh_token. Run get_token.py to authenticate.",
            file=sys.stderr,
        )
        sys.exit(1)
    if not creds.get("developer_token"):
        print("Error: developer_token missing from credentials.", file=sys.stderr)
        sys.exit(1)

    oauth = build_oauth(creds)
    oauth.request_oauth_tokens_by_refresh_token(creds["refresh_token"])

    customer_id = creds.get("customer_id") or None
    return AuthorizationData(
        account_id=account_id,
        customer_id=int(customer_id) if customer_id else None,
        developer_token=creds["developer_token"],
        authentication=oauth,
    )
