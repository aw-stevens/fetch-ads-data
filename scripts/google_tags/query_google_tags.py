#!/usr/bin/env python3
"""
Query Google Tags configuration via the GA4 Admin API.

Lists data streams (measurement IDs), key events (conversions),
custom dimensions/metrics, and linked Google Ads accounts.

Usage:
    python query_google_tags.py --action list-streams
    python query_google_tags.py --action list-key-events --property 123456789
    python query_google_tags.py --action list-custom-dimensions --format json
    python query_google_tags.py --action list-ads-links

Credentials and properties configured in ~/.ad-analytics/config.json
"""

import argparse
import csv
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import config

# Set ADC path from config (same as GA4 Data API)
adc_path = config.credentials_path("google_analytics")
if adc_path:
    os.environ.setdefault("GOOGLE_APPLICATION_CREDENTIALS", adc_path)

from google.analytics.admin_v1beta import AnalyticsAdminServiceClient

ACTIONS = [
    "list-streams",
    "list-key-events",
    "list-custom-dimensions",
    "list-custom-metrics",
    "list-ads-links",
]

STREAM_TYPE_NAMES = {
    0: "UNSPECIFIED",
    1: "WEB",
    2: "ANDROID_APP",
    3: "IOS_APP",
}


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


def list_streams(client, property_id: str) -> list[dict]:
    rows = []
    for s in client.list_data_streams(parent=f"properties/{property_id}"):
        row = {
            "display_name": s.display_name,
            "type": STREAM_TYPE_NAMES.get(s.type_, str(s.type_)),
        }
        if s.web_stream_data:
            row["measurement_id"] = s.web_stream_data.measurement_id
            row["default_uri"] = s.web_stream_data.default_uri
        else:
            row["measurement_id"] = ""
            row["default_uri"] = ""
        row["stream_id"] = s.name.split("/")[-1]
        rows.append(row)
    return rows


def list_key_events(client, property_id: str) -> list[dict]:
    COUNTING = {0: "UNSPECIFIED", 1: "ONCE_PER_EVENT", 2: "ONCE_PER_SESSION"}
    rows = []
    for e in client.list_key_events(parent=f"properties/{property_id}"):
        rows.append({
            "event_name": e.event_name,
            "counting": COUNTING.get(e.counting_method, str(e.counting_method)),
            "created": e.create_time.strftime("%Y-%m-%d") if e.create_time else "",
            "deletable": str(e.deletable) if hasattr(e, "deletable") else "",
        })
    return rows


def list_custom_dimensions(client, property_id: str) -> list[dict]:
    SCOPE = {0: "UNSPECIFIED", 1: "EVENT", 2: "USER", 3: "ITEM"}
    rows = []
    for d in client.list_custom_dimensions(parent=f"properties/{property_id}"):
        rows.append({
            "parameter_name": d.parameter_name,
            "display_name": d.display_name,
            "scope": SCOPE.get(d.scope, str(d.scope)),
            "description": d.description or "",
        })
    return rows


def list_custom_metrics(client, property_id: str) -> list[dict]:
    SCOPE = {0: "UNSPECIFIED", 1: "EVENT"}
    UNIT = {0: "UNSPECIFIED", 1: "STANDARD", 2: "CURRENCY", 4: "FEET", 5: "METERS",
            6: "KILOMETERS", 7: "MILES", 8: "MILLISECONDS", 9: "SECONDS",
            10: "MINUTES", 11: "HOURS"}
    rows = []
    for m in client.list_custom_metrics(parent=f"properties/{property_id}"):
        rows.append({
            "parameter_name": m.parameter_name,
            "display_name": m.display_name,
            "scope": SCOPE.get(m.scope, str(m.scope)),
            "unit": UNIT.get(m.measurement_unit, str(m.measurement_unit)),
            "description": m.description or "",
        })
    return rows


def list_ads_links(client, property_id: str) -> list[dict]:
    rows = []
    for link in client.list_google_ads_links(parent=f"properties/{property_id}"):
        rows.append({
            "customer_id": link.customer_id,
            "ads_personalization": str(link.ads_personalization_enabled),
            "link_id": link.name.split("/")[-1],
        })
    return rows


ACTION_MAP = {
    "list-streams": list_streams,
    "list-key-events": list_key_events,
    "list-custom-dimensions": list_custom_dimensions,
    "list-custom-metrics": list_custom_metrics,
    "list-ads-links": list_ads_links,
}


def main():
    default_property = config.default_id("google_analytics")

    parser = argparse.ArgumentParser(description="Query Google Tags / GA4 Admin API")
    parser.add_argument(
        "--action",
        required=True,
        choices=ACTIONS,
        help="What to query",
    )
    parser.add_argument(
        "--property",
        default=default_property or None,
        required=not bool(default_property),
        help="GA4 property ID (digits only)",
    )
    parser.add_argument(
        "--format",
        default="table",
        choices=["table", "csv", "json"],
        help="Output format (default: table)",
    )
    args = parser.parse_args()

    client = AnalyticsAdminServiceClient()
    action_fn = ACTION_MAP[args.action]

    try:
        rows = action_fn(client, args.property)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    _output(rows, args.format)


if __name__ == "__main__":
    main()
