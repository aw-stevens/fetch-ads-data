#!/usr/bin/env python3
"""
Find Google Ads advertiser accounts by name or keyword, via DataForSEO's Google Ads
Advertisers API (Google Ads Transparency Center data).

Returns matching advertisers (single accounts, and brands that run several accounts) with
their advertiser IDs, location, verification status, and approximate ad count, plus any
matching advertiser domains. Feed the IDs or domains to query_ads_search.py.

Modes:
    standard  Standard Queue: task_post, then poll task_get (cheapest; minutes)
    priority  Standard Queue with high priority (about 2x price; usually under a minute)
    live      Live endpoint, one call per keyword (most expensive; seconds)

Usage:
    python query_ads_advertisers.py "example brand"
    python query_ads_advertisers.py "example brand" "example software" --mode live --format json
    python query_ads_advertisers.py "example brand" --all-locations --dry-run

    # Collect results for tasks that were posted earlier but timed out (free)
    python query_ads_advertisers.py --task-ids 01234567-89ab-cdef-0123-456789abcdef

Billing: per keyword (one task returns every match). Retrieving queued results is free.
Every call is checked against the daily spend cap first.

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

TASK_POST = "/v3/serp/google/ads_advertisers/task_post"
LIVE = "/v3/serp/google/ads_advertisers/live/advanced"
MAX_KEYWORDS = 100  # task_post accepts up to 100 tasks per request
MAX_KEYWORD_CHARS = 700
RATES = {"standard": "ads_advertisers_standard_per_task",
         "priority": "ads_advertisers_priority_per_task",
         "live": "ads_advertisers_live_per_task"}

CSV_COLUMNS = ["keyword", "rank", "kind", "name", "advertiser_id", "location", "verified",
               "approx_ads_count", "domain"]


def task_get(task_id: str) -> str:
    return f"/v3/serp/google/ads_advertisers/task_get/advanced/{task_id}"


def clean_keywords(raw: list[str]) -> list[str]:
    seen = set()
    out = []
    for kw in raw:
        kw = " ".join(kw.split())
        if not kw or kw.lower() in seen:
            continue
        if len(kw) > MAX_KEYWORD_CHARS:
            raise dfs.DataForSeoError(f"Keyword exceeds {MAX_KEYWORD_CHARS} characters: {kw[:40]!r}...")
        seen.add(kw.lower())
        out.append(kw)
    if not out:
        raise dfs.DataForSeoError("No keywords provided.")
    if len(out) > MAX_KEYWORDS:
        raise dfs.DataForSeoError(f"Too many keywords ({len(out)}); max {MAX_KEYWORDS} per run.")
    return out


def build_tasks(keywords: list[str], location_code: int | None, mode: str) -> list[dict]:
    tasks = []
    for kw in keywords:
        task = {"keyword": kw}
        if location_code:
            task["location_code"] = location_code
        if mode == "priority":
            task["priority"] = 2
        tasks.append(task)
    return tasks


def projected_cost(n_keywords: int, mode: str) -> float:
    return n_keywords * dfs.rate(RATES[mode])


# --- Parsing ---

def _str(v):
    return v if isinstance(v, str) else None


def _int(v):
    return v if isinstance(v, int) and not isinstance(v, bool) else None


def _bool(v):
    return v if isinstance(v, bool) else None


def _all_or_none(flags: list) -> bool | None:
    """True if every flag is True, False if every flag is False, None if mixed or empty."""
    return flags[0] if flags and all(f is flags[0] for f in flags) and flags[0] is not None else None


def _account(item: dict) -> dict:
    return {
        "advertiser_id": _str(item.get("advertiser_id")),
        "location": _str(item.get("location")),
        "verified": _bool(item.get("verified")),
        "approx_ads_count": _int(item.get("approx_ads_count")),
    }


def parse_advertisers(raw: dict, params: dict | None = None) -> dict:
    """Flatten one ads_advertisers result. Single accounts and multi-account brands share
    one shape: `accounts` lists every advertiser account, `advertiser_ids` their IDs."""
    params = params or {}
    advertisers, domains = [], []
    for item in raw.get("items") or []:
        if not isinstance(item, dict):
            continue
        kind = item.get("type")
        if kind == "ads_domain":
            if _str(item.get("domain")):
                domains.append(item["domain"])
            continue
        if kind == "ads_multi_account_advertiser":
            accounts = [_account(a) for a in item.get("advertisers") or [] if isinstance(a, dict)]
            label = "multi_account"
        elif kind == "ads_advertiser":
            accounts = [_account(item)]
            label = "advertiser"
        else:
            continue
        advertisers.append({
            "rank": _int(item.get("rank_group")),
            "kind": label,
            "name": _str(item.get("title")),
            "location": _str(item.get("location")),
            "verified": _bool(item.get("verified")) if label == "advertiser" else _all_or_none(
                [a["verified"] for a in accounts]),
            "approx_ads_count": _int(item.get("approx_ads_count")),
            "advertiser_ids": [a["advertiser_id"] for a in accounts if a["advertiser_id"]],
            "accounts": accounts,
        })
    return {
        "keyword": params.get("keyword") or raw.get("keyword"),
        "location_code": params.get("location_code") if params else raw.get("location_code"),
        "fetched_at": raw.get("datetime"),
        "advertisers": advertisers,
        "domains": domains,
    }


def _parse_task(task: dict) -> dict:
    result = task.get("result") or [{}]
    raw = result[0] if isinstance(result, list) else result
    return parse_advertisers(raw or {}, task.get("data"))


# --- Fetching ---

def fetch_queued(api: dfs.Client, tracker: dfs.SpendTracker, tasks: list[dict], mode: str,
                 interval: float, timeout: float, sleep=time.sleep):
    ids, errors = dfs.post_queued(api, tracker, TASK_POST, tasks, [t["keyword"] for t in tasks],
                                  projected_cost(len(tasks), mode), f"ads_advertisers_{mode}")
    return collect(api, ids, interval, timeout, errors, sleep=sleep)


def collect(api: dfs.Client, ids: list[str], interval: float, timeout: float,
            errors: dict | None = None, sleep=time.sleep):
    done, failed, pending = dfs.poll_tasks(api, task_get, ids, interval=interval,
                                           timeout=timeout, sleep=sleep, empty_ok=True)
    errors = dict(errors or {})
    errors.update({f"task {tid}": msg for tid, msg in failed.items()})
    rows = [_parse_task(done[tid]) for tid in ids if tid in done]
    return rows, errors, pending


def fetch_live(api: dfs.Client, tracker: dfs.SpendTracker, tasks: list[dict]):
    per_task = projected_cost(1, "live")
    rows, errors = [], {}
    for task in tasks:
        t = dfs.post_live(api, tracker, LIVE, task, per_task, "ads_advertisers_live")
        try:
            dfs.task_ok(t, accept=(dfs.OK, dfs.NO_RESULTS))
        except dfs.DataForSeoError as exc:
            errors[task["keyword"]] = str(exc)
            continue
        rows.append(_parse_task({**t, "data": t.get("data") or task}))
    return rows, errors, []


# --- Output ---

def _verified(v):
    return {True: "yes", False: "no"}.get(v, "mixed")


def print_tables(rows: list[dict]) -> None:
    for r in rows:
        print(f"=== {r['keyword']} (location {r['location_code'] or 'all'}) — "
              f"{len(r['advertisers'])} advertisers ===")
        if r["advertisers"]:
            dfs.print_table(
                [{**a, "accounts": len(a["accounts"]), "verified": _verified(a["verified"]),
                  "advertiser_ids": " ".join(a["advertiser_ids"])} for a in r["advertisers"]],
                ["rank", "name", "location", "verified", "approx_ads_count", "accounts", "advertiser_ids"],
            )
        else:
            print("No matching advertisers.")
        if r["domains"]:
            print("\nAdvertiser domains: " + ", ".join(r["domains"]))
        print()


def csv_rows(rows: list[dict]):
    for r in rows:
        kw = r["keyword"]
        for a in r["advertisers"]:
            for acct in a["accounts"]:
                yield {"keyword": kw, "rank": a["rank"], "kind": a["kind"], "name": a["name"], **acct}
        for d in r["domains"]:
            yield {"keyword": kw, "kind": "domain", "domain": d}


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
        description="Find Google Ads advertiser IDs by name or keyword (Ads Transparency Center) via DataForSEO")
    parser.add_argument("keywords", nargs="*", help="Advertiser names or keywords")
    parser.add_argument("--file", help="Read additional keywords from a file, one per line")
    parser.add_argument("--mode", default="standard", choices=["standard", "priority", "live"],
                        help="standard (default, cheapest, minutes), priority (~2x, <1 min), live (~3x, seconds)")
    parser.add_argument("--location-code", type=int, default=None,
                        help="DataForSEO location code (default: config or 2840 = United States)")
    parser.add_argument("--all-locations", action="store_true",
                        help="Search advertisers in any location (sends no location)")
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

        if args.all_locations and args.location_code:
            raise dfs.DataForSeoError("Use either --location-code or --all-locations, not both.")
        raw = list(args.keywords)
        if args.file:
            raw += Path(args.file).expanduser().read_text().splitlines()
        keywords = clean_keywords(raw)
        location = None if args.all_locations else (args.location_code or dfs.default_location_code())
        tasks = build_tasks(keywords, location, args.mode)
        tracker = dfs.SpendTracker()
        projected = projected_cost(len(tasks), args.mode)

        if args.dry_run:
            print(json.dumps({
                "dry_run": True,
                "mode": args.mode,
                "endpoint": LIVE if args.mode == "live" else TASK_POST,
                "keyword_count": len(keywords),
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
            rows, errors, pending = fetch_live(api, tracker, tasks)
        else:
            rows, errors, pending = fetch_queued(api, tracker, tasks, args.mode,
                                                 args.poll_interval, args.timeout)
    except dfs.DataForSeoError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(2 if isinstance(exc, dfs.CapExceeded) else 1)

    output(rows, errors, pending, args.format, tracker.summary(tracker.total - before))


if __name__ == "__main__":
    main()
