"""
Remediation Command Generator
Maps finding_type → AWS CLI command string.

Security:
  - resource_id and region are sanitised before interpolation to prevent
    command injection. Only safe character sets are allowed through.
  - Malformed/missing values produce a safe placeholder comment, never an error.
"""
import logging
import re
from datetime import datetime
from models import Finding, Resource, RemediationCommand

logger = logging.getLogger(__name__)

# ── Safe-character patterns ───────────────────────────────────────────────────
# AWS resource IDs: alphanumeric, hyphens, underscores, colons (for ARNs), slashes, dots
_SAFE_RESOURCE_ID_RE = re.compile(r"[^a-zA-Z0-9\-_:/.@]")

# AWS regions: only lowercase letters and hyphens (e.g. us-east-1)
_SAFE_REGION_RE = re.compile(r"[^a-z0-9\-]")

TEMPLATES = {
    "unattached_ebs": "aws ec2 delete-volume --volume-id {resource_id} --region {region}",
    "idle_ec2":       "aws ec2 stop-instances --instance-ids {resource_id} --region {region}",
    "orphaned_eip":   "aws ec2 release-address --allocation-id {resource_id} --region {region}",
    "idle_alb":       "aws elbv2 delete-load-balancer --load-balancer-arn {resource_id}",
    "old_snapshot":   "aws ec2 delete-snapshot --snapshot-id {resource_id} --region {region}",
}


def _sanitise_resource_id(value: str | None) -> str:
    """
    Strip any character that is not alphanumeric, hyphen, underscore, colon,
    forward-slash, dot, or @. Returns a safe placeholder if the result is empty.
    """
    if not value or not value.strip():
        logger.warning("Empty or None resource_id received — using placeholder.")
        return "<UNKNOWN_RESOURCE_ID>"
    sanitised = _SAFE_RESOURCE_ID_RE.sub("", value.strip())
    if not sanitised:
        logger.warning("resource_id '%s' contained only unsafe characters — using placeholder.", value)
        return "<UNKNOWN_RESOURCE_ID>"
    if sanitised != value.strip():
        logger.warning(
            "resource_id sanitised: '%s' → '%s' (unsafe chars removed)", value.strip(), sanitised
        )
    return sanitised


def _sanitise_region(value: str | None) -> str:
    """
    Strip anything that is not a lowercase letter, digit, or hyphen.
    Defaults to 'us-east-1' if the result is empty.
    """
    if not value or not value.strip():
        logger.warning("Empty or None region received — defaulting to 'us-east-1'.")
        return "us-east-1"
    sanitised = _SAFE_REGION_RE.sub("", value.strip().lower())
    if not sanitised:
        logger.warning("Region '%s' contained only unsafe characters — defaulting to 'us-east-1'.", value)
        return "us-east-1"
    if sanitised != value.strip().lower():
        logger.warning("Region sanitised: '%s' → '%s'", value.strip(), sanitised)
    return sanitised


def generate_command(finding: Finding, resource: Resource) -> RemediationCommand:
    """
    Build an AWS CLI remediation command for the given finding.
    Inputs are sanitised before interpolation.
    Never raises — returns a safe placeholder on any error.
    """
    try:
        resource_id = _sanitise_resource_id(getattr(resource, "resource_id", None))
        region      = _sanitise_region(getattr(resource, "region", None))
        finding_type = (getattr(finding, "finding_type", None) or "unknown").strip()

        template = TEMPLATES.get(finding_type)
        if not template:
            logger.warning("No CLI template for finding_type='%s'.", finding_type)
            command_text = f"# No remediation command available for finding_type='{finding_type}'"
        else:
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
        command_text = "# Command generation failed — see server logs"

    preview = command_text[:80] + ("…" if len(command_text) > 80 else "")
    logger.info(
        "Remediation command generated | finding_id=%s | type=%s | preview='%s'",
        finding.id, finding_type, preview,
    )

    return RemediationCommand(
        finding_id=finding.id,
        command_type="aws_cli",
        command_text=command_text,
        generated_at=datetime.utcnow(),
    )
