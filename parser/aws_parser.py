import csv
import io
from datetime import datetime
from typing import List, Dict, Any


REQUIRED_COLUMNS = {
    "resource_id", "resource_name", "resource_type",
    "region", "monthly_cost_usd", "status", "last_active_date"
}


def parse_aws_csv(file_content: bytes) -> List[Dict[str, Any]]:
    """
    Parse AWS Cost and Usage Report CSV.
    Returns a list of resource dicts ready for DB insertion.
    """
    text = file_content.decode("utf-8", errors="replace")
    reader = csv.DictReader(io.StringIO(text))

    # Normalize headers: strip whitespace, lowercase
    if reader.fieldnames is None:
        raise ValueError("CSV file is empty or has no header row.")

    normalized_headers = [h.strip().lower().replace(" ", "_") for h in reader.fieldnames]
    missing = REQUIRED_COLUMNS - set(normalized_headers)
    if missing:
        raise ValueError(f"CSV missing required columns: {missing}")

    resources = []
    for row in reader:
        # Re-key with normalized names
        normalized_row = {
            h.strip().lower().replace(" ", "_"): v.strip()
            for h, v in row.items()
            if h is not None
        }

        # Parse last_active_date — accept multiple formats
        last_active_date = None
        raw_date = normalized_row.get("last_active_date", "")
        if raw_date:
            for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
                try:
                    last_active_date = datetime.strptime(raw_date, fmt)
                    break
                except ValueError:
                    continue

        # Parse monthly cost
        try:
            monthly_cost = float(normalized_row.get("monthly_cost_usd", "0") or "0")
        except ValueError:
            monthly_cost = 0.0

        resource = {
            "resource_id": normalized_row.get("resource_id", ""),
            "resource_name": normalized_row.get("resource_name", ""),
            "resource_type": normalized_row.get("resource_type", ""),
            "region": normalized_row.get("region", "us-east-1"),
            "monthly_cost_usd": monthly_cost,
            "status": normalized_row.get("status", ""),
            "last_active_date": last_active_date,
        }

        if resource["resource_id"]:
            resources.append(resource)

    return resources
