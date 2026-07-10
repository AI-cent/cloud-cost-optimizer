import logging
import re as _re
import time
from collections import defaultdict
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile, File, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel, field_validator
from typing import List, Optional
from datetime import datetime
import os

MAX_CSV_BYTES = 10 * 1024 * 1024  # 10 MB

logger = logging.getLogger(__name__)

# ── In-memory rate limiter for /auth/login ──────────────────────────────────
# Tracks (ip → list of attempt timestamps within the current window)
_LOGIN_ATTEMPTS: dict = defaultdict(list)
_LOGIN_RATE_LIMIT = 5      # max attempts
_LOGIN_WINDOW_SEC = 60     # per window (seconds)


def _check_login_rate_limit(ip: str) -> None:
    """Raise 429 if the IP has exceeded the login rate limit."""
    now = time.monotonic()
    window_start = now - _LOGIN_WINDOW_SEC
    attempts = _LOGIN_ATTEMPTS[ip]
    # Prune timestamps outside the window
    _LOGIN_ATTEMPTS[ip] = [t for t in attempts if t > window_start]
    if len(_LOGIN_ATTEMPTS[ip]) >= _LOGIN_RATE_LIMIT:
        raise HTTPException(
            status_code=429,
            detail={"error": "Too many requests", "detail": "Too many login attempts. Please wait 1 minute before trying again."},
        )
    _LOGIN_ATTEMPTS[ip].append(now)


def http_err(status: int, error: str, detail: str, endpoint: str = ""):
    if status >= 500:
        logger.error("API_ERROR endpoint=%s status=%d error=%s detail=%s", endpoint, status, error, detail)
    raise HTTPException(status_code=status, detail={"error": error, "detail": detail})

from database import get_db
from models import User, Resource, Finding, RemediationCommand
from auth.auth_handler import hash_password, verify_password, create_access_token
from auth.auth_bearer import JWTBearer
from parser.aws_parser import parse_aws_csv
from engine.orphan_detector import run_detection
from engine.remediation import remediate_finding
from notifications.email_sender import send_remediation_email, NOTIFICATION_EMAIL

router = APIRouter()
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "..", "dashboard", "templates"))
jwt_bearer = JWTBearer()

# --------------------------------------------------------------------------- #
# Pydantic schemas
# --------------------------------------------------------------------------- #

class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str
    role: Optional[str] = "viewer"

    @field_validator("username")
    @classmethod
    def username_valid(cls, v: str) -> str:
        v = v.strip()
        if not (3 <= len(v) <= 50):
            raise ValueError("Username must be 3–50 characters.")
        if not _re.fullmatch(r"[A-Za-z0-9_]+", v):
            raise ValueError("Username may only contain letters, numbers, and underscores.")
        return v

    @field_validator("email")
    @classmethod
    def email_valid(cls, v: str) -> str:
        v = v.strip()
        if not _re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", v):
            raise ValueError("Invalid email address.")
        return v

    @field_validator("password")
    @classmethod
    def password_valid(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters.")
        if not _re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter.")
        if not _re.search(r"\d", v):
            raise ValueError("Password must contain at least one number.")
        return v


class LoginRequest(BaseModel):
    username: str
    password: str


class BulkRemediateRequest(BaseModel):
    finding_ids: List[int]

    @field_validator("finding_ids")
    @classmethod
    def ids_valid(cls, v: List[int]) -> List[int]:
        if not v:
            raise ValueError("finding_ids must not be empty.")
        if any(i <= 0 for i in v):
            raise ValueError("All finding_ids must be positive integers.")
        return v


# --------------------------------------------------------------------------- #
# Auth endpoints
# --------------------------------------------------------------------------- #

def require_admin(payload: dict, db: Session):
    """Raise 403 if the token belongs to a viewer."""
    username = payload.get("sub")
    user = db.query(User).filter(User.username == username).first()
    if not user or user.role != "admin":
        http_err(403, "Forbidden", "Admin access required.")
    return user


@router.post("/auth/register")
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == req.username).first():
        http_err(400, "Bad request", "Username already exists.")
    if db.query(User).filter(User.email == req.email).first():
        http_err(400, "Bad request", "Email already registered.")

    # First registered user is always admin regardless of input
    is_first = db.query(User).count() == 0
    role = "admin" if is_first else (req.role or "viewer").lower()
    if role not in ("admin", "viewer"):
        role = "viewer"

    user = User(
        username=req.username,
        email=req.email,
        hashed_password=hash_password(req.password),
        role=role,
    )
    db.add(user)
    db.commit()
    return {"message": f"User '{req.username}' registered successfully.", "role": role}


