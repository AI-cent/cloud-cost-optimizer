import logging
import os
from dotenv import load_dotenv

# Load .env BEFORE any module that reads env vars (especially auth_handler)
load_dotenv()

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from logging.handlers import RotatingFileHandler

_log_fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

_console_handler = logging.StreamHandler()
_console_handler.setFormatter(_log_fmt)

_log_file = os.getenv("LOG_FILE", os.path.join(os.path.dirname(__file__), "app.log"))
_file_handler = RotatingFileHandler(
    _log_file, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
)
_file_handler.setFormatter(_log_fmt)

logging.basicConfig(level=logging.INFO, handlers=[_console_handler, _file_handler])

from database import engine, Base
from api.routes import router
from sqlalchemy import text

# Create all DB tables on startup
Base.metadata.create_all(bind=engine)

# Migrate: add role column to existing databases that predate this change
with engine.connect() as conn:
    try:
        conn.execute(text("ALTER TABLE users ADD COLUMN role VARCHAR DEFAULT 'viewer' NOT NULL"))
        conn.commit()
        # Promote first user to admin if they were created before roles existed
        conn.execute(text("UPDATE users SET role='admin' WHERE id=(SELECT MIN(id) FROM users)"))
        conn.commit()
    except Exception:
        pass  # Column already exists — safe to ignore

app = FastAPI(
    title=os.getenv("APP_NAME", "Cloud Cost Optimizer"),
    description="API-first Cloud Cost Optimizer & Remediation Engine",
    version="1.0.0",
)

# ── CORS: restrict to localhost origins only ─────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Standardised error responses ────────────────────────────────────────────

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    # Extract human-readable messages; strip non-serialisable objects
    messages = [f"{' → '.join(str(l) for l in e['loc'])}: {e['msg']}" for e in exc.errors()]
    return JSONResponse(
        status_code=422,
        content={"error": "Validation error", "detail": messages},
    )

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logging.getLogger("app").error(
        "UNHANDLED_ERROR endpoint=%s %s detail=%s",
        request.method, request.url.path, str(exc), exc_info=True,
    )
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": "An unexpected error occurred."},
    )

app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
