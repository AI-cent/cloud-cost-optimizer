from typing import List, Optional
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import get_db
from models import Resource, Finding, RemediationCommand
from parser.aws_parser import parse_and_ingest
from engine.orphan_detector import detect_all

router = APIRouter()
templates = Jinja2Templates(directory="dashboard/templates")


# ── POST /ingest ─────────────────────────────────────────────────────────────
@router.post("/ingest", summary="Upload AWS billing CSV and run detection")
async def ingest(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only .csv files accepted.")

    content = await file.read()
    try:
        resources = parse_and_ingest(content, db)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    findings = detect_all(db)

    return {
        "message": "Ingest complete",
        "resources_ingested": len(resources),
        "findings_generated": len(findings),
        "findings_summary": {
            "Critical": sum(1 for f in findings if f.severity == "Critical"),
            "High":     sum(1 for f in findings if f.severity == "High"),
            "Medium":   sum(1 for f in findings if f.severity == "Medium"),
            "Low":      sum(1 for f in findings if f.severity == "Low"),
        },
    }


# ── GET /findings ─────────────────────────────────────────────────────────────
@router.get("/findings", summary="List all findings sorted by waste descending")
def list_findings(db: Session = Depends(get_db)):
    findings = (
        db.query(Finding)
        .order_by(Finding.estimated_monthly_waste_usd.desc())
        .all()
    )

    result = []
    for f in findings:
        resource = db.query(Resource).filter(Resource.resource_id == f.resource_id).first()
        cmd = (
            db.query(RemediationCommand)
            .filter(RemediationCommand.finding_id == f.id)
            .first()
        )
        result.append({
            "finding_id": f.id,
            "resource_id": f.resource_id,
            "resource_name": resource.resource_name if resource else "N/A",
            "resource_type": resource.resource_type if resource else "N/A",
            "region": resource.region if resource else "N/A",
            "finding_type": f.finding_type,
            "severity": f.severity,
            "estimated_monthly_waste_usd": f.estimated_monthly_waste_usd,
            "detected_at": f.detected_at.isoformat(),
            "remediation_command": cmd.command_text if cmd else None,
        })

    return result


# ── GET /findings/{id}/remediation ───────────────────────────────────────────
@router.get("/findings/{finding_id}/remediation", summary="Get remediation command for a finding")
def get_remediation(finding_id: int, db: Session = Depends(get_db)):
    finding = db.query(Finding).filter(Finding.id == finding_id).first()
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found")

    cmd = (
        db.query(RemediationCommand)
        .filter(RemediationCommand.finding_id == finding_id)
        .first()
    )
    if not cmd:
        raise HTTPException(status_code=404, detail="No remediation command found for this finding")

    resource = db.query(Resource).filter(Resource.resource_id == finding.resource_id).first()

    return {
        "finding_id": finding_id,
        "finding_type": finding.finding_type,
        "severity": finding.severity,
        "resource_id": finding.resource_id,
        "resource_name": resource.resource_name if resource else "N/A",
        "region": resource.region if resource else "N/A",
        "command_type": cmd.command_type,
        "command_text": cmd.command_text,
        "generated_at": cmd.generated_at.isoformat(),
    }


# ── GET /summary ──────────────────────────────────────────────────────────────
@router.get("/summary", summary="Aggregated cost waste summary")
def get_summary(db: Session = Depends(get_db)):
    findings = db.query(Finding).all()

    if not findings:
        return {
            "total_waste_usd": 0,
            "findings_by_severity": {},
            "findings_by_resource_type": {},
            "top_3_most_wasteful": [],
        }

    total_waste = sum(f.estimated_monthly_waste_usd for f in findings)

    by_severity: dict = {}
    for f in findings:
        by_severity[f.severity] = by_severity.get(f.severity, 0) + 1

    by_type: dict = {}
    waste_by_type: dict = {}
    for f in findings:
        resource = db.query(Resource).filter(Resource.resource_id == f.resource_id).first()
        rtype = resource.resource_type if resource else "Unknown"
        by_type[rtype] = by_type.get(rtype, 0) + 1
        waste_by_type[rtype] = waste_by_type.get(rtype, 0.0) + f.estimated_monthly_waste_usd

    # Top 3 most wasteful resources
    top3 = sorted(findings, key=lambda f: f.estimated_monthly_waste_usd, reverse=True)[:3]
    top3_out = []
    for f in top3:
        resource = db.query(Resource).filter(Resource.resource_id == f.resource_id).first()
        top3_out.append({
            "resource_id": f.resource_id,
            "resource_name": resource.resource_name if resource else "N/A",
            "resource_type": resource.resource_type if resource else "N/A",
            "estimated_monthly_waste_usd": f.estimated_monthly_waste_usd,
            "severity": f.severity,
        })

    return {
        "total_waste_usd": round(total_waste, 2),
        "findings_by_severity": by_severity,
        "findings_by_resource_type": by_type,
        "waste_by_resource_type": {k: round(v, 2) for k, v in waste_by_type.items()},
        "top_3_most_wasteful": top3_out,
    }


# ── GET /dashboard ────────────────────────────────────────────────────────────
@router.get("/dashboard", response_class=HTMLResponse, summary="HTML dashboard")
def dashboard(request: Request, db: Session = Depends(get_db)):
    findings = (
        db.query(Finding)
        .order_by(Finding.estimated_monthly_waste_usd.desc())
        .all()
    )

    total_waste = round(sum(f.estimated_monthly_waste_usd for f in findings), 2)
    total_orphaned = len(findings)

    by_severity: dict = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0}
    waste_by_type: dict = {}
    rows = []

    for f in findings:
        by_severity[f.severity] = by_severity.get(f.severity, 0) + 1
        resource = db.query(Resource).filter(Resource.resource_id == f.resource_id).first()
        rtype = resource.resource_type if resource else "Unknown"
        waste_by_type[rtype] = waste_by_type.get(rtype, 0.0) + f.estimated_monthly_waste_usd
        cmd = (
            db.query(RemediationCommand)
            .filter(RemediationCommand.finding_id == f.id)
            .first()
        )
        rows.append({
            "resource_id": f.resource_id,
            "resource_name": resource.resource_name if resource else "N/A",
            "resource_type": rtype,
            "region": resource.region if resource else "N/A",
            "severity": f.severity,
            "waste": f.estimated_monthly_waste_usd,
            "command": cmd.command_text if cmd else "N/A",
        })

    # Most wasteful resource type
    most_wasteful_type = max(waste_by_type, key=waste_by_type.get) if waste_by_type else "N/A"
    highest_severity_count = by_severity.get("Critical", 0) or by_severity.get("High", 0)

    return templates.TemplateResponse(request, "index.html", {
        "total_waste": total_waste,
        "total_orphaned": total_orphaned,
        "most_wasteful_type": most_wasteful_type,
        "highest_severity_count": highest_severity_count,
        "by_severity": by_severity,
        "waste_by_type": {k: round(v, 2) for k, v in waste_by_type.items()},
        "rows": rows,
    })
