#!/usr/bin/env python3
"""List all LinkedIn ad accounts accessible with current credentials."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from auth import api_get


def main():
    parser = argparse.ArgumentParser(description="List accessible LinkedIn ad accounts")
    parser.add_argument("--format", default="table", choices=["table", "json"])
    args = parser.parse_args()

    data = api_get(
        "/adAccounts",
        params={
            "q": "search",
            "count": 100,
        },
    )
    accounts = data.get("elements", [])

    if not accounts:
        print("No ad accounts found.")
        return

    if args.format == "json":
        print(json.dumps(accounts, indent=2))
        return

    # Table
    print(f"{'ID':<15} {'Name':<40} {'Status':<10} {'Currency':<10} {'Type'}")
    print("-" * 90)
    for acct in accounts:
        print(
            f"{acct.get('id', ''):<15} "
            f"{acct.get('name', ''):<40} "
            f"{acct.get('status', ''):<10} "
            f"{acct.get('currency', ''):<10} "
            f"{acct.get('type', '')}"
        )


if __name__ == "__main__":
    main()
