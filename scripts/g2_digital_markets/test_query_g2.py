#!/usr/bin/env python3
"""Quick repro/test for the conversions_by_type aggregation bug.

Reproduces the crash where `aggregate()` assumed conversions_by_type was a dict
but the API returned it as a list of {type, count} objects, then verifies the
fix normalizes both shapes correctly.

Run:
    python scripts/g2_digital_markets/test_query_g2.py
"""

import importlib.util
import sys
from pathlib import Path

# Load query_g2.py directly (sibling module, hyphenated package path agnostic).
_spec = importlib.util.spec_from_file_location(
    "query_g2", str(Path(__file__).parent / "query_g2.py")
)
query_g2 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(query_g2)


def _records_list_shape():
    """conversions_by_type as a list of {type, count} — the shape that crashed."""
    return [
        {"date_of_report": "2026-05-03", "clicks": "10", "conversions": "4", "cost": "20.0",
         "conversions_by_type": [{"type": "bookDemo", "count": 3}, {"type": "freeTrial", "count": 1}]},
        {"date_of_report": "2026-05-20", "clicks": "5", "conversions": "2", "cost": "10.0",
         "conversions_by_type": [{"type": "bookDemo", "count": 1}, {"type": "other", "count": 1}]},
        {"date_of_report": "2026-06-01", "clicks": "8", "conversions": "1", "cost": "16.0",
         "conversions_by_type": [{"type": "freeTrial", "count": 1}]},
    ]


def _records_dict_shape():
    """conversions_by_type as a dict — the shape the code originally assumed."""
    return [
        {"date_of_report": "2026-05-03", "clicks": "10", "conversions": "4", "cost": "20.0",
         "conversions_by_type": {"bookDemo": 3, "freeTrial": 1}},
        {"date_of_report": "2026-05-20", "clicks": "5", "conversions": "2", "cost": "10.0",
         "conversions_by_type": {"bookDemo": 1, "other": 1}},
    ]


def test_list_shape_does_not_crash_and_aggregates():
    rows = query_g2.aggregate(_records_list_shape(), ["month"])
    by_month = {r["month"]: r for r in rows}

    assert set(by_month) == {"2026-05", "2026-06"}, by_month
    # May groups the two May records together.
    assert by_month["2026-05"]["conversions_by_type"] == {"bookDemo": 4, "freeTrial": 1, "other": 1}, \
        by_month["2026-05"]["conversions_by_type"]
    assert by_month["2026-06"]["conversions_by_type"] == {"freeTrial": 1}, \
        by_month["2026-06"]["conversions_by_type"]
    print("PASS: list shape aggregates without crashing")


def test_dict_shape_still_works():
    rows = query_g2.aggregate(_records_dict_shape(), ["month"])
    by_month = {r["month"]: r for r in rows}
    assert by_month["2026-05"]["conversions_by_type"] == {"bookDemo": 4, "freeTrial": 1, "other": 1}, \
        by_month["2026-05"]["conversions_by_type"]
    print("PASS: dict shape still works")


def test_normalize_edge_cases():
    n = query_g2._normalize_conversions_by_type
    assert n(None) == []
    assert n([]) == []
    assert n({}) == []
    assert n({"bookDemo": 2}) == [("bookDemo", 2)]
    assert n([{"type": "bookDemo", "count": 2}]) == [("bookDemo", 2)]
    assert n([{"no_type": 1}]) == []          # missing type → skipped
    assert n(["garbage"]) == []               # non-dict items → skipped
    print("PASS: _normalize_conversions_by_type edge cases")


if __name__ == "__main__":
    test_list_shape_does_not_crash_and_aggregates()
    test_dict_shape_still_works()
    test_normalize_edge_cases()
    print("All tests passed.")
    sys.exit(0)
