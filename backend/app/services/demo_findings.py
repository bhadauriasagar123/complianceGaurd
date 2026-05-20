"""Curated findings for known intentionally-vulnerable practice applications."""

import json
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

_DATA_PATH = Path(__file__).resolve().parents[2] / "data" / "demo_findings.json"


@lru_cache
def _load_catalog() -> dict[str, Any]:
    if not _DATA_PATH.exists():
        return {"host_groups": []}
    with _DATA_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def host_matches_pattern(hostname: str, pattern: str) -> bool:
    hostname = hostname.lower().strip(".")
    pattern = pattern.lower().strip(".")
    if pattern.startswith("*."):
        suffix = pattern[2:]
        return hostname == suffix or hostname.endswith(f".{suffix}")
    return hostname == pattern or hostname.endswith(f".{pattern}")


def get_demo_findings_for_target(target: str) -> list[dict[str, Any]]:
    """
    Return supplemental findings when the target is a known practice / demo application.
    Only used in mock/cloud mode — not a substitute for authorized real scanning.
    """
    if target.startswith(("http://", "https://")):
        host = urlparse(target).hostname or target
    else:
        host = target.split("/")[0]

    if not host:
        return []

    catalog = _load_catalog()
    matched: list[dict[str, Any]] = []
    for group in catalog.get("host_groups", []):
        patterns = group.get("patterns", [])
        if any(host_matches_pattern(host, p) for p in patterns):
            for item in group.get("findings", []):
                finding = dict(item)
                finding.setdefault("scanner", "demo_catalog")
                finding["affected_asset"] = finding.get("affected_asset") or host
                matched.append(finding)

    return matched
