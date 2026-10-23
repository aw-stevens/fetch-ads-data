#!/usr/bin/env python3
"""
Ads an advertiser runs on Google, via DataForSEO's Google Ads Search API (Google Ads
Transparency Center data).

Give an advertiser domain (example.com) or advertiser IDs (AR..., from
query_ads_advertisers.py). Returns each ad's format, first/last shown dates, the
advertiser account behind it, a Transparency Center link, and a preview image/URL.
The API returns no ad copy — open the link or preview to read it.

Each domain is its own task. Advertiser IDs are grouped into one task (up to 25 per
task), so the accounts of one brand share a single result list.

Modes:
    standard  Standard Queue: task_post, then poll task_get (cheapest; minutes)
    priority  Standard Queue with high priority (about 2x price; usually under a minute)
    live      Live endpoint, one call per task (most expensive; seconds)

Usage:
    python query_ads_search.py example.com
    python query_ads_search.py example.com --platform google_search --ad-format text --mode live
    python query_ads_search.py AR01234567890123456789 AR98765432109876543210 --format json
    python query_ads_search.py example.com --date-from 2026-01-01 --date-to 2026-03-31 --dry-run

    # Collect results for tasks that were posted earlier but timed out (free)
    python query_ads_search.py --task-ids 01234567-89ab-cdef-0123-456789abcdef

Billing: per task per 40 ads (depth rounds up to the next 40). Retrieving queued results
is free. Every call is checked against the daily spend cap first.

Credentials: DATAFORSEO_LOGIN / DATAFORSEO_PASSWORD, or ~/.fetch-ads-data/dataforseo.json
"""

import argparse
import csv
import json
import re
import sys
import time
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import client as dfs

TASK_POST = "/v3/serp/google/ads_search/task_post"
LIVE = "/v3/serp/google/ads_search/live/advanced"
MAX_TASKS = 100  # task_post accepts up to 100 tasks per request
IDS_PER_TASK = 25
PAGE_SIZE = 40  # billed per 40 ads
MAX_DEPTH = {"standard": 700, "priority": 700, "live": 120}
EARLIEST_DATE = "2018-05-31"
PLATFORMS = ["all", "google_search", "youtube", "google_play", "google_maps", "google_shopping"]
AD_FORMATS = ["all", "text", "image", "video"]
RATES = {"standard": "ads_search_standard_per_page", "priority": "ads_search_priority_per_page",
         "live": "ads_search_live_per_page"}
ADVERTISER_ID = re.compile(r"AR\d{10,}")

CSV_COLUMNS = ["target", "rank", "advertiser_id", "advertiser_name", "verified", "creative_id",
               "format", "first_shown", "last_shown", "transparency_url", "preview_url",
               "preview_image_url", "preview_image_width", "preview_image_height"]


def task_get(task_id: str) -> str:
    return f"/v3/serp/google/ads_search/task_get/advanced/{task_id}"


def clean_domain(raw: str) -> str:
    d = raw.strip().lower()
    d = re.sub(r"^[a-z]+://", "", d).split("/")[0].split("?")[0]
    return d[4:] if d.startswith("www.") else d


def split_targets(raw: list[str]) -> tuple[list[str], list[str]]:
    """Separate advertiser IDs (AR...) from domains; normalize and de-duplicate both."""
    domains, ids = [], []
    for item in raw:
        item = item.strip()
        if not item:
            continue
        if ADVERTISER_ID.fullmatch(item.upper()):
            if item.upper() not in ids:
                ids.append(item.upper())
        else:
            d = clean_domain(item)
            if "." not in d or " " in d:
                raise dfs.DataForSeoError(f"Not a domain or advertiser ID (AR...): {item!r}")
            if d not in domains:
                domains.append(d)
    if not domains and not ids:
        raise dfs.DataForSeoError("No domains or advertiser IDs provided.")
    return domains, ids


