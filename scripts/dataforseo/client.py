"""
Shared DataForSEO helpers: credentials, HTTP client, Standard Queue polling, and the
local daily spend cap.

Credentials (first match wins):
    1. DATAFORSEO_LOGIN / DATAFORSEO_PASSWORD environment variables
    2. ~/.fetch-ads-data/dataforseo.json  ->  {"login": "...", "password": "..."}
       (path set by dataforseo.credentials in config.json)

Spend cap:
    DataForSEO bills per request against a prepaid balance. Every billed call is
    projected against a per-day (UTC) cap before it is sent and recorded afterwards
    in ~/.fetch-ads-data/dataforseo-costs/YYYY-MM-DD.json. Cap precedence:
    DATAFORSEO_DAILY_CAP_USD env var > dataforseo.daily_cap_usd in config.json > $1.00.
"""

import base64
import json
import math
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import config

import requests

SERVICE = "dataforseo"
BASE_URL = "https://api.dataforseo.com"
OK = 20000
TASK_CREATED = 20100
NO_RESULTS = 40102
IN_PROGRESS = (40601, 40602)  # task handed / in queue — keep polling

DEFAULT_CAP_USD = 1.0
DEFAULT_CREDS = Path.home() / ".fetch-ads-data" / "dataforseo.json"
DEFAULT_COST_DIR = Path.home() / ".fetch-ads-data" / "dataforseo-costs"
DEFAULT_LOCATION_CODE = 2840  # United States
DEFAULT_LANGUAGE_CODE = "en"

# Projection rates in USD. Actual charges are taken from each response's `cost` field
# when recording; these only gate calls before they are sent. Override any of them
# under dataforseo.pricing in config.json. https://dataforseo.com/pricing
PRICING = {
    "search_volume_live_per_task": 0.09,    # per request, up to 1,000 keywords
    "serp_standard_per_page": 0.0006,       # per SERP page of 10 results
    "serp_priority_per_page": 0.0012,
    "serp_live_per_page": 0.002,
}


class DataForSeoError(Exception):
    pass


class CapExceeded(DataForSeoError):
    pass


def service_config() -> dict:
    """dataforseo section of config.json, or {} when there is no config (env-only use)."""
    if not config.CONFIG_FILE.exists():
        return {}
    return config.service_config(SERVICE)


def rate(name: str) -> float:
    return float((service_config().get("pricing") or {}).get(name, PRICING[name]))


def default_location_code() -> int:
    return int(service_config().get("default_location_code") or DEFAULT_LOCATION_CODE)


def default_language_code() -> str:
    return service_config().get("default_language_code") or DEFAULT_LANGUAGE_CODE


def chunk(items: list, size: int) -> list[list]:
    if size <= 0:
        raise ValueError(f"chunk size must be > 0, got {size}")
    return [items[i:i + size] for i in range(0, len(items), size)]


def serp_pages(depth: int) -> int:
    """SERPs are billed per page of 10 results; depth rounds up to the next ten."""
    return max(1, math.ceil(depth / 10))


# --- Credentials ---

def load_credentials() -> tuple[str, str]:
    login = os.environ.get("DATAFORSEO_LOGIN", "").strip()
    password = os.environ.get("DATAFORSEO_PASSWORD", "").strip()
    if login and password:
        return login, password

    # Fall back to the default path so configs created before this service existed still work.
    creds_path = (config.credentials_path(SERVICE) if config.CONFIG_FILE.exists() else "") or str(DEFAULT_CREDS)
    if Path(creds_path).exists():
        data = json.loads(Path(creds_path).read_text())
        login = str(data.get("login", "")).strip()
        password = str(data.get("password", "")).strip()
        if login and password:
            return login, password

    raise DataForSeoError(
        "DataForSEO credentials not found. Set DATAFORSEO_LOGIN and DATAFORSEO_PASSWORD, or "
        'create ~/.fetch-ads-data/dataforseo.json with {"login": "...", "password": "..."} '
        "(API login/password from https://app.dataforseo.com/api-access)."
    )


def auth_header(login: str, password: str) -> str:
    return "Basic " + base64.b64encode(f"{login}:{password}".encode()).decode()


# --- HTTP ---

class Client:
    def __init__(self, login: str, password: str, base_url: str = BASE_URL, timeout: int = 120):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.headers = {"Authorization": auth_header(login, password), "Content-Type": "application/json"}

    @classmethod
    def from_env(cls) -> "Client":
        return cls(*load_credentials(), base_url=service_config().get("base_url") or BASE_URL)

    def post(self, endpoint: str, body) -> dict:
        resp = requests.post(f"{self.base_url}{endpoint}", headers=self.headers,
                             data=json.dumps(body), timeout=self.timeout)
        return self._parse(resp, endpoint)

    def get(self, endpoint: str) -> dict:
        resp = requests.get(f"{self.base_url}{endpoint}", headers=self.headers, timeout=self.timeout)
        return self._parse(resp, endpoint)

    @staticmethod
    def _parse(resp, endpoint: str) -> dict:
        if resp.status_code in (401, 403):
            raise DataForSeoError(
                f"HTTP {resp.status_code} on {endpoint}: credentials rejected. Use the API "
                "login/password from https://app.dataforseo.com/api-access (not the account password)."
            )
        if resp.status_code >= 400:
            raise DataForSeoError(f"HTTP {resp.status_code} on {endpoint}: {resp.text.strip()[:500]}")
        try:
            payload = resp.json()
        except ValueError:
            raise DataForSeoError(f"Non-JSON response on {endpoint}: {resp.text.strip()[:500]}")
        status = payload.get("status_code")
        if status is not None and status != OK:
            raise DataForSeoError(
                f"DataForSEO error on {endpoint}: {payload.get('status_message', 'unknown')} "
                f"(status_code={status})"
            )
        return payload


