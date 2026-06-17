#!/usr/bin/env python3
"""List Microsoft Advertising (Bing Ads) accounts accessible with current credentials.

A user may have access to several customers (e.g. their own plus a managed/agency
customer). GetAccountsInfo only returns accounts under the customer set in the request
HEADER, so we enumerate every accessible customer (GetCustomersInfo) and query accounts
under each with the matching header. Output includes the owning customer_id, which is
what config.json's microsoft_ads.customer_id / the AuthorizationData header must be set to.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from auth import ENVIRONMENT, build_oauth, load_creds

from bingads.authorization import AuthorizationData
from bingads.service_client import ServiceClient


def _as_list(wrapper, attr):
    """suds array wrappers expose the items under a single attribute; normalize to list."""
    if wrapper is None:
        return []
    inner = getattr(wrapper, attr, None)
    return inner or []


def main():
    parser = argparse.ArgumentParser(description="List accessible Microsoft Advertising accounts")
    parser.add_argument("--format", default="table", choices=["table", "json"])
    args = parser.parse_args()

    creds = load_creds()
    oauth = build_oauth(creds)
    oauth.request_oauth_tokens_by_refresh_token(creds["refresh_token"])
    dev_token = creds["developer_token"]

    def service(customer_id):
        ad = AuthorizationData(customer_id=customer_id, developer_token=dev_token, authentication=oauth)
        return ServiceClient(service="CustomerManagementService", version=13,
                             authorization_data=ad, environment=ENVIRONMENT)

    # Discover every customer the user can access.
    disco = service(creds.get("customer_id") or None)
    customers = _as_list(disco.GetCustomersInfo(CustomerNameFilter="", TopN=100), "CustomerInfo")

    rows = []
    for cust in customers:
        cust_id = getattr(cust, "Id", "")
        cust_name = getattr(cust, "Name", "")
        # GetAccountsInfo requires the customer in the request header to match.
        accounts = _as_list(
            service(cust_id).GetAccountsInfo(CustomerId=cust_id, OnlyParentAccounts=False),
            "AccountInfo",
        )
        for a in accounts:
            rows.append({
                "account_id": getattr(a, "Id", ""),
                "account_name": getattr(a, "Name", ""),
                "number": getattr(a, "Number", ""),
                "status": getattr(a, "AccountLifeCycleStatus", ""),
                "customer_id": cust_id,
                "customer_name": cust_name,
            })

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
