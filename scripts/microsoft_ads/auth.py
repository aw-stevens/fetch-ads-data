"""Microsoft Advertising (Bing Ads) credential management and REST API helpers.

Mirrors scripts/linkedin_ads/auth.py: credentials live in a JSON file pointed at by
config, OAuth refresh happens headlessly, and a rotated refresh token is persisted
back to disk automatically (Microsoft refresh tokens last up to 90 days; Google
refresh tokens don't rotate).

Talks to the Microsoft Advertising REST API (v13) with plain `requests` — the SOAP
API (and the `bingads` SDK built on it) is fully deprecated on 2027-01-31.
"""

import json
import sys
import time
from pathlib import Path
from urllib.parse import parse_qs, quote_plus, urlparse

import requests

sys.path.insert(0, str(Path(__file__).parent.parent))
import config

REPORTING_BASE = "https://reporting.api.bingads.microsoft.com/Reporting/v13"
CUSTOMER_BASE = "https://clientcenter.api.bingads.microsoft.com/CustomerManagement/v13"

# OAuth endpoints and scopes — identical to what bingads 13.0.28 used (production),
# so existing refresh tokens keep working.
GOOGLE_OAUTH = {
    "authorize_url": (
        "https://accounts.google.com/o/oauth2/v2/auth?client_id={client_id}"
        "&scope=openid%20email%20profile&response_type=code&redirect_uri={redirect_uri}"
        "&access_type=offline&prompt=consent"
    ),
    "token_url": "https://oauth2.googleapis.com/token",
    "redirect_uri": "http://localhost",
    "scope": "openid email profile",
}
MICROSOFT_OAUTH = {
    "authorize_url": (
        "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize?client_id={client_id}"
        "&scope=https%3A%2F%2Fads.microsoft.com%2Fmsads.manage%20offline_access"
        "&response_type=code&redirect_uri={redirect_uri}"
    ),
    "token_url": "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token",
    "redirect_uri": "https://login.microsoftonline.com/common/oauth2/nativeclient",
    "scope": "https://ads.microsoft.com/msads.manage offline_access",
}

RETRY_STATUSES = {429, 500, 502, 503, 504}


class ApiError(Exception):
    """A Microsoft Advertising API or OAuth error, with a printable message."""


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


def _identity(creds: dict) -> str:
    return (creds.get("identity") or "microsoft").lower()


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


def _oauth_client(creds: dict) -> dict:
    """Resolve the OAuth client + endpoints for the configured identity type.

    - identity "google" (Google-backed Microsoft Advertising users): authenticates at
      accounts.google.com (redirect http://localhost). Needs a Google OAuth client id
      + secret.
    - identity "microsoft": Microsoft identity platform, native/desktop app (no secret),
      redirect .../oauth2/nativeclient.
    """
    if _identity(creds) == "google":
        client_id, client_secret = _google_client(creds)
        return {**GOOGLE_OAUTH, "client_id": client_id, "client_secret": client_secret}
    if not creds.get("client_id"):
        print("Error: client_id missing from credentials.", file=sys.stderr)
        sys.exit(1)
    tenant = creds.get("tenant") or "common"
    return {
        **MICROSOFT_OAUTH,
        "authorize_url": MICROSOFT_OAUTH["authorize_url"].replace("{tenant}", tenant),
        "token_url": MICROSOFT_OAUTH["token_url"].format(tenant=tenant),
        "client_id": creds["client_id"],
        "client_secret": None,
    }


def authorization_url(creds: dict) -> str:
    """The browser URL where the user grants consent (step 1 of get_token.py)."""
    client = _oauth_client(creds)
    return client["authorize_url"].format(
        client_id=client["client_id"],
        redirect_uri=quote_plus(client["redirect_uri"]),
    )


def _token_request(client: dict, data: dict) -> dict:
    data = {"client_id": client["client_id"], **data}
    if client.get("client_secret"):
        data["client_secret"] = client["client_secret"]
    resp = requests.post(client["token_url"], data=data, timeout=60)
    if resp.status_code != 200:
        try:
            body = resp.json()
            detail = f"{body.get('error')}: {body.get('error_description', '')}".strip()
        except ValueError:
            detail = f"HTTP {resp.status_code}"
        raise ApiError(f"OAuth token request failed ({detail}). Re-run get_token.py to re-authenticate.")
    return resp.json()


