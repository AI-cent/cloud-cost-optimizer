import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from logger import setup_logging
from database import init_db
from api.routes import router

setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application starting up — initialising database")
    init_db()
    logger.info("Database initialised. Cloud Cost Optimizer is ready.")
    yield
    logger.info("Application shutting down.")


app = FastAPI(
    title="Cloud Cost Optimizer",
    description="API-first AWS orphaned resource detector and remediation engine",
    version="1.0.0",
    lifespan=lifespan,
)

# ── CORS — allow only localhost origins ───────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost",
        "http://localhost:8000",
        "http://127.0.0.1",
        "http://127.0.0.1:8000",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

# ── Global exception handler — no stack traces ever reach the client ──────────
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception on %s %s: %s", request.method, request.url.path, exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "internal_server_error", "detail": "An unexpected error occurred."},
    )

# Jinja2 templates
templates = Jinja2Templates(directory="dashboard/templates")

# Include all routes
app.include_router(router)
