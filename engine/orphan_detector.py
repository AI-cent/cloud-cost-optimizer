"""
Orphan Detection Engine
Implements 5 rules against the resources table.
Writes findings + remediation_commands to DB.
"""
from datetime import datetime, timedelta
from typing import List

from sqlalchemy.orm import Session
from models import Resource, Finding, RemediationCommand
from engine.remediation import generate_command


IDLE_EC2_DAYS = 30
OLD_SNAPSHOT_DAYS = 90


def _clear_existing_findings(resource_id: str, db: Session):
    """Remove stale findings for a resource before re-detecting."""
    db.query(Finding).filter(Finding.resource_id == resource_id).delete()
    db.flush()


def detect_all(db: Session) -> List[Finding]:
    """Run all 5 detection rules. Returns list of new Finding objects."""
    resources: List[Resource] = db.query(Resource).all()
    new_findings: List[Finding] = []
    now = datetime.utcnow()

    for r in resources:
        _clear_existing_findings(r.resource_id, db)
        finding = None

        # Rule 1: Unattached EBS Volume
        if r.resource_type == "EBS Volume" and r.status == "available":
            finding = Finding(
                resource_id=r.resource_id,
                finding_type="unattached_ebs",
                severity="High",
                estimated_monthly_waste_usd=r.monthly_cost_usd,
                detected_at=now,
            )

        # Rule 2: Idle EC2 Instance
        elif r.resource_type == "EC2 Instance":
            if r.last_active_date and (now - r.last_active_date) > timedelta(days=IDLE_EC2_DAYS):
                finding = Finding(
                    resource_id=r.resource_id,
                    finding_type="idle_ec2",
                    severity="Critical",
                    estimated_monthly_waste_usd=r.monthly_cost_usd,
                    detected_at=now,
                )

        # Rule 3: Orphaned Elastic IP
        elif r.resource_type == "Elastic IP" and r.status == "unassociated":
            finding = Finding(
                resource_id=r.resource_id,
                finding_type="orphaned_eip",
                severity="Medium",
                estimated_monthly_waste_usd=r.monthly_cost_usd,
                detected_at=now,
            )

        # Rule 4: Idle Load Balancer
        elif r.resource_type == "Load Balancer" and r.status == "idle":
            finding = Finding(
                resource_id=r.resource_id,
                finding_type="idle_alb",
                severity="High",
                estimated_monthly_waste_usd=r.monthly_cost_usd,
                detected_at=now,
            )

        # Rule 5: Old Snapshot
        elif r.resource_type == "Snapshot":
            if r.last_active_date and (now - r.last_active_date) > timedelta(days=OLD_SNAPSHOT_DAYS):
                finding = Finding(
                    resource_id=r.resource_id,
                    finding_type="old_snapshot",
                    severity="Low",
                    estimated_monthly_waste_usd=r.monthly_cost_usd,
                    detected_at=now,
                )

        if finding:
            db.add(finding)
            db.flush()  # get finding.id
            cmd = generate_command(finding=finding, resource=r)
            db.add(cmd)
            new_findings.append(finding)

    db.commit()
    for f in new_findings:
        db.refresh(f)

    return new_findings
