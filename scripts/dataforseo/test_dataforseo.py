#!/usr/bin/env python3
"""Offline tests for the DataForSEO scripts (no network, no credentials, no spend).

Covers credential loading (env vars vs file), keyword cleaning and chunking, volume row
flattening, SERP parsing (paid ads with top/bottom placement, organic, PAA, related
searches, features), Ads Transparency ads search and advertiser lookup, Standard Queue
polling, live mode, the daily spend cap, and API error handling. HTTP is mocked at requests.get / requests.post.

Run:
    python scripts/dataforseo/test_dataforseo.py
"""

import contextlib
import io
import json
import os
import sys
import tempfile
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).parent))
import client as dfs
import query_ads_advertisers
import query_ads_search
import query_serp
import query_volume
import verify


class FakeResp:
    def __init__(self, status=200, body=None, text=None):
        self.status_code = status
        self._body = body
        self.text = text if text is not None else json.dumps(body)

    def json(self):
        if self._body is None:
            raise ValueError("no json")
        return self._body


def ok(tasks, cost=None):
    body = {"status_code": 20000, "status_message": "Ok.", "tasks": tasks}
    if cost is not None:
        body["cost"] = cost
    return FakeResp(body=body)


def _api():
    return dfs.Client("login", "pw", base_url="https://api.test")


def _tracker(tmp, cap=1.0):
    return dfs.SpendTracker(directory=Path(tmp), cap=cap, day="2026-01-01")


# Patch config lookups so tests never read the developer's real ~/.fetch-ads-data.
_NO_CONFIG = mock.patch.object(dfs, "service_config", return_value={})


# --- Credentials ---

def test_credentials_env_wins_and_file_fallback():
    with _NO_CONFIG, mock.patch.dict(os.environ, {"DATAFORSEO_LOGIN": "a", "DATAFORSEO_PASSWORD": "b"}):
        assert dfs.load_credentials() == ("a", "b")
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "dataforseo.json"
        path.write_text(json.dumps({"login": "c", "password": "d"}))
        env = {k: v for k, v in os.environ.items() if not k.startswith("DATAFORSEO_")}
        with mock.patch.dict(os.environ, env, clear=True), \
                mock.patch.object(dfs.config, "CONFIG_FILE", Path(tmp) / "config.json"), \
                mock.patch.object(dfs.config, "credentials_path", return_value=str(path)):
            (Path(tmp) / "config.json").write_text("{}")
            assert dfs.load_credentials() == ("c", "d")
            path.write_text(json.dumps({"login": "c"}))
            try:
                dfs.load_credentials()
            except dfs.DataForSeoError as exc:
                assert "DATAFORSEO_LOGIN" in str(exc)
            else:
                raise AssertionError("expected DataForSeoError")


def test_credentials_default_path_without_config_section():
    # Configs created before this service existed have no dataforseo.credentials entry.
    with tempfile.TemporaryDirectory() as tmp:
        default = Path(tmp) / "dataforseo.json"
        default.write_text(json.dumps({"login": "e", "password": "f"}))
        (Path(tmp) / "config.json").write_text(json.dumps({"google_ads": {}}))
        env = {k: v for k, v in os.environ.items() if not k.startswith("DATAFORSEO_")}
        with mock.patch.dict(os.environ, env, clear=True), \
                mock.patch.object(dfs.config, "CONFIG_FILE", Path(tmp) / "config.json"), \
                mock.patch.object(dfs, "DEFAULT_CREDS", default):
            assert dfs.load_credentials() == ("e", "f")


def test_auth_header():
    assert dfs.auth_header("user", "pass") == "Basic dXNlcjpwYXNz"
    assert _api().headers["Authorization"] == "Basic bG9naW46cHc="


# --- Spend cap ---

def test_cap_blocks_and_records():
    with tempfile.TemporaryDirectory() as tmp:
        t = _tracker(tmp, cap=0.10)
        t.check(0.09)
        t.record("keyword_volume", 5, 0.09)
        try:
            t.check(0.09)
        except dfs.CapExceeded as exc:
            assert "cap $0.10" in str(exc)
        else:
            raise AssertionError("expected CapExceeded")
        reloaded = _tracker(tmp, cap=0.10)
        assert reloaded.total == 0.09 and len(reloaded.tally["calls"]) == 1
        assert reloaded.summary(0.09)["remaining_usd"] == 0.01


