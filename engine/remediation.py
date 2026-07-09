"""
Remediation Command Generator
Maps finding_type → AWS CLI command string.
"""
from datetime import datetime
from models import Finding, Resource, RemediationCommand

TEMPLATES = {
    "unattached_ebs": "aws ec2 delete-volume --volume-id {resource_id} --region {region}",
    "idle_ec2":       "aws ec2 stop-instances --instance-ids {resource_id} --region {region}",
    "orphaned_eip":   "aws ec2 release-address --allocation-id {resource_id} --region {region}",
    "idle_alb":       "aws elbv2 delete-load-balancer --load-balancer-arn {resource_id}",
    "old_snapshot":   "aws ec2 delete-snapshot --snapshot-id {resource_id} --region {region}",
}


def generate_command(finding: Finding, resource: Resource) -> RemediationCommand:
    template = TEMPLATES.get(finding.finding_type, "# No command available for {finding_type}")
    command_text = template.format(
        resource_id=resource.resource_id,
        region=resource.region,
        finding_type=finding.finding_type,
    )
    return RemediationCommand(
        finding_id=finding.id,
        command_type="aws_cli",
        command_text=command_text,
        generated_at=datetime.utcnow(),
    )
