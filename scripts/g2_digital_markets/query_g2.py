#!/usr/bin/env python3
"""
Query the G2 Digital Markets Click Report API (Capterra / GetApp / Software Advice).

Returns historical PPC click data across G2 Digital Markets channels, categories,
and countries. Supports server-side filtering, automatic cursor pagination, and
client-side aggregation (group by month, channel, vendor/product, etc.).

Usage:
    # Raw records for a date range
    python query_g2.py --start 2026-05-01 --end 2026-05-31

    # Monthly spend/clicks/conversions/CPL
    python query_g2.py --start 2026-01-01 --end 2026-05-31 --group-by month

    # Monthly breakdown per channel
    python query_g2.py --start 2026-01-01 --end 2026-05-31 --group-by month,channel

    # Filter to one channel + country, group by vendor/product
    python query_g2.py --start 2026-05-01 --end 2026-05-31 \
        --channel capterra --country US --group-by product_name

    # Confirm the API key works (smallest possible request)
    python query_g2.py --action verify

Date formats:
    Custom:  YYYY-MM-DD
    Named:   today, yesterday, 7daysAgo, 30daysAgo, 90daysAgo

Notes:
    - Click data is NOT final until the monthly invoice is issued. Month-end review
      may lower totals, so this report can read slightly higher than the invoice.
    - Rate limit: 1000 requests/minute. Pagination follows meta.next automatically.

Credentials and endpoint configured in ~/.fetch-ads-data/config.json
"""

import argparse
import csv
import json
import sys
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import urlparse, parse_qs

sys.path.insert(0, str(Path(__file__).parent.parent))
import config

import requests

SERVICE = "g2_digital_markets"
DEFAULT_BASE_URL = "https://public-api.capterra.com/v2"

# Record fields summed when aggregating. Derived metrics are recomputed afterward.
SUM_FIELDS = ["clicks", "conversions", "cost"]
# Fields the API may return per click record (varies by account/version).
KNOWN_FIELDS = [
    "date_of_report", "vendor_name", "product_name", "campaign_name", "category",
    "avg_cpc", "avg_position", "clicks", "conversions", "conversion_rate",
    "cost", "cpl", "channel", "country", "email", "vendor_id", "campaign_id",
    "landing_page",
]


def _api_key() -> str:
    creds_path = config.credentials_path(SERVICE)
    if not creds_path or not Path(creds_path).exists():
        print(
            "Error: G2 Digital Markets credentials not found. Create "
            "~/.fetch-ads-data/g2-digital-markets.json with {\"api_key\": \"...\"}.",
            file=sys.stderr,
        )
        sys.exit(1)
    data = json.loads(Path(creds_path).read_text())
    key = data.get("api_key", "").strip()
    if not key:
        print("Error: 'api_key' missing or empty in g2-digital-markets.json.", file=sys.stderr)
        sys.exit(1)
    return key


def _resolve_date(value: str) -> str:
    """Resolve a date string or shorthand to YYYY-MM-DD (the format the API expects)."""
    today = date.today()
    shortcuts = {
        "today": today,
        "yesterday": today - timedelta(days=1),
        "7daysAgo": today - timedelta(days=7),
        "30daysAgo": today - timedelta(days=30),
        "90daysAgo": today - timedelta(days=90),
    }
    d = shortcuts.get(value)
    if d is None:
        d = date.fromisoformat(value)  # raises on bad input
    return d.isoformat()


def _request(base_url: str, params: dict, api_key: str, auth_in: str, auth_param: str) -> dict:
    """Single GET /clicks request. API key sent as a header or query param per config."""
    url = f"{base_url.rstrip('/')}/clicks"
    headers = {"Accept": "application/json"}
    query = {k: v for k, v in params.items() if v is not None and v != ""}
    if auth_in == "query":
        query[auth_param] = api_key
    else:  # default: header
        headers[auth_param] = api_key
    resp = requests.get(url, headers=headers, params=query, timeout=60)
    if resp.status_code == 400:
        raise SystemExit(f"Error 400 (invalid parameters): {resp.text.strip()}")
    if resp.status_code in (401, 403):
        raise SystemExit(
            f"Error {resp.status_code} (auth): API key rejected. Check "
            "~/.fetch-ads-data/g2-digital-markets.json and the 'auth_in' setting "
            f"(currently '{auth_in}') in config.json. Response: {resp.text.strip()}"
        )
    if resp.status_code == 404:
        raise SystemExit(f"Error 404 (not found): {resp.text.strip()}")
    if resp.status_code >= 500:
        raise SystemExit(f"Error {resp.status_code} (G2 server error): {resp.text.strip()}")
    resp.raise_for_status()
    return resp.json()