def test_cap_from_env_and_validation():
    with _NO_CONFIG, mock.patch.dict(os.environ, {"DATAFORSEO_DAILY_CAP_USD": "2.5"}):
        assert dfs.cap_usd() == 2.5
    with _NO_CONFIG, mock.patch.dict(os.environ, {"DATAFORSEO_DAILY_CAP_USD": "-1"}):
        try:
            dfs.cap_usd()
        except dfs.DataForSeoError:
            pass
        else:
            raise AssertionError("expected DataForSeoError")
    env = {k: v for k, v in os.environ.items() if k != "DATAFORSEO_DAILY_CAP_USD"}
    with mock.patch.dict(os.environ, env, clear=True), \
            mock.patch.object(dfs, "service_config", return_value={"daily_cap_usd": 3}):
        assert dfs.cap_usd() == 3.0


# --- Keyword volume ---

def test_clean_keywords_and_chunking():
    kws = query_volume.clean_keywords(["  CRM  software ", "crm software", "", "email tool"])
    assert kws == ["CRM software", "email tool"]
    try:
        query_volume.clean_keywords(["x " * 11])
    except dfs.DataForSeoError:
        pass
    else:
        raise AssertionError("expected DataForSeoError for an 11-word keyword")
    bodies = query_volume.build_requests([f"kw {i}" for i in range(1500)], 2826, "en")
    assert [len(b[0]["keywords"]) for b in bodies] == [700, 700, 100]
    assert all(len(b) == 1 for b in bodies)  # live endpoints take one task per call
    assert bodies[0][0]["location_code"] == 2826 and bodies[0][0]["language_code"] == "en"


def test_volume_fetch_flattens_and_records_actual_cost():
    raw = {
        "keyword": "crm software", "search_volume": 1000, "cpc": 12.5, "competition": "HIGH",
        "competition_index": 90, "low_top_of_page_bid": 4.1, "high_top_of_page_bid": 20.0,
        "monthly_searches": [
            {"year": 2025, "month": 12, "search_volume": 900},
            {"year": 2025, "month": 11, "search_volume": 1100},
        ],
    }
    empty = {"keyword": "tiny niche phrase", "search_volume": None, "cpc": None,
             "competition": None, "competition_index": None, "monthly_searches": None}
    bodies = query_volume.build_requests(["crm software", "tiny niche phrase"], 2840, "en")
    resp = ok([{"status_code": 20000, "result": [raw, empty]}], cost=0.09)
    with tempfile.TemporaryDirectory() as tmp, _NO_CONFIG, \
            mock.patch.object(dfs.requests, "post", return_value=resp) as post:
        tracker = _tracker(tmp)
        rows = query_volume.fetch_volume(_api(), tracker, bodies, sleep=lambda s: None)
        assert tracker.total == 0.09
    assert post.call_args.args[0] == "https://api.test" + query_volume.ENDPOINT
    assert json.loads(post.call_args.kwargs["data"]) == bodies[0]
    assert rows[0]["search_volume"] == 1000 and rows[0]["competition"] == "HIGH"
    assert [m["month"] for m in rows[0]["monthly_searches"]] == [11, 12]  # oldest first
    assert query_volume._trend_text(rows[0]["monthly_searches"]) == "2025-11:1100 2025-12:900"
    assert rows[1]["search_volume"] is None and rows[1]["monthly_searches"] is None


def test_volume_cap_checked_per_chunk():
    bodies = query_volume.build_requests([f"kw {i}" for i in range(1400)], 2840, "en")
    resp = ok([{"status_code": 20000, "result": []}], cost=0.09)
    with tempfile.TemporaryDirectory() as tmp, _NO_CONFIG, \
            mock.patch.object(dfs.requests, "post", return_value=resp) as post:
        tracker = _tracker(tmp, cap=0.10)
        try:
            query_volume.fetch_volume(_api(), tracker, bodies, sleep=lambda s: None)
        except dfs.CapExceeded:
            pass
        else:
            raise AssertionError("expected CapExceeded on the second chunk")
        assert post.call_count == 1 and tracker.total == 0.09


def test_volume_no_results_is_empty_not_error():
    resp = ok([{"status_code": 40102, "status_message": "No Search Results.", "result": None}], cost=0.09)
    with tempfile.TemporaryDirectory() as tmp, _NO_CONFIG, \
            mock.patch.object(dfs.requests, "post", return_value=resp):
        rows = query_volume.fetch_volume(_api(), _tracker(tmp),
                                         query_volume.build_requests(["zzz"], 2840, "en"))
    assert rows == []


