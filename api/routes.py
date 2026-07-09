import logging
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from database import get_db
from models import Resource, Finding, RemediationCommand
from parser.aws_parser import parse_and_ingest
from engine.orphan_detector import detect_all

logger = logging.getLogger(__name__)
router = APIRouter()
templates = Jinja2Templates(directory="dashboard/templates")


def _error(status: int, error: str, detail: str) -> JSONResponse:
    """Consistent error envelope — never exposes stack traces."""
    return JSONResponse(status_code=status, content={"error": error, "detail": detail})


# ── POST /ingest ─────────────────────────────────────────────────────────────
@router.post("/ingest", summary="Upload AWS billing CSV and run detection")
async def ingest(file: UploadFile = File(...), db: Session = Depends(get_db)):
    # Validate file extension
    if not (file.filename or "").lower().endswith(".csv"):
        return _error(400, "invalid_file_type", "Only .csv files are accepted.")

    try:
        content = await file.read()
    except Exception as exc:
        logger.error("Failed to read uploaded file: %s", exc)
        return _error(500, "file_read_error", "Could not read the uploaded file.")

    if not content:
        return _error(400, "empty_file", "The uploaded file is empty.")

    # Parse & ingest
    try:
        resources, skipped = parse_and_ingest(content, db)
    except ValueError as exc:
        return _error(422, "csv_validation_error", str(exc))
    except Exception as exc:
        logger.error("Unexpected error during ingest: %s", exc, exc_info=True)
        return _error(500, "ingest_error", "An unexpected error occurred during ingestion.")

    # Run detection
    try:
        findings = detect_all(db)
    except Exception as exc:
        logger.error("Unexpected error during detection: %s", exc, exc_info=True)
        return _error(500, "detection_error", "Ingestion succeeded but orphan detection failed.")

    return {
        "message": "Ingest complete",
        "resources_ingested": len(resources),
        "resources_skipped": skipped,
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
    try:
        findings = (
            db.query(Finding)
            .order_by(Finding.estimated_monthly_waste_usd.desc())
            .all()
        )
    except Exception as exc:
        logger.error("Failed to query findings: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail={"error": "db_error", "detail": "Could not fetch findings."})

    result = []
    for f in findings:
        try:
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
        except Exception as exc:
            logger.warning("Skipping finding id=%s due to serialisation error: %s", f.id, exc)
            continue

    return result


# ── GET /findings/{id}/remediation ───────────────────────────────────────────
@router.get("/findings/{finding_id}/remediation",
            summary="Get remediation command for a specific finding")
def get_remediation(finding_id: int, db: Session = Depends(get_db)):
    if finding_id <= 0:
        raise HTTPException(
            status_code=400,
            detail={"error": "invalid_id", "detail": "finding_id must be a positive integer."},
        )

    try:
        finding = db.query(Finding).filter(Finding.id == finding_id).first()
    except Exception as exc:
        logger.error("DB error fetching finding %d: %s", finding_id, exc, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"error": "db_error", "detail": "Could not fetch finding."},
        )

    if not finding:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "detail": f"Finding with id={finding_id} does not exist."},
        )

    try:
        cmd = (
            db.query(RemediationCommand)
            .filter(RemediationCommand.finding_id == finding_id)
            .first()
        )
        resource = db.query(Resource).filter(Resource.resource_id == finding.resource_id).first()
    except Exception as exc:
        logger.error("DB error fetching remediation for finding %d: %s", finding_id, exc, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"error": "db_error", "detail": "Could not fetch remediation command."},
        )

    if not cmd:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "detail": f"No remediation command found for finding id={finding_id}."},
        )

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
    try:
        findings = db.query(Finding).all()
    except Exception as exc:
        logger.error("DB error fetching summary: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"error": "db_error", "detail": "Could not compute summary."},
        )

    if not findings:
        return {
            "total_waste_usd": 0,
            "findings_by_severity": {},
            "findings_by_resource_type": {},
            "waste_by_resource_type": {},
            "top_3_most_wasteful": [],
        }

    try:
        total_waste = sum(f.estimated_monthly_waste_usd for f in findings)
        by_severity: dict = {}
        by_type: dict = {}
        waste_by_type: dict = {}

        for f in findings:
            by_severity[f.severity] = by_severity.get(f.severity, 0) + 1
            resource = db.query(Resource).filter(Resource.resource_id == f.resource_id).first()
            rtype = resource.resource_type if resource else "Unknown"
            by_type[rtype] = by_type.get(rtype, 0) + 1
            waste_by_type[rtype] = waste_by_type.get(rtype, 0.0) + f.estimated_monthly_waste_usd

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

    except Exception as exc:
        logger.error("Unexpected error computing summary: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"error": "summary_error", "detail": "Failed to compute summary."},
        )


# ── GET /dashboard ────────────────────────────────────────────────────────────
@router.get("/dashboard", response_class=HTMLResponse, summary="HTML dashboard")
def dashboard(request: Request, db: Session = Depends(get_db)):
    try:
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
            try:
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
            except Exception as exc:
                logger.warning("Skipping finding id=%s in dashboard render: %s", f.id, exc)
                continue

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

    except Exception as exc:
        logger.error("Dashboard render failed: %s", exc, exc_info=True)
        return HTMLResponse(
            content="<h1>500 — Dashboard Error</h1><p>Could not load dashboard. Check server logs.</p>",
            status_code=500,
        )