def _cursor_from_next(next_url: str) -> str:
    """Extract the cursor query param from a meta.next URL."""
    if not next_url:
        return ""
    qs = parse_qs(urlparse(next_url).query)
    vals = qs.get("cursor", [])
    return vals[0] if vals else ""


def fetch_clicks(base_url: str, api_key: str, auth_in: str, auth_param: str,
                 start: str, end: str, channel: str, category: str, country: str,
                 page_size: int, include_conversion_type: bool,
                 max_pages: int) -> list[dict]:
    """Fetch all click records across the date range, following cursor pagination."""
    base_params = {
        "start_date": start,
        "end_date": end,
        "channel": channel,
        "category": category,
        "country": country,
        "page_size": str(page_size) if page_size else None,
    }
    if include_conversion_type:
        base_params["include_conversion_type"] = "true"

    records: list[dict] = []
    cursor = ""
    for _ in range(max_pages):
        params = dict(base_params)
        if cursor:
            params["cursor"] = cursor
        payload = _request(base_url, params, api_key, auth_in, auth_param)
        records.extend(payload.get("clicks", []) or [])
        cursor = _cursor_from_next((payload.get("meta") or {}).get("next", ""))
        if not cursor:
            break
    else:
        print(
            f"Warning: stopped after {max_pages} pages; more data may exist. "
            "Narrow the date range or raise --max-pages.",
            file=sys.stderr,
        )
    return records


def _to_float(v) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _normalize_conversions_by_type(cbt) -> list[tuple]:
    """Normalize the per-record conversions_by_type into (type, count) pairs.

    The API returns this field in one of two shapes depending on account/version:
      - dict:  {"bookDemo": 3, "freeTrial": 1, "other": 0}
      - list:  [{"type": "bookDemo", "count": 3}, {"type": "freeTrial", "count": 1}]
    Anything else (None, unexpected types) yields no pairs.
    """
    if not cbt:
        return []
    if isinstance(cbt, dict):
        return list(cbt.items())
    if isinstance(cbt, list):
        pairs = []
        for item in cbt:
            if not isinstance(item, dict):
                continue
            ctype = item.get("type") or item.get("name") or item.get("conversion_type")
            if ctype is None:
                continue
            cnt = item.get("count", item.get("conversions", item.get("value", 0)))
            pairs.append((str(ctype), cnt))
        return pairs
    return []


def aggregate(records: list[dict], group_by: list[str]) -> list[dict]:
    """Group records by the given keys, summing clicks/conversions/cost and
    recomputing derived metrics (avg_cpc, conversion_rate, cpl, avg_position)."""
    groups: dict[tuple, dict] = {}
    for r in records:
        key = tuple(_group_value(r, g) for g in group_by)
        agg = groups.setdefault(key, {
            "clicks": 0.0, "conversions": 0.0, "cost": 0.0,
            "_pos_weight": 0.0, "_pos_sum": 0.0, "conversions_by_type": {},
        })
        for f in SUM_FIELDS:
            agg[f] += _to_float(r.get(f))
        # Click-weighted average position
        clicks = _to_float(r.get("clicks"))
        if "avg_position" in r and clicks > 0:
            agg["_pos_sum"] += _to_float(r.get("avg_position")) * clicks
            agg["_pos_weight"] += clicks
        for ctype, cnt in _normalize_conversions_by_type(r.get("conversions_by_type")):
            agg["conversions_by_type"][ctype] = agg["conversions_by_type"].get(ctype, 0) + _to_float(cnt)

    rows = []
    for key, agg in groups.items():
        row = {g: k for g, k in zip(group_by, key)}
        clicks, conversions, cost = agg["clicks"], agg["conversions"], agg["cost"]
        row["clicks"] = int(round(clicks))
        row["conversions"] = int(round(conversions))
        row["cost"] = round(cost, 2)
        row["avg_cpc"] = round(cost / clicks, 2) if clicks else 0.0
        row["conversion_rate"] = round(conversions / clicks, 4) if clicks else 0.0
        row["cpl"] = round(cost / conversions, 2) if conversions else 0.0
        if agg["_pos_weight"]:
            row["avg_position"] = round(agg["_pos_sum"] / agg["_pos_weight"], 1)
        if agg["conversions_by_type"]:
            row["conversions_by_type"] = {k: int(round(v)) for k, v in agg["conversions_by_type"].items()}
        rows.append(row)

    # Sort by group keys for stable output
    rows.sort(key=lambda r: tuple(str(r.get(g, "")) for g in group_by))
    return rows


