"""
Ad Analytics MCP Server — single server exposing all 6 tools.

Google Ads: google_ads_query, google_ads_list_accounts
Google Analytics: google_analytics_query, google_analytics_realtime
LinkedIn Ads: linkedin_ads_query, linkedin_ads_list_accounts
"""

import subprocess
import sys
from pathlib import Path

from mcp.server.fastmcp import FastMCP

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
        customer_id: Google Ads customer ID (digits only). Defaults to config default.
        format: Output format — 'table' (default, human-readable), 'csv', or 'json'.
    """
    cmd = [VENV_PYTHON, str(SCRIPTS / "google_ads" / "query_ads.py"), query, "--format", format]
    if customer_id:
        cmd += ["--customer-id", customer_id]
    return _run(cmd)


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
        property_id: GA4 property ID. Defaults to config default.
        start_date: Start of date range. Named: 7daysAgo, 30daysAgo, 90daysAgo, yesterday.
            Or YYYY-MM-DD. Default: 30daysAgo.
        end_date: End of date range. Default: today.
        limit: Maximum rows to return. Default: 100.
        format: Output format — 'table' (default), 'csv', or 'json'.
    """
    cmd = [VENV_PYTHON, str(SCRIPTS / "google_analytics" / "query_ga.py"),
           "--metrics", *metrics,
           "--start", start_date,
           "--end", end_date,
           "--limit", str(limit),
           "--format", format]
    if property_id:
        cmd += ["--property", property_id]
    if dimensions:
        cmd += ["--dimensions", *dimensions]
    return _run(cmd)


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
        property_id: GA4 property ID. Defaults to config default.
        limit: Maximum rows to return. Default: 50.
        format: Output format — 'table' (default), 'csv', or 'json'.
    """
    cmd = [VENV_PYTHON, str(SCRIPTS / "google_analytics" / "query_ga.py"),
           "--metrics", *metrics,
           "--limit", str(limit),
           "--format", format,
           "--realtime"]
    if property_id:
        cmd += ["--property", property_id]
    if dimensions:
        cmd += ["--dimensions", *dimensions]
    return _run(cmd)


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
        account_id: Sponsored account ID (digits only). Defaults to config default.
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
    cmd = [
        VENV_PYTHON,
        str(SCRIPTS / "linkedin_ads" / "query_li_ads.py"),
        "--pivot", pivot,
        "--start", start,
        "--end", end,
        "--granularity", granularity,
        "--fields", fields,
        "--format", format,
    ]
    if account_id:
        cmd += ["--account-id", account_id]
    return _run(cmd)


@mcp.tool(
    name="linkedin_ads_list_accounts",
    annotations={"readOnlyHint": True, "openWorldHint": False},
)
def linkedin_ads_list_accounts(format: str = "table") -> str:
    """List all LinkedIn ad accounts accessible with the current credentials."""
    return _run([VENV_PYTHON, str(SCRIPTS / "linkedin_ads" / "list_li_accounts.py"), "--format", format])


if __name__ == "__main__":
    mcp.run(transport="stdio")
