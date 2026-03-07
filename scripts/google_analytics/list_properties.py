#!/usr/bin/env python3
"""
List GA4 properties configured in ~/.ad-analytics/config.json.

Also verifies access by running a simple query against each property.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import config


def main():
    properties = config.account_list("google_analytics")
    if not properties:
        print("No properties configured in config.json under google_analytics.properties")
        return

    try:
        from google.analytics.data_v1beta import BetaAnalyticsDataClient
        from google.analytics.data_v1beta.types import (
            Metric, RunReportRequest, DateRange
        )
    except ImportError:
        print("Install: pip install google-analytics-data", file=sys.stderr)
        sys.exit(1)

    import os
    adc_path = config.credentials_path("google_analytics")
    if adc_path:
        os.environ.setdefault("GOOGLE_APPLICATION_CREDENTIALS", adc_path)

    client = BetaAnalyticsDataClient()
    default = config.default_id("google_analytics")

    print(f"{'Property ID':<15} {'Site':<40} {'Access':<10} {'Default'}")
    print("-" * 75)

    for prop_id, name in properties.items():
        is_default = "yes" if prop_id == default else ""
        try:
            response = client.run_report(RunReportRequest(
                property=f"properties/{prop_id}",
                metrics=[Metric(name="sessions")],
                date_ranges=[DateRange(start_date="7daysAgo", end_date="today")],
                limit=1,
            ))
            access = "OK"
        except Exception:
            access = "DENIED"
        print(f"{prop_id:<15} {name:<40} {access:<10} {is_default}")


if __name__ == "__main__":
    main()