# --- HTTP / API errors ---

def test_http_and_api_errors():
    cases = [
        (FakeResp(401, text="unauthorized"), "credentials rejected"),
        (FakeResp(500, text="boom"), "HTTP 500"),
        (FakeResp(200, text="<html>"), "Non-JSON"),
        (FakeResp(body={"status_code": 40200, "status_message": "Payment required."}), "Payment required"),
    ]
    for resp, needle in cases:
        with mock.patch.object(dfs.requests, "get", return_value=resp):
            try:
                _api().get("/v3/x")
            except dfs.DataForSeoError as exc:
                assert needle in str(exc), (needle, str(exc))
            else:
                raise AssertionError(f"expected DataForSeoError for {needle}")


# --- SERP parsing ---

SERP_RESULT = {
    "keyword": "crm software", "location_code": 2840, "language_code": "en",
    "se_results_count": 123000,
    "item_types": ["paid", "organic", "people_also_ask", "organic", "paid", "related_searches"],
    "items": [
        {"type": "paid", "rank_group": 1, "rank_absolute": 1, "page": 1, "domain": "ads-one.example",
         "title": "Ad One", "description": "Try it free", "url": "https://ads-one.example/x",
         "breadcrumb": "ads-one.example", "links": [{"title": "Pricing"}, {"title": "Demo"}]},
        {"type": "paid", "rank_group": 2, "rank_absolute": 2, "page": 1, "domain": "ads-two.example",
         "title": "Ad Two", "description": "Compare plans", "url": "https://ads-two.example/"},
        {"type": "organic", "rank_group": 1, "rank_absolute": 3, "page": 1, "domain": "example.com",
         "title": "Best CRM", "url": "https://example.com/crm", "description": "A guide"},
        {"type": "people_also_ask", "rank_absolute": 4, "items": [
            {"type": "people_also_ask_element", "title": "What is a CRM?"},
            {"type": "people_also_ask_element", "title": "Is there a free CRM?"}]},
        {"type": "featured_snippet", "rank_absolute": 5, "domain": "example.org", "title": "Snippet"},
        {"type": "organic", "rank_group": 2, "rank_absolute": 6, "page": 1, "domain": "example.net",
         "title": "CRM reviews", "url": "https://example.net/", "description": None},
        {"type": "paid", "rank_group": 3, "rank_absolute": 7, "page": 1, "domain": "ads-three.example",
         "title": "Ad Three", "description": "Bottom ad", "url": "https://ads-three.example/"},
        {"type": "related_searches", "rank_absolute": 8, "items": ["free crm", "crm for small business"]},
    ],
}


def test_parse_serp_keeps_paid_with_placement():
    r = query_serp.parse_serp(SERP_RESULT, {"device": "mobile"})
    assert r["query"] == "crm software" and r["total_results"] == 123000 and r["device"] == "mobile"
    assert [(p["domain"], p["position"], p["placement"]) for p in r["paid"]] == [
        ("ads-one.example", 1, "top"), ("ads-two.example", 2, "top"), ("ads-three.example", 3, "bottom")]
    assert r["paid"][0]["sitelinks"] == 2 and r["paid"][0]["description"] == "Try it free"
    assert [o["domain"] for o in r["organic"]] == ["example.com", "example.net"]
    assert r["people_also_ask"] == ["What is a CRM?", "Is there a free CRM?"]
    assert r["related_searches"] == ["free crm", "crm for small business"]
    types = [f["type"] for f in r["serp_features"]]
    assert types == ["people_also_ask", "featured_snippet", "related_searches"]
    assert "paid" not in types and "organic" not in types


def test_parse_serp_edge_cases():
    r = query_serp.parse_serp({"items": [{"type": "paid", "rank_absolute": 1, "domain": "a.example"}]},
                              {"keyword": "q"})
    assert r["query"] == "q" and r["paid"][0]["placement"] == "unknown"
    empty = query_serp.parse_serp({"keyword": "q", "items": None})
    assert empty["paid"] == [] and empty["organic"] == [] and empty["serp_features"] == []
    # related searches given as objects instead of strings
    obj = query_serp.parse_serp({"items": [{"type": "related_searches", "items": [{"title": "x"}]}]})
    assert obj["related_searches"] == ["x"]


