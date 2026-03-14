#!/usr/bin/env python3
"""
List all Google Ads accounts accessible with current credentials.

Usage:
    python list_accounts.py

Credentials loaded from path configured in ~/.fetch-ads-data/config.json
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import config


def main():
    try:
        from google.ads.googleads.client import GoogleAdsClient
        from google.ads.googleads.errors import GoogleAdsException
    except ImportError:
        print("Install: pip install google-ads", file=sys.stderr)
        sys.exit(1)

    creds_path = config.credentials_path("google_ads")
    if creds_path:
        client = GoogleAdsClient.load_from_storage(path=creds_path)
    else:
        client = GoogleAdsClient.load_from_storage()

    customer_service = client.get_service("CustomerService")

    try:
        accessible = customer_service.list_accessible_customers()
        resource_names = accessible.resource_names
    except GoogleAdsException as ex:
        print(f"Error listing accounts: {ex}", file=sys.stderr)
        sys.exit(1)

    if not resource_names:
        print("No accessible customer accounts found.")
        return

    print(f"Found {len(resource_names)} accessible account(s):\n")
    ga_service = client.get_service("GoogleAdsService")

    for resource_name in resource_names:
        customer_id = resource_name.split("/")[-1]
        try:
            query = """
                SELECT
                    customer.id,
                    customer.descriptive_name,
                    customer.currency_code,
                    customer.time_zone,
                    customer.manager
                FROM customer
                LIMIT 1
            """
            response = ga_service.search(customer_id=customer_id, query=query)
            for row in response:
                c = row.customer
                acct_type = "Manager (MCC)" if c.manager else "Standard"
                print(f"  Customer ID : {c.id}")
                print(f"  Name        : {c.descriptive_name}")
                print(f"  Type        : {acct_type}")
                print(f"  Currency    : {c.currency_code}")
                print(f"  Timezone    : {c.time_zone}")
                print()
        except GoogleAdsException as ex:
            msg = ex.failure.errors[0].message if ex.failure.errors else str(ex)
            print(f"  Customer ID : {customer_id} (could not fetch details: {msg})\n")


if __name__ == "__main__":
    main()