def validate_dates(date_from: str | None, date_to: str | None, today: date | None = None) -> None:
    if not date_from and not date_to:
        return
    if not (date_from and date_to):
        raise dfs.DataForSeoError("--date-from and --date-to must be given together.")
    today = today or date.today()
    try:
        start, end = date.fromisoformat(date_from), date.fromisoformat(date_to)
    except ValueError:
        raise dfs.DataForSeoError("Dates must be YYYY-MM-DD.")
    if start < date.fromisoformat(EARLIEST_DATE) or end > today or start > end:
        raise dfs.DataForSeoError(
            f"Date range must satisfy {EARLIEST_DATE} <= date-from <= date-to <= today ({today})."
        )


def build_tasks(domains: list[str], ids: list[str], location_code: int | None, platform: str,
                ad_format: str, date_from: str | None, date_to: str | None, depth: int,
                mode: str) -> tuple[list[dict], list[str]]:
    """One task per domain, plus one task per 25 advertiser IDs. Returns (tasks, labels)."""
    targets = [("target", d) for d in domains] + [("advertiser_ids", g) for g in dfs.chunk(ids, IDS_PER_TASK)]
    tasks, labels = [], []
    for key, value in targets:
        task = {key: value, "depth": depth}
        if location_code:
            task["location_code"] = location_code
        if platform != "all":
            task["platform"] = platform
        if ad_format != "all":
            task["format"] = ad_format
        if date_from:
            task["date_from"], task["date_to"] = date_from, date_to
        if mode == "priority":
            task["priority"] = 2
        tasks.append(task)
        labels.append(value if key == "target" else "ids:" + ",".join(value))
    if len(tasks) > MAX_TASKS:
        raise dfs.DataForSeoError(f"Too many tasks ({len(tasks)}); max {MAX_TASKS} per run.")
    return tasks, labels


def projected_cost(n_tasks: int, depth: int, mode: str) -> float:
    return n_tasks * dfs.serp_pages(depth, PAGE_SIZE) * dfs.rate(RATES[mode])


# --- Parsing ---

def _str(v):
    return v if isinstance(v, str) else None


def _int(v):
    return v if isinstance(v, int) and not isinstance(v, bool) else None


def _image(v) -> dict:
    # Documented as an array, returned as an object in examples — accept both.
    if isinstance(v, list):
        v = v[0] if v else None
    return v if isinstance(v, dict) else {}


def parse_ads(raw: dict, params: dict | None = None) -> dict:
    """Flatten one ads_search result. `params` is the task's echoed request (task["data"])."""
    params = params or {}
    ads = []
    for item in raw.get("items") or []:
        if not isinstance(item, dict) or item.get("type") != "ads_search":
            continue
        image = _image(item.get("preview_image"))
        ads.append({
            "rank": _int(item.get("rank_group")),
            "advertiser_id": _str(item.get("advertiser_id")),
            "advertiser_name": _str(item.get("title")),
            "verified": item.get("verified") if isinstance(item.get("verified"), bool) else None,
            "creative_id": _str(item.get("creative_id")),
            "format": _str(item.get("format")),
            "first_shown": _str(item.get("first_shown")),
            "last_shown": _str(item.get("last_shown")),
            "transparency_url": _str(item.get("url")),
            "preview_url": _str(item.get("preview_url")),
            "preview_image_url": _str(image.get("url")),
            "preview_image_width": _int(image.get("width")),
            "preview_image_height": _int(image.get("height")),
        })

    advertisers: dict = {}
    for ad in ads:
        a = advertisers.setdefault(ad["advertiser_id"], {
            "advertiser_id": ad["advertiser_id"], "name": ad["advertiser_name"],
            "verified": ad["verified"], "ads": 0})
        a["ads"] += 1

    ids = params.get("advertiser_ids") or []
    depth = _int(params.get("depth")) or PAGE_SIZE
    return {
        "target": params.get("target") or (("ids:" + ",".join(ids)) if ids else raw.get("keyword")),
        "advertiser_ids_requested": ids,
        # No location in the request means all locations, whatever the result echoes.
        "location_code": params.get("location_code") if params else raw.get("location_code"),
        "platform": params.get("platform") or "all",
        "ad_format": params.get("format") or "all",
        "date_from": params.get("date_from"),
        "date_to": params.get("date_to"),
        "depth": depth,
        "fetched_at": raw.get("datetime"),
        "ads_returned": len(ads),
        "may_have_more": len(ads) >= depth,
        "advertisers": list(advertisers.values()),
        "ads": ads,
    }


