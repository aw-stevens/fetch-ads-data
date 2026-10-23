#!/usr/bin/env python3
"""
Google Ads keyword search volume via DataForSEO (Keywords Data API, Live).

Returns average monthly search volume, CPC, competition, top-of-page bid range, and the
monthly trend for each keyword. Keywords are sent in chunks of 700 per request.

Usage:
    # Volume for a few keywords (US / English by default)
    python query_volume.py "crm software" "email marketing tool"

    # Keywords from a file (one per line), UK / English, as CSV
    python query_volume.py --file keywords.txt --location-code 2826 --format csv

    # Preview requests and projected cost without calling the API
    python query_volume.py "crm software" --dry-run

Billing: one charge per request (up to 1,000 keywords), so 1 keyword costs the same as
700. Every call is checked against the daily spend cap first (see client.py).

Credentials: DATAFORSEO_LOGIN / DATAFORSEO_PASSWORD, or ~/.fetch-ads-data/dataforseo.json
"""

import argparse
import csv
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import client as dfs

ENDPOINT = "/v3/keywords_data/google_ads/search_volume/live"
KEYWORDS_PER_REQUEST = 700
MAX_KEYWORDS = 10_000
MAX_KEYWORD_CHARS = 80
MAX_KEYWORD_WORDS = 10
# Google Ads Live endpoints allow 12 requests/minute per account.
REQUEST_SPACING_SECONDS = 5.1

COLUMNS = [
    "keyword", "search_volume", "cpc", "competition", "competition_index",
    "low_top_of_page_bid", "high_top_of_page_bid", "monthly_searches",
]


def clean_keywords(raw: list[str]) -> list[str]:
    """Strip, drop blanks, de-duplicate (case-insensitive, first spelling wins), validate."""
    seen = set()
    out = []
    for kw in raw:
        kw = " ".join(kw.split())
        if not kw or kw.lower() in seen:
            continue
        if len(kw) > MAX_KEYWORD_CHARS or len(kw.split()) > MAX_KEYWORD_WORDS:
            raise dfs.DataForSeoError(
                f"Keyword exceeds {MAX_KEYWORD_CHARS} characters / {MAX_KEYWORD_WORDS} words: {kw!r}"
            )
        seen.add(kw.lower())
        out.append(kw)
    if not out:
        raise dfs.DataForSeoError("No keywords provided.")
    if len(out) > MAX_KEYWORDS:
        raise dfs.DataForSeoError(f"Too many keywords ({len(out)}); max {MAX_KEYWORDS} per run.")
    return out


def build_requests(keywords: list[str], location_code: int, language_code: str) -> list[list[dict]]:
    """One request body per chunk. Live endpoints take exactly one task per call."""
    return [
        [{"keywords": kws, "location_code": location_code, "language_code": language_code}]
        for kws in dfs.chunk(keywords, KEYWORDS_PER_REQUEST)
    ]


def _num(v):
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def flatten_row(raw: dict) -> dict:
    monthly = raw.get("monthly_searches")
    if isinstance(monthly, list):
        monthly = sorted(
            ({"year": m.get("year"), "month": m.get("month"), "search_volume": m.get("search_volume")}
             for m in monthly if isinstance(m, dict)),
            key=lambda m: (m["year"] or 0, m["month"] or 0),
        )
    else:
        monthly = None
    return {
        "keyword": raw.get("keyword") or "",
        "search_volume": _num(raw.get("search_volume")),
        "cpc": _num(raw.get("cpc")),
        "competition": raw.get("competition") if isinstance(raw.get("competition"), str) else None,
        "competition_index": _num(raw.get("competition_index")),
        "low_top_of_page_bid": _num(raw.get("low_top_of_page_bid")),
        "high_top_of_page_bid": _num(raw.get("high_top_of_page_bid")),
        "monthly_searches": monthly,
    }


def fetch_volume(api: dfs.Client, tracker: dfs.SpendTracker, bodies: list[list[dict]],
                 sleep=time.sleep) -> list[dict]:
    """Send each chunk, checking the cap before and recording the charge after each one,
    so a mid-run failure still leaves an accurate tally of what was billed."""
    per_task = dfs.rate("search_volume_live_per_task")
    rows = []
    for i, body in enumerate(bodies):
        tracker.check(per_task)
        if i:
            sleep(REQUEST_SPACING_SECONDS)
        payload = api.post(ENDPOINT, body)
        tracker.record("keyword_volume", len(body[0]["keywords"]), dfs.response_cost(payload, per_task))
        task = (payload.get("tasks") or [{}])[0]
        dfs.task_ok(task, accept=(dfs.OK, dfs.NO_RESULTS))  # no data for any keyword is not an error
        rows.extend(flatten_row(r) for r in (task.get("result") or []) if isinstance(r, dict))
    return rows


def _trend_text(monthly) -> str:
    if not monthly:
        return ""
    return " ".join(f"{m['year']}-{m['month']:02d}:{m['search_volume']}" for m in monthly
                    if m.get("year") and m.get("month"))


def output(rows: list[dict], fmt: str, cost: dict | None) -> None:
    if fmt == "json":
        print(json.dumps({"data": rows, "cost": cost}, indent=2))
        return
    flat = [{**r, "monthly_searches": _trend_text(r["monthly_searches"])} for r in rows]
    if fmt == "csv":
        writer = csv.DictWriter(sys.stdout, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(flat)
        if cost:
            dfs.print_cost(cost, file=sys.stderr)
        return
    dfs.print_table(flat, COLUMNS)
    if cost:
        dfs.print_cost(cost)


def main():
    parser = argparse.ArgumentParser(description="Google Ads keyword search volume via DataForSEO")
    parser.add_argument("keywords", nargs="*", help="Keywords to look up")
    parser.add_argument("--file", help="Read additional keywords from a file, one per line")
    parser.add_argument("--location-code", type=int, default=None,
                        help="DataForSEO location code (default: config or 2840 = United States)")
    parser.add_argument("--language-code", default=None,
                        help="Language code (default: config or 'en')")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show request bodies and projected cost without calling the API")
    parser.add_argument("--format", default="table", choices=["table", "csv", "json"],
                        help="Output format (default: table)")
    args = parser.parse_args()

    try:
        raw = list(args.keywords)
        if args.file:
            raw += Path(args.file).expanduser().read_text().splitlines()
        keywords = clean_keywords(raw)
        location = args.location_code or dfs.default_location_code()
        language = args.language_code or dfs.default_language_code()
        bodies = build_requests(keywords, location, language)
        tracker = dfs.SpendTracker()
        projected = len(bodies) * dfs.rate("search_volume_live_per_task")

        if args.dry_run:
            print(json.dumps({
                "dry_run": True,
                "endpoint": ENDPOINT,
                "keyword_count": len(keywords),
                "request_count": len(bodies),
                "projected_cost_usd": round(projected, 6),
                "today_total_usd": round(tracker.total, 6),
                "daily_cap_usd": tracker.cap,
                "within_cap": tracker.total + projected <= tracker.cap + 1e-9,
                "requests": bodies,
            }, indent=2))
            return

        tracker.check(projected)
        before = tracker.total
        rows = fetch_volume(dfs.Client.from_env(), tracker, bodies)
    except dfs.DataForSeoError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(2 if isinstance(exc, dfs.CapExceeded) else 1)

    output(rows, args.format, tracker.summary(tracker.total - before))


if __name__ == "__main__":
    main()
