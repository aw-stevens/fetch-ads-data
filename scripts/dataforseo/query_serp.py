#!/usr/bin/env python3
"""
Google organic SERP results via DataForSEO (SERP API, advanced result type).

For each query returns the paid ads (who is advertising, ad copy, top/bottom placement),
organic results, People Also Ask questions, related searches, and other SERP features.

Modes:
    standard  Standard Queue: task_post, then poll task_get (cheapest; minutes)
    priority  Standard Queue with high priority (about 2x price; usually under a minute)
    live      Live endpoint, one call per query (most expensive; seconds)

Usage:
    python query_serp.py "crm software" "email marketing tool"
    python query_serp.py "crm software" --mode live --device mobile --format json
    python query_serp.py --file queries.txt --dry-run

    # Collect results for tasks that were posted earlier but timed out (free)
    python query_serp.py --task-ids 01234567-89ab-cdef-0123-456789abcdef

Billing: per query per page of 10 results (depth rounds up to the next ten). Retrieving
queued results is free. Every call is checked against the daily spend cap first.

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

TASK_POST = "/v3/serp/google/organic/task_post"
LIVE = "/v3/serp/google/organic/live/advanced"
MAX_QUERIES = 100  # task_post accepts up to 100 tasks per request
RATES = {"standard": "serp_standard_per_page", "priority": "serp_priority_per_page",
         "live": "serp_live_per_page"}

CSV_COLUMNS = ["query", "section", "position", "rank_absolute", "placement",
               "domain", "title", "url", "description"]


def task_get(task_id: str) -> str:
    return f"/v3/serp/google/organic/task_get/advanced/{task_id}"


def clean_queries(raw: list[str]) -> list[str]:
    seen = set()
    out = []
    for q in raw:
        q = " ".join(q.split())
        if q and q.lower() not in seen:
            seen.add(q.lower())
            out.append(q)
    if not out:
        raise dfs.DataForSeoError("No queries provided.")
    if len(out) > MAX_QUERIES:
        raise dfs.DataForSeoError(f"Too many queries ({len(out)}); max {MAX_QUERIES} per run.")
    return out


def build_tasks(queries: list[str], location_code: int, language_code: str,
                device: str, depth: int, mode: str) -> list[dict]:
    tasks = []
    for q in queries:
        task = {"keyword": q, "location_code": location_code, "language_code": language_code,
                "device": device, "depth": depth}
        if mode == "priority":
            task["priority"] = 2
        tasks.append(task)
    return tasks


def projected_cost(n_queries: int, depth: int, mode: str) -> float:
    return n_queries * dfs.serp_pages(depth) * dfs.rate(RATES[mode])


# --- Parsing ---

def _str(v):
    return v if isinstance(v, str) else None


def _int(v):
    return v if isinstance(v, int) and not isinstance(v, bool) else None


def parse_serp(raw: dict, params: dict | None = None) -> dict:
    """Flatten one advanced SERP result into paid / organic / PAA / related / features.
    `params` is the task's echoed request (task["data"]), used for fields the result omits."""
    params = params or {}
    items = [i for i in (raw.get("items") or []) if isinstance(i, dict)]

    # Paid placement is not a field in the response: an ad ranked above the first organic
    # result on its page is "top", anything after it is "bottom".
    first_organic: dict = {}
    for item in items:
        if item.get("type") == "organic" and _int(item.get("rank_absolute")) is not None:
            page = item.get("page") or 1
            first_organic[page] = min(first_organic.get(page, item["rank_absolute"]), item["rank_absolute"])

    paid, organic, paa, related, features = [], [], [], [], []
    for item in items:
        kind = item.get("type") or ""
        rank_abs = _int(item.get("rank_absolute"))
        if kind == "paid":
            page = item.get("page") or 1
            if page not in first_organic or rank_abs is None:
                placement = "unknown"
            else:
                placement = "top" if rank_abs < first_organic[page] else "bottom"
            paid.append({
                "position": _int(item.get("rank_group")),
                "rank_absolute": rank_abs,
                "placement": placement,
                "page": page,
                "domain": _str(item.get("domain")),
                "title": _str(item.get("title")),
                "description": _str(item.get("description")),
                "url": _str(item.get("url")),
                "breadcrumb": _str(item.get("breadcrumb")),
                "sitelinks": len(item.get("links") or []),
            })
        elif kind == "organic":
            organic.append({
                "position": _int(item.get("rank_group")),
                "rank_absolute": rank_abs,
                "domain": _str(item.get("domain")),
                "title": _str(item.get("title")),
                "url": _str(item.get("url")),
                "description": _str(item.get("description")),
            })
        elif kind == "people_also_ask":
            for q in item.get("items") or []:
                if isinstance(q, dict) and _str(q.get("title")):
                    paa.append(q["title"])
            features.append({"type": kind, "rank_absolute": rank_abs})
        elif kind == "related_searches":
            for q in item.get("items") or []:
                text = q if isinstance(q, str) else (q.get("title") if isinstance(q, dict) else None)
                if _str(text):
                    related.append(text)
            features.append({"type": kind, "rank_absolute": rank_abs})
        else:
            feature = {"type": kind, "rank_absolute": rank_abs}
            for key in ("title", "domain", "url"):
                if _str(item.get(key)):
                    feature[key] = item[key]
            features.append(feature)

    return {
        "query": raw.get("keyword") or params.get("keyword"),
        "location_code": raw.get("location_code") or params.get("location_code"),
        "language_code": raw.get("language_code") or params.get("language_code"),
        "device": params.get("device") or "desktop",
        "total_results": _int(raw.get("se_results_count")),
        "item_types": raw.get("item_types") or [],
        "paid": paid,
        "organic": organic,
        "people_also_ask": paa,
        "related_searches": related,
        "serp_features": features,
    }


