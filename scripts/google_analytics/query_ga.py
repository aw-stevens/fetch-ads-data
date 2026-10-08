#!/usr/bin/env python3
"""
Query Google Analytics 4 using the Data API (standard or realtime).

Usage:
    python query_ga.py \
        --property 123456789 \
        --dimensions sessionSource sessionMedium \
        --metrics sessions newUsers \
        --start 30daysAgo --end today \
        --limit 20 --format table

    python query_ga.py --realtime \
        --dimensions city \
        --metrics activeUsers \
        --limit 10

Date formats (ignored for --realtime):
    Named:  today, yesterday, 7daysAgo, 28daysAgo, 30daysAgo, 90daysAgo
    Custom: YYYY-MM-DD

Credentials and properties configured in ~/.fetch-ads-data/config.json
"""

import argparse
import csv
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import config

# Set ADC path from config
adc_path = config.credentials_path("google_analytics")
if adc_path:
    os.environ.setdefault("GOOGLE_APPLICATION_CREDENTIALS", adc_path)


def format_value(val, header_name):
    """Round floats for readability."""
    try:
        f = float(val)
        if f == int(f):
            return str(int(f))
        return f"{f:.2f}"
    except ValueError:
        return val


def main():
    default_property = config.default_id("google_analytics")

    parser = argparse.ArgumentParser(description="Query GA4 via the Data API")
    parser.add_argument(
        "--property",
        default=default_property or None,
        required=not bool(default_property),
        help="GA4 property ID (digits only). Defaults to google_analytics.default_properties in config.",
    )
    parser.add_argument("--dimensions", nargs="+", default=[], metavar="DIM", help="Dimension names")
    parser.add_argument("--metrics", nargs="+", required=True, metavar="MET", help="Metric names")
    parser.add_argument("--start", default="30daysAgo", help="Start date (default: 30daysAgo)")
    parser.add_argument("--end", default="today", help="End date (default: today)")
    parser.add_argument("--limit", type=int, default=100, help="Row limit (default: 100)")
    parser.add_argument("--format", choices=["table", "csv", "json"], default="table")
    parser.add_argument("--realtime", action="store_true", help="Query realtime data (last 30 min)")
    args = parser.parse_args()

    try:
        from google.analytics.data_v1beta import BetaAnalyticsDataClient
        from google.analytics.data_v1beta.types import (
            DateRange, Dimension, Metric, RunReportRequest, RunRealtimeReportRequest
        )
    except ImportError:
        print("Install: pip install google-analytics-data", file=sys.stderr)
        sys.exit(1)

    client = BetaAnalyticsDataClient()
    prop = f"properties/{args.property}"
    dims = [Dimension(name=d) for d in args.dimensions]
    mets = [Metric(name=m) for m in args.metrics]

    try:
        if args.realtime:
            response = client.run_realtime_report(RunRealtimeReportRequest(
                property=prop, dimensions=dims, metrics=mets, limit=args.limit,
            ))
        else:
            response = client.run_report(RunReportRequest(
                property=prop, dimensions=dims, metrics=mets,
                date_ranges=[DateRange(start_date=args.start, end_date=args.end)],
                limit=args.limit,
            ))
    except Exception as ex:
        print(f"Error: {ex}", file=sys.stderr)
        sys.exit(1)

    dim_headers = [h.name for h in response.dimension_headers]
    met_headers = [h.name for h in response.metric_headers]
    all_headers = dim_headers + met_headers

    rows = []
    for row in response.rows:
        dim_vals = [v.value for v in row.dimension_values]
        met_vals = [format_value(v.value, met_headers[i]) for i, v in enumerate(row.metric_values)]
        rows.append(dict(zip(all_headers, dim_vals + met_vals)))

    if not rows:
        print("No results.")
        return

    if args.format == "json":
        print(json.dumps(rows, indent=2))

    elif args.format == "csv":
        writer = csv.DictWriter(sys.stdout, fieldnames=all_headers)
        writer.writeheader()
        writer.writerows(rows)

    else:  # table
        widths = {h: max(len(h), max(len(str(r[h])) for r in rows)) for h in all_headers}
        sep = " | "
        header_line = sep.join(h.ljust(widths[h]) for h in all_headers)
        print(header_line)
        print("-" * len(header_line))
        for row in rows:
            print(sep.join(str(row[h]).ljust(widths[h]) for h in all_headers))
        print(f"\n({len(rows)} rows)")


if __name__ == "__main__":
    main()
