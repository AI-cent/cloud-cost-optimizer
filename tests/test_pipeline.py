"""
pytest test suite for Cloud Cost Optimizer
Run: pytest tests/ -v
"""
import pytest
from fastapi.testclient import TestClient
import io
import csv

# Use /tmp SQLite for tests (avoids read-only filesystem issues)
TEST_DATABASE_URL = "sqlite:////tmp/test_cost_optimizer.db"

import os
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-pytest"

# Remove stale test db if exists
if os.path.exists("/tmp/test_cost_optimizer.db"):
    os.remove("/tmp/test_cost_optimizer.db")

from database import Base, get_db
import database as _db_module

# Patch the engine in the database module to use test DB
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

test_engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
_db_module.engine = test_engine
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
_db_module.SessionLocal = TestingSessionLocal

from main import app

Base.metadata.create_all(bind=test_engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

# Remove the duplicate engine import that was already done above
client = TestClient(app)

# ── Sample CSV ──
SAMPLE_CSV = """resource_id,resource_name,resource_type,region,monthly_cost_usd,status,last_active_date
vol-test001,test-volume,EBS Volume,us-east-1,50.00,available,2024-01-01
i-test002,idle-instance,EC2 Instance,us-east-1,100.00,running,2020-01-01
eipalloc-test003,unused-ip,Elastic IP,us-east-1,3.65,unassociated,2024-01-01
arn:aws:elasticloadbalancing:us-east-1:123:loadbalancer/app/test/abc,idle-lb,Load Balancer,us-east-1,22.00,idle,2024-01-01
snap-test005,old-snap,Snapshot,us-east-1,8.00,completed,2020-01-01
"""

TOKEN = None
FINDING_ID = None


class TestAuth:
    def test_register(self):
        res = client.post("/auth/register", json={
            "username": "testuser", "email": "test@example.com", "password": "testpass123"
        })
        assert res.status_code == 200
        assert "registered" in res.json()["message"]

    def test_register_duplicate(self):
        res = client.post("/auth/register", json={
            "username": "testuser", "email": "test@example.com", "password": "testpass123"
        })
        assert res.status_code == 400

    def test_login_success(self):
        global TOKEN
        res = client.post("/auth/login", json={"username": "testuser", "password": "testpass123"})
        assert res.status_code == 200
        TOKEN = res.json()["access_token"]
        assert TOKEN is not None

    def test_login_wrong_password(self):
        res = client.post("/auth/login", json={"username": "testuser", "password": "wrong"})
        assert res.status_code == 401

    def test_me(self):
        res = client.get("/auth/me", headers={"Authorization": f"Bearer {TOKEN}"})
        assert res.status_code == 200
        assert res.json()["username"] == "testuser"

    def test_protected_without_token(self):
        res = client.get("/findings")
        assert res.status_code in (401, 403)  # HTTPBearer returns 403; missing header returns 401


class TestIngest:
    def test_ingest_csv(self):
        global FINDING_ID
        res = client.post(
            "/ingest",
            headers={"Authorization": f"Bearer {TOKEN}"},
            files={"file": ("aws_billing.csv", SAMPLE_CSV.encode(), "text/csv")},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["resources_ingested"] == 5
        assert data["findings_detected"] == 5  # All 5 rules should trigger

    def test_ingest_wrong_format(self):
        res = client.post(
            "/ingest",
            headers={"Authorization": f"Bearer {TOKEN}"},
            files={"file": ("data.txt", b"not a csv", "text/plain")},
        )
        assert res.status_code == 400


class TestFindings:
    def test_get_findings(self):
        global FINDING_ID
        res = client.get("/findings", headers={"Authorization": f"Bearer {TOKEN}"})
        assert res.status_code == 200
        findings = res.json()
        assert len(findings) >= 5
        # Sorted by estimated_monthly_waste_usd descending
        wastes = [f["estimated_monthly_waste_usd"] for f in findings]
        assert wastes == sorted(wastes, reverse=True)
        FINDING_ID = findings[0]["id"]

    def test_finding_status(self):
        res = client.get(f"/findings/{FINDING_ID}/status", headers={"Authorization": f"Bearer {TOKEN}"})
        assert res.status_code == 200
        assert res.json()["status"] == "pending"

    def test_finding_remediation_command(self):
        res = client.get(f"/findings/{FINDING_ID}/remediation", headers={"Authorization": f"Bearer {TOKEN}"})
        assert res.status_code == 200
        assert "command_text" in res.json()
        assert len(res.json()["command_text"]) > 5


class TestSummary:
    def test_summary(self):
        res = client.get("/summary", headers={"Authorization": f"Bearer {TOKEN}"})
        assert res.status_code == 200
        data = res.json()
        assert "total_waste_usd" in data
        assert data["total_waste_usd"] > 0
        assert "findings_by_severity" in data
        assert "top_3_wasteful_resources" in data


class TestRemediation:
    def test_remediate_no_aws_creds(self):
        """Should fail gracefully with CLI alternative when no AWS creds."""
        res = client.post(f"/remediate/{FINDING_ID}", headers={"Authorization": f"Bearer {TOKEN}"})
        assert res.status_code == 200
        data = res.json()
        # Either success or graceful failure with CLI alternative
        assert "success" in data
        if not data["success"]:
            assert "cli_alternative" in data or "message" in data

    def test_bulk_remediate(self):
        res_findings = client.get("/findings", headers={"Authorization": f"Bearer {TOKEN}"})
        ids = [f["id"] for f in res_findings.json()[:2]]
        res = client.post(
            "/remediate/bulk",
            headers={"Authorization": f"Bearer {TOKEN}"},
            json={"finding_ids": ids},
        )
        assert res.status_code == 200
        data = res.json()
        assert "total" in data
        assert data["total"] == len(ids)


class TestClearData:
    def test_clear_data(self):
        res = client.delete("/data", headers={"Authorization": f"Bearer {TOKEN}"})
        assert res.status_code == 200
        assert "cleared" in res.json()["message"].lower()

    def test_findings_empty_after_clear(self):
        res = client.get("/findings", headers={"Authorization": f"Bearer {TOKEN}"})
        assert res.status_code == 200
        assert res.json() == []


class TestDashboard:
    def test_dashboard_no_auth_required(self):
        res = client.get("/dashboard")
        assert res.status_code == 200
        assert "Cloud Cost Optimizer" in res.text