@router.post("/auth/login")
def login(req: LoginRequest, request: Request, db: Session = Depends(get_db)):
    # Rate-limit by client IP before doing any DB work
    client_ip = request.client.host if request.client else "unknown"
    _check_login_rate_limit(client_ip)

    user = db.query(User).filter(User.username == req.username).first()
    # Never reveal whether username or password is wrong
    if not user or not verify_password(req.password, user.hashed_password):
        logger.warning(
            "LOGIN_FAILURE username=%s ip=%s timestamp=%s",
            req.username, client_ip, datetime.utcnow().isoformat(),
        )
        http_err(401, "Unauthorised", "Invalid username or password.")
    if not user.is_active:
        logger.warning(
            "LOGIN_FAILURE username=%s ip=%s reason=account_disabled timestamp=%s",
            req.username, client_ip, datetime.utcnow().isoformat(),
        )
        http_err(403, "Forbidden", "Account is disabled.")
    token = create_access_token({"sub": user.username, "user_id": user.id, "role": user.role})
    logger.info(
        "LOGIN_SUCCESS username=%s ip=%s timestamp=%s",
        user.username, client_ip, datetime.utcnow().isoformat(),
    )
    return {"access_token": token, "token_type": "bearer"}


@router.get("/auth/me")
def get_me(payload: dict = Depends(jwt_bearer), db: Session = Depends(get_db)):
    username = payload.get("sub")
    user = db.query(User).filter(User.username == username).first()
    if not user:
        http_err(404, "Not found", "User not found.")
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "role": user.role,
        "created_at": user.created_at,
        "is_active": user.is_active,
    }


# --------------------------------------------------------------------------- #
# Dashboard (no JWT required — auth handled in-browser)
# --------------------------------------------------------------------------- #

@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    # Support both old (context dict) and new (request keyword) Starlette APIs
    try:
        return templates.TemplateResponse(request=request, name="index.html")
    except TypeError:
        return templates.TemplateResponse("index.html", {"request": request})


# --------------------------------------------------------------------------- #
# Protected API endpoints
# --------------------------------------------------------------------------- #

@router.post("/ingest")
async def ingest(
    file: UploadFile = File(...),
    payload: dict = Depends(jwt_bearer),
    db: Session = Depends(get_db),
):
    if not (file.filename or "").endswith(".csv"):
        http_err(400, "Bad request", "Only .csv files are accepted.")

    content = await file.read()

    if not content:
        http_err(400, "Bad request", "Uploaded file is empty.")

    if len(content) > MAX_CSV_BYTES:
        http_err(400, "Bad request", f"File exceeds maximum size of 10 MB (got {len(content)//1024} KB).")

    try:
        resources_data = parse_aws_csv(content)
    except ValueError as e:
        http_err(422, "Validation error", str(e))

    if not resources_data:
        http_err(400, "Bad request", "No valid resources found in CSV.")

    user_id = payload.get("user_id")
    inserted_ids = []

    for r in resources_data:
        resource = Resource(
            resource_id=r["resource_id"],
            resource_name=r["resource_name"],
            resource_type=r["resource_type"],
            region=r["region"],
            monthly_cost_usd=r["monthly_cost_usd"],
            status=r["status"],
            last_active_date=r["last_active_date"],
            uploaded_by=user_id,
        )
        db.add(resource)
        db.flush()
        inserted_ids.append(resource.id)

    db.commit()

    findings_count = run_detection(db, inserted_ids)

    logger.info(
        "INGEST_COMPLETE username=%s filename=%s rows=%d findings=%d timestamp=%s",
        payload.get("sub", "unknown"),
        file.filename,
        len(inserted_ids),
        findings_count,
        datetime.utcnow().isoformat(),
    )

    return {
        "message": "Ingestion complete.",
        "resources_ingested": len(inserted_ids),
        "findings_detected": findings_count,
    }


@router.get("/findings")
def get_findings(payload: dict = Depends(jwt_bearer), db: Session = Depends(get_db)):
    findings = (
        db.query(Finding)
        .order_by(Finding.estimated_monthly_waste_usd.desc())
        .all()
    )
    result = []
    for f in findings:
        resource = f.resource
        cmd = f.remediation_commands[0] if f.remediation_commands else None
        result.append({
            "id": f.id,
            "finding_type": f.finding_type,
            "severity": f.severity,
            "estimated_monthly_waste_usd": f.estimated_monthly_waste_usd,
            "status": f.status,
            "detected_at": f.detected_at,
            "remediated_at": f.remediated_at,
            "resource": {
                "id": resource.resource_id,
                "name": resource.resource_name,
                "type": resource.resource_type,
                "region": resource.region,
                "monthly_cost_usd": resource.monthly_cost_usd,
                "status": resource.status,
            } if resource else None,
            "cli_command": cmd.command_text if cmd else None,
        })
    return result