def _parse_task(task: dict) -> dict:
    result = task.get("result") or [{}]
    raw = result[0] if isinstance(result, list) else result
    return parse_ads(raw or {}, task.get("data"))


# --- Fetching ---

def fetch_queued(api: dfs.Client, tracker: dfs.SpendTracker, tasks: list[dict], labels: list[str],
                 mode: str, depth: int, interval: float, timeout: float, sleep=time.sleep):
    ids, errors = dfs.post_queued(api, tracker, TASK_POST, tasks, labels,
                                  projected_cost(len(tasks), depth, mode), f"ads_search_{mode}")
    return collect(api, ids, interval, timeout, errors, sleep=sleep)


def collect(api: dfs.Client, ids: list[str], interval: float, timeout: float,
            errors: dict | None = None, sleep=time.sleep):
    done, failed, pending = dfs.poll_tasks(api, task_get, ids, interval=interval,
                                           timeout=timeout, sleep=sleep, empty_ok=True)
    errors = dict(errors or {})
    errors.update({f"task {tid}": msg for tid, msg in failed.items()})
    rows = [_parse_task(done[tid]) for tid in ids if tid in done]
    return rows, errors, pending


def fetch_live(api: dfs.Client, tracker: dfs.SpendTracker, tasks: list[dict], labels: list[str],
               depth: int):
    per_task = projected_cost(1, depth, "live")
    rows, errors = [], {}
    for task, label in zip(tasks, labels):
        t = dfs.post_live(api, tracker, LIVE, task, per_task, "ads_search_live")
        try:
            dfs.task_ok(t, accept=(dfs.OK, dfs.NO_RESULTS))
        except dfs.DataForSeoError as exc:
            errors[label] = str(exc)
            continue
        rows.append(_parse_task({**t, "data": t.get("data") or task}))
    return rows, errors, []


# --- Output ---

def _day(ts):
    return ts[:10] if ts else ""


def print_tables(rows: list[dict]) -> None:
    for r in rows:
        filters = [f"location {r['location_code'] or 'all'}", f"platform {r['platform']}",
                   f"format {r['ad_format']}"]
        if r["date_from"]:
            filters.append(f"{r['date_from']} to {r['date_to']}")
        print(f"=== {r['target']} ({' / '.join(filters)}) — {r['ads_returned']} ads ===")
        if not r["ads"]:
            print("No ads found in the Ads Transparency Center for these filters. If the advertiser's "
                  "ads are not tied to this domain, look up its advertiser IDs with "
                  "query_ads_advertisers.py.\n")
            continue
        print("Advertiser accounts: " + "; ".join(
            f"{a['name']} [{a['advertiser_id']}]{' verified' if a['verified'] else ''} — {a['ads']} ads"
            for a in r["advertisers"]))
        dfs.print_table(
            [{**a, "first_shown": _day(a["first_shown"]), "last_shown": _day(a["last_shown"])}
             for a in r["ads"]],
            ["rank", "format", "first_shown", "last_shown", "advertiser_name", "transparency_url"],
        )
        if r["may_have_more"]:
            print(f"Showing the first {r['ads_returned']} ads; raise --depth for more "
                  f"(billed per {PAGE_SIZE}).")
        print()


def csv_rows(rows: list[dict]):
    for r in rows:
        for a in r["ads"]:
            yield {"target": r["target"], **{k: a.get(k) for k in CSV_COLUMNS[1:]}}


