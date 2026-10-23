"""
Ad Analytics MCP Server — single server exposing all 21 tools.

Google Ads: google_ads_query, google_ads_list_accounts
Google Analytics: google_analytics_query, google_analytics_realtime
Google Tags: google_tags_query, google_tags_list_streams
Google Tag Manager: gtm_query, gtm_list_accounts
Google Search Console: google_search_console_query, google_search_console_list_sites
LinkedIn Ads: linkedin_ads_query, linkedin_ads_list_accounts
G2 Digital Markets: g2_digital_markets_query, g2_digital_markets_verify
Microsoft Advertising: microsoft_ads_query, microsoft_ads_list_accounts
DataForSEO: dataforseo_keyword_volume, dataforseo_serp, dataforseo_ads_search,
    dataforseo_ads_advertisers, dataforseo_verify
"""

import json
import subprocess
import sys
from pathlib import Path

try:
    from mcp.server.mcpserver import MCPServer  # mcp >= 2 (FastMCP was renamed)
except ImportError:
    from mcp.server.fastmcp import FastMCP as MCPServer  # mcp 1.x — existing venvs

# Import config for default IDs
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
import config

mcp = MCPServer("ad_analytics")

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


# --- Microsoft Advertising (Bing Ads) ---

@mcp.tool(
    name="microsoft_ads_query",
    annotations={"readOnlyHint": True, "openWorldHint": False},
)
def microsoft_ads_query(
    account_id: str = "",
    report_type: str = "campaign",
    aggregation: str = "Summary",
    start: str = "30daysAgo",
    end: str = "yesterday",
    columns: str = "",
    format: str = "table",
) -> str:
    """Query Microsoft Advertising (Bing Ads) performance via the Reporting API.

    Bing has no query language, so this mirrors the shape of the other ad-platform
    query tools (entity + metrics + time + format) rather than a literal query string.
    Returns spend, clicks, impressions, and conversions by account or campaign, with
    optional monthly/daily time bucketing.

    Args:
        account_id: Microsoft Advertising account ID (digits only). Pass a specific ID
            to query one account, or leave empty to query all default accounts from config.
        report_type: 'campaign' (default — per-campaign rows) or 'account' (account totals).
        aggregation: Time bucketing — Summary (default, whole range), Daily, Weekly,
            Monthly, or Yearly. For monthly spend use Monthly.
        start: Start date as YYYY-MM-DD or shorthand: 7daysAgo, 30daysAgo (default),
            90daysAgo, yesterday.
        end: End date as YYYY-MM-DD or 'yesterday' (default) or 'today'.
        columns: Comma-separated report columns. Leave empty for sensible defaults
            (TimePeriod, account/campaign names + IDs, CurrencyCode, Impressions, Clicks,
            Spend, Conversions). TimePeriod is dropped automatically for Summary.
        format: Output format — 'table' (default), 'csv', or 'json'.
    """
    ids = [account_id] if account_id else config.default_ids("microsoft_ads")
    if not ids:
        return "Error: No account_id provided and no defaults configured."
    accounts = config.account_list("microsoft_ads")
    results = []
    for aid in ids:
        cmd = [
            VENV_PYTHON,
            str(SCRIPTS / "microsoft_ads" / "query_ms_ads.py"),
            "--account-id", aid,
            "--report-type", report_type,
            "--aggregation", aggregation,
            "--start", start,
            "--end", end,
            "--format", format,
        ]
        if columns:
            cmd += ["--columns", columns]
        label = accounts.get(aid, aid)
        output = _run(cmd)
        results.append(f"=== {label} ({aid}) ===\n{output}" if len(ids) > 1 else output)
    return "\n\n".join(results)


@mcp.tool(
    name="microsoft_ads_list_accounts",
    annotations={"readOnlyHint": True, "openWorldHint": False},
)
def microsoft_ads_list_accounts(format: str = "table") -> str:
    """List all Microsoft Advertising accounts accessible with the current credentials."""
    return _run([VENV_PYTHON, str(SCRIPTS / "microsoft_ads" / "list_accounts.py"), "--format", format])


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
    over the date range is handled automatically. Use group_by="month" for monthly G2DM PPC
    spend, clicks, conversions, and CPL.

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


# --- DataForSEO (keyword volume, SERP, Ads Transparency) ---
# Paid API: each call is checked against a local daily spend cap before it is sent.

