from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv
import os

from database import engine, Base
from api.routes import router
from sqlalchemy import text

load_dotenv()

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

app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
