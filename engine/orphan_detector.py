"""
Orphan Detection Engine
Implements 5 rules against the resources table.
Each rule runs in its own try/except — one failure never stops the others.
"""
import logging
from datetime import datetime, timedelta
from typing import List

from sqlalchemy.orm import Session
from models import Resource, Finding, RemediationCommand
from engine.remediation import generate_command

logger = logging.getLogger(__name__)

IDLE_EC2_DAYS = 30
OLD_SNAPSHOT_DAYS = 90


def _clear_existing_findings(resource_id: str, db: Session):
    """Remove stale findings for a resource before re-detecting."""
    try:
        db.query(Finding).filter(Finding.resource_id == resource_id).delete()
        db.flush()
    except Exception as exc:
        logger.error("Failed to clear findings for '%s': %s", resource_id, exc)
        db.rollback()


def _apply_rule_1_unattached_ebs(resource: Resource, now: datetime) -> Finding | None:
    """Unattached EBS Volume: status = 'available' → High"""
    if resource.resource_type == "EBS Volume" and resource.status == "available":
        return Finding(
            resource_id=resource.resource_id,
            finding_type="unattached_ebs",
            severity="High",
            estimated_monthly_waste_usd=resource.monthly_cost_usd,
            detected_at=now,
        )
    return None


def _apply_rule_2_idle_ec2(resource: Resource, now: datetime) -> Finding | None:
    """Idle EC2: last_active_date older than 30 days → Critical"""
    if resource.resource_type != "EC2 Instance":
        return None
    if not resource.last_active_date:
        logger.warning("EC2 '%s' has no last_active_date — skipping idle check", resource.resource_id)
        return None
    if (now - resource.last_active_date) > timedelta(days=IDLE_EC2_DAYS):
        return Finding(
            resource_id=resource.resource_id,
            finding_type="idle_ec2",
            severity="Critical",
            estimated_monthly_waste_usd=resource.monthly_cost_usd,
            detected_at=now,
        )
    return None


def _apply_rule_3_orphaned_eip(resource: Resource, now: datetime) -> Finding | None:
    """Orphaned Elastic IP: status = 'unassociated' → Medium"""
    if resource.resource_type == "Elastic IP" and resource.status == "unassociated":
        return Finding(
            resource_id=resource.resource_id,
            finding_type="orphaned_eip",
            severity="Medium",
            estimated_monthly_waste_usd=resource.monthly_cost_usd,
            detected_at=now,
        )
    return None


def _apply_rule_4_idle_alb(resource: Resource, now: datetime) -> Finding | None:
    """Idle Load Balancer: status = 'idle' → High"""
    if resource.resource_type == "Load Balancer" and resource.status == "idle":
        return Finding(
            resource_id=resource.resource_id,
            finding_type="idle_alb",
            severity="High",
            estimated_monthly_waste_usd=resource.monthly_cost_usd,
            detected_at=now,
        )
    return None


def _apply_rule_5_old_snapshot(resource: Resource, now: datetime) -> Finding | None:
    """Old Snapshot: last_active_date older than 90 days → Low"""
    if resource.resource_type != "Snapshot":
        return None
    if not resource.last_active_date:
        logger.warning("Snapshot '%s' has no last_active_date — skipping age check", resource.resource_id)
        return None
    if (now - resource.last_active_date) > timedelta(days=OLD_SNAPSHOT_DAYS):
        return Finding(
            resource_id=resource.resource_id,
            finding_type="old_snapshot",
            severity="Low",
            estimated_monthly_waste_usd=resource.monthly_cost_usd,
            detected_at=now,
        )
    return None


RULES = [
    _apply_rule_1_unattached_ebs,
    _apply_rule_2_idle_ec2,
    _apply_rule_3_orphaned_eip,
    _apply_rule_4_idle_alb,
    _apply_rule_5_old_snapshot,
]


def detect_all(db: Session) -> List[Finding]:
    """
    Run all 5 detection rules over every resource.
    Each rule is isolated — one failure never blocks others.
    Returns list of new Finding objects persisted to DB.
    """
    try:
        resources: List[Resource] = db.query(Resource).all()
    except Exception as exc:
        logger.error("Failed to fetch resources from DB: %s", exc)
        return []

    new_findings: List[Finding] = []
    now = datetime.utcnow()

    for resource in resources:
        _clear_existing_findings(resource.resource_id, db)
        resource_finding = None

        for rule_fn in RULES:
            try:
                finding = rule_fn(resource, now)
                if finding:
                    resource_finding = finding
                    break  # one finding per resource — take the first match
            except Exception as exc:
                logger.error(
                    "Rule '%s' failed on resource '%s': %s",
                    rule_fn.__name__, resource.resource_id, exc
                )
                continue  # never let one rule crash the loop

        if resource_finding:
            try:
                db.add(resource_finding)
                db.flush()  # get finding.id before generating command

                cmd: RemediationCommand = generate_command(
                    finding=resource_finding, resource=resource
                )
                db.add(cmd)
                new_findings.append(resource_finding)

            except Exception as exc:
                logger.error(
                    "Failed to persist finding for resource '%s': %s",
                    resource.resource_id, exc
                )
                db.rollback()
                continue

    try:
        db.commit()
    except Exception as exc:
        logger.error("Failed to commit findings to DB: %s", exc)
        db.rollback()
        return []

    for f in new_findings:
        try:
            db.refresh(f)
        except Exception:
            pass  # non-fatal

    logger.info("Detection complete: %d findings generated across %d resources.",
                len(new_findings), len(resources))
    return new_findings