def test_ads_test_mode():
    task = query_serp.build_tasks(["a"], 2840, "en", "desktop", 10, "live", ads_test=True)[0]
    assert task["search_param"] == "adtest=on"
    assert "search_param" not in query_serp.build_tasks(["a"], 2840, "en", "desktop", 10, "live")[0]
    # Detected from the echoed request, or from check_url when collecting by task id.
    assert query_serp.parse_serp({}, {"search_param": "adtest=on"})["ads_test"] is True
    assert query_serp.parse_serp({"check_url": "https://www.google.com/search?q=a&adtest=on"})["ads_test"] is True
    assert query_serp.parse_serp(SERP_RESULT)["ads_test"] is False


def test_table_never_claims_no_advertisers():
    for params, hint in (({}, True), ({"search_param": "adtest=on"}, False)):
        r = query_serp.parse_serp({"keyword": "q", "items": []}, params)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            query_serp.print_tables([r])
        text = buf.getvalue()
        assert "No ads captured in this fetch" in text and "No ads shown" not in text
        assert ("ads test mode to capture ads" in text) is hint


def test_serp_cost_projection():
    with _NO_CONFIG:
        assert query_serp.projected_cost(10, 10, "standard") == 10 * 0.0006
        assert abs(query_serp.projected_cost(1, 15, "live") - 2 * 0.002) < 1e-12  # depth 15 → 2 pages
        assert dfs.serp_pages(100) == 10
    tasks = query_serp.build_tasks(["a"], 2840, "en", "desktop", 10, "priority")
    assert tasks[0]["priority"] == 2
    assert "priority" not in query_serp.build_tasks(["a"], 2840, "en", "desktop", 10, "standard")[0]


# --- SERP fetching ---

def test_standard_queue_post_then_poll():
    posted = ok([
        {"id": "t1", "status_code": 20100, "data": {"keyword": "crm software"}},
        {"id": None, "status_code": 40501, "status_message": "Invalid Field: 'keyword'."},
    ], cost=0.0006)
    queued = ok([{"id": "t1", "status_code": 40602, "status_message": "Task In Queue.", "result": None}])
    done = ok([{"id": "t1", "status_code": 20000, "data": {"device": "desktop"}, "result": [SERP_RESULT]}])
    sleeps = []
    tasks = query_serp.build_tasks(["crm software", "bad"], 2840, "en", "desktop", 10, "standard")
    with tempfile.TemporaryDirectory() as tmp, _NO_CONFIG, \
            mock.patch.object(dfs.requests, "post", return_value=posted) as post, \
            mock.patch.object(dfs.requests, "get", side_effect=[queued, done]) as get:
        tracker = _tracker(tmp)
        rows, errors, pending = query_serp.fetch_queued(
            _api(), tracker, tasks, "standard", 10, interval=7, timeout=300, sleep=sleeps.append)
        assert tracker.total == 0.0006
    assert post.call_args.args[0].endswith(query_serp.TASK_POST)
    assert get.call_args.args[0].endswith("/task_get/advanced/t1")
    assert sleeps == [7]
    assert len(rows) == 1 and rows[0]["paid"][0]["domain"] == "ads-one.example"
    assert "bad" in errors and "Invalid Field" in errors["bad"]
    assert pending == []


def test_poll_timeout_returns_pending_ids():
    queued = ok([{"id": "t1", "status_code": 40601, "result": None}])
    clock = iter([0, 5, 11])
    with mock.patch.object(dfs.requests, "get", return_value=queued):
        done, failed, pending = dfs.poll_tasks(_api(), query_serp.task_get, ["t1"], interval=5,
                                               timeout=10, sleep=lambda s: None, now=lambda: next(clock))
    assert done == {} and failed == {} and pending == ["t1"]


def test_poll_retries_transient_errors():
    done_resp = ok([{"id": "t1", "status_code": 20000, "result": [SERP_RESULT]}])
    with mock.patch.object(dfs.requests, "get", side_effect=[FakeResp(502, text="bad gateway"), done_resp]):
        done, failed, pending = dfs.poll_tasks(_api(), query_serp.task_get, ["t1"], interval=1,
                                               timeout=60, sleep=lambda s: None)
    assert list(done) == ["t1"] and not failed and not pending


