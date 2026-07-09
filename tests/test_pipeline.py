"""
Integration test suite for the Cloud Cost Optimizer pipeline.
Run with:  pytest tests/test_pipeline.py -v
"""
import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Use in-memory SQLite for tests
os.environ["DATABASE_URL"] = "sqlite:////tmp/test_cloud_optimizer.db"
os.environ["JWT_SECRET_KEY"] = "test-secret-key"

from database import Base, get_db
from main import app

TEST_DB_URL = "sqlite:////tmp/test_cloud_optimizer.db"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="module", autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    # cleanup file
    if os.path.exists("/tmp/test_cloud_optimizer.db"):
        os.remove("/tmp/test_cloud_optimizer.db")


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

# ── Shared state ──
AUTH = {}

SAMPLE_CSV = b"""resource_id,resource_name,resource_type,region,monthly_cost_usd,status,last_active_date
vol-test001,test-ebs,EBS Volume,us-east-1,40.00,available,2026-01-01
i-test001,idle-ec2,EC2 Instance,us-east-1,150.00,running,2025-12-01
eipalloc-test001,orphan-eip,Elastic IP,us-east-1,3.65,unassociated,2026-03-01
arn:aws:elasticloadbalancing:us-east-1:123:loadbalancer/app/idle/abc,idle-alb,Load Balancer,us-east-1,20.00,idle,2026-01-01
snap-test001,old-snap,Snapshot,us-east-1,5.00,completed,2025-09-01
"""


# ── 1. Register ──
def test_register():
    res = client.post("/auth/register", json={
        "username": "testuser",
        "email": "test@example.com",
        "password": "Password123!",
    })
    assert res.status_code == 200
    assert "registered" in res.json()["message"].lower()


# ── 2. Duplicate register ──
def test_register_duplicate():
    res = client.post("/auth/register", json={
        "username": "testuser",
        "email": "test@example.com",
        "password": "Password123!",
    })
    assert res.status_code == 400


# ── 3. Login ──
def test_login():
    res = client.post("/auth/login", json={"username": "testuser", "password": "Password123!"})
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    AUTH["token"] = data["access_token"]
    AUTH["headers"] = {"Authorization": f"Bearer {data['access_token']}"}


# ── 4. Bad login ──
def test_login_wrong_password():
    res = client.post("/auth/login", json={"username": "testuser", "password": "wrongpass"})
    assert res.status_code == 401


# ── 5. Me endpoint ──
def test_me():
    res = client.get("/auth/me", headers=AUTH["headers"])
    assert res.status_code == 200
    assert res.json()["username"] == "testuser"


# ── 6. Protected route without token ──
def test_protected_without_token():
    res = client.get("/findings")
    assert res.status_code in (401, 403)  # HTTPBearer returns 401 or 403 depending on version


# ── 7. Ingest CSV ──
def test_ingest_csv():
    res = client.post(
        "/ingest",
        headers=AUTH["headers"],
        files={"file": ("aws_billing.csv", SAMPLE_CSV, "text/csv")},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["resources_ingested"] == 5
    assert data["findings_detected"] == 5  # all 5 rule types triggered


# ── 8. Get findings ──
def test_get_findings():
    res = client.get("/findings", headers=AUTH["headers"])
    assert res.status_code == 200
    findings = res.json()
    assert len(findings) >= 5
    # Sorted by waste descending
    wastes = [f["estimated_monthly_waste_usd"] for f in findings]
    assert wastes == sorted(wastes, reverse=True)


# ── 9. All 5 finding types present ──
def test_finding_types():
    res = client.get("/findings", headers=AUTH["headers"])
    types = {f["finding_type"] for f in res.json()}
    expected = {"unattached_ebs", "idle_ec2", "orphaned_eip", "idle_alb", "old_snapshot"}
    assert expected == types


# ── 10. Get finding status ──
def test_finding_status():
    res = client.get("/findings/1/status", headers=AUTH["headers"])
    assert res.status_code == 200
    assert res.json()["status"] == "pending"


# ── 11. Get remediation CLI command ──
def test_remediation_command():
    res = client.get("/findings/1/remediation", headers=AUTH["headers"])
    assert res.status_code == 200
    data = res.json()
    assert data["cli_command"] is not None
    assert "aws" in data["cli_command"]


# ── 12. Summary endpoint ──
def test_summary():
    res = client.get("/summary", headers=AUTH["headers"])
    assert res.status_code == 200
    data = res.json()
    assert "total_waste_usd" in data
    assert data["total_waste_usd"] > 0
    assert "findings_by_severity" in data
    assert "waste_by_resource_type" in data
    assert "top_3_wasteful_resources" in data
    assert len(data["top_3_wasteful_resources"]) <= 3


# ── 13. Remediate single (will fail gracefully — no real AWS creds) ──
def test_remediate_single():
    res = client.post("/remediate/1", headers=AUTH["headers"])
    assert res.status_code == 200
    data = res.json()
    assert "success" in data
    assert "message" in data
    # Either success or graceful failure with CLI hint
    assert data["status"] in ("remediated", "failed")


# ── 14. Bulk remediate ──
def test_bulk_remediate():
    res = client.post(
        "/remediate/bulk",
        headers=AUTH["headers"],
        json={"finding_ids": [2, 3]},
    )
    assert res.status_code == 200
    data = res.json()
    assert "succeeded" in data
    assert "failed" in data
    assert data["succeeded"] + data["failed"] == 2


# ── 15. 404 on missing finding ──
def test_finding_not_found():
    res = client.get("/findings/9999/status", headers=AUTH["headers"])
    assert res.status_code == 404


# ── 16. Ingest bad file type ──
def test_ingest_non_csv():
    res = client.post(
        "/ingest",
        headers=AUTH["headers"],
        files={"file": ("data.txt", b"not a csv", "text/plain")},
    )
    assert res.status_code == 400


# ── 17. Clear data ──
def test_clear_data():
    res = client.delete("/data", headers=AUTH["headers"])
    assert res.status_code == 200
    assert "cleared" in res.json()["message"].lower()
    # Verify empty
    findings = client.get("/findings", headers=AUTH["headers"]).json()
    assert findings == []


# ── 18. Dashboard route accessible without token ──
def test_dashboard_no_auth():
    res = client.get("/dashboard")
    assert res.status_code == 200
    assert "Cloud Cost Optimizer" in res.text
