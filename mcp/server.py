"""
Ad Analytics MCP Server — single server exposing all 6 tools.

Google Ads: google_ads_query, google_ads_list_accounts
Google Analytics: google_analytics_query, google_analytics_realtime
LinkedIn Ads: linkedin_ads_query, linkedin_ads_list_accounts
"""

import json
import subprocess
import sys
from pathlib import Path

from mcp.server.fastmcp import FastMCP

# Import config for default IDs
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
import config

mcp = FastMCP("ad_analytics")

VENV_PYTHON = str(Path.home() / ".ad-analytics" / "venv" / "bin" / "python")
SCRIPTS = Path(__file__).parent.parent / "scripts"


def _run(cmd: list[str]) -> str:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return f"Error:\n{result.stderr.strip()}"
    return result.stdout.strip()


# --- Google Ads ---

@mcp.tool(
    name="google_ads_query",
    annotations={"readOnlyHint": True, "openWorldHint": False},
)
def google_ads_query(
    query: str,
    customer_id: str = "",
    format: str = "table",
) -> str:
    """Execute a GAQL (Google Ads Query Language) query and return results.

    Args:
        query: GAQL query string. Example:
            SELECT campaign.name, metrics.impressions, metrics.clicks, metrics.cost_micros
            FROM campaign
            WHERE segments.date DURING LAST_30_DAYS
            ORDER BY metrics.cost_micros DESC
            LIMIT 20
        customer_id: Google Ads customer ID (digits only). Pass a specific ID to query
            one account, or leave empty to query all default accounts from config.
        format: Output format — 'table' (default, human-readable), 'csv', or 'json'.
    """
    ids = [customer_id] if customer_id else config.default_ids("google_ads")
    if not ids:
        return "Error: No customer_id provided and no defaults configured."
    accounts = config.account_list("google_ads")
    results = []
    for cid in ids:
        cmd = [VENV_PYTHON, str(SCRIPTS / "google_ads" / "query_ads.py"), query, "--customer-id", cid, "--format", format]
        label = accounts.get(cid, cid)
        output = _run(cmd)
        results.append(f"=== {label} ({cid}) ===\n{output}" if len(ids) > 1 else output)
    return "\n\n".join(results)


@mcp.tool(
    name="google_ads_list_accounts",
    annotations={"readOnlyHint": True, "openWorldHint": False},
)
def google_ads_list_accounts() -> str:
    """List all Google Ads accounts accessible with the current credentials."""
    return _run([VENV_PYTHON, str(SCRIPTS / "google_ads" / "list_accounts.py")])


# --- Google Analytics ---

@mcp.tool(
    name="google_analytics_query",
    annotations={"readOnlyHint": True, "openWorldHint": False},
)
def google_analytics_query(
    dimensions: list[str],
    metrics: list[str],
    property_id: str = "",
    start_date: str = "30daysAgo",
    end_date: str = "today",
    limit: int = 100,
    format: str = "table",
) -> str:
    """Run a standard GA4 report and return results.

    Args:
        dimensions: List of GA4 dimension names (e.g. ["sessionSource", "sessionMedium"]).
            Pass an empty list for metric-only queries.
        metrics: List of GA4 metric names (e.g. ["sessions", "newUsers", "engagementRate"]).
        property_id: GA4 property ID. Pass a specific ID to query one property,
            or leave empty to query all default properties from config.
        start_date: Start of date range. Named: 7daysAgo, 30daysAgo, 90daysAgo, yesterday.
            Or YYYY-MM-DD. Default: 30daysAgo.
        end_date: End of date range. Default: today.
        limit: Maximum rows to return. Default: 100.
        format: Output format — 'table' (default), 'csv', or 'json'.
    """
    ids = [property_id] if property_id else config.default_ids("google_analytics")
    if not ids:
        return "Error: No property_id provided and no defaults configured."
    properties = config.account_list("google_analytics")
    results = []
    for pid in ids:
        cmd = [VENV_PYTHON, str(SCRIPTS / "google_analytics" / "query_ga.py"),
               "--property", pid,
               "--metrics", *metrics,
               "--start", start_date,
               "--end", end_date,
               "--limit", str(limit),
               "--format", format]
        if dimensions:
            cmd += ["--dimensions", *dimensions]
        label = properties.get(pid, pid)
        output = _run(cmd)
        results.append(f"=== {label} ({pid}) ===\n{output}" if len(ids) > 1 else output)
    return "\n\n".join(results)