def test_live_mode_per_query_with_errors():
    good = ok([{"status_code": 20000, "data": {"device": "desktop"}, "result": [SERP_RESULT]}], cost=0.002)
    none = ok([{"status_code": 40102, "status_message": "No Search Results.", "result": None}], cost=0.0)
    tasks = query_serp.build_tasks(["crm software", "zzqqxx"], 2840, "en", "desktop", 10, "live")
    with tempfile.TemporaryDirectory() as tmp, _NO_CONFIG, \
            mock.patch.object(dfs.requests, "post", side_effect=[good, none]) as post:
        tracker = _tracker(tmp)
        rows, errors, pending = query_serp.fetch_live(_api(), tracker, tasks, 10)
        assert tracker.total == 0.002
    assert post.call_count == 2 and post.call_args.args[0].endswith(query_serp.LIVE)
    assert len(rows) == 1 and "zzqqxx" in errors and pending == []


def test_csv_rows_sections():
    r = query_serp.parse_serp(SERP_RESULT)
    sections = [row["section"] for row in query_serp.csv_rows([r])]
    assert sections.count("paid") == 3 and sections.count("organic") == 2
    assert sections.count("people_also_ask") == 2 and sections.count("related_search") == 2
    assert "featured_snippet" in sections


# --- Ads search (Ads Transparency) ---

ADS_RESULT = {
    "keyword": "example.com", "type": "ads_search", "location_code": 2840,
    "datetime": "2026-01-15 10:00:00 +00:00", "item_types": ["ads_search"], "items_count": 3,
    "items": [
        {"type": "ads_search", "rank_group": 1, "rank_absolute": 1, "advertiser_id": "AR00000000000000000001",
         "creative_id": "CR00000000000000000011", "title": "Example Co", "verified": True, "format": "text",
         "url": "https://adstransparency.google.com/advertiser/AR00000000000000000001/creative/CR00000000000000000011?region=US",
         "preview_image": {"url": "https://img.example/1", "height": 199, "width": 380}, "preview_url": None,
         "first_shown": "2025-06-03 09:57:49 +00:00", "last_shown": "2026-01-14 08:37:19 +00:00"},
        {"type": "ads_search", "rank_group": 2, "rank_absolute": 2, "advertiser_id": "AR00000000000000000001",
         "creative_id": "CR00000000000000000012", "title": "Example Co", "verified": True, "format": "video",
         "url": "https://adstransparency.google.com/x", "preview_image": [{"url": "https://img.example/2"}],
         "preview_url": "https://preview.example/2",
         "first_shown": "2025-09-01 00:00:00 +00:00", "last_shown": "2025-12-01 00:00:00 +00:00"},
        {"type": "ads_search", "rank_group": 3, "rank_absolute": 3, "advertiser_id": "AR00000000000000000002",
         "creative_id": "CR00000000000000000021", "title": "Example Co Europe", "verified": False,
         "format": "image", "url": "https://adstransparency.google.com/y", "preview_image": None},
        {"type": "something_else", "rank_absolute": 4},
    ],
}


def test_split_targets_and_build_tasks():
    domains, ids = query_ads_search.split_targets(
        ["https://www.Example.com/pricing?x=1", "example.com", "ar00000000000000000001",
         "AR00000000000000000002", "AR00000000000000000001", "example.org"])
    assert domains == ["example.com", "example.org"]
    assert ids == ["AR00000000000000000001", "AR00000000000000000002"]
    for bad in (["not a domain"], [""], ["localhost"]):
        try:
            query_ads_search.split_targets(bad)
        except dfs.DataForSeoError:
            pass
        else:
            raise AssertionError(f"expected DataForSeoError for {bad}")

    many = [f"AR{i:020d}" for i in range(30)]
    tasks, labels = query_ads_search.build_tasks(["example.com"], many, 2840, "google_search", "text",
                                                 "2026-01-01", "2026-01-31", 40, "priority")
    assert len(tasks) == 3 and tasks[0]["target"] == "example.com"
    assert [len(t["advertiser_ids"]) for t in tasks[1:]] == [25, 5]
    assert labels[0] == "example.com" and labels[2].startswith("ids:AR")
    assert tasks[0] == {"target": "example.com", "depth": 40, "location_code": 2840,
                        "platform": "google_search", "format": "text", "date_from": "2026-01-01",
                        "date_to": "2026-01-31", "priority": 2}
    # Defaults are left out; no location means all locations.
    plain, _ = query_ads_search.build_tasks(["example.com"], [], None, "all", "all", None, None, 40, "standard")
    assert plain == [{"target": "example.com", "depth": 40}]


