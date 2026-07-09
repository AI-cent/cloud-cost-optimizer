"""
AWS Billing CSV Parser
Accepts a CSV with columns:
  ResourceId, ResourceName, ResourceType, Region, MonthlyCost, Status, LastActiveDate

Parses each row and upserts into the `resources` table.
Bad rows are skipped with a warning — never crashes on a single bad row.
Returns (upserted_list, skipped_count).
"""
import csv
import io
import logging
from datetime import datetime
from typing import List, Tuple

from sqlalchemy.orm import Session
from models import Resource

logger = logging.getLogger(__name__)

REQUIRED_COLUMNS = {
    "ResourceId", "ResourceName", "ResourceType",
    "Region", "MonthlyCost", "Status", "LastActiveDate",
}

DATE_FORMATS = ("%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y", "%d-%m-%Y")


def _parse_date(raw: str) -> datetime | None:
    """Try multiple date formats; return None if all fail."""
    raw = raw.strip()
    if not raw:
        return None
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    logger.warning("Unrecognised date format '%s' — treating as None", raw)
    return None


def _parse_cost(raw: str, resource_id: str) -> float:
    """Parse cost to float; default to 0.0 on error."""
    try:
        return float(raw.strip())
    except (ValueError, AttributeError):
        logger.warning("Invalid MonthlyCost '%s' for resource '%s' — defaulting to 0.0", raw, resource_id)
        return 0.0


def parse_and_ingest(file_content: bytes, db: Session) -> Tuple[List[Resource], int]:
    """
    Parse CSV bytes and upsert resources.

    Returns:
        (upserted_resources, skipped_row_count)

    Raises:
        ValueError  — if file is empty or required columns are missing entirely
        UnicodeDecodeError — if file is not valid UTF-8
    """
    try:
        text = file_content.decode("utf-8")
    except UnicodeDecodeError as e:
        raise ValueError(f"File is not valid UTF-8: {e}") from e

    reader = csv.DictReader(io.StringIO(text))

    if not reader.fieldnames:
        raise ValueError("CSV file is empty or has no header row.")

    # Strip BOM / whitespace from header names
    cleaned_headers = {f.strip().lstrip("﻿") for f in reader.fieldnames}
    missing = REQUIRED_COLUMNS - cleaned_headers
    if missing:
        raise ValueError(
            f"CSV is missing required columns: {sorted(missing)}. "
            f"Found: {sorted(cleaned_headers)}"
        )

    upserted: List[Resource] = []
    skipped = 0

    for row_num, row in enumerate(reader, start=2):  # start=2 (row 1 = header)
        # ── Validate ResourceId ────────────────────────────────────────────
        resource_id = (row.get("ResourceId") or "").strip()
        if not resource_id:
            logger.warning("Row %d: empty ResourceId — skipping", row_num)
            skipped += 1
            continue

        # ── Parse fields safely ───────────────────────────────────────────
        try:
            monthly_cost = _parse_cost(row.get("MonthlyCost", "0"), resource_id)
            last_active = _parse_date(row.get("LastActiveDate", ""))
            resource_name = (row.get("ResourceName") or resource_id).strip()
            resource_type = (row.get("ResourceType") or "Unknown").strip()
            region = (row.get("Region") or "unknown").strip()
            status = (row.get("Status") or "").strip()

        except Exception as exc:
            logger.warning("Row %d (resource '%s'): unexpected parse error — %s — skipping",
                           row_num, resource_id, exc)
            skipped += 1
            continue

        # ── Upsert ────────────────────────────────────────────────────────
        try:
            existing = db.query(Resource).filter(Resource.resource_id == resource_id).first()
            if existing:
                existing.resource_name = resource_name
                existing.resource_type = resource_type
                existing.region = region
                existing.monthly_cost_usd = monthly_cost
                existing.status = status
                existing.last_active_date = last_active
                existing.ingest_timestamp = datetime.utcnow()
                upserted.append(existing)
            else:
                resource = Resource(
                    resource_id=resource_id,
                    resource_name=resource_name,
                    resource_type=resource_type,
                    region=region,
                    monthly_cost_usd=monthly_cost,
                    status=status,
                    last_active_date=last_active,
                    ingest_timestamp=datetime.utcnow(),
                )
                db.add(resource)
                upserted.append(resource)

        except Exception as exc:
            logger.warning("Row %d (resource '%s'): DB upsert error — %s — skipping",
                           row_num, resource_id, exc)
            db.rollback()
            skipped += 1
            continue

    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        raise ValueError(f"Database commit failed: {exc}") from exc

    for r in upserted:
        try:
            db.refresh(r)
        except Exception:
            pass  # non-fatal; ID already assigned

    if skipped:
        logger.warning("Ingestion complete: %d rows upserted, %d rows skipped.", len(upserted), skipped)
    else:
        logger.info("Ingestion complete: %d rows upserted, 0 skipped.", len(upserted))

    return upserted, skipped
