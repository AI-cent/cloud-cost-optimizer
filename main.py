from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.templating import Jinja2Templates
from database import init_db
from api.routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Cloud Cost Optimizer",
    description="API-first AWS orphaned resource detector and remediation engine",
    version="1.0.0",
    lifespan=lifespan,
)

# Jinja2 templates
templates = Jinja2Templates(directory="dashboard/templates")

# Include all routes
app.include_router(router)