def _parse_task(task: dict) -> dict:
    result = task.get("result") or [{}]
    raw = result[0] if isinstance(result, list) else result
    return parse_serp(raw or {}, task.get("data"))


# --- Fetching ---

def fetch_queued(api: dfs.Client, tracker: dfs.SpendTracker, tasks: list[dict], mode: str,
                 depth: int, interval: float, timeout: float, sleep=time.sleep):
    projected = projected_cost(len(tasks), depth, mode)
    tracker.check(projected)
    payload = api.post(TASK_POST, tasks)
    tracker.record(f"serp_{mode}", len(tasks), dfs.response_cost(payload, projected))

    posted = payload.get("tasks") or []
    ids, errors = [], {}
    for i, task in enumerate(tasks):
        t = posted[i] if i < len(posted) else {}
        if t.get("status_code") == dfs.TASK_CREATED and t.get("id"):
            ids.append(t["id"])
        else:
            errors[task["keyword"]] = f"{t.get('status_message', 'task not created')} (status_code={t.get('status_code')})"
    return collect(api, ids, interval, timeout, errors, sleep=sleep)


def collect(api: dfs.Client, ids: list[str], interval: float, timeout: float,
            errors: dict | None = None, sleep=time.sleep):
    done, failed, pending = dfs.poll_tasks(api, task_get, ids, interval=interval,
                                           timeout=timeout, sleep=sleep)
    errors = dict(errors or {})
    errors.update({f"task {tid}": msg for tid, msg in failed.items()})
    rows = [_parse_task(done[tid]) for tid in ids if tid in done]
    return rows, errors, pending


def fetch_live(api: dfs.Client, tracker: dfs.SpendTracker, tasks: list[dict], depth: int):
    per_query = projected_cost(1, depth, "live")
    rows, errors = [], {}
    for task in tasks:
        tracker.check(per_query)
        payload = api.post(LIVE, [task])
        tracker.record("serp_live", 1, dfs.response_cost(payload, per_query))
        t = (payload.get("tasks") or [{}])[0]
        try:
            dfs.task_ok(t)
        except dfs.DataForSeoError as exc:
            errors[task["keyword"]] = str(exc)
            continue
        rows.append(_parse_task(t))
    return rows, errors, []


# --- Output ---

def _short(text, n=90):
    if not text:
        return ""
    return text if len(text) <= n else text[: n - 1] + "…"