def test_ads_search_dates_and_cost():
    from datetime import date
    today = date(2026, 3, 1)
    query_ads_search.validate_dates(None, None, today)
    query_ads_search.validate_dates("2018-05-31", "2026-03-01", today)
    for args in (("2026-01-01", None), ("2018-05-30", "2026-01-01"), ("2026-02-01", "2026-01-01"),
                 ("2026-01-01", "2026-03-02"), ("01/01/2026", "2026-02-01")):
        try:
            query_ads_search.validate_dates(*args, today)
        except dfs.DataForSeoError:
            pass
        else:
            raise AssertionError(f"expected DataForSeoError for {args}")
    with _NO_CONFIG:
        assert query_ads_search.projected_cost(2, 40, "standard") == 2 * 0.0006
        assert abs(query_ads_search.projected_cost(1, 41, "live") - 2 * 0.002) < 1e-12  # 41 ads → 2 pages
        assert abs(query_ads_search.projected_cost(1, 700, "priority") - 18 * 0.0012) < 1e-12


def test_parse_ads():
    params = {"target": "example.com", "location_code": 2840, "platform": "google_search", "depth": 3}
    r = query_ads_search.parse_ads(ADS_RESULT, params)
    assert r["target"] == "example.com" and r["platform"] == "google_search" and r["ad_format"] == "all"
    assert r["ads_returned"] == 3 and r["may_have_more"] is True
    a = r["ads"][0]
    assert (a["rank"], a["advertiser_name"], a["format"], a["creative_id"]) == (1, "Example Co", "text",
                                                                                "CR00000000000000000011")
    assert a["preview_image_url"] == "https://img.example/1" and a["preview_image_width"] == 380
    assert a["first_shown"].startswith("2025-06-03") and a["transparency_url"].startswith("https://adstransparency")
    assert r["ads"][1]["preview_image_url"] == "https://img.example/2"  # array form
    assert r["ads"][2]["preview_image_url"] is None
    assert r["advertisers"] == [
        {"advertiser_id": "AR00000000000000000001", "name": "Example Co", "verified": True, "ads": 2},
        {"advertiser_id": "AR00000000000000000002", "name": "Example Co Europe", "verified": False, "ads": 1}]
    # ID task label; no location requested means all locations even if the result echoes one.
    ids = query_ads_search.parse_ads(ADS_RESULT, {"advertiser_ids": ["AR1", "AR2"]})
    assert ids["target"] == "ids:AR1,AR2" and ids["location_code"] is None and ids["may_have_more"] is False
    empty = query_ads_search.parse_ads({"items": None}, {"target": "example.org"})
    assert empty["ads"] == [] and empty["advertisers"] == []


def test_ads_search_queued_with_no_results():
    posted = ok([{"id": "t1", "status_code": 20100}, {"id": "t2", "status_code": 20100}], cost=0.0012)
    done = ok([{"id": "t1", "status_code": 20000, "data": {"target": "example.com", "depth": 40},
                "result": [ADS_RESULT]}])
    none = ok([{"id": "t2", "status_code": 40102, "status_message": "No Search Results.",
                "data": {"target": "example.org", "depth": 40}, "result": None}])
    tasks, labels = query_ads_search.build_tasks(["example.com", "example.org"], [], 2840, "all", "all",
                                                 None, None, 40, "standard")
    with tempfile.TemporaryDirectory() as tmp, _NO_CONFIG, \
            mock.patch.object(dfs.requests, "post", return_value=posted) as post, \
            mock.patch.object(dfs.requests, "get", side_effect=[done, none]) as get:
        tracker = _tracker(tmp)
        rows, errors, pending = query_ads_search.fetch_queued(
            _api(), tracker, tasks, labels, "standard", 40, interval=1, timeout=60, sleep=lambda s: None)
        assert tracker.total == 0.0012
        assert tracker.tally["calls"][0]["operation"] == "ads_search_standard"
    assert post.call_args.args[0].endswith(query_ads_search.TASK_POST)
    assert json.loads(post.call_args.kwargs["data"]) == tasks
    assert get.call_args_list[0].args[0].endswith("/ads_search/task_get/advanced/t1")
    assert [r["target"] for r in rows] == ["example.com", "example.org"]
    assert rows[0]["ads_returned"] == 3 and rows[1]["ads"] == []  # 40102 is zero ads, not an error
    assert errors == {} and pending == []


