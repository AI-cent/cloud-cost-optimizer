import csv
import io
import re
from datetime import datetime
from typing import List, Dict, Any


# Canonical field name → list of accepted aliases (all lowercased, stripped)
COLUMN_ALIASES = {
    "resource_id":       ["resource_id", "resourceid"],
    "resource_name":     ["resource_name", "resourcename"],
    "resource_type":     ["resource_type", "resourcetype"],
    "region":            ["region"],
    "monthly_cost_usd":  ["monthly_cost_usd", "monthlycost", "monthly_cost", "cost_usd", "cost"],
    "status":            ["status"],
    "last_active_date":  ["last_active_date", "lastactivedate", "last_active"],
}


def _normalize_header(h: str) -> str:
    """Lowercase, strip, collapse spaces/underscores."""
    return h.strip().lower().replace(" ", "_")


def _build_alias_map(headers: list) -> Dict[str, str]:
    """
    Map each normalized CSV header → canonical field name.
    Returns {normalized_csv_header: canonical_name}.
    """
    alias_map = {}
    for canonical, aliases in COLUMN_ALIASES.items():
        for h in headers:
            norm = _normalize_header(h)
            if norm in aliases:
                alias_map[norm] = canonical
    return alias_map


def parse_aws_csv(file_content: bytes) -> List[Dict[str, Any]]:
    """
    Parse AWS Cost and Usage Report CSV.
    Accepts both snake_case and CamelCase column names.
    Returns a list of resource dicts ready for DB insertion.
    """
    text = file_content.decode("utf-8", errors="replace")
    reader = csv.DictReader(io.StringIO(text))

    if reader.fieldnames is None:
        raise ValueError("CSV file is empty or has no header row.")

    alias_map = _build_alias_map(reader.fieldnames)
    resolved_canonicals = set(alias_map.values())
    required = set(COLUMN_ALIASES.keys())
    missing = required - resolved_canonicals
    if missing:
        raise ValueError(
            f"CSV missing required columns: {missing}. "
            f"Got headers: {list(reader.fieldnames)}"
        )

    resources = []
    for row in reader:
        # Re-key: normalized CSV header → canonical name
        canonical_row = {}
        for h, v in row.items():
            if h is None:
                continue
            norm = _normalize_header(h)
            canonical = alias_map.get(norm)
            if canonical:
                canonical_row[canonical] = (v or "").strip()

        # Parse last_active_date — accept multiple formats
        last_active_date = None
        raw_date = canonical_row.get("last_active_date", "")
        if raw_date:
            for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
                try:
                    last_active_date = datetime.strptime(raw_date, fmt)
                    break
                except ValueError:
                    continue

        # Parse monthly cost — strip currency symbols
        raw_cost = re.sub(r"[^\d.]", "", canonical_row.get("monthly_cost_usd", "0") or "0")
        try:
            monthly_cost = float(raw_cost)
        except ValueError:
            monthly_cost = 0.0

        resource = {
            "resource_id":      canonical_row.get("resource_id", ""),
            "resource_name":    canonical_row.get("resource_name", ""),
            "resource_type":    canonical_row.get("resource_type", ""),
            "region":           canonical_row.get("region", "us-east-1"),
            "monthly_cost_usd": monthly_cost,
            "status":           canonical_row.get("status", ""),
            "last_active_date": last_active_date,
        }

        if resource["resource_id"]:
            resources.append(resource)

    return resources