def print_tables(rows: list[dict]) -> None:
    for r in rows:
        total = f"{r['total_results']:,} results" if r["total_results"] is not None else "results"
        print(f"=== {r['query']} (location {r['location_code']} / {r['language_code']} / "
              f"{r['device']}) — {total} ===")
        print(f"Item types: {', '.join(r['item_types']) or 'none'}")

        print(f"\nPaid ads ({len(r['paid'])})")
        if r["paid"]:
            dfs.print_table(
                [{**p, "title": _short(p["title"], 60), "description": _short(p["description"])}
                 for p in r["paid"]],
                ["position", "placement", "domain", "title", "description"],
            )
        else:
            print("No ads shown for this query.")

        print(f"\nOrganic ({len(r['organic'])})")
        dfs.print_table([{**o, "title": _short(o["title"], 70)} for o in r["organic"]],
                        ["position", "domain", "title", "url"])

        if r["people_also_ask"]:
            print("\nPeople also ask:")
            for q in r["people_also_ask"]:
                print(f"  - {q}")
        if r["related_searches"]:
            print("\nRelated searches: " + "; ".join(r["related_searches"]))
        others = [f for f in r["serp_features"] if f["type"] not in ("people_also_ask", "related_searches")]
        if others:
            print("\nOther SERP features: " + ", ".join(
                f"{f['type']}@{f['rank_absolute']}" + (f" ({f['domain']})" if f.get("domain") else "")
                for f in others))
        print()


def csv_rows(rows: list[dict]):
    for r in rows:
        q = r["query"]
        for p in r["paid"]:
            yield {"query": q, "section": "paid", **{k: p.get(k) for k in CSV_COLUMNS[2:]}}
        for o in r["organic"]:
            yield {"query": q, "section": "organic", **{k: o.get(k) for k in CSV_COLUMNS[2:]}}
        for t in r["people_also_ask"]:
            yield {"query": q, "section": "people_also_ask", "title": t}
        for t in r["related_searches"]:
            yield {"query": q, "section": "related_search", "title": t}
        for f in r["serp_features"]:
            if f["type"] not in ("people_also_ask", "related_searches"):
                yield {"query": q, "section": f["type"], "rank_absolute": f["rank_absolute"],
                       "domain": f.get("domain"), "title": f.get("title"), "url": f.get("url")}


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
    parser = argparse.ArgumentParser(description="Google organic SERP (ads, organic, PAA, features) via DataForSEO")
    parser.add_argument("queries", nargs="*", help="Search queries")
    parser.add_argument("--file", help="Read additional queries from a file, one per line")
    parser.add_argument("--mode", default="standard", choices=["standard", "priority", "live"],
                        help="standard (default, cheapest, minutes), priority (~2x, <1 min), live (~3x, seconds)")
    parser.add_argument("--location-code", type=int, default=None,
                        help="DataForSEO location code (default: config or 2840 = United States)")
    parser.add_argument("--language-code", default=None, help="Language code (default: config or 'en')")
    parser.add_argument("--device", default="desktop", choices=["desktop", "mobile"],
                        help="Device to emulate (default: desktop)")
    parser.add_argument("--depth", type=int, default=10,
                        help="Results to fetch, 10-100 (default: 10). Billed per 10.")
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

        if not 10 <= args.depth <= 100:
            raise dfs.DataForSeoError("--depth must be between 10 and 100.")
        raw = list(args.queries)
        if args.file:
            raw += Path(args.file).expanduser().read_text().splitlines()
        queries = clean_queries(raw)
        location = args.location_code or dfs.default_location_code()
        language = args.language_code or dfs.default_language_code()
        tasks = build_tasks(queries, location, language, args.device, args.depth, args.mode)
        tracker = dfs.SpendTracker()
        projected = projected_cost(len(queries), args.depth, args.mode)

        if args.dry_run:
            print(json.dumps({
                "dry_run": True,
                "mode": args.mode,
                "endpoint": LIVE if args.mode == "live" else TASK_POST,
                "query_count": len(queries),
                "billed_pages_per_query": dfs.serp_pages(args.depth),
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
            rows, errors, pending = fetch_live(api, tracker, tasks, args.depth)
        else:
            rows, errors, pending = fetch_queued(api, tracker, tasks, args.mode, args.depth,
                                                 args.poll_interval, args.timeout)
    except dfs.DataForSeoError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(2 if isinstance(exc, dfs.CapExceeded) else 1)

    output(rows, errors, pending, args.format, tracker.summary(tracker.total - before))


if __name__ == "__main__":
    main()
