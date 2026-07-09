from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from pydantic import BaseModel

import models
from database import get_db
from auth.auth_handler import hash_password, verify_password, create_access_token
from auth.auth_bearer import get_current_user
from parser.aws_parser import parse_aws_csv
from engine.orphan_detector import run_detection
from engine.remediation import remediate_resource

router = APIRouter()


# ──────────────────────────────────────────────
# Schemas
# ──────────────────────────────────────────────

class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str


class BulkRemediateRequest(BaseModel):
    finding_ids: list[int]


# ──────────────────────────────────────────────
# Auth endpoints
# ──────────────────────────────────────────────

@router.post("/auth/register")
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    if db.query(models.User).filter(models.User.username == req.username).first():
        raise HTTPException(status_code=400, detail="Username already exists")
    if db.query(models.User).filter(models.User.email == req.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = models.User(
        username=req.username,
        email=req.email,
        hashed_password=hash_password(req.password),
    )
    db.add(user)
    db.commit()
    return {"message": f"User '{req.username}' registered successfully"}


@router.post("/auth/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == req.username).first()
    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is inactive")

    token = create_access_token({"sub": user.username})
    return {"access_token": token, "token_type": "bearer"}


@router.get("/auth/me")
def me(current_user: models.User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "created_at": current_user.created_at,
        "is_active": current_user.is_active,
    }


# ──────────────────────────────────────────────
# Ingest
# ──────────────────────────────────────────────

@router.post("/ingest")
async def ingest(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only .csv files are accepted")

    content = await file.read()
    rows = parse_aws_csv(content)

    if not rows:
        raise HTTPException(status_code=422, detail="No valid rows found in CSV")

    resource_objs = []
    for row in rows:
        resource = models.Resource(
            resource_id=row["resource_id"],
            resource_name=row["resource_name"],
            resource_type=row["resource_type"],
            region=row["region"],
            monthly_cost_usd=row["monthly_cost_usd"],
            status=row["status"],
            last_active_date=row["last_active_date"],
            uploaded_by=current_user.id,
        )
        db.add(resource)
        resource_objs.append(resource)

    db.flush()
    findings_count = run_detection(db, resource_objs)
    db.commit()

    return {
        "message": "Ingestion complete",
        "resources_ingested": len(resource_objs),
        "findings_detected": findings_count,
    }


# ──────────────────────────────────────────────
# Findings
# ──────────────────────────────────────────────

@router.get("/findings")
def get_findings(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    findings = (
        db.query(models.Finding)
        .order_by(models.Finding.estimated_monthly_waste_usd.desc())
        .all()
    )
    result = []
    for f in findings:
        r = f.resource
        cmd = f.remediation_commands[0].command_text if f.remediation_commands else None
        result.append({
            "id": f.id,
            "resource_id": r.resource_id if r else None,
            "resource_name": r.resource_name if r else None,
            "resource_type": r.resource_type if r else None,
            "region": r.region if r else None,
            "finding_type": f.finding_type,
            "severity": f.severity,
            "estimated_monthly_waste_usd": f.estimated_monthly_waste_usd,
            "status": f.status,
            "detected_at": f.detected_at,
            "remediated_at": f.remediated_at,
            "cli_command": cmd,
        })
    return result


@router.get("/findings/{finding_id}/remediation")
def get_remediation(
    finding_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    finding = db.query(models.Finding).filter(models.Finding.id == finding_id).first()
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found")

    cmd = finding.remediation_commands[0].command_text if finding.remediation_commands else None
    return {"finding_id": finding_id, "cli_command": cmd}


@router.get("/findings/{finding_id}/status")
def get_finding_status(
    finding_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    finding = db.query(models.Finding).filter(models.Finding.id == finding_id).first()
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found")
    return {"finding_id": finding_id, "status": finding.status}


# ──────────────────────────────────────────────
# Remediation
# ──────────────────────────────────────────────

@router.post("/remediate/bulk")
def remediate_bulk(
    req: BulkRemediateRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    succeeded = 0
    failed = 0
    details = []

    for fid in req.finding_ids:
        finding = db.query(models.Finding).filter(models.Finding.id == fid).first()
        if not finding:
            failed += 1
            details.append({"finding_id": fid, "success": False, "message": "Not found"})
            continue

        resource = finding.resource
        result = remediate_resource(resource) if resource else {"success": False, "message": "No resource"}

        finding.status = "remediated" if result["success"] else "failed"
        if result["success"]:
            finding.remediated_at = datetime.now(timezone.utc)
            succeeded += 1
        else:
            failed += 1

        details.append({"finding_id": fid, "success": result["success"], "message": result["message"]})

    db.commit()
    return {"succeeded": succeeded, "failed": failed, "details": details}


@router.post("/remediate/{finding_id}")
def remediate_single(
    finding_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    finding = db.query(models.Finding).filter(models.Finding.id == finding_id).first()
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found")

    resource = finding.resource
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found for this finding")

    result = remediate_resource(resource)

    finding.status = "remediated" if result["success"] else "failed"
    if result["success"]:
        finding.remediated_at = datetime.now(timezone.utc)
    db.commit()

    return {
        "finding_id": finding_id,
        "success": result["success"],
        "message": result["message"],
        "status": finding.status,
    }


# ──────────────────────────────────────────────
# Summary
# ──────────────────────────────────────────────

@router.get("/summary")
def summary(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    findings = db.query(models.Finding).all()

    total_waste = sum(f.estimated_monthly_waste_usd for f in findings)

    by_severity = {}
    for f in findings:
        by_severity[f.severity] = by_severity.get(f.severity, 0) + 1

    by_type: dict[str, float] = {}
    for f in findings:
        rtype = f.resource.resource_type if f.resource else "Unknown"
        by_type[rtype] = by_type.get(rtype, 0) + f.estimated_monthly_waste_usd

    # Top 3 most wasteful resources
    resources = (
        db.query(models.Resource)
        .order_by(models.Resource.monthly_cost_usd.desc())
        .limit(3)
        .all()
    )
    top3 = [
        {
            "resource_id": r.resource_id,
            "resource_name": r.resource_name,
            "resource_type": r.resource_type,
            "monthly_cost_usd": r.monthly_cost_usd,
        }
        for r in resources
    ]

    pending_count = sum(1 for f in findings if f.status == "pending")

    return {
        "total_waste_usd": round(total_waste, 2),
        "total_findings": len(findings),
        "pending_remediations": pending_count,
        "findings_by_severity": by_severity,
        "waste_by_resource_type": {k: round(v, 2) for k, v in by_type.items()},
        "top_3_wasteful_resources": top3,
    }


# ──────────────────────────────────────────────
# Data management
# ──────────────────────────────────────────────

@router.delete("/data")
def clear_data(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    db.query(models.RemediationCommand).delete()
    db.query(models.Finding).delete()
    db.query(models.Resource).delete()
    db.commit()
    return {"message": "All resources, findings, and remediation commands have been cleared"}
