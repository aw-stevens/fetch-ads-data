#!/usr/bin/env python3
"""Query Microsoft Advertising (Bing Ads) performance via the Reporting API.

Bing has no query language, so this mirrors the *shape* of the other query tools
(entity + metrics + time + format) rather than a literal query string. It submits an
Account- or Campaign-PerformanceReport, polls until ready, downloads the CSV, and
prints table / csv / json — the same UX as google_ads_query / linkedin_ads_query.
"""

import argparse
import csv
import json
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from auth import ENVIRONMENT, authorization_data

sys.path.insert(0, str(Path(__file__).parent.parent))
import config

from bingads.service_client import ServiceClient
from bingads.v13.reporting import ReportingDownloadParameters, ReportingServiceManager

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
COLUMN_ARRAY_TYPE = {
    "campaign": "ArrayOfCampaignPerformanceReportColumn",
    "account": "ArrayOfAccountPerformanceReportColumn",
}
COLUMN_ITEM_ATTR = {
    "campaign": "CampaignPerformanceReportColumn",
    "account": "AccountPerformanceReportColumn",
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


def _build_report_request(reporting_service, report_type, columns, aggregation,
                          account_id, start, end):
    request = reporting_service.factory.create(REPORT_REQUEST_TYPE[report_type])
    request.Aggregation = aggregation
    request.Format = "Csv"
    request.ReturnOnlyCompleteData = False
    request.ExcludeReportHeader = True
    request.ExcludeReportFooter = True
    request.ExcludeColumnHeaders = False
    request.ReportName = f"{report_type.capitalize()} Performance Report"

    # Scope — restrict to the requested account.
    account_ids = reporting_service.factory.create("ArrayOflong")
    account_ids.long.append(int(account_id))
    scope = request.Scope
    scope.AccountIds = account_ids
    if report_type == "campaign":
        scope.Campaigns = None

    # Columns.
    column_array = reporting_service.factory.create(COLUMN_ARRAY_TYPE[report_type])
    getattr(column_array, COLUMN_ITEM_ATTR[report_type]).extend(columns)
    request.Columns = column_array

    # Time — explicit custom date range.
    report_time = reporting_service.factory.create("ReportTime")
    start_date = reporting_service.factory.create("Date")
    start_date.Day, start_date.Month, start_date.Year = start.day, start.month, start.year
    end_date = reporting_service.factory.create("Date")
    end_date.Day, end_date.Month, end_date.Year = end.day, end.month, end.year
    report_time.CustomDateRangeStart = start_date
    report_time.CustomDateRangeEnd = end_date
    report_time.PredefinedTime = None
    request.Time = report_time
    return request


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

    auth_data = authorization_data(account_id=int(args.account_id))
    reporting_service = ServiceClient(
        service="ReportingService",
        version=13,
        authorization_data=auth_data,
        environment=ENVIRONMENT,
    )
    request = _build_report_request(
        reporting_service, args.report_type, columns, args.aggregation,
        args.account_id, start, end,
    )

    reporting_manager = ReportingServiceManager(
        authorization_data=auth_data,
        poll_interval_in_milliseconds=5000,
        environment=ENVIRONMENT,
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        params = ReportingDownloadParameters(
            report_request=request,
            result_file_directory=tmpdir,
            result_file_name="ms_ads_report.csv",
            overwrite_result_file=True,
            timeout_in_milliseconds=3_600_000,
        )
        report = reporting_manager.download_report(params)

        if report is None or report.record_count == 0:
            print("No data returned.")
            return

        report_columns = list(report.report_columns)
        rows = [{c: rec.value(c) for c in report_columns} for rec in report.report_records]
        report.close()

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