def exchange_code(creds: dict, response_uri: str) -> dict:
    """Exchange the ?code=... from the pasted redirect URL for tokens."""
    code = (parse_qs(urlparse(response_uri).query).get("code") or [None])[0]
    if not code:
        raise ApiError("The pasted URL doesn't contain a ?code= parameter.")
    client = _oauth_client(creds)
    return _token_request(client, {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": client["redirect_uri"],
    })


def access_token(creds: dict) -> str:
    """Exchange the stored refresh_token for an access token.

    If the provider returns a new refresh token (Microsoft identities rotate; Google
    doesn't), it is persisted back to the credentials file so unattended runs keep
    working across rotations.
    """
    if not creds.get("refresh_token"):
        raise ApiError("no refresh_token. Run get_token.py to authenticate.")
    client = _oauth_client(creds)
    tokens = _token_request(client, {
        "grant_type": "refresh_token",
        "refresh_token": creds["refresh_token"],
        "scope": client["scope"],
    })
    new_refresh = tokens.get("refresh_token")
    if new_refresh and new_refresh != creds["refresh_token"]:
        creds["refresh_token"] = new_refresh
        save_creds(creds)
    return tokens["access_token"]


class Client:
    """Authenticated Microsoft Advertising REST client (one access token per run)."""

    def __init__(self, creds: dict = None, customer_id=None, account_id=None, token: str = None):
        self.creds = creds or load_creds()
        if not self.creds.get("developer_token"):
            raise ApiError("developer_token missing from credentials.")
        self.token = token or access_token(self.creds)
        self.customer_id = customer_id if customer_id is not None else (self.creds.get("customer_id") or None)
        self.account_id = account_id

    def headers(self, customer_id=None, account_id=None) -> dict:
        h = {
            "Authorization": f"Bearer {self.token}",
            "DeveloperToken": self.creds["developer_token"],
            "Content-Type": "application/json",
        }
        cust = customer_id if customer_id is not None else self.customer_id
        acct = account_id if account_id is not None else self.account_id
        if cust:
            h["CustomerId"] = str(cust)
        if acct:
            h["CustomerAccountId"] = str(acct)
        if _identity(self.creds) == "google":
            # Required for Google-federated users on REST (SOAP inferred it).
            h["IdentityProvider"] = "Google"
        return h

    def post(self, url: str, body: dict, customer_id=None, account_id=None) -> dict:
        """POST JSON, retrying transient failures; raise ApiError on API faults."""
        headers = self.headers(customer_id, account_id)
        for attempt in range(4):
            try:
                resp = requests.post(url, json=body, headers=headers, timeout=120)
            except requests.RequestException as exc:
                if attempt == 3:
                    raise ApiError(f"request to {url} failed: {exc}") from None
            else:
                if resp.status_code not in RETRY_STATUSES or attempt == 3:
                    break
            time.sleep(2 ** (attempt + 1))
        if resp.status_code >= 400:
            raise ApiError(_fault_message(resp))
        return resp.json() if resp.content else {}


def _fault_message(resp) -> str:
    """Flatten a REST ApiFault / AdApiFaultDetail body into one readable line."""
    try:
        body = resp.json()
    except ValueError:
        return f"HTTP {resp.status_code}: {resp.text[:500]}"
    errors = []
    for key in ("Errors", "OperationErrors", "BatchErrors"):
        for e in body.get(key) or []:
            code = e.get("ErrorCode") or e.get("Code")
            msg = e.get("Message", "")
            details = e.get("Details")
            errors.append(f"{code} ({e.get('Code')}): {msg}" + (f" — {details}" if details else ""))
    text = "; ".join(errors) or json.dumps(body)[:500]
    tracking = body.get("TrackingId")
    return f"HTTP {resp.status_code}: {text}" + (f" (TrackingId {tracking})" if tracking else "")
