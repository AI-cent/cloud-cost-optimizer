"""
Remediation Command Generator
Maps finding_type → AWS CLI command string.
Handles missing/malformed resource IDs gracefully.
"""
import logging
from datetime import datetime
from models import Finding, Resource, RemediationCommand

logger = logging.getLogger(__name__)

TEMPLATES = {
    "unattached_ebs": "aws ec2 delete-volume --volume-id {resource_id} --region {region}",
    "idle_ec2":       "aws ec2 stop-instances --instance-ids {resource_id} --region {region}",
    "orphaned_eip":   "aws ec2 release-address --allocation-id {resource_id} --region {region}",
    "idle_alb":       "aws elbv2 delete-load-balancer --load-balancer-arn {resource_id}",
    "old_snapshot":   "aws ec2 delete-snapshot --snapshot-id {resource_id} --region {region}",
}

FALLBACK_COMMAND = "# No remediation command available for finding_type='{finding_type}'"


def _sanitise(value: str | None, fallback: str) -> str:
    """Return value stripped, or fallback if empty/None."""
    if value and value.strip():
        return value.strip()
    logger.warning("Missing or empty value — using fallback '%s'", fallback)
    return fallback


def generate_command(finding: Finding, resource: Resource) -> RemediationCommand:
    """
    Build an AWS CLI remediation command for the given finding.
    Never raises — returns a placeholder command on any error.
    """
    try:
        resource_id = _sanitise(
            getattr(resource, "resource_id", None),
            fallback="<UNKNOWN_RESOURCE_ID>",
        )
        region = _sanitise(
            getattr(resource, "region", None),
            fallback="us-east-1",
        )
        finding_type = _sanitise(
            getattr(finding, "finding_type", None),
            fallback="unknown",
        )

        template = TEMPLATES.get(finding_type, FALLBACK_COMMAND)

        command_text = template.format(
            resource_id=resource_id,
            region=region,
            finding_type=finding_type,
        )

    except Exception as exc:
        logger.error(
            "Failed to generate remediation command for finding_id=%s resource='%s': %s",
            getattr(finding, "id", "?"),
            getattr(resource, "resource_id", "?"),
            exc,
        )
        command_text = f"# Command generation failed: {exc}"

    return RemediationCommand(
        finding_id=finding.id,
        command_type="aws_cli",
        command_text=command_text,
        generated_at=datetime.utcnow(),
    )
