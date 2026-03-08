#!/usr/bin/env python3
"""Query LinkedIn Ads Analytics API."""

import argparse
import csv
import json
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from auth import api_get

sys.path.insert(0, str(Path(__file__).parent.parent))
import config

DEFAULT_FIELDS = "impressions,clicks,costInLocalCurrency,externalWebsiteConversions,externalWebsitePostClickConversions,externalWebsitePostViewConversions,dateRange,pivotValues"


def _resolve_date(value: str) -> date:
    today = date.today()
    shortcuts = {
        "today": today,
        "yesterday": today - timedelta(days=1),
        "7daysAgo": today - timedelta(days=7),
        "30daysAgo": today - timedelta(days=30),
        "90daysAgo": today - timedelta(days=90),
    }
    return shortcuts.get(value) or date.fromisoformat(value)


def _fmt_date(d: date) -> str:
    return f"(year:{d.year},month:{d.month},day:{d.day})"


def _resolve_pivot_names(elements: list[dict], pivot: str, account_id: str) -> dict:
    """Fetch friendly names for pivot entity IDs via the LinkedIn API.

    Returns {id: name} mapping. Only resolves CAMPAIGN and CAMPAIGN_GROUP pivots;
    other pivots return an empty dict (IDs are used as-is).
    """
    if pivot not in ("CAMPAIGN", "CAMPAIGN_GROUP"):
        return {}

    # Collect unique entity IDs from pivotValues
    entity_ids = set()
    for el in elements:
        for urn in el.get("pivotValues", []):
            entity_ids.add(urn.split(":")[-1])

    if not entity_ids:
        return {}

    # v202602+ requires account ID in the URL path
    resource = "adCampaigns" if pivot == "CAMPAIGN" else "adCampaignGroups"
    names = {}
    for eid in entity_ids:
        try:
            data = api_get(f"/adAccounts/{account_id}/{resource}/{eid}")
            names[eid] = data.get("name", eid)
        except SystemExit:
            names[eid] = eid  # fallback if lookup fails
    return names


def _flatten(element: dict, pivot: str, pivot_names: dict = None) -> dict:
    """Flatten a response element into a flat dict for tabular output."""
    row = {}
    dr = element.get("dateRange")
    if dr:
        s, e = dr.get("start", {}), dr.get("end", {})
        row["date_start"] = f"{s.get('year','')}-{s.get('month',0):02d}-{s.get('day',0):02d}"
        row["date_end"] = f"{e.get('year','')}-{e.get('month',0):02d}-{e.get('day',0):02d}"
    pivot_vals = element.get("pivotValues", [])
    raw_ids = [v.split(":")[-1] for v in pivot_vals]
    row["pivot"] = pivot
    if pivot_names:
        row["pivot_name"] = ", ".join(pivot_names.get(rid, rid) for rid in raw_ids)
    row["pivot_id"] = ", ".join(raw_ids)
    for k, v in element.items():
        if k not in ("dateRange", "pivotValues"):
            row[k] = v
    return row


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


def main():
    default_account = config.default_id("linkedin_ads")

    parser = argparse.ArgumentParser(description="Query LinkedIn Ads analytics")
    parser.add_argument(
        "--account-id",
        default=default_account or None,
        required=not bool(default_account),
        help="Sponsored account ID (digits only)",
    )
    parser.add_argument(
        "--pivot",
        default="CAMPAIGN",
        choices=[
            "ACCOUNT",
            "CAMPAIGN",
            "CAMPAIGN_GROUP",
            "CREATIVE",
            "MEMBER_COMPANY",
            "MEMBER_INDUSTRY",
            "MEMBER_SENIORITY",
            "MEMBER_JOB_TITLE",
            "MEMBER_COUNTRY_V2",
        ],
        help="Grouping dimension (default: CAMPAIGN)",
    )
    parser.add_argument(
        "--start",
        default="30daysAgo",
        help="Start date: YYYY-MM-DD or 7daysAgo/30daysAgo/90daysAgo/yesterday (default: 30daysAgo)",
    )
    parser.add_argument(
        "--end",
        default="yesterday",
        help="End date: YYYY-MM-DD or yesterday/today (default: yesterday)",
    )
    parser.add_argument(
        "--granularity",
        default="ALL",
        choices=["DAILY", "MONTHLY", "ALL"],
        help="Time granularity (default: ALL)",
    )
    parser.add_argument(
        "--fields",
        default=DEFAULT_FIELDS,
        help=f"Comma-separated metrics (default: {DEFAULT_FIELDS})",
    )
    parser.add_argument(
        "--format",
        default="table",
        choices=["table", "csv", "json"],
        help="Output format (default: table)",
    )
    args = parser.parse_args()

    start = _resolve_date(args.start)
    end = _resolve_date(args.end)
    date_range = f"(start:{_fmt_date(start)},end:{_fmt_date(end)})"
    # URN colons must be percent-encoded inside List() for LinkedIn's REST API
    account_urn = f"urn%3Ali%3AsponsoredAccount%3A{args.account_id}"

    params = {
        "q": "analytics",
        "pivot": args.pivot,
        "timeGranularity": args.granularity,
        "dateRange": date_range,
        "accounts": f"List({account_urn})",
        "fields": args.fields,
    }

    data = api_get("/adAnalytics", params=params)
    elements = data.get("elements", [])

    if not elements:
        print("No data returned.")
        return

    pivot_names = _resolve_pivot_names(elements, args.pivot, args.account_id)
    rows = [_flatten(el, args.pivot, pivot_names) for el in elements]

    if args.format == "json":
        print(json.dumps(rows, indent=2))
    elif args.format == "csv":
        writer = csv.DictWriter(sys.stdout, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    else:
        _print_table(rows)


if __name__ == "__main__":
    main()
