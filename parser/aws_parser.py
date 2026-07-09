"""
Parse AWS Cost and Usage Report CSV exports.

Expected columns (flexible — maps common AWS CUR column names):
  resource_id, resource_name, resource_type, region,
  monthly_cost_usd, status, last_active_date
"""
import csv
import io
from datetime import datetime


COLUMN_ALIASES = {
    "resource_id":        ["resource_id", "resourceid", "resource id", "lineitem/resourceid"],
    "resource_name":      ["resource_name", "resourcename", "resource name", "resourcetags/user:name"],
    "resource_type":      ["resource_type", "resourcetype", "resource type", "lineitem/productcode", "product/productname"],
    "region":             ["region", "product/region", "lineitem/availabilityzone"],
    "monthly_cost_usd":   ["monthly_cost_usd", "monthlycostusd", "lineitem/unblendedcost", "cost"],
    "status":             ["status", "resource_status"],
    "last_active_date":   ["last_active_date", "lastactivedate", "last active date"],
}


def _resolve_header(headers: list[str]) -> dict[str, str]:
    """Return mapping canonical_name -> actual CSV header."""
    lower_headers = {h.lower().strip(): h for h in headers}
    resolved = {}
    for canonical, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            if alias.lower() in lower_headers:
                resolved[canonical] = lower_headers[alias.lower()]
                break
    return resolved


def _parse_date(val: str) -> datetime | None:
    if not val or val.strip() == "":
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(val.strip(), fmt)
        except ValueError:
            continue
    return None


def parse_aws_csv(content: bytes) -> list[dict]:
    """
    Parse raw CSV bytes.
    Returns list of dicts with canonical keys ready for DB insertion.
    """
    text = content.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    headers = reader.fieldnames or []
    col_map = _resolve_header(list(headers))

    rows = []
    for row in reader:
        def get(key: str, default="") -> str:
            col = col_map.get(key)
            return row.get(col, default).strip() if col else default

        resource_id = get("resource_id")
        if not resource_id:
            continue  # skip rows with no resource ID

        try:
            cost = float(get("monthly_cost_usd", "0") or "0")
        except ValueError:
            cost = 0.0

        rows.append({
            "resource_id":       resource_id,
            "resource_name":     get("resource_name") or resource_id,
            "resource_type":     get("resource_type", "Unknown"),
            "region":            get("region", "us-east-1"),
            "monthly_cost_usd":  cost,
            "status":            get("status", "unknown"),
            "last_active_date":  _parse_date(get("last_active_date")),
        })

    return rows