def _group_value(record: dict, key: str) -> str:
    if key == "month":
        d = str(record.get("date_of_report", ""))
        return d[:7] if len(d) >= 7 else d  # YYYY-MM
    return str(record.get(key, "") or "")


def _select_fields(records: list[dict]) -> list[dict]:
    """Project raw records to a stable, ordered set of known fields (plus any extras)."""
    rows = []
    for r in records:
        ordered = {f: r.get(f) for f in KNOWN_FIELDS if f in r}
        for k, v in r.items():
            if k not in ordered:
                ordered[k] = v
        rows.append(ordered)
    return rows


def _print_table(rows: list[dict]) -> None:
    if not rows:
        print("No results.")
        return
    cols: list[str] = []
    for r in rows:
        for k in r.keys():
            if k not in cols:
                cols.append(k)

    def cell(r, c):
        v = r.get(c, "")
        return json.dumps(v) if isinstance(v, (dict, list)) else str(v)

    widths = {c: max(len(c), max(len(cell(r, c)) for r in rows)) for c in cols}
    print("  ".join(c.ljust(widths[c]) for c in cols))
    print("  ".join("-" * widths[c] for c in cols))
    for r in rows:
        print("  ".join(cell(r, c).ljust(widths[c]) for c in cols))


def _output(rows: list[dict], fmt: str) -> None:
    if fmt == "json":
        print(json.dumps(rows, indent=2))
    elif fmt == "csv":
        if not rows:
            return
        cols: list[str] = []
        for r in rows:
            for k in r.keys():
                if k not in cols:
                    cols.append(k)
        writer = csv.DictWriter(sys.stdout, fieldnames=cols)
        writer.writeheader()
        for r in rows:
            writer.writerow({k: (json.dumps(v) if isinstance(v, (dict, list)) else v) for k, v in r.items()})
    else:
        _print_table(rows)


def main():
    cfg = config.service_config(SERVICE)
    base_url = cfg.get("base_url") or DEFAULT_BASE_URL
    auth_in = (cfg.get("auth_in") or "header").lower()
    auth_param = cfg.get("auth_param") or "api_key"

    parser = argparse.ArgumentParser(description="Query the G2 Digital Markets Click Report API")
    parser.add_argument("--action", default="query", choices=["query", "verify"],
                        help="query (default) or verify (test the API key)")
    parser.add_argument("--start", default="30daysAgo",
                        help="Start date (first click): YYYY-MM-DD or 7daysAgo/30daysAgo/90daysAgo (default: 30daysAgo)")
    parser.add_argument("--end", default="today",
                        help="End date (last click): YYYY-MM-DD or today/yesterday (default: today)")
    parser.add_argument("--channel", default="",
                        help="Filter by channel: capterra, getapp, software advice")
    parser.add_argument("--category", default="", help="Filter by category")
    parser.add_argument("--country", default="", help="Filter by country")
    parser.add_argument("--group-by", default="",
                        help="Comma-separated grouping keys (sums clicks/conversions/cost, "
                             "recomputes avg_cpc/conversion_rate/cpl). Keys: month, channel, "
                             "country, category, product_name, vendor_name, campaign_name. "
                             "Empty = raw per-record output.")
    parser.add_argument("--include-conversion-type", action="store_true",
                        help="Include conversions_by_type breakdown (bookDemo, freeTrial, other)")
    parser.add_argument("--page-size", type=int, default=1000,
                        help="Records per request / page (default: 1000)")
    parser.add_argument("--max-pages", type=int, default=100,
                        help="Safety cap on paginated requests (default: 100)")
    parser.add_argument("--format", default="table", choices=["table", "csv", "json"],
                        help="Output format (default: table)")
    args = parser.parse_args()

    api_key = _api_key()

    if args.action == "verify":
        end = _resolve_date("today")
        start = _resolve_date("30daysAgo")
        payload = _request(base_url, {"start_date": start, "end_date": end, "page_size": "1"},
                           api_key, auth_in, auth_param)
        n = len(payload.get("clicks", []) or [])
        print(f"OK — G2 Digital Markets API key works. Sample request returned {n} record(s).")
        return

    start = _resolve_date(args.start)
    end = _resolve_date(args.end)
    group_by = [g.strip() for g in args.group_by.split(",") if g.strip()]

    records = fetch_clicks(
        base_url, api_key, auth_in, auth_param,
        start, end, args.channel, args.category, args.country,
        args.page_size, args.include_conversion_type, args.max_pages,
    )

    if not records:
        print("No data returned.")
        return

    rows = aggregate(records, group_by) if group_by else _select_fields(records)
    _output(rows, args.format)


if __name__ == "__main__":
    main()
