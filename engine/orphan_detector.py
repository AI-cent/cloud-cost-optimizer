"""
Orphan detection engine — 5 rules.
Operates on Resource ORM objects and writes Finding + RemediationCommand rows.
"""
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
import models
from engine.remediation import generate_cli_command


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _days_old(dt: datetime | None) -> float:
    if dt is None:
        return float("inf")
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return (_now() - dt).days


def _upsert_finding(
    db: Session,
    resource: models.Resource,
    finding_type: str,
    severity: str,
) -> models.Finding:
    """Create or return existing finding for this resource+type."""
    existing = (
        db.query(models.Finding)
        .filter(
            models.Finding.resource_id == resource.id,
            models.Finding.finding_type == finding_type,
        )
        .first()
    )
    if existing:
        return existing

    finding = models.Finding(
        resource_id=resource.id,
        finding_type=finding_type,
        severity=severity,
        estimated_monthly_waste_usd=resource.monthly_cost_usd,
        status="pending",
        detected_at=_now(),
    )
    db.add(finding)
    db.flush()  # get finding.id without full commit

    # Generate CLI command
    cmd_text = generate_cli_command(resource)
    if cmd_text:
        cmd = models.RemediationCommand(
            finding_id=finding.id,
            command_type="aws_cli",
            command_text=cmd_text,
        )
        db.add(cmd)

    return finding


def run_detection(db: Session, resources: list[models.Resource]) -> int:
    """
    Run all 5 orphan detection rules against the given resources.
    Returns count of new findings created.
    """
    count = 0

    for r in resources:
        rtype = (r.resource_type or "").strip()
        status = (r.status or "").strip().lower()

        # Rule 1 — Unattached EBS Volume
        if rtype == "EBS Volume" and status == "available":
            _upsert_finding(db, r, "unattached_ebs", "High")
            count += 1

        # Rule 2 — Idle EC2 Instance (last active > 30 days)
        elif rtype == "EC2 Instance" and _days_old(r.last_active_date) > 30:
            _upsert_finding(db, r, "idle_ec2", "Critical")
            count += 1

        # Rule 3 — Orphaned Elastic IP
        elif rtype == "Elastic IP" and status == "unassociated":
            _upsert_finding(db, r, "orphaned_eip", "Medium")
            count += 1

        # Rule 4 — Idle Load Balancer
        elif rtype == "Load Balancer" and status == "idle":
            _upsert_finding(db, r, "idle_alb", "High")
            count += 1

        # Rule 5 — Old Snapshot (last active > 90 days)
        elif rtype == "Snapshot" and _days_old(r.last_active_date) > 90:
            _upsert_finding(db, r, "old_snapshot", "Low")
            count += 1

    db.commit()
    return count