@mcp.tool(
    name="dataforseo_keyword_volume",
    annotations={"readOnlyHint": True, "openWorldHint": True},
)
def dataforseo_keyword_volume(
    keywords: list[str],
    location_code: int = 0,
    language_code: str = "",
    dry_run: bool = False,
    format: str = "table",
) -> str:
    """Get Google Ads keyword search volume via DataForSEO — average monthly searches, CPC,
    competition (LOW/MEDIUM/HIGH + 0-100 index), top-of-page bid range, and monthly trend.

    Costs money: billed per request of up to 700 keywords (one keyword costs the same as
    700), so batch keywords into one call. Refused if it would exceed the daily spend cap.

    Args:
        keywords: Keywords to look up (e.g. ["crm software", "email marketing tool"]).
            Max 80 characters / 10 words each, up to 10,000 per call. Duplicates are dropped.
        location_code: DataForSEO location code. 0 (default) uses the config default or
            2840 (United States). Others: 2826 UK, 2124 Canada, 2036 Australia.
        language_code: Language code. Empty (default) uses the config default or "en".
        dry_run: When true, returns the request bodies and projected cost without calling
            the API or spending anything.
        format: Output format — 'table' (default), 'csv', or 'json'.
    """
    cmd = [VENV_PYTHON, str(SCRIPTS / "dataforseo" / "query_volume.py"), "--format", format]
    if location_code:
        cmd += ["--location-code", str(location_code)]
    if language_code:
        cmd += ["--language-code", language_code]
    if dry_run:
        cmd += ["--dry-run"]
    return _run(cmd + ["--", *keywords])  # "--" so a keyword starting with "-" isn't a flag


@mcp.tool(
    name="dataforseo_serp",
    annotations={"readOnlyHint": True, "openWorldHint": True},
)
def dataforseo_serp(
    queries: list[str] = [],
    mode: str = "standard",
    location_code: int = 0,
    language_code: str = "",
    device: str = "desktop",
    depth: int = 10,
    ads_test: bool = False,
    task_ids: list[str] = [],
    dry_run: bool = False,
    format: str = "table",
) -> str:
    """Fetch Google search results pages via DataForSEO: organic results, People Also Ask
    questions, related searches, other SERP features, and any paid ads captured (advertiser
    domain, ad title/description, position, top/bottom placement).

    Ads are often missing from normal fetches, even on heavily advertised queries. To see
    who advertises, set ads_test=true (organic urls/domains are then blank, so use a
    separate call for organic). A SERP is one sample: no ads does not mean nobody bids.

    Costs money: billed per query per 10 results. Refused if it would exceed the daily
    spend cap.

    Args:
        queries: Search queries (e.g. ["crm software"]). Up to 100 per call.
        mode: 'standard' (default — cheapest, queued, can take several minutes),
            'priority' (~2x price, usually under a minute), or 'live' (~3x price, seconds).
        location_code: DataForSEO location code. 0 (default) uses the config default or
            2840 (United States).
        language_code: Language code. Empty (default) uses the config default or "en".
        device: 'desktop' (default) or 'mobile'.
        depth: Number of results, 10-100 (default 10). Each extra 10 is billed again.
        ads_test: Send Google's adtest=on flag so ads are captured more often (same price).
            Organic results come back without url/domain in this mode.
        task_ids: Task IDs from an earlier call that timed out while queued. When set,
            collects those results instead of posting new queries (no charge).
        dry_run: When true, returns the task bodies and projected cost without calling the API.
        format: Output format — 'table' (default), 'csv', or 'json'.
    """
    cmd = [VENV_PYTHON, str(SCRIPTS / "dataforseo" / "query_serp.py"), "--format", format]
    if task_ids:
        return _run(cmd + ["--task-ids", *task_ids])
    cmd += ["--mode", mode, "--device", device, "--depth", str(depth)]
    if ads_test:
        cmd += ["--ads-test"]
    if location_code:
        cmd += ["--location-code", str(location_code)]
    if language_code:
        cmd += ["--language-code", language_code]
    if dry_run:
        cmd += ["--dry-run"]
    return _run(cmd + ["--", *queries])


