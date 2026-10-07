#!/usr/bin/env python3
"""List Microsoft Advertising (Bing Ads) accounts accessible with current credentials.

A user may have access to several customers (e.g. their own plus a managed/agency
customer). GetAccountsInfo only returns accounts under the customer set in the request
HEADER, so we enumerate every accessible customer (GetCustomersInfo) and query accounts
under each with the matching header. Output includes the owning customer_id, which is
what microsoft-ads.json's customer_id (sent as the CustomerId header) must be set to.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from auth import CUSTOMER_BASE, ApiError, Client


def _long(value):
    """REST serializes longs as JSON strings; keep the SOAP-era int output."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return value if value is not None else ""


def _list_accounts(client: Client) -> list:
    # Discover every customer the user can access.
    customers = client.post(
        f"{CUSTOMER_BASE}/CustomersInfo/Query",
        {"CustomerNameFilter": "", "TopN": 100},
    ).get("CustomersInfo") or []

    rows = []
    for cust in customers:
        cust_id = _long(cust.get("Id"))
        cust_name = cust.get("Name", "")
        # GetAccountsInfo requires the customer in the request header to match.
        accounts = client.post(
            f"{CUSTOMER_BASE}/AccountsInfo/Query",
            {"CustomerId": cust_id, "OnlyParentAccounts": False},
            customer_id=cust_id,
        ).get("AccountsInfo") or []
        for a in accounts:
            rows.append({
                "account_id": _long(a.get("Id")),
                "account_name": a.get("Name", ""),
                "number": a.get("Number", ""),
                "status": a.get("AccountLifeCycleStatus", ""),
                "customer_id": cust_id,
                "customer_name": cust_name,
            })
    return rows


def main():
    parser = argparse.ArgumentParser(description="List accessible Microsoft Advertising accounts")
    parser.add_argument("--format", default="table", choices=["table", "json"])
    args = parser.parse_args()

    try:
        rows = _list_accounts(Client())
    except ApiError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    if not rows:
        print("No accounts found.")
        return

    if args.format == "json":
        print(json.dumps(rows, indent=2, default=str))
        return

    cols = ["account_id", "account_name", "number", "status", "customer_id", "customer_name"]
    widths = {c: max(len(c), max(len(str(r[c])) for r in rows)) for c in cols}
    print("  ".join(c.ljust(widths[c]) for c in cols))
    print("  ".join("-" * widths[c] for c in cols))
    for r in rows:
        print("  ".join(str(r[c]).ljust(widths[c]) for c in cols))


if __name__ == "__main__":
    main()
