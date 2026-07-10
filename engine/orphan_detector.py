import logging
import re
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from models import Resource, Finding, RemediationCommand

logger = logging.getLogger(__name__)

_SAFE_RESOURCE_ID = re.compile(r"[^A-Za-z0-9\-_:/]")
_SAFE_REGION      = re.compile(r"[^A-Za-z0-9\-]")


def _sanitize_resource_id(value: str) -> str:
    """Keep only alphanumeric, hyphens, underscores, colons, and forward-slashes (for ARNs)."""
    return _SAFE_RESOURCE_ID.sub("", value or "")


def _sanitize_region(value: str) -> str:
    """Keep only letters, numbers, and hyphens (e.g. us-east-1)."""
    return _SAFE_REGION.sub("", value or "")


RULES = [
    {
        "finding_type": "unattached_ebs",
        "resource_type": "EBS Volume",
        "severity": "High",
        "condition": lambda r: r.status and r.status.lower() == "available",
    },
    {
        "finding_type": "idle_ec2",
        "resource_type": "EC2 Instance",
        "severity": "Critical",
        "condition": lambda r: (
            r.last_active_date is not None
            and r.last_active_date < datetime.utcnow() - timedelta(days=30)
        ),
    },
    {
        "finding_type": "orphaned_eip",
        "resource_type": "Elastic IP",
        "severity": "Medium",
        "condition": lambda r: r.status and r.status.lower() == "unassociated",
    },
    {
        "finding_type": "idle_alb",
        "resource_type": "Load Balancer",
        "severity": "High",
        "condition": lambda r: r.status and r.status.lower() == "idle",
    },
    {
        "finding_type": "old_snapshot",
        "resource_type": "Snapshot",
        "severity": "Low",
        "condition": lambda r: (
            r.last_active_date is not None
            and r.last_active_date < datetime.utcnow() - timedelta(days=90)
        ),
    },
]

CLI_TEMPLATES = {
    "EBS Volume": "aws ec2 delete-volume --volume-id {resource_id} --region {region}",
    "EC2 Instance": "aws ec2 stop-instances --instance-ids {resource_id} --region {region}",
    "Elastic IP": "aws ec2 release-address --allocation-id {resource_id} --region {region}",
    "Load Balancer": "aws elbv2 delete-load-balancer --load-balancer-arn {resource_id}",
    "Snapshot": "aws ec2 delete-snapshot --snapshot-id {resource_id} --region {region}",
}


def run_detection(db: Session, resource_ids: list) -> int:
    """
    Run all 5 orphan detection rules against newly ingested resources.
    Creates Finding and RemediationCommand records.
    Returns number of findings created.
    """
    resources = db.query(Resource).filter(Resource.id.in_(resource_ids)).all()
    findings_created = 0

    for resource in resources:
        for rule in RULES:
            try:
                if resource.resource_type != rule["resource_type"]:
                    continue
                if not rule["condition"](resource):
                    continue

                # Avoid duplicate findings for same resource + finding_type
                existing = db.query(Finding).filter(
                    Finding.resource_id == resource.id,
                    Finding.finding_type == rule["finding_type"],
                    Finding.status == "pending",
                ).first()
                if existing:
                    continue

                finding = Finding(
                    resource_id=resource.id,
                    finding_type=rule["finding_type"],
                    severity=rule["severity"],
                    estimated_monthly_waste_usd=resource.monthly_cost_usd,
                    status="pending",
                )
                db.add(finding)
                db.flush()

                cli_template = CLI_TEMPLATES.get(resource.resource_type, "")
                cli_command = cli_template.format(
                    resource_id=_sanitize_resource_id(resource.resource_id),
                    region=_sanitize_region(resource.region),
                )
                cmd = RemediationCommand(
                    finding_id=finding.id,
                    command_type="aws_cli",
                    command_text=cli_command,
                )
                db.add(cmd)
                findings_created += 1

            except Exception as exc:
                logger.warning(
                    "Rule %r failed for resource %r: %s — skipping.",
                    rule.get("finding_type"), resource.resource_id, exc
                )
                db.rollback()

    db.commit()
    return findings_created
