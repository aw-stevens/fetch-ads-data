#!/usr/bin/env python3
"""Offline tests for the Microsoft Advertising REST client (no network, no credentials).

Covers the report request body, submit → poll → zipped-CSV download, the
"Success with no download URL" (zero rows) case, REST headers for Google identities,
API fault formatting, and refresh-token rotation persistence.

Run:
    python scripts/microsoft_ads/test_rest_client.py
"""

import io
import json
import sys
import tempfile
import zipfile
from datetime import date
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))
import auth
import query_ms_ads


class FakeResp:
    def __init__(self, status=200, body=None, content=None):
        self.status_code = status
        self._body = body
        self.content = content if content is not None else (json.dumps(body).encode() if body is not None else b"")
        self.text = self.content.decode("utf-8", "replace")

    def json(self):
        if self._body is None:
            raise ValueError("no json")
        return self._body

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(self.status_code)


def _zip_csv(text: str) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("report.csv", "﻿" + text)
    return buf.getvalue()


def _client(identity="google"):
    with mock.patch.object(auth, "access_token", return_value="AT"):
        return auth.Client(
            {"identity": identity, "developer_token": "DT", "customer_id": "111"},
            account_id=222,
        )


def test_request_body():
    body = query_ms_ads._build_report_request(
        "campaign", ["CampaignName", "Spend"], "Daily", "222", date(2026, 9, 30), date(2026, 10, 6),
    )["ReportRequest"]
    assert body["Type"] == "CampaignPerformanceReportRequest"
    assert body["Scope"] == {"AccountIds": [222]}
    assert body["Columns"] == ["CampaignName", "Spend"]
    assert body["Time"]["CustomDateRangeEnd"] == {"Year": 2026, "Month": 10, "Day": 6}
    assert body["ExcludeReportHeader"] and body["ExcludeReportFooter"]
    assert "FormatVersion" not in body  # keep v1.0 formatting (e.g. "20.00%") for output parity


def test_headers():
    h = _client("google").headers()
    assert h["Authorization"] == "Bearer AT" and h["DeveloperToken"] == "DT"
    assert h["CustomerId"] == "111" and h["CustomerAccountId"] == "222"
    assert h["IdentityProvider"] == "Google"
    assert "IdentityProvider" not in _client("microsoft").headers()
    assert _client().headers(customer_id=999)["CustomerId"] == "999"


def test_run_report_success_and_empty():
    client = _client()
    posts = [
        FakeResp(body={"ReportRequestId": "R1"}),
        FakeResp(body={"ReportRequestStatus": {"Status": "Pending"}}),
        FakeResp(body={"ReportRequestStatus": {"Status": "Success", "ReportDownloadUrl": "https://dl"}}),
    ]
    csv_text = 'CampaignName,Spend\r\n_Brand,"1,234.50"\r\nOther,0.05\r\n'
    with mock.patch.object(auth.requests, "post", side_effect=posts), \
         mock.patch.object(query_ms_ads.requests, "get", return_value=FakeResp(content=_zip_csv(csv_text))) as get, \
         mock.patch.object(query_ms_ads.time, "sleep"):
        rows = query_ms_ads._run_report(client, {"ReportRequest": {}})
    assert rows == [{"CampaignName": "_Brand", "Spend": "1,234.50"}, {"CampaignName": "Other", "Spend": "0.05"}]
    assert "headers" not in get.call_args.kwargs  # pre-signed URL: no auth sent

    posts = [
        FakeResp(body={"ReportRequestId": "R2"}),
        FakeResp(body={"ReportRequestStatus": {"Status": "Success", "ReportDownloadUrl": None}}),
    ]
    with mock.patch.object(auth.requests, "post", side_effect=posts):
        assert query_ms_ads._run_report(client, {"ReportRequest": {}}) == []


def test_fault_message():
    fault = FakeResp(400, {
        "TrackingId": "T1", "Type": "ApiFault",
        "Errors": [{"Code": 2010, "ErrorCode": "InvalidCustomDateRangeEnd", "Message": "bad end"}],
    })
    with mock.patch.object(auth.requests, "post", return_value=fault):
        try:
            _client().post("https://x", {})
        except auth.ApiError as exc:
            msg = str(exc)
        else:
            raise AssertionError("expected ApiError")
    assert "InvalidCustomDateRangeEnd (2010): bad end" in msg and "TrackingId T1" in msg


def test_refresh_rotation_persisted():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "microsoft-ads.json"
        creds = {"identity": "microsoft", "client_id": "C", "developer_token": "DT", "refresh_token": "OLD"}
        path.write_text(json.dumps(creds))
        with mock.patch.object(auth, "_creds_file", return_value=path):
            # Google-style response: no new refresh token → file untouched.
            with mock.patch.object(auth.requests, "post", return_value=FakeResp(body={"access_token": "A1"})) as post:
                assert auth.access_token(creds) == "A1"
            sent = post.call_args.kwargs["data"]
            assert sent["grant_type"] == "refresh_token" and sent["scope"] == auth.MICROSOFT_OAUTH["scope"]
            assert "client_secret" not in sent
            assert json.loads(path.read_text())["refresh_token"] == "OLD"
            # Microsoft-style rotation → new token written back.
            with mock.patch.object(auth.requests, "post",
                                   return_value=FakeResp(body={"access_token": "A2", "refresh_token": "NEW"})):
                assert auth.access_token(creds) == "A2"
            assert json.loads(path.read_text())["refresh_token"] == "NEW"


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"ok  {t.__name__}")
    print(f"All {len(tests)} microsoft_ads tests passed")