def task_ok(task: dict, accept=(OK,)) -> None:
    """Raise if a task-level status_code is not one of `accept`."""
    status = task.get("status_code")
    if status not in accept:
        raise DataForSeoError(f"{task.get('status_message', 'unknown')} (status_code={status})")


def poll_tasks(client: Client, endpoint_for, task_ids: list[str], interval: float = 10,
               timeout: float = 300, sleep=time.sleep, now=time.monotonic) -> tuple[dict, dict, list]:
    """Poll Standard Queue tasks until each has a result, failed, or the timeout passes.

    Retrieving results (task_get) is free; only task_post is billed. Returns
    (results: {id: task}, errors: {id: message}, pending: [ids still queued]).
    """
    pending = list(task_ids)
    results: dict = {}
    errors: dict = {}
    deadline = now() + timeout
    while pending:
        still = []
        for tid in pending:
            try:
                task = (client.get(endpoint_for(tid)).get("tasks") or [{}])[0]
            except (DataForSeoError, requests.RequestException):
                still.append(tid)  # transient fetch failure — the task is already paid for, retry
                continue
            status = task.get("status_code")
            if status in IN_PROGRESS or (status == OK and task.get("result") is None):
                still.append(tid)
            elif status == OK:
                results[tid] = task
            else:
                errors[tid] = f"{task.get('status_message', 'unknown')} (status_code={status})"
        pending = still
        if not pending or now() >= deadline:
            break
        sleep(interval)
    return results, errors, pending


# --- Daily spend cap ---

def cap_usd() -> float:
    raw = os.environ.get("DATAFORSEO_DAILY_CAP_USD", "")
    if raw == "":
        raw = service_config().get("daily_cap_usd", DEFAULT_CAP_USD)
    try:
        value = float(raw)
    except (TypeError, ValueError):
        raise DataForSeoError(f"Daily cap must be a non-negative number, got {raw!r}")
    if value < 0 or math.isnan(value):
        raise DataForSeoError(f"Daily cap must be a non-negative number, got {raw!r}")
    return value


def cost_dir() -> Path:
    raw = os.environ.get("DATAFORSEO_COST_LOG_DIR") or service_config().get("cost_log_dir")
    return Path(raw).expanduser() if raw else DEFAULT_COST_DIR


def utc_today() -> str:
    return datetime.now(timezone.utc).date().isoformat()


class SpendTracker:
    """Per-UTC-day spend tally persisted as JSON. Not locked — concurrent calls can both
    pass the projection check, so treat the cap as a guard rail, not a hard limit."""

    def __init__(self, directory: Path | None = None, cap: float | None = None, day: str | None = None):
        self.dir = directory or cost_dir()
        self.cap = cap_usd() if cap is None else cap
        self.day = day or utc_today()
        self.path = self.dir / f"{self.day}.json"
        self.tally = self._load()

    def _load(self) -> dict:
        if not self.path.exists():
            return {"date": self.day, "total_usd": 0.0, "calls": []}
        try:
            data = json.loads(self.path.read_text())
        except (OSError, ValueError) as exc:
            raise DataForSeoError(f"Could not read spend tally {self.path}: {exc}")
        return {"date": self.day, "total_usd": float(data.get("total_usd", 0.0)),
                "calls": list(data.get("calls", []))}

    @property
    def total(self) -> float:
        return self.tally["total_usd"]

    def check(self, projected: float) -> None:
        if self.total + projected > self.cap + 1e-9:
            raise CapExceeded(
                f"DataForSEO daily cap would be exceeded: today ${self.total:.4f} + projected "
                f"${projected:.4f} > cap ${self.cap:.2f} (UTC {self.day}). Raise "
                "dataforseo.daily_cap_usd in config.json or DATAFORSEO_DAILY_CAP_USD, "
                "or reduce the request."
            )

    def record(self, operation: str, units: int, cost: float) -> None:
        self.tally["total_usd"] = round(self.total + cost, 6)
        self.tally["calls"].append({
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "operation": operation,
            "units": units,
            "cost_usd": round(cost, 6),
        })
        self.dir.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.tally, indent=2))

    def summary(self, call_cost: float) -> dict:
        return {
            "call_cost_usd": round(call_cost, 6),
            "today_total_usd": round(self.total, 6),
            "daily_cap_usd": self.cap,
            "remaining_usd": round(max(self.cap - self.total, 0.0), 6),
        }


def response_cost(payload: dict, fallback: float) -> float:
    """Actual charge reported by the API, falling back to the projection."""
    cost = payload.get("cost")
    return float(cost) if isinstance(cost, (int, float)) else fallback


# --- Output helpers ---

def print_table(rows: list[dict], cols: list[str] | None = None) -> None:
    if not rows:
        print("No results.")
        return
    if cols is None:
        cols = []
        for r in rows:
            for k in r:
                if k not in cols:
                    cols.append(k)

    def cell(r, c):
        v = r.get(c)
        return "" if v is None else str(v)

    widths = {c: max(len(c), max(len(cell(r, c)) for r in rows)) for c in cols}
    print("  ".join(c.ljust(widths[c]) for c in cols))
    print("  ".join("-" * widths[c] for c in cols))
    for r in rows:
        print("  ".join(cell(r, c).ljust(widths[c]) for c in cols))


def print_cost(summary: dict, file=sys.stdout) -> None:
    print(
        f"\nDataForSEO cost: ${summary['call_cost_usd']:.4f} this call; "
        f"${summary['today_total_usd']:.4f} of ${summary['daily_cap_usd']:.2f} daily cap used "
        f"(${summary['remaining_usd']:.4f} left, UTC day).",
        file=file,
    )
