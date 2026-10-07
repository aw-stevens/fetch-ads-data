#!/usr/bin/env python3
"""Query Microsoft Advertising (Bing Ads) performance via the REST Reporting API.

Bing has no query language, so this mirrors the *shape* of the other query tools
(entity + metrics + time + format) rather than a literal query string. It submits an
Account- or Campaign-PerformanceReport (GenerateReport/Submit), polls until ready
(GenerateReport/Poll), downloads the zipped CSV, and prints table / csv / json — the same UX as google_ads_query / linkedin_ads_query.
"""

import argparse
import csv
import io
import json
import sys
import time
import zipfile
from datetime import date, timedelta
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent))
from auth import REPORTING_BASE, ApiError, Client

sys.path.insert(0, str(Path(__file__).parent.parent))
import config

POLL_INTERVAL_SECONDS = 5
POLL_TIMEOUT_SECONDS = 3600

# Default columns per report type. TimePeriod is dropped automatically for Summary
# aggregation (it is only valid for time-bucketed aggregations).
DEFAULT_COLUMNS = {
    "campaign": [
        "TimePeriod", "AccountName", "AccountId", "CampaignName", "CampaignId",
        "CurrencyCode", "Impressions", "Clicks", "Spend", "Conversions",
    ],
    "account": [
        "TimePeriod", "AccountName", "AccountId",
        "CurrencyCode", "Impressions", "Clicks", "Spend", "Conversions",
    ],
}

REPORT_REQUEST_TYPE = {
    "campaign": "CampaignPerformanceReportRequest",
    "account": "AccountPerformanceReportRequest",
}


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


def _print_table(rows: list) -> None:
    if not rows:
        print("No results.")
        return
    cols = list(rows[0].keys())
    widths = {c: max(len(c), max(len(str(r.get(c, ""))) for r in rows)) for c in cols}
    print("  ".join(c.ljust(widths[c]) for c in cols))
    print("  ".join("-" * widths[c] for c in cols))
    for row in rows:
        print("  ".join(str(row.get(c, "")).ljust(widths[c]) for c in cols))


def _build_report_request(report_type, columns, aggregation, account_id, start, end) -> dict:
    """REST/JSON ReportRequest body (same settings the SOAP request used)."""
    def _date(d):
        return {"Year": d.year, "Month": d.month, "Day": d.day}

    return {
        "ReportRequest": {
            "Type": REPORT_REQUEST_TYPE[report_type],
            "Aggregation": aggregation,
            "Format": "Csv",
            "ReturnOnlyCompleteData": False,
            "ExcludeReportHeader": True,
            "ExcludeReportFooter": True,
            "ExcludeColumnHeaders": False,
            "ReportName": f"{report_type.capitalize()} Performance Report",
            "Columns": list(columns),
            "Scope": {"AccountIds": [int(account_id)]},
            "Time": {
                "CustomDateRangeStart": _date(start),
                "CustomDateRangeEnd": _date(end),
            },
        }
    }


def _run_report(client: Client, request: dict) -> list:
    """Submit → poll → download the report; return rows as a list of dicts."""
    submit = client.post(f"{REPORTING_BASE}/GenerateReport/Submit", request)
    request_id = submit["ReportRequestId"]

    deadline = time.monotonic() + POLL_TIMEOUT_SECONDS
    while True:
        poll = client.post(f"{REPORTING_BASE}/GenerateReport/Poll", {"ReportRequestId": request_id})
        status = poll["ReportRequestStatus"]
        if status["Status"] != "Pending":
            break
        if time.monotonic() > deadline:
            raise ApiError(f"report {request_id} still pending after {POLL_TIMEOUT_SECONDS}s")
        time.sleep(POLL_INTERVAL_SECONDS)

    if status["Status"] != "Success":
        raise ApiError(f"report {request_id} finished with status {status['Status']}")
    url = status.get("ReportDownloadUrl")
    if not url:  # Success with no download URL == no rows for the range
        return []

    # Pre-signed URL (valid ~5 min): no auth headers. Body is a ZIP holding one CSV.
    resp = requests.get(url, timeout=300)
    resp.raise_for_status()
    blob = resp.content
    if blob[:2] == b"PK":
        with zipfile.ZipFile(io.BytesIO(blob)) as zf:
            blob = zf.read(zf.namelist()[0])
    text = blob.decode("utf-8-sig")
    return list(csv.DictReader(io.StringIO(text)))


def main():
    default_account = config.default_id("microsoft_ads")

    parser = argparse.ArgumentParser(description="Query Microsoft Advertising performance")
    parser.add_argument(
        "--account-id",
        default=default_account or None,
        required=not bool(default_account),
        help="Microsoft Advertising account ID (digits only)",
    )
    parser.add_argument(
        "--report-type",
        default="campaign",
        choices=["campaign", "account"],
        help="Entity to report on (default: campaign)",
    )
    parser.add_argument(
        "--aggregation",
        default="Summary",
        choices=["Summary", "Daily", "Weekly", "Monthly", "Yearly"],
        help="Time aggregation (default: Summary)",
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
        "--columns",
        default="",
        help="Comma-separated report columns. Default depends on --report-type.",
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

    if args.columns:
        columns = [c.strip() for c in args.columns.split(",") if c.strip()]
    else:
        columns = list(DEFAULT_COLUMNS[args.report_type])
        if args.aggregation == "Summary" and "TimePeriod" in columns:
            columns.remove("TimePeriod")

    request = _build_report_request(
        args.report_type, columns, args.aggregation, args.account_id, start, end,
    )
    try:
        client = Client(account_id=int(args.account_id))
        rows = _run_report(client, request)
    except (ApiError, requests.RequestException) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    if not rows:
        print("No data returned.")
        return

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
