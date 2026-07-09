"""
Remediation engine.
- generate_cli_command: returns AWS CLI string for a resource
- remediate_resource: executes via boto3
"""
from datetime import datetime, timezone
import models


CLI_TEMPLATES = {
    "EBS Volume":    "aws ec2 delete-volume --volume-id {resource_id} --region {region}",
    "EC2 Instance":  "aws ec2 stop-instances --instance-ids {resource_id} --region {region}",
    "Elastic IP":    "aws ec2 release-address --allocation-id {resource_id} --region {region}",
    "Load Balancer": "aws elbv2 delete-load-balancer --load-balancer-arn {resource_id}",
    "Snapshot":      "aws ec2 delete-snapshot --snapshot-id {resource_id} --region {region}",
}


def generate_cli_command(resource: models.Resource) -> str | None:
    template = CLI_TEMPLATES.get(resource.resource_type)
    if not template:
        return None
    return template.format(
        resource_id=resource.resource_id,
        region=resource.region or "us-east-1",
    )


def remediate_resource(resource: models.Resource) -> dict:
    """
    Attempt boto3 remediation. Returns {"success": bool, "message": str}.
    Falls back gracefully if AWS credentials are not configured.
    """
    try:
        import boto3
        from botocore.exceptions import NoCredentialsError, ClientError

        rtype = resource.resource_type
        region = resource.region or "us-east-1"
        rid = resource.resource_id

        try:
            if rtype == "EBS Volume":
                client = boto3.client("ec2", region_name=region)
                client.delete_volume(VolumeId=rid)

            elif rtype == "EC2 Instance":
                client = boto3.client("ec2", region_name=region)
                client.stop_instances(InstanceIds=[rid])

            elif rtype == "Elastic IP":
                client = boto3.client("ec2", region_name=region)
                client.release_address(AllocationId=rid)

            elif rtype == "Load Balancer":
                client = boto3.client("elbv2", region_name=region)
                client.delete_load_balancer(LoadBalancerArn=rid)

            elif rtype == "Snapshot":
                client = boto3.client("ec2", region_name=region)
                client.delete_snapshot(SnapshotId=rid)

            else:
                return {"success": False, "message": f"No boto3 handler for resource type: {rtype}"}

            return {"success": True, "message": f"Successfully remediated {rid}"}

        except NoCredentialsError:
            cli_cmd = generate_cli_command(resource)
            return {
                "success": False,
                "message": (
                    "AWS credentials not configured. "
                    "Run `aws configure` or set AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY env vars. "
                    f"Alternatively, run manually: {cli_cmd}"
                ),
            }
        except ClientError as e:
            return {"success": False, "message": str(e)}

    except ImportError:
        cli_cmd = generate_cli_command(resource)
        return {
            "success": False,
            "message": f"boto3 not available. Run manually: {cli_cmd}",
        }
