#!/usr/bin/env python3
"""List Microsoft Advertising (Bing Ads) accounts accessible with current credentials.

Resolves the authenticated user's CustomerId (from credentials or via GetUser) and
calls GetAccountsInfo. Mirrors scripts/linkedin_ads/list_li_accounts.py.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from auth import ENVIRONMENT, authorization_data, load_creds

from bingads.service_client import ServiceClient


def _customer_service(auth_data):
    return ServiceClient(
        service="CustomerManagementService",
        version=13,
        authorization_data=auth_data,
        environment=ENVIRONMENT,
    )


def _resolve_customer_id(auth_data, customer_service) -> int:
    creds = load_creds()
    if creds.get("customer_id"):
        return int(creds["customer_id"])
    user = customer_service.GetUser(UserId=None).User
    return int(user.CustomerId)


def main():
    parser = argparse.ArgumentParser(description="List accessible Microsoft Advertising accounts")
    parser.add_argument("--format", default="table", choices=["table", "json"])
    args = parser.parse_args()

    auth_data = authorization_data()
    customer_service = _customer_service(auth_data)
    customer_id = _resolve_customer_id(auth_data, customer_service)

    response = customer_service.GetAccountsInfo(
        CustomerId=customer_id,
        OnlyParentAccounts=False,
    )
    # suds returns an ArrayOfAccountInfoWithCustomerData wrapper
    accounts = getattr(response, "AccountInfoWithCustomerData", None) or []
    if accounts and hasattr(accounts, "AccountInfoWithCustomerData"):
        accounts = accounts.AccountInfoWithCustomerData

    if not accounts:
        print("No accounts found.")
        return

    rows = [
        {
            "id": getattr(a, "Id", ""),
            "name": getattr(a, "Name", ""),
            "number": getattr(a, "Number", ""),
            "status": getattr(a, "AccountLifeCycleStatus", ""),
            "customer_id": getattr(a, "CustomerId", customer_id),
        }
        for a in accounts
    ]

    if args.format == "json":
        print(json.dumps(rows, indent=2, default=str))
        return

    print(f"{'ID':<15} {'Name':<40} {'Number':<12} {'Status':<12} {'CustomerId'}")
    print("-" * 95)
    for r in rows:
        print(
            f"{str(r['id']):<15} "
            f"{str(r['name']):<40} "
            f"{str(r['number']):<12} "
            f"{str(r['status']):<12} "
            f"{r['customer_id']}"
        )


if __name__ == "__main__":
    main()
