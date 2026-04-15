#!/usr/bin/env python3
"""
List Google Tag Manager accounts and containers.

Usage:
    python list_accounts.py
    python list_accounts.py --format json
"""

import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import config

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build


def _get_service():
    creds_path = config.credentials_path("google_tag_manager")
    if not creds_path or not Path(creds_path).exists():
        print("Error: GTM credentials not found. Run get_token.py first.", file=sys.stderr)
        sys.exit(1)
    creds_data = json.loads(Path(creds_path).read_text())
    creds = Credentials(
        token=None,
        refresh_token=creds_data["refresh_token"],
        token_uri=creds_data["token_uri"],
        client_id=creds_data["client_id"],
        client_secret=creds_data["client_secret"],
    )
    return build("tagmanager", "v2", credentials=creds)


def _print_table(rows: list[dict]) -> None:
    if not rows:
        print("No results.")
        return
    cols = list(rows[0].keys())
    widths = {c: max(len(c), max(len(str(r.get(c, ""))) for r in rows)) for c in cols}
    header = "  ".join(c.ljust(widths[c]) for c in cols)
    sep = "  ".join("-" * widths[c] for c in cols)
    print(header)
    print(sep)
    for row in rows:
        print("  ".join(str(row.get(c, "")).ljust(widths[c]) for c in cols))


def _output(rows: list[dict], fmt: str) -> None:
    if fmt == "json":
        print(json.dumps(rows, indent=2))
    elif fmt == "csv":
        if rows:
            writer = csv.DictWriter(sys.stdout, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
    else:
        _print_table(rows)


def main():
    parser = argparse.ArgumentParser(description="List GTM accounts and containers")
    parser.add_argument(
        "--format",
        default="table",
        choices=["table", "csv", "json"],
        help="Output format (default: table)",
    )
    args = parser.parse_args()

    service = _get_service()
    accounts = service.accounts().list().execute().get("account", [])

    rows = []
    for acct in accounts:
        acct_id = acct["accountId"]
        acct_name = acct.get("name", "")
        containers = (
            service.accounts()
            .containers()
            .list(parent=acct["path"])
            .execute()
            .get("container", [])
        )
        for ctr in containers:
            usage = ", ".join(ctr.get("usageContext", []))
            rows.append({
                "account_id": acct_id,
                "account_name": acct_name,
                "container_id": ctr["containerId"],
                "container_name": ctr.get("name", ""),
                "public_id": ctr.get("publicId", ""),
                "usage_context": usage,
            })

    _output(rows, args.format)


if __name__ == "__main__":
    main()
