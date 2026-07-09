from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv
import os

from database import engine, Base
from api.routes import router

load_dotenv()

# Create all DB tables on startup
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=os.getenv("APP_NAME", "Cloud Cost Optimizer"),
    description="API-first Cloud Cost Optimizer & Remediation Engine",
    version="1.0.0",
)

app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
