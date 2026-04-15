#!/usr/bin/env python3
"""
Query Google Tag Manager container configuration.

Usage:
    python query_gtm.py --action list-tags --account 123 --container 456
    python query_gtm.py --action list-triggers --account 123 --container 456
    python query_gtm.py --action list-variables --account 123 --container 456
    python query_gtm.py --action list-containers --account 123
    python query_gtm.py --action get-version --account 123 --container 456
    python query_gtm.py --action list-tags --format json

Credentials configured in ~/.fetch-ads-data/config.json
"""

import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import config

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build


ACTIONS = [
    "list-containers",
    "list-workspaces",
    "list-tags",
    "list-triggers",
    "list-variables",
    "list-built-in-variables",
    "list-folders",
    "get-version",
]


def _get_service():
    creds_path = config.credentials_path("google_tag_manager")
    if not creds_path or not Path(creds_path).exists():
        print("Error: GTM credentials not found. Run get_token.py first.", file=sys.stderr)
        sys.exit(1)
    creds_data = json.loads(Path(creds_path).read_text())
    creds = Credentials(
        token=None,
        refresh_token=creds_data["refresh_token"],
        token_uri=creds_data["token_uri"],
        client_id=creds_data["client_id"],
        client_secret=creds_data["client_secret"],
    )
    return build("tagmanager", "v2", credentials=creds)


def _print_table(rows: list[dict]) -> None:
    if not rows:
        print("No results.")
        return
    cols = list(rows[0].keys())
    widths = {c: max(len(c), max(len(str(r.get(c, ""))) for r in rows)) for c in cols}
    header = "  ".join(c.ljust(widths[c]) for c in cols)
    sep = "  ".join("-" * widths[c] for c in cols)
    print(header)
    print(sep)
    for row in rows:
        print("  ".join(str(row.get(c, "")).ljust(widths[c]) for c in cols))