def test_ads_search_live_and_cap():
    good = ok([{"status_code": 20000, "data": {"target": "example.com"}, "result": [ADS_RESULT]}], cost=0.002)
    bad = ok([{"status_code": 40501, "status_message": "Invalid Field: 'target'."}], cost=0.0)
    tasks, labels = query_ads_search.build_tasks(["example.com", "example.net"], [], 2840, "all", "all",
                                                 None, None, 40, "live")
    with tempfile.TemporaryDirectory() as tmp, _NO_CONFIG, \
            mock.patch.object(dfs.requests, "post", side_effect=[good, bad]) as post:
        tracker = _tracker(tmp)
        rows, errors, pending = query_ads_search.fetch_live(_api(), tracker, tasks, labels, 40)
        assert tracker.total == 0.002
    assert post.call_count == 2 and post.call_args.args[0].endswith(query_ads_search.LIVE)
    assert len(rows) == 1 and "Invalid Field" in errors["example.net"] and pending == []
    # Cap is checked before each live call.
    with tempfile.TemporaryDirectory() as tmp, _NO_CONFIG, \
            mock.patch.object(dfs.requests, "post", return_value=good) as post:
        tracker = _tracker(tmp, cap=0.003)
        try:
            query_ads_search.fetch_live(_api(), tracker, tasks, labels, 40)
        except dfs.CapExceeded:
            pass
        else:
            raise AssertionError("expected CapExceeded on the second live call")
        assert post.call_count == 1


def test_ads_search_output():
    r = query_ads_search.parse_ads(ADS_RESULT, {"target": "example.com", "depth": 40})
    empty = query_ads_search.parse_ads({}, {"target": "example.org"})
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        query_ads_search.print_tables([r, empty])
    text = buf.getvalue()
    assert "example.com" in text and "2025-06-03" in text and "Example Co [AR00000000000000000001] verified" in text
    assert "No ads found" in text and "query_ads_advertisers.py" in text
    rows = list(query_ads_search.csv_rows([r]))
    assert len(rows) == 3 and set(rows[0]) == set(query_ads_search.CSV_COLUMNS)


# --- Advertiser lookup ---

ADVERTISERS_RESULT = {
    "keyword": "example brand", "type": "ads_advertisers", "location_code": 2840,
    "item_types": ["ads_multi_account_advertiser", "ads_advertiser", "ads_domain"],
    "items": [
        {"type": "ads_multi_account_advertiser", "rank_group": 1, "rank_absolute": 1, "title": "Example Brand Inc.",
         "location": "US", "approx_ads_count": 1200, "advertisers": [
             {"type": "advertiser", "advertiser_id": "AR00000000000000000001", "location": "US",
              "verified": True, "approx_ads_count": 1000},
             {"type": "advertiser", "advertiser_id": "AR00000000000000000002", "location": "US",
              "verified": False, "approx_ads_count": 200}]},
        {"type": "ads_advertiser", "rank_group": 1, "rank_absolute": 2, "title": "Example Brand Shop",
         "advertiser_id": "AR00000000000000000003", "location": "GB", "verified": True, "approx_ads_count": 15},
        {"type": "ads_domain", "rank_group": 1, "rank_absolute": 3, "domain": "example.com"},
        {"type": "ads_domain", "rank_group": 2, "rank_absolute": 4, "domain": "shop.example.com"},
    ],
}


