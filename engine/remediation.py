from datetime import datetime
from sqlalchemy.orm import Session
from models import Finding, Resource, RemediationCommand

# Import boto3 once at module level so exception classes are in scope for except clauses.
try:
    import boto3
    from botocore.exceptions import NoCredentialsError, ClientError
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False
    NoCredentialsError = Exception   # placeholder so except clause never matches on ImportError path
    ClientError = Exception


def remediate_finding(finding_id: int, db: Session) -> dict:
    """
    Attempt to remediate a finding via boto3.
    Falls back gracefully if AWS credentials are not configured.
    Returns a result dict with success flag and relevant fields.
    """
    finding = db.query(Finding).filter(Finding.id == finding_id).first()
    if not finding:
        return {"success": False, "message": f"Finding {finding_id} not found."}

    if finding.status == "remediated":
        return {"success": False, "message": "Finding already remediated."}

    resource = db.query(Resource).filter(Resource.id == finding.resource_id).first()
    if not resource:
        return {"success": False, "message": "Associated resource not found."}

    cmd_record = (
        db.query(RemediationCommand)
        .filter(RemediationCommand.finding_id == finding_id)
        .first()
    )
    cli_command = cmd_record.command_text if cmd_record else "No CLI command available."

    if not BOTO3_AVAILABLE:
        finding.status = "failed"
        db.commit()
        return {
            "success": False,
            "message": f"boto3 not installed. Use the CLI command instead: {cli_command}",
            "cli_alternative": cli_command,
        }

    # Fast credential check — avoids boto3 hanging on network timeouts
    try:
        session = boto3.session.Session()
        creds = session.get_credentials()
        if creds is None:
            raise NoCredentialsError()
        creds = creds.get_frozen_credentials()
        if not creds.access_key:
            raise NoCredentialsError()
    except NoCredentialsError:
        finding.status = "failed"
        db.commit()
        return {
            "success": False,
            "message": f"AWS credentials not configured. Use the CLI command instead: {cli_command}",
            "cli_alternative": cli_command,
        }

    try:
        action_taken = _execute_boto3(finding.finding_type, resource)
        finding.status = "remediated"
        finding.remediated_at = datetime.utcnow()
        db.commit()
        return {
            "success": True,
            "finding_id": finding_id,
            "resource_id": resource.resource_id,
            "action_taken": action_taken,
            "status": "remediated",
            "timestamp": finding.remediated_at.isoformat(),
            "message": f"Successfully remediated {resource.resource_type} ({resource.resource_id}).",
        }

    except NoCredentialsError:
        finding.status = "failed"
        db.commit()
        return {
            "success": False,
            "message": (
                f"AWS credentials not configured. "
                f"Use the CLI command instead: {cli_command}"
            ),
            "cli_alternative": cli_command,
        }

    except ClientError as e:
        finding.status = "failed"
        db.commit()
        return {
            "success": False,
            "message": f"AWS API error: {e.response['Error']['Message']}",
            "cli_alternative": cli_command,
        }

    except Exception as e:
        finding.status = "failed"
        db.commit()
        return {
            "success": False,
            "message": f"Unexpected error: {str(e)}",
            "cli_alternative": cli_command,
        }


def _execute_boto3(finding_type: str, resource) -> str:
    rid    = resource.resource_id
    region = resource.region

    if finding_type == "unattached_ebs":
        client = boto3.client("ec2", region_name=region)
        client.delete_volume(VolumeId=rid)
        return f"Deleted EBS volume {rid}"

    elif finding_type == "idle_ec2":
        client = boto3.client("ec2", region_name=region)
        client.stop_instances(InstanceIds=[rid])
        return f"Stopped EC2 instance {rid}"

    elif finding_type == "orphaned_eip":
        client = boto3.client("ec2", region_name=region)
        client.release_address(AllocationId=rid)
        return f"Released Elastic IP {rid}"

    elif finding_type == "idle_alb":
        client = boto3.client("elbv2", region_name=region)
        client.delete_load_balancer(LoadBalancerArn=rid)
        return f"Deleted Load Balancer {rid}"

    elif finding_type == "old_snapshot":
        client = boto3.client("ec2", region_name=region)
        client.delete_snapshot(SnapshotId=rid)
        return f"Deleted Snapshot {rid}"

    else:
        raise ValueError(f"Unknown finding type: {finding_type}")
