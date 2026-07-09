from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from fastapi.responses import HTMLResponse

from database import engine, Base
from api.routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create all tables on startup
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    lifespan=lifespan,
    title="Cloud Cost Optimizer",
    description="API-first AWS cloud cost analysis and remediation engine",
    version="1.0.0",
)

templates = Jinja2Templates(directory="dashboard/templates")

# Mount all API routes
app.include_router(router)


@app.get("/dashboard", response_class=HTMLResponse, tags=["Dashboard"])
def dashboard(request: Request):
    """Serve the HTML dashboard. No JWT required — auth is handled client-side."""
    return templates.TemplateResponse(request=request, name="index.html")


@app.get("/", include_in_schema=False)
def root():
    return {"message": "Cloud Cost Optimizer API — visit /docs or /dashboard"}
