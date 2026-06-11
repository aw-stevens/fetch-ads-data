"""
Ad Analytics MCP Server — single server exposing all 14 tools.

Google Ads: google_ads_query, google_ads_list_accounts
Google Analytics: google_analytics_query, google_analytics_realtime
Google Tags: google_tags_query, google_tags_list_streams
Google Tag Manager: gtm_query, gtm_list_accounts
Google Search Console: google_search_console_query, google_search_console_list_sites
LinkedIn Ads: linkedin_ads_query, linkedin_ads_list_accounts
G2 Digital Markets: g2_digital_markets_query, g2_digital_markets_verify
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

VENV_PYTHON = str(Path.home() / ".fetch-ads-data" / "venv" / "bin" / "python")
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
    fields: str = "impressions,clicks,costInLocalCurrency,externalWebsiteConversions,externalWebsitePostClickConversions,externalWebsitePostViewConversions,dateRange,pivotValues",
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


# --- Google Tags (GA4 Admin API) ---

@mcp.tool(
    name="google_tags_query",
    annotations={"readOnlyHint": True, "openWorldHint": False},
)
def google_tags_query(
    action: str,
    property_id: str = "",
    format: str = "table",
) -> str:
    """Query Google Tags / GA4 property configuration.

    Args:
        action: What to query. One of:
            - list-streams: Data streams (measurement IDs like G-XXXXX)
            - list-key-events: Conversion/key events configured for the property
            - list-custom-dimensions: Custom event and user dimensions
            - list-custom-metrics: Custom metrics
            - list-ads-links: Linked Google Ads accounts
        property_id: GA4 property ID (digits only). Pass a specific ID to query
            one property, or leave empty to query the first default property from config.
        format: Output format — 'table' (default), 'csv', or 'json'.
    """
    pid = property_id or config.default_id("google_analytics")
    if not pid:
        return "Error: No property_id provided and no defaults configured."
    properties = config.account_list("google_analytics")
    label = properties.get(pid, pid)
    cmd = [
        VENV_PYTHON,
        str(SCRIPTS / "google_tags" / "query_google_tags.py"),
        "--action", action,
        "--property", pid,
        "--format", format,
    ]
    output = _run(cmd)
    return f"=== {label} ({pid}) ===\n{output}" if property_id == "" else output


@mcp.tool(
    name="google_tags_list_streams",
    annotations={"readOnlyHint": True, "openWorldHint": False},
)
def google_tags_list_streams(
    property_id: str = "",
    format: str = "table",
) -> str:
    """List all data streams (Google Tags / measurement IDs) for GA4 properties.

    Args:
        property_id: GA4 property ID. Leave empty to list streams for all
            default properties from config.
        format: Output format — 'table' (default), 'csv', or 'json'.
    """
    ids = [property_id] if property_id else config.default_ids("google_analytics")
    if not ids:
        return "Error: No property_id provided and no defaults configured."
    properties = config.account_list("google_analytics")
    results = []
    for pid in ids:
        cmd = [
            VENV_PYTHON,
            str(SCRIPTS / "google_tags" / "query_google_tags.py"),
            "--action", "list-streams",
            "--property", pid,
            "--format", format,
        ]
        label = properties.get(pid, pid)
        output = _run(cmd)
        results.append(f"=== {label} ({pid}) ===\n{output}" if len(ids) > 1 else output)
    return "\n\n".join(results)


# --- Google Tag Manager ---

@mcp.tool(
    name="gtm_list_accounts",
    annotations={"readOnlyHint": True, "openWorldHint": False},
)
def gtm_list_accounts(format: str = "table") -> str:
    """List all Google Tag Manager accounts and containers accessible with current credentials.

    Args:
        format: Output format — 'table' (default), 'csv', or 'json'.
    """
    return _run([VENV_PYTHON, str(SCRIPTS / "google_tag_manager" / "list_accounts.py"), "--format", format])


@mcp.tool(
    name="gtm_query",
    annotations={"readOnlyHint": True, "openWorldHint": False},
)
def gtm_query(
    action: str,
    account_id: str = "",
    container_id: str = "",
    workspace_id: str = "",
    format: str = "table",
) -> str:
    """Query Google Tag Manager container configuration.

    Args:
        action: What to query. One of:
            - list-containers: Containers in an account
            - list-workspaces: Workspaces in a container
            - list-tags: All tags with type, firing triggers, and key parameters
            - list-triggers: All triggers with type and conditions
            - list-variables: Custom variables
            - list-built-in-variables: Enabled built-in variables
            - list-folders: Tag folders
            - get-version: Currently published (live) container version
        account_id: GTM account ID. Leave empty to use default from config.
        container_id: GTM container ID. Leave empty to use default from config.
        workspace_id: Workspace ID. Leave empty to auto-detect default workspace.
        format: Output format — 'table' (default), 'csv', or 'json'.
    """
    aid = account_id or config.default_id("google_tag_manager")
    if not aid:
        return "Error: No account_id provided and no default configured."
    cmd = [
        VENV_PYTHON,
        str(SCRIPTS / "google_tag_manager" / "query_gtm.py"),
        "--action", action,
        "--account", aid,
        "--format", format,
    ]
    if container_id:
        cmd += ["--container", container_id]
    if workspace_id:
        cmd += ["--workspace", workspace_id]
    accounts = config.account_list("google_tag_manager")
    label = accounts.get(aid, aid)
    output = _run(cmd)
    return f"=== {label} ({aid}) ===\n{output}" if not account_id else output


# --- Google Search Console ---

@mcp.tool(
    name="google_search_console_query",
    annotations={"readOnlyHint": True, "openWorldHint": False},
)
def google_search_console_query(
    dimensions: list[str] = ["query"],
    site: str = "",
    start: str = "30daysAgo",
    end: str = "today",
    search_type: str = "web",
    limit: int = 25,
    format: str = "table",
) -> str:
    """Query Google Search Console search analytics — impressions, clicks, CTR, position.

    Args:
        dimensions: Dimensions to group by. One or more of: query, page, country,
            device, date, searchAppearance. Default: ["query"].
        site: Site URL (e.g. "https://example.com/"). Leave empty to use default from config.
        start: Start date as YYYY-MM-DD or shorthand: 7daysAgo, 30daysAgo (default),
               90daysAgo. Note: GSC data has ~3 day lag.
        end: End date as YYYY-MM-DD or 'today'/'yesterday' (default: today).
        search_type: Filter by search type: web (default), image, video, news,
            discover, googleNews.
        limit: Maximum rows to return (default: 25, max: 25000).
        format: Output format — 'table' (default), 'csv', or 'json'.
    """
    site_url = site or config.default_id("google_search_console")
    if not site_url:
        return "Error: No site provided and no default configured."
    sites = config.account_list("google_search_console")
    label = sites.get(site_url, site_url)
    cmd = [
        VENV_PYTHON,
        str(SCRIPTS / "google_search_console" / "query_gsc.py"),
        "--site", site_url,
        "--dimensions", *dimensions,
        "--start", start,
        "--end", end,
        "--search-type", search_type,
        "--limit", str(limit),
        "--format", format,
    ]
    output = _run(cmd)
    return f"=== {label} ===\n{output}" if not site else output


@mcp.tool(
    name="google_search_console_list_sites",
    annotations={"readOnlyHint": True, "openWorldHint": False},
)
def google_search_console_list_sites(format: str = "table") -> str:
    """List all sites accessible in Google Search Console."""
    return _run([
        VENV_PYTHON,
        str(SCRIPTS / "google_search_console" / "query_gsc.py"),
        "--action", "list-sites",
        "--format", format,
    ])


# --- G2 Digital Markets (Click Report API) ---

@mcp.tool(
    name="g2_digital_markets_query",
    annotations={"readOnlyHint": True, "openWorldHint": True},
)
def g2_digital_markets_query(
    start: str = "30daysAgo",
    end: str = "today",
    group_by: str = "",
    channel: str = "",
    category: str = "",
    country: str = "",
    include_conversion_type: bool = False,
    format: str = "table",
) -> str:
    """Query the G2 Digital Markets Click Report — PPC clicks, conversions, cost, CPL
    across Capterra, GetApp, and Software Advice.

    Returns per-record click data, or aggregated totals when group_by is set. Pagination
    over the date range is handled automatically. Use this to feed monthly G2DM PPC spend,
    clicks, conversions, and CPL into marketing reporting.

    Args:
        start: Start date (date of first click) as YYYY-MM-DD, or shorthand 7daysAgo,
            30daysAgo (default), 90daysAgo.
        end: End date (date of last click) as YYYY-MM-DD, or 'today' (default) / 'yesterday'.
        group_by: Comma-separated grouping keys. Empty (default) returns raw per-record rows.
            When set, sums clicks/conversions/cost and recomputes avg_cpc, conversion_rate,
            and cpl per group. Keys: month, channel, country, category, product_name,
            vendor_name, campaign_name. Example: "month" for monthly totals, or
            "month,channel" for a per-channel monthly breakdown.
        channel: Filter by channel — capterra, getapp, or "software advice".
        category: Filter by software category.
        country: Filter by country.
        include_conversion_type: When true, includes a conversions_by_type breakdown
            (bookDemo, freeTrial, other).
        format: Output format — 'table' (default), 'csv', or 'json'.
    """
    cmd = [
        VENV_PYTHON,
        str(SCRIPTS / "g2_digital_markets" / "query_g2.py"),
        "--start", start,
        "--end", end,
        "--format", format,
    ]
    if group_by:
        cmd += ["--group-by", group_by]
    if channel:
        cmd += ["--channel", channel]
    if category:
        cmd += ["--category", category]
    if country:
        cmd += ["--country", country]
    if include_conversion_type:
        cmd += ["--include-conversion-type"]
    return _run(cmd)


@mcp.tool(
    name="g2_digital_markets_verify",
    annotations={"readOnlyHint": True, "openWorldHint": True},
)
def g2_digital_markets_verify() -> str:
    """Verify the G2 Digital Markets API key is configured and accepted (sends a minimal
    test request). Use this during setup to confirm connectivity before running reports."""
    return _run([
        VENV_PYTHON,
        str(SCRIPTS / "g2_digital_markets" / "query_g2.py"),
        "--action", "verify",
    ])


if __name__ == "__main__":
    mcp.run(transport="stdio")