@router.get("/findings/{finding_id}/remediation")
def get_remediation_command(
    finding_id: int,
    payload: dict = Depends(jwt_bearer),
    db: Session = Depends(get_db),
):
    finding = db.query(Finding).filter(Finding.id == finding_id).first()
    if not finding:
        http_err(404, "Not found", "Finding not found.")
    cmd = finding.remediation_commands[0] if finding.remediation_commands else None
    return {
        "finding_id": finding_id,
        "command_type": cmd.command_type if cmd else None,
        "command_text": cmd.command_text if cmd else "No command available.",
        "generated_at": cmd.generated_at if cmd else None,
    }


@router.get("/findings/{finding_id}/status")
def get_finding_status(
    finding_id: int,
    payload: dict = Depends(jwt_bearer),
    db: Session = Depends(get_db),
):
    finding = db.query(Finding).filter(Finding.id == finding_id).first()
    if not finding:
        http_err(404, "Not found", "Finding not found.")
    return {
        "finding_id": finding_id,
        "status": finding.status,
        "remediated_at": finding.remediated_at,
    }


@router.post("/remediate/bulk")
def remediate_bulk(
    req: BulkRemediateRequest,
    payload: dict = Depends(jwt_bearer),
    db: Session = Depends(get_db),
):
    require_admin(payload, db)
    succeeded = []
    failed = []
    for fid in req.finding_ids:
        result = remediate_finding(fid, db)
        if result["success"]:
            succeeded.append(fid)
        else:
            failed.append({"finding_id": fid, "reason": result.get("message")})
    return {
        "total": len(req.finding_ids),
        "succeeded": len(succeeded),
        "failed": len(failed),
        "succeeded_ids": succeeded,
        "failed_details": failed,
    }


@router.post("/remediate/{finding_id}")
def remediate_one(
    finding_id: int,
    background_tasks: BackgroundTasks,
    payload: dict = Depends(jwt_bearer),
    db: Session = Depends(get_db),
):
    require_admin(payload, db)
    result = remediate_finding(finding_id, db)

    if result.get("success"):
        remediated_by = payload.get("sub", "unknown")
        # Send email in background — doesn't block the API response
        background_tasks.add_task(
            send_remediation_email,
            resource_id        = result.get("resource_id", ""),
            resource_name      = result.get("resource_name") or result.get("resource_id", ""),
            resource_type      = result.get("resource_type", ""),
            region             = result.get("region", ""),
            action             = result.get("action_taken", "Remediated"),
            savings_per_month  = result.get("estimated_monthly_waste_usd", 0.0),
            remediated_by      = remediated_by,
            timestamp          = result.get("timestamp"),
        )
        result["email_sent"]       = True   # optimistic — fires in background
        result["notification_email"] = NOTIFICATION_EMAIL

    return result


@router.get("/summary")
def get_summary(payload: dict = Depends(jwt_bearer), db: Session = Depends(get_db)):
    total_waste = db.query(func.sum(Finding.estimated_monthly_waste_usd)).scalar() or 0.0

    by_severity = (
        db.query(Finding.severity, func.count(Finding.id))
        .group_by(Finding.severity)
        .all()
    )

    by_type = (
        db.query(Resource.resource_type, func.count(Finding.id))
        .join(Finding, Finding.resource_id == Resource.id)
        .group_by(Resource.resource_type)
        .all()
    )

    top_resources = (
        db.query(
            Resource.resource_id,
            Resource.resource_name,
            Resource.resource_type,
            Finding.estimated_monthly_waste_usd,
        )
        .join(Finding, Finding.resource_id == Resource.id)
        .order_by(Finding.estimated_monthly_waste_usd.desc())
        .limit(3)
        .all()
    )

    pending_count = db.query(Finding).filter(Finding.status == "pending").count()

    return {
        "total_waste_usd": round(total_waste, 2),
        "pending_remediations": pending_count,
        "findings_by_severity": {row[0]: row[1] for row in by_severity},
        "findings_by_resource_type": {row[0]: row[1] for row in by_type},
        "top_3_wasteful_resources": [
            {
                "resource_id": r[0],
                "resource_name": r[1],
                "resource_type": r[2],
                "estimated_monthly_waste_usd": r[3],
            }
            for r in top_resources
        ],
    }


@router.get("/users")
def list_users(payload: dict = Depends(jwt_bearer), db: Session = Depends(get_db)):
    require_admin(payload, db)
    users = db.query(User).order_by(User.id).all()
    return [
        {"id": u.id, "username": u.username, "email": u.email, "role": u.role, "created_at": u.created_at, "is_active": u.is_active}
        for u in users
    ]


@router.delete("/data")
def clear_data(payload: dict = Depends(jwt_bearer), db: Session = Depends(get_db)):
    require_admin(payload, db)
    db.query(RemediationCommand).delete()
    db.query(Finding).delete()
    db.query(Resource).delete()
    db.commit()
    return {"message": "All resources, findings, and remediation commands have been cleared."}