def _output(rows: list[dict], fmt: str) -> None:
    if fmt == "json":
        print(json.dumps(rows, indent=2))
    elif fmt == "csv":
        if rows:
            writer = csv.DictWriter(sys.stdout, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
    else:
        _print_table(rows)


def _get_default_workspace(service, container_path: str) -> str:
    """Find the default workspace for a container."""
    workspaces = (
        service.accounts()
        .containers()
        .workspaces()
        .list(parent=container_path)
        .execute()
        .get("workspace", [])
    )
    if not workspaces:
        print("Error: No workspaces found in container.", file=sys.stderr)
        sys.exit(1)
    # Prefer "Default Workspace", fall back to first
    for ws in workspaces:
        if ws.get("name", "").lower() == "default workspace":
            return ws["workspaceId"]
    return workspaces[0]["workspaceId"]


def _extract_param(params: list[dict], key: str) -> str:
    """Extract a parameter value from GTM's parameter list format."""
    for p in params or []:
        if p.get("key") == key:
            return p.get("value", "")
    return ""


# --- Actions ---


def list_containers(service, account_path: str) -> list[dict]:
    containers = (
        service.accounts()
        .containers()
        .list(parent=account_path)
        .execute()
        .get("container", [])
    )
    rows = []
    for c in containers:
        rows.append({
            "container_id": c["containerId"],
            "name": c.get("name", ""),
            "public_id": c.get("publicId", ""),
            "usage_context": ", ".join(c.get("usageContext", [])),
        })
    return rows


def list_workspaces(service, container_path: str) -> list[dict]:
    workspaces = (
        service.accounts()
        .containers()
        .workspaces()
        .list(parent=container_path)
        .execute()
        .get("workspace", [])
    )
    rows = []
    for ws in workspaces:
        rows.append({
            "workspace_id": ws["workspaceId"],
            "name": ws.get("name", ""),
            "description": ws.get("description", ""),
        })
    return rows


def list_tags(service, workspace_path: str) -> list[dict]:
    # Fetch triggers first to resolve IDs to names
    triggers = (
        service.accounts()
        .containers()
        .workspaces()
        .triggers()
        .list(parent=workspace_path)
        .execute()
        .get("trigger", [])
    )
    trigger_map = {t["triggerId"]: t.get("name", t["triggerId"]) for t in triggers}

    tags = (
        service.accounts()
        .containers()
        .workspaces()
        .tags()
        .list(parent=workspace_path)
        .execute()
        .get("tag", [])
    )
    rows = []
    for tag in tags:
        firing = [trigger_map.get(tid, tid) for tid in tag.get("firingTriggerId", [])]
        blocking = [trigger_map.get(tid, tid) for tid in tag.get("blockingTriggerId", [])]
        params = tag.get("parameter", [])
        measurement_id = _extract_param(params, "measurementId") or _extract_param(params, "trackingId")
        row = {
            "tag_id": tag["tagId"],
            "name": tag.get("name", ""),
            "type": tag.get("type", ""),
            "firing_triggers": ", ".join(firing) if firing else "",
            "blocking_triggers": ", ".join(blocking) if blocking else "",
            "paused": str(tag.get("paused", False)),
        }
        if measurement_id:
            row["measurement_id"] = measurement_id
        rows.append(row)
    return rows


def list_triggers(service, workspace_path: str) -> list[dict]:
    triggers = (
        service.accounts()
        .containers()
        .workspaces()
        .triggers()
        .list(parent=workspace_path)
        .execute()
        .get("trigger", [])
    )
    rows = []
    for t in triggers:
        # Build a brief filter summary from conditions
        filters = []
        for f in t.get("filter", []) or []:
            param = f.get("parameter", [])
            if len(param) >= 2:
                filters.append(f"{param[0].get('value', '')} {f.get('type', '')} {param[1].get('value', '')}")
        for f in t.get("customEventFilter", []) or []:
            param = f.get("parameter", [])
            if len(param) >= 2:
                filters.append(f"{param[0].get('value', '')} {f.get('type', '')} {param[1].get('value', '')}")

        rows.append({
            "trigger_id": t["triggerId"],
            "name": t.get("name", ""),
            "type": t.get("type", ""),
            "filter": "; ".join(filters) if filters else "",
        })
    return rows


def list_variables(service, workspace_path: str) -> list[dict]:
    variables = (
        service.accounts()
        .containers()
        .workspaces()
        .variables()
        .list(parent=workspace_path)
        .execute()
        .get("variable", [])
    )
    rows = []
    for v in variables:
        rows.append({
            "variable_id": v["variableId"],
            "name": v.get("name", ""),
            "type": v.get("type", ""),
        })
    return rows


def list_built_in_variables(service, workspace_path: str) -> list[dict]:
    result = (
        service.accounts()
        .containers()
        .workspaces()
        .built_in_variables()
        .list(parent=workspace_path)
        .execute()
        .get("builtInVariable", [])
    )
    rows = []
    for v in result:
        rows.append({
            "name": v.get("name", ""),
            "type": v.get("type", ""),
        })
    return rows


def list_folders(service, workspace_path: str) -> list[dict]:
    folders = (
        service.accounts()
        .containers()
        .workspaces()
        .folders()
        .list(parent=workspace_path)
        .execute()
        .get("folder", [])
    )
    rows = []
    for f in folders:
        rows.append({
            "folder_id": f["folderId"],
            "name": f.get("name", ""),
        })
    return rows


def get_version(service, container_path: str) -> list[dict]:
    version = (
        service.accounts()
        .containers()
        .versions()
        .live(parent=container_path)
        .execute()
    )
    return [{
        "version": version.get("containerVersionId", ""),
        "name": version.get("name", ""),
        "description": version.get("description", ""),
        "fingerprint": version.get("fingerprint", ""),
        "tag_count": len(version.get("tag", [])),
        "trigger_count": len(version.get("trigger", [])),
        "variable_count": len(version.get("variable", [])),
    }]


def main():
    gtm_cfg = config.service_config("google_tag_manager")
    default_account = gtm_cfg.get("default_account", "")
    default_container = gtm_cfg.get("default_container", "")

    parser = argparse.ArgumentParser(description="Query Google Tag Manager")
    parser.add_argument(
        "--action",
        required=True,
        choices=ACTIONS,
        help="Action to perform",
    )
    parser.add_argument(
        "--account",
        default=default_account or None,
        required=not bool(default_account),
        help="GTM account ID. Defaults to config.",
    )
    parser.add_argument(
        "--container",
        default=default_container or None,
        help="GTM container ID. Defaults to config.",
    )
    parser.add_argument(
        "--workspace",
        default=None,
        help="Workspace ID. Auto-detects default if not specified.",
    )
    parser.add_argument(
        "--format",
        default="table",
        choices=["table", "csv", "json"],
        help="Output format (default: table)",
    )
    args = parser.parse_args()

    service = _get_service()
    account_path = f"accounts/{args.account}"

    # Actions that only need account
    if args.action == "list-containers":
        rows = list_containers(service, account_path)
        _output(rows, args.format)
        return

    # All other actions need container
    if not args.container:
        print("Error: --container required (or set default_container in config).", file=sys.stderr)
        sys.exit(1)

    container_path = f"{account_path}/containers/{args.container}"

    # get-version works at the container level (no workspace needed)
    if args.action == "get-version":
        rows = get_version(service, container_path)
        _output(rows, args.format)
        return

    # Remaining actions need a workspace
    workspace_id = args.workspace or _get_default_workspace(service, container_path)
    workspace_path = f"{container_path}/workspaces/{workspace_id}"

    action_map = {
        "list-workspaces": lambda: list_workspaces(service, container_path),
        "list-tags": lambda: list_tags(service, workspace_path),
        "list-triggers": lambda: list_triggers(service, workspace_path),
        "list-variables": lambda: list_variables(service, workspace_path),
        "list-built-in-variables": lambda: list_built_in_variables(service, workspace_path),
        "list-folders": lambda: list_folders(service, workspace_path),
    }

    rows = action_map[args.action]()
    _output(rows, args.format)


if __name__ == "__main__":
    main()