@mcp.tool(
    name="google_analytics_realtime",
    annotations={"readOnlyHint": True, "openWorldHint": False},
)
def google_analytics_realtime(
    metrics: list[str],
    dimensions: list[str] = [],
    property_id: str = "",
    limit: int = 50,
    format: str = "table",
) -> str:
    """Run a GA4 realtime report showing data from the last 30 minutes.

    Args:
        metrics: List of realtime metric names (e.g. ["activeUsers"]).
        dimensions: List of realtime dimension names (e.g. ["city", "country", "pagePath",
            "deviceCategory", "sessionSource"]). Optional.
        property_id: GA4 property ID. Pass a specific ID to query one property,
            or leave empty to query all default properties from config.
        limit: Maximum rows to return. Default: 50.
        format: Output format — 'table' (default), 'csv', or 'json'.
    """
    ids = [property_id] if property_id else config.default_ids("google_analytics")
    if not ids:
        return "Error: No property_id provided and no defaults configured."
    properties = config.account_list("google_analytics")
    results = []
    for pid in ids:
        cmd = [VENV_PYTHON, str(SCRIPTS / "google_analytics" / "query_ga.py"),
               "--property", pid,
               "--metrics", *metrics,
               "--limit", str(limit),
               "--format", format,
               "--realtime"]
        if dimensions:
            cmd += ["--dimensions", *dimensions]
        label = properties.get(pid, pid)
        output = _run(cmd)
        results.append(f"=== {label} ({pid}) ===\n{output}" if len(ids) > 1 else output)
    return "\n\n".join(results)


# --- LinkedIn Ads ---

@mcp.tool(
    name="linkedin_ads_query",
    annotations={"readOnlyHint": True, "openWorldHint": False},
)
def linkedin_ads_query(
    account_id: str = "",
    pivot: str = "CAMPAIGN",
    start: str = "30daysAgo",
    end: str = "yesterday",
    granularity: str = "ALL",
    fields: str = "impressions,clicks,costInLocalCurrency,dateRange,pivotValues",
    format: str = "table",
) -> str:
    """Query LinkedIn Ads analytics for an ad account.

    Args:
        account_id: Sponsored account ID (digits only). Pass a specific ID to query
            one account, or leave empty to query all default accounts from config.
        pivot: Grouping dimension. One of: ACCOUNT, CAMPAIGN (default), CAMPAIGN_GROUP,
               CREATIVE, MEMBER_COMPANY, MEMBER_INDUSTRY, MEMBER_SENIORITY,
               MEMBER_JOB_TITLE, MEMBER_COUNTRY_V2.
        start: Start date as YYYY-MM-DD or shorthand: 7daysAgo, 30daysAgo (default),
               90daysAgo, yesterday.
        end: End date as YYYY-MM-DD or 'yesterday' (default) or 'today'.
        granularity: DAILY, MONTHLY, or ALL (default — aggregate full range).
        fields: Comma-separated metrics. Default covers impressions, clicks, spend,
                date range, pivot values.
        format: 'table' (default), 'csv', or 'json'.
    """
    ids = [account_id] if account_id else config.default_ids("linkedin_ads")
    if not ids:
        return "Error: No account_id provided and no defaults configured."
    accounts = config.account_list("linkedin_ads")
    results = []
    for aid in ids:
        cmd = [
            VENV_PYTHON,
            str(SCRIPTS / "linkedin_ads" / "query_li_ads.py"),
            "--account-id", aid,
            "--pivot", pivot,
            "--start", start,
            "--end", end,
            "--granularity", granularity,
            "--fields", fields,
            "--format", format,
        ]
        label = accounts.get(aid, aid)
        output = _run(cmd)
        results.append(f"=== {label} ({aid}) ===\n{output}" if len(ids) > 1 else output)
    return "\n\n".join(results)


@mcp.tool(
    name="linkedin_ads_list_accounts",
    annotations={"readOnlyHint": True, "openWorldHint": False},
)
def linkedin_ads_list_accounts(format: str = "table") -> str:
    """List all LinkedIn ad accounts accessible with the current credentials."""
    return _run([VENV_PYTHON, str(SCRIPTS / "linkedin_ads" / "list_li_accounts.py"), "--format", format])


if __name__ == "__main__":
    mcp.run(transport="stdio")
