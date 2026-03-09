#!/usr/bin/env python3
"""
Query Google Search Console Search Analytics API.

Usage:
    python query_gsc.py --dimensions query --limit 20
    python query_gsc.py --dimensions page --start 7daysAgo --limit 10
    python query_gsc.py --dimensions query page --search-type image
    python query_gsc.py --dimensions date --start 30daysAgo
    python query_gsc.py --action list-sites

Date formats:
    Named:  7daysAgo, 30daysAgo, 90daysAgo, yesterday
    Custom: YYYY-MM-DD

Note: Search Console data has a ~3 day lag. Dates are auto-adjusted.

Credentials configured in ~/.ad-analytics/config.json
"""

import argparse
import csv
import json
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import config

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build


def _get_service():
    creds_path = config.credentials_path("google_search_console")
    if not creds_path or not Path(creds_path).exists():
        print("Error: Search Console credentials not found. Run get_token.py first.", file=sys.stderr)
        sys.exit(1)
    creds_data = json.loads(Path(creds_path).read_text())
    creds = Credentials(
        token=None,
        refresh_token=creds_data["refresh_token"],
        token_uri=creds_data["token_uri"],
        client_id=creds_data["client_id"],
        client_secret=creds_data["client_secret"],
    )
    return build("searchconsole", "v1", credentials=creds)


def _resolve_date(value: str) -> date:
    today = date.today()
    # GSC data lags ~3 days
    latest = today - timedelta(days=3)
    shortcuts = {
        "today": latest,
        "yesterday": latest,
        "7daysAgo": latest - timedelta(days=7),
        "30daysAgo": latest - timedelta(days=30),
        "90daysAgo": latest - timedelta(days=90),
    }
    d = shortcuts.get(value) or date.fromisoformat(value)
    return min(d, latest)


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


def list_sites(service, fmt: str) -> None:
    sites = service.sites().list().execute()
    rows = []
    for s in sites.get("siteEntry", []):
        rows.append({
            "site_url": s["siteUrl"],
            "permission": s["permissionLevel"],
        })
    _output(rows, fmt)


def query_analytics(service, site_url: str, dimensions: list[str],
                    start: date, end: date, search_type: str,
                    limit: int, fmt: str) -> None:
    body = {
        "startDate": start.isoformat(),
        "endDate": end.isoformat(),
        "dimensions": dimensions,
        "rowLimit": limit,
    }
    if search_type != "web":
        body["type"] = search_type

    resp = service.searchanalytics().query(siteUrl=site_url, body=body).execute()
    api_rows = resp.get("rows", [])

    if not api_rows:
        print("No data returned.")
        return

    rows = []
    for r in api_rows:
        row = {}
        for i, dim in enumerate(dimensions):
            row[dim] = r["keys"][i] if i < len(r["keys"]) else ""
        row["clicks"] = int(r["clicks"])
        row["impressions"] = int(r["impressions"])
        row["ctr"] = f"{r['ctr']:.1%}"
        row["position"] = f"{r['position']:.1f}"
        rows.append(row)

    _output(rows, fmt)


def main():
    default_site = config.default_id("google_search_console")

    parser = argparse.ArgumentParser(description="Query Google Search Console")
    parser.add_argument(
        "--action",
        default="query",
        choices=["query", "list-sites"],
        help="Action to perform (default: query)",
    )
    parser.add_argument(
        "--site",
        default=default_site or None,
        help="Site URL (e.g. https://example.com/). Defaults to config.",
    )
    parser.add_argument(
        "--dimensions",
        nargs="+",
        default=["query"],
        choices=["query", "page", "country", "device", "date", "searchAppearance"],
        help="Dimensions to group by (default: query)",
    )
    parser.add_argument(
        "--start",
        default="30daysAgo",
        help="Start date: YYYY-MM-DD or 7daysAgo/30daysAgo/90daysAgo (default: 30daysAgo)",
    )
    parser.add_argument(
        "--end",
        default="today",
        help="End date: YYYY-MM-DD or today/yesterday (default: today)",
    )
    parser.add_argument(
        "--search-type",
        default="web",
        choices=["web", "image", "video", "news", "discover", "googleNews"],
        help="Search type filter (default: web)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=25,
        help="Maximum rows (default: 25, max: 25000)",
    )
    parser.add_argument(
        "--format",
        default="table",
        choices=["table", "csv", "json"],
        help="Output format (default: table)",
    )
    args = parser.parse_args()

    service = _get_service()

    if args.action == "list-sites":
        list_sites(service, args.format)
        return

    if not args.site:
        print("Error: No --site provided and no default configured.", file=sys.stderr)
        sys.exit(1)

    start = _resolve_date(args.start)
    end = _resolve_date(args.end)

    query_analytics(service, args.site, args.dimensions, start, end,
                    args.search_type, args.limit, args.format)


if __name__ == "__main__":
    main()