def output(rows, errors, pending, fmt, cost):
    if fmt == "json":
        print(json.dumps({"data": rows, "errors": errors, "pending_task_ids": pending,
                          "cost": cost}, indent=2))
        return
    notes = []
    if errors:
        notes += [f"Error for {k}: {v}" for k, v in errors.items()]
    if pending:
        notes.append("Still queued (results not ready before timeout). Fetch later at no extra "
                     "cost with: --task-ids " + " ".join(pending))
    if fmt == "csv":
        writer = csv.DictWriter(sys.stdout, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(csv_rows(rows))
        for n in notes:
            print(n, file=sys.stderr)
        if cost:
            dfs.print_cost(cost, file=sys.stderr)
        return
    print_tables(rows)
    for n in notes:
        print(n)
    if cost:
        dfs.print_cost(cost)


def main():
    parser = argparse.ArgumentParser(
        description="Ads an advertiser runs on Google (Ads Transparency Center) via DataForSEO")
    parser.add_argument("targets", nargs="*",
                        help="Advertiser domains (example.com) and/or advertiser IDs (AR...)")
    parser.add_argument("--mode", default="standard", choices=["standard", "priority", "live"],
                        help="standard (default, cheapest, minutes), priority (~2x, <1 min), live (~3x, seconds)")
    parser.add_argument("--location-code", type=int, default=None,
                        help="DataForSEO location code (default: config or 2840 = United States)")
    parser.add_argument("--all-locations", action="store_true",
                        help="Search ads shown in any location (sends no location)")
    parser.add_argument("--platform", default="all", choices=PLATFORMS,
                        help="Where the ads ran (default: all)")
    parser.add_argument("--ad-format", default="all", choices=AD_FORMATS,
                        help="Ad format filter (default: all)")
    parser.add_argument("--date-from", default=None, help="Shown on/after YYYY-MM-DD (needs --date-to)")
    parser.add_argument("--date-to", default=None, help="Shown on/before YYYY-MM-DD (needs --date-from)")
    parser.add_argument("--depth", type=int, default=PAGE_SIZE,
                        help=f"Max ads per task (default {PAGE_SIZE}; up to 700 queued, 120 live). Billed per 40.")
    parser.add_argument("--poll-interval", type=float, default=10, help="Seconds between polls (queued modes)")
    parser.add_argument("--timeout", type=float, default=300, help="Max seconds to wait for queued tasks")
    parser.add_argument("--task-ids", nargs="+", default=None,
                        help="Collect results for previously posted task IDs instead of posting new ones (free)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show task bodies and projected cost without calling the API")
    parser.add_argument("--format", default="table", choices=["table", "csv", "json"],
                        help="Output format (default: table)")
    args = parser.parse_args()

    try:
        if args.task_ids:
            rows, errors, pending = collect(dfs.Client.from_env(), args.task_ids,
                                            args.poll_interval, args.timeout)
            output(rows, errors, pending, args.format, None)
            return

        if not 1 <= args.depth <= MAX_DEPTH[args.mode]:
            raise dfs.DataForSeoError(f"--depth must be between 1 and {MAX_DEPTH[args.mode]} in {args.mode} mode.")
        if args.all_locations and args.location_code:
            raise dfs.DataForSeoError("Use either --location-code or --all-locations, not both.")
        validate_dates(args.date_from, args.date_to)
        domains, ids = split_targets(args.targets)
        location = None if args.all_locations else (args.location_code or dfs.default_location_code())
        tasks, labels = build_tasks(domains, ids, location, args.platform, args.ad_format,
                                    args.date_from, args.date_to, args.depth, args.mode)
        tracker = dfs.SpendTracker()
        projected = projected_cost(len(tasks), args.depth, args.mode)

        if args.dry_run:
            print(json.dumps({
                "dry_run": True,
                "mode": args.mode,
                "endpoint": LIVE if args.mode == "live" else TASK_POST,
                "task_count": len(tasks),
                "billed_pages_per_task": dfs.serp_pages(args.depth, PAGE_SIZE),
                "projected_cost_usd": round(projected, 6),
                "today_total_usd": round(tracker.total, 6),
                "daily_cap_usd": tracker.cap,
                "within_cap": tracker.total + projected <= tracker.cap + 1e-9,
                "tasks": tasks,
            }, indent=2))
            return

        tracker.check(projected)
        before = tracker.total
        api = dfs.Client.from_env()
        if args.mode == "live":
            rows, errors, pending = fetch_live(api, tracker, tasks, labels, args.depth)
        else:
            rows, errors, pending = fetch_queued(api, tracker, tasks, labels, args.mode, args.depth,
                                                 args.poll_interval, args.timeout)
    except dfs.DataForSeoError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(2 if isinstance(exc, dfs.CapExceeded) else 1)

    output(rows, errors, pending, args.format, tracker.summary(tracker.total - before))


if __name__ == "__main__":
    main()
