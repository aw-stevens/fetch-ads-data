"""LinkedIn Ads credential management and API helpers."""

import json
import sys
from pathlib import Path
from urllib.parse import quote

import requests

sys.path.insert(0, str(Path(__file__).parent.parent))
import config

BASE_URL = "https://api.linkedin.com/rest"
TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
API_VERSION = "202602"


def _creds_file() -> Path:
    path = config.credentials_path("linkedin_ads")
    if path:
        return Path(path)
    return Path.home() / ".fetch-ads-data" / "linkedin-ads.json"


def load_creds() -> dict:
    creds_file = _creds_file()
    if not creds_file.exists():
        print(
            f"Error: credentials not found at {creds_file}\n"
            f"Run setup.sh to authenticate.",
            file=sys.stderr,
        )
        sys.exit(1)
    return json.loads(creds_file.read_text())


def save_creds(creds: dict) -> None:
    creds_file = _creds_file()
    creds_file.write_text(json.dumps(creds, indent=2))
    creds_file.chmod(0o600)


def _refresh_access_token(creds: dict) -> str:
    """Exchange refresh_token for a new access_token. Updates the credentials file."""
    resp = requests.post(
        TOKEN_URL,
        data={
            "grant_type": "refresh_token",
            "refresh_token": creds["refresh_token"],
            "client_id": creds["client_id"],
            "client_secret": creds["client_secret"],
        },
    )
    if not resp.ok:
        print(f"Token refresh failed: {resp.status_code} {resp.text}", file=sys.stderr)
        sys.exit(1)
    data = resp.json()
    creds["access_token"] = data["access_token"]
    if "refresh_token" in data:
        creds["refresh_token"] = data["refresh_token"]
    save_creds(creds)
    return creds["access_token"]


def _headers(access_token: str) -> dict:
    return {
        "Authorization": f"Bearer {access_token}",
        "Linkedin-Version": API_VERSION,
        "X-Restli-Protocol-Version": "2.0.0",
    }


def _build_url(path: str, params: dict = None) -> str:
    """Build URL preserving commas/parens needed by LinkedIn's Rest.li protocol."""
    url = f"{BASE_URL}{path}" if path.startswith("/") else path
    if params:
        parts = []
        for k, v in params.items():
            parts.append(f"{quote(str(k), safe='')}={quote(str(v), safe='%,().:')}")
        url = f"{url}?{'&'.join(parts)}"
    return url


def api_get(path: str, params: dict = None) -> dict:
    """GET request with auto-refresh on 401. Returns parsed JSON."""
    creds = load_creds()
    access_token = creds.get("access_token", "")
    if not access_token:
        print("Error: no access_token. Run setup.sh to authenticate.", file=sys.stderr)
        sys.exit(1)

    url = _build_url(path, params)
    resp = requests.get(url, headers=_headers(access_token))

    if resp.status_code == 401 and creds.get("refresh_token"):
        access_token = _refresh_access_token(creds)
        resp = requests.get(url, headers=_headers(access_token))

    if not resp.ok:
        print(f"API error {resp.status_code}: {resp.text}", file=sys.stderr)
        sys.exit(1)

    return resp.json()