@mcp.tool(
    name="dataforseo_ads_search",
    annotations={"readOnlyHint": True, "openWorldHint": True},
)
def dataforseo_ads_search(
    targets: list[str] = [],
    mode: str = "standard",
    location_code: int = 0,
    all_locations: bool = False,
    platform: str = "all",
    ad_format: str = "all",
    date_from: str = "",
    date_to: str = "",
    depth: int = 40,
    task_ids: list[str] = [],
    dry_run: bool = False,
    format: str = "table",
) -> str:
    """List the ads an advertiser runs on Google, from the Google Ads Transparency Center via
    DataForSEO: format (text/image/video), first and last shown dates, advertiser account,
    a Transparency Center link, and a preview image/URL per ad. No ad copy is returned —
    the link or preview shows it.

    Use for "what ads does example.com run". Unlike dataforseo_serp, this is per advertiser,
    not a sample of one search page. If a domain returns nothing, find the advertiser's IDs
    with dataforseo_ads_advertisers and pass those instead.

    Costs money: billed per domain (or per group of up to 25 IDs) per 40 ads. Refused if it
    would exceed the daily spend cap.

    Args:
        targets: Advertiser domains (e.g. ["example.com"]) and/or advertiser IDs ("AR" + digits).
            Each domain is one task; all IDs are grouped into one task per 25.
        mode: 'standard' (default — cheapest, queued, can take several minutes),
            'priority' (~2x price, usually under a minute), or 'live' (~3x price, seconds).
        location_code: Where the ads were shown. 0 (default) uses the config default or
            2840 (United States).
        all_locations: When true, sends no location (ads shown anywhere).
        platform: 'all' (default), 'google_search', 'youtube', 'google_play', 'google_maps',
            or 'google_shopping'.
        ad_format: 'all' (default), 'text', 'image', or 'video'.
        date_from: Only ads shown on/after this date, YYYY-MM-DD (earliest 2018-05-31).
            Requires date_to.
        date_to: Only ads shown on/before this date, YYYY-MM-DD. Requires date_from.
        depth: Max ads per task (default 40; up to 700 queued, 120 live). Each extra 40 is billed again.
        task_ids: Task IDs from an earlier call that timed out while queued. When set,
            collects those results instead of posting new tasks (no charge).
        dry_run: When true, returns the task bodies and projected cost without calling the API.
        format: Output format — 'table' (default), 'csv', or 'json'.
    """
    cmd = [VENV_PYTHON, str(SCRIPTS / "dataforseo" / "query_ads_search.py"), "--format", format]
    if task_ids:
        return _run(cmd + ["--task-ids", *task_ids])
    cmd += ["--mode", mode, "--platform", platform, "--ad-format", ad_format, "--depth", str(depth)]
    if all_locations:
        cmd += ["--all-locations"]
    elif location_code:
        cmd += ["--location-code", str(location_code)]
    if date_from:
        cmd += ["--date-from", date_from]
    if date_to:
        cmd += ["--date-to", date_to]
    if dry_run:
        cmd += ["--dry-run"]
    return _run(cmd + ["--", *targets])


@mcp.tool(
    name="dataforseo_ads_advertisers",
    annotations={"readOnlyHint": True, "openWorldHint": True},
)
def dataforseo_ads_advertisers(
    keywords: list[str] = [],
    mode: str = "standard",
    location_code: int = 0,
    all_locations: bool = False,
    task_ids: list[str] = [],
    dry_run: bool = False,
    format: str = "table",
) -> str:
    """Find Google Ads advertiser accounts by name or keyword, from the Google Ads
    Transparency Center via DataForSEO. Returns advertiser IDs (brands with several
    accounts are grouped), location, verification, approximate ad count, and matching
    advertiser domains — inputs for dataforseo_ads_search.

    Costs money: billed per keyword. Refused if it would exceed the daily spend cap.

    Args:
        keywords: Advertiser names or keywords (e.g. ["example brand"]). Up to 100 per call.
        mode: 'standard' (default — cheapest, queued, can take several minutes),
            'priority' (~2x price, usually under a minute), or 'live' (~3x price, seconds).
        location_code: Advertiser location. 0 (default) uses the config default or
            2840 (United States).
        all_locations: When true, sends no location (advertisers anywhere).
        task_ids: Task IDs from an earlier call that timed out while queued. When set,
            collects those results instead of posting new tasks (no charge).
        dry_run: When true, returns the task bodies and projected cost without calling the API.
        format: Output format — 'table' (default), 'csv', or 'json'.
    """
    cmd = [VENV_PYTHON, str(SCRIPTS / "dataforseo" / "query_ads_advertisers.py"), "--format", format]
    if task_ids:
        return _run(cmd + ["--task-ids", *task_ids])
    cmd += ["--mode", mode]
    if all_locations:
        cmd += ["--all-locations"]
    elif location_code:
        cmd += ["--location-code", str(location_code)]
    if dry_run:
        cmd += ["--dry-run"]
    return _run(cmd + ["--", *keywords])


@mcp.tool(
    name="dataforseo_verify",
    annotations={"readOnlyHint": True, "openWorldHint": True},
)
def dataforseo_verify() -> str:
    """Verify DataForSEO credentials (free call) and show the account balance plus today's
    spend through this plugin against the daily cap."""
    return _run([VENV_PYTHON, str(SCRIPTS / "dataforseo" / "verify.py")])


if __name__ == "__main__":
    mcp.run(transport="stdio")