def test_parse_advertisers():
    r = query_ads_advertisers.parse_advertisers(ADVERTISERS_RESULT, {"keyword": "example brand",
                                                                     "location_code": 2840})
    assert r["keyword"] == "example brand" and r["location_code"] == 2840
    assert r["domains"] == ["example.com", "shop.example.com"]
    multi, single = r["advertisers"]
    assert multi["kind"] == "multi_account" and multi["name"] == "Example Brand Inc."
    assert multi["advertiser_ids"] == ["AR00000000000000000001", "AR00000000000000000002"]
    assert multi["verified"] is None and multi["approx_ads_count"] == 1200  # mixed verification
    assert single["kind"] == "advertiser" and single["advertiser_ids"] == ["AR00000000000000000003"]
    assert single["verified"] is True and single["accounts"][0]["location"] == "GB"
    assert query_ads_advertisers._all_or_none([True, True]) is True
    assert query_ads_advertisers._all_or_none([False, False]) is False
    assert query_ads_advertisers._all_or_none([]) is None
    rows = list(query_ads_advertisers.csv_rows([r]))
    assert [x["kind"] for x in rows] == ["multi_account", "multi_account", "advertiser", "domain", "domain"]
    assert rows[1]["advertiser_id"] == "AR00000000000000000002" and rows[1]["name"] == "Example Brand Inc."
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        query_ads_advertisers.print_tables([r])
    text = buf.getvalue()
    assert "mixed" in text and "AR00000000000000000001 AR00000000000000000002" in text
    assert "Advertiser domains: example.com, shop.example.com" in text


def test_advertisers_tasks_and_cost():
    kws = query_ads_advertisers.clean_keywords(["  Example  Brand ", "example brand", "", "other"])
    assert kws == ["Example Brand", "other"]
    assert query_ads_advertisers.build_tasks(kws, None, "standard") == [{"keyword": "Example Brand"},
                                                                         {"keyword": "other"}]
    assert query_ads_advertisers.build_tasks(["a"], 2826, "priority") == [
        {"keyword": "a", "location_code": 2826, "priority": 2}]
    with _NO_CONFIG:
        assert query_ads_advertisers.projected_cost(3, "standard") == 3 * 0.0006
        assert query_ads_advertisers.projected_cost(1, "live") == 0.002
    try:
        query_ads_advertisers.clean_keywords([f"kw {i}" for i in range(101)])
    except dfs.DataForSeoError:
        pass
    else:
        raise AssertionError("expected DataForSeoError for >100 keywords")


def test_advertisers_queued_and_live():
    posted = ok([{"id": "t1", "status_code": 20100},
                 {"id": None, "status_code": 40501, "status_message": "Invalid Field: 'keyword'."}], cost=0.0006)
    done = ok([{"id": "t1", "status_code": 20000, "data": {"keyword": "example brand", "location_code": 2840},
                "result": [ADVERTISERS_RESULT]}])
    tasks = query_ads_advertisers.build_tasks(["example brand", "bad"], 2840, "standard")
    with tempfile.TemporaryDirectory() as tmp, _NO_CONFIG, \
            mock.patch.object(dfs.requests, "post", return_value=posted), \
            mock.patch.object(dfs.requests, "get", return_value=done) as get:
        tracker = _tracker(tmp)
        rows, errors, pending = query_ads_advertisers.fetch_queued(
            _api(), tracker, tasks, "standard", interval=1, timeout=60, sleep=lambda s: None)
        assert tracker.total == 0.0006
    assert get.call_args.args[0].endswith("/ads_advertisers/task_get/advanced/t1")
    assert len(rows) == 1 and len(rows[0]["advertisers"]) == 2 and "Invalid Field" in errors["bad"]

    live = ok([{"status_code": 20000, "data": {"keyword": "example brand"}, "result": [ADVERTISERS_RESULT]}],
              cost=0.002)
    with tempfile.TemporaryDirectory() as tmp, _NO_CONFIG, \
            mock.patch.object(dfs.requests, "post", return_value=live) as post:
        tracker = _tracker(tmp)
        rows, errors, _ = query_ads_advertisers.fetch_live(_api(), tracker, tasks[:1])
        assert tracker.total == 0.002 and tracker.tally["calls"][0]["operation"] == "ads_advertisers_live"
    assert post.call_args.args[0].endswith(query_ads_advertisers.LIVE)
    assert rows[0]["domains"] == ["example.com", "shop.example.com"] and errors == {}


# --- Verify ---

def test_verify_summary():
    resp = ok([{"status_code": 20000, "result": [{"login": "you@example.com", "money": {"balance": 42.5}}]}])
    with tempfile.TemporaryDirectory() as tmp, mock.patch.object(dfs.requests, "get", return_value=resp):
        info = verify.summarize(_api().get(verify.ENDPOINT), _tracker(tmp))
    assert info["login"] == "you@example.com" and info["balance_usd"] == 42.5
    assert info["today_local_spend_usd"] == 0.0


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"ok  {t.__name__}")
    print(f"All {len(tests)} dataforseo tests passed")
