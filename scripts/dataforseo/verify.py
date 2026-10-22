#!/usr/bin/env python3
"""
Verify DataForSEO credentials and show the account balance alongside today's local spend
against the daily cap. Uses the free /v3/appendix/user_data endpoint (no charge).

Usage:
    python verify.py
    python verify.py --format json
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import client as dfs

ENDPOINT = "/v3/appendix/user_data"


def summarize(payload: dict, tracker: dfs.SpendTracker) -> dict:
    task = (payload.get("tasks") or [{}])[0]
    dfs.task_ok(task)
    result = task.get("result") or [{}]
    user = result[0] if isinstance(result, list) and result else {}
    money = user.get("money") or {}
    return {
        "login": user.get("login"),
        "balance_usd": money.get("balance"),
        "today_local_spend_usd": round(tracker.total, 6),
        "daily_cap_usd": tracker.cap,
        "calls_today": len(tracker.tally["calls"]),
        "tally_file": str(tracker.path),
    }


def main():
    parser = argparse.ArgumentParser(description="Verify DataForSEO credentials and show spend")
    parser.add_argument("--format", default="table", choices=["table", "json"],
                        help="Output format (default: table)")
    args = parser.parse_args()

    try:
        tracker = dfs.SpendTracker()
        info = summarize(dfs.Client.from_env().get(ENDPOINT), tracker)
    except dfs.DataForSeoError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    if args.format == "json":
        print(json.dumps(info, indent=2))
        return
    balance = info["balance_usd"]
    print(f"OK — DataForSEO credentials work (login: {info['login']}).")
    if isinstance(balance, (int, float)):
        print(f"Account balance: ${balance:.2f}")
    print(f"Today's spend via this plugin: ${info['today_local_spend_usd']:.4f} of "
          f"${info['daily_cap_usd']:.2f} daily cap ({info['calls_today']} billed call(s), UTC day).")


if __name__ == "__main__":
    main()
