"""
AWS Billing CSV Parser
Accepts a CSV with columns:
  ResourceId, ResourceName, ResourceType, Region, MonthlyCost, Status, LastActiveDate

Parses each row and upserts into the `resources` table.
Returns the list of Resource ORM objects created/updated.
"""
import csv
import io
from datetime import datetime
from typing import List

from sqlalchemy.orm import Session
from models import Resource


EXPECTED_COLUMNS = {
    "ResourceId", "ResourceName", "ResourceType",
    "Region", "MonthlyCost", "Status", "LastActiveDate",
}


def parse_and_ingest(file_content: bytes, db: Session) -> List[Resource]:
    text = file_content.decode("utf-8")
    reader = csv.DictReader(io.StringIO(text))

    # Validate headers
    if not reader.fieldnames:
        raise ValueError("CSV file is empty or has no headers.")
    missing = EXPECTED_COLUMNS - {f.strip() for f in reader.fieldnames}
    if missing:
        raise ValueError(f"CSV missing required columns: {missing}")

    upserted: List[Resource] = []

    for row in reader:
        resource_id = row["ResourceId"].strip()
        if not resource_id:
            continue

        # Parse last_active_date (accept YYYY-MM-DD or blank)
        raw_date = row.get("LastActiveDate", "").strip()
        last_active = None
        if raw_date:
            for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y"):
                try:
                    last_active = datetime.strptime(raw_date, fmt)
                    break
                except ValueError:
                    continue

        monthly_cost = 0.0
        try:
            monthly_cost = float(row["MonthlyCost"].strip())
        except (ValueError, KeyError):
            pass

        # Upsert: update if exists, insert if new
        existing = db.query(Resource).filter(Resource.resource_id == resource_id).first()
        if existing:
            existing.resource_name = row["ResourceName"].strip()
            existing.resource_type = row["ResourceType"].strip()
            existing.region = row["Region"].strip()
            existing.monthly_cost_usd = monthly_cost
            existing.status = row["Status"].strip()
            existing.last_active_date = last_active
            existing.ingest_timestamp = datetime.utcnow()
            upserted.append(existing)
        else:
            resource = Resource(
                resource_id=resource_id,
                resource_name=row["ResourceName"].strip(),
                resource_type=row["ResourceType"].strip(),
                region=row["Region"].strip(),
                monthly_cost_usd=monthly_cost,
                status=row["Status"].strip(),
                last_active_date=last_active,
                ingest_timestamp=datetime.utcnow(),
            )
            db.add(resource)
            upserted.append(resource)

    db.commit()

    # Refresh all to get IDs
    for r in upserted:
        db.refresh(r)

    return upserted
