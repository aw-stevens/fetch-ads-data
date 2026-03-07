"""Shared config loader for ad-analytics plugin."""

import json
import sys
from pathlib import Path

CONFIG_FILE = Path.home() / ".ad-analytics" / "config.json"


def load_config() -> dict:
    if not CONFIG_FILE.exists():
        print(f"Error: {CONFIG_FILE} not found. Run ad-analytics setup.", file=sys.stderr)
        sys.exit(1)
    return json.loads(CONFIG_FILE.read_text())


def service_config(service: str) -> dict:
    return load_config().get(service, {})


def default_id(service: str) -> str:
    cfg = service_config(service)
    return cfg.get("default_account") or cfg.get("default_property") or ""


def resolve_id(service: str, name_or_id: str) -> str:
    """Resolve a friendly name OR raw ID to a raw ID."""
    cfg = service_config(service)
    mapping = cfg.get("accounts") or cfg.get("properties") or {}
    # Check if it's already a raw ID
    if name_or_id in mapping:
        return name_or_id
    # Check if it's a friendly name (reverse lookup)
    reverse = {v.lower(): k for k, v in mapping.items()}
    return reverse.get(name_or_id.lower(), name_or_id)


def credentials_path(service: str) -> str:
    cfg = service_config(service)
    path = cfg.get("credentials", "")
    return str(Path(path).expanduser()) if path else ""


def account_list(service: str) -> dict:
    """Return {id: name} mapping for a service."""
    cfg = service_config(service)
    return cfg.get("accounts") or cfg.get("properties") or {}
