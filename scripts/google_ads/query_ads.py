#!/usr/bin/env python3
"""
Query Google Ads using GAQL (Google Ads Query Language).

Usage:
    python query_ads.py "<GAQL query>" [--customer-id ID] [--format table|csv|json]

Examples:
    python query_ads.py "SELECT campaign.name, metrics.impressions, metrics.clicks, metrics.cost_micros FROM campaign WHERE segments.date DURING LAST_30_DAYS ORDER BY metrics.cost_micros DESC LIMIT 20" --customer-id 1234567890

Notes:
    - Cost fields (metrics.cost_micros) are divided by 1,000,000 and displayed as dollars.
    - Credentials loaded from path configured in ~/.fetch-ads-data/config.json
    - Customer ID defaults to config default_account, or use --customer-id / GOOGLE_ADS_CUSTOMER_ID env var.
"""

import sys
import json
import csv
import re
import argparse
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import config


def get_nested(obj, path):
    """Get a nested attribute from a proto-plus message using dot notation."""
    parts = path.split(".")
    for part in parts:
        try:
            obj = getattr(obj, part)
        except AttributeError:
            return None
    # Handle enums (proto-plus returns enum wrappers with .name)
    if hasattr(obj, "name") and hasattr(obj, "value") and isinstance(obj.value, int):
        return obj.name
    return obj


def format_value(val, field_name):
    """Format a value for display, converting micros to dollars for cost fields."""
    if val is None:
        return ""
    if "micros" in field_name and isinstance(val, (int, float)):
        return f"${val / 1_000_000:.2f}"
    if isinstance(val, float):
        return f"{val:.4f}"
    return str(val)


def parse_select_fields(query):
    """Extract the list of selected fields from a GAQL query string."""
    match = re.search(r"SELECT\s+(.*?)\s+FROM", query, re.IGNORECASE | re.DOTALL)
    if not match:
        print("Error: Could not parse SELECT fields from query.", file=sys.stderr)
        sys.exit(1)
    fields_str = match.group(1)
    return [f.strip() for f in fields_str.split(",")]


def main():
    parser = argparse.ArgumentParser(
        description="Query Google Ads using GAQL",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("query", help="GAQL query string")
    parser.add_argument(
        "--customer-id",
        help="Google Ads customer ID (10 digits, no dashes). Falls back to config default.",
    )
    parser.add_argument(
        "--format",
        choices=["table", "csv", "json"],
        default="table",
        help="Output format (default: table)",
    )
    args = parser.parse_args()

    try:
        from google.ads.googleads.client import GoogleAdsClient
        from google.ads.googleads.errors import GoogleAdsException
    except ImportError:
        print("Error: google-ads not installed. Run: pip install google-ads", file=sys.stderr)
        sys.exit(1)

    customer_id = (
        args.customer_id
        or os.environ.get("GOOGLE_ADS_CUSTOMER_ID", "")
        or config.default_id("google_ads")
    ).replace("-", "")
    if not customer_id:
        print(
            "Error: Provide --customer-id, set GOOGLE_ADS_CUSTOMER_ID, or configure default in config.json.",
            file=sys.stderr,
        )
        sys.exit(1)

    creds_path = config.credentials_path("google_ads")
    if creds_path:
        client = GoogleAdsClient.load_from_storage(path=creds_path)
    else:
        client = GoogleAdsClient.load_from_storage()

    ga_service = client.get_service("GoogleAdsService")
    fields = parse_select_fields(args.query)

    try:
        stream = ga_service.search_stream(customer_id=customer_id, query=args.query)
        rows = []
        for batch in stream:
            for row in batch.results:
                row_data = {f: get_nested(row, f) for f in fields}
                rows.append(row_data)
    except GoogleAdsException as ex:
        for error in ex.failure.errors:
            print(f"Google Ads API error: {error.message}", file=sys.stderr)
        sys.exit(1)

    if not rows:
        print("No results.")
        return

    if args.format == "json":
        def serialize(v):
            if v is None:
                return None
            if isinstance(v, bytes):
                return v.decode()
            return v

        print(json.dumps([{k: serialize(v) for k, v in r.items()} for r in rows], indent=2, default=str))

    elif args.format == "csv":
        writer = csv.DictWriter(sys.stdout, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: format_value(v, k) for k, v in row.items()})

    else:  # table
        formatted = [{f: format_value(row[f], f) for f in fields} for row in rows]
        widths = {f: max(len(f), max(len(r[f]) for r in formatted)) for f in fields}
        sep = " | "
        header = sep.join(f.ljust(widths[f]) for f in fields)
        print(header)
        print("-" * len(header))
        for row in formatted:
            print(sep.join(row[f].ljust(widths[f]) for f in fields))
        print(f"\n({len(rows)} rows)")


if __name__ == "__main__":
    main()
