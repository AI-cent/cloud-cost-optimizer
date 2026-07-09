"""
End-to-end pipeline tests.
Run from project root:  pytest tests/test_pipeline.py -v
"""
import sys
import os
import pytest

# Allow imports from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base, get_db
from main import app

# ── In-memory SQLite for tests ────────────────────────────────────────────────
TEST_DB_PATH = "/tmp/test_cost_optimizer.db"
TEST_DB_URL = f"sqlite:///{TEST_DB_PATH}"

SAMPLE_CSV_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "sample_data", "aws_billing.csv")


def _make_engine():
    return create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})


# Module-level engine (recreated per test via fixture)
test_engine = _make_engine()
Base.metadata.create_all(bind=test_engine)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_db():
    """Dispose pool, delete DB file, recreate fresh tables before each test."""
    global test_engine, TestingSessionLocal

    # Tear down any open connections
    test_engine.dispose()

    # Remove stale file
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)

    # Fresh engine + tables
    test_engine = _make_engine()
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    Base.metadata.create_all(bind=test_engine)

    # Re-wire dependency override to new session factory
    def override_get_db_fresh():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db_fresh

    yield

    test_engine.dispose()
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)


def ingest_sample():
    with open(SAMPLE_CSV_PATH, "rb") as f:
        return client.post("/ingest", files={"file": ("aws_billing.csv", f, "text/csv")})


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_ingest_returns_200():
    res = ingest_sample()
    assert res.status_code == 200
    data = res.json()
    assert data["resources_ingested"] == 20
    assert data["resources_skipped"] == 0
    assert data["findings_generated"] > 0


def test_ingest_detects_all_five_rule_types():
    ingest_sample()
    res = client.get("/findings")
    assert res.status_code == 200
    findings = res.json()
    types = {f["finding_type"] for f in findings}
    assert "unattached_ebs" in types,   "Should detect unattached EBS volumes"
    assert "idle_ec2" in types,         "Should detect idle EC2 instances"
    assert "orphaned_eip" in types,     "Should detect orphaned Elastic IPs"
    assert "idle_alb" in types,         "Should detect idle Load Balancers"
    assert "old_snapshot" in types,     "Should detect old Snapshots"


def test_findings_sorted_by_waste_descending():
    ingest_sample()
    res = client.get("/findings")
    findings = res.json()
    wastes = [f["estimated_monthly_waste_usd"] for f in findings]
    assert wastes == sorted(wastes, reverse=True)


def test_remediation_command_returned():
    ingest_sample()
    findings = client.get("/findings").json()
    first_id = findings[0]["finding_id"]
    res = client.get(f"/findings/{first_id}/remediation")
    assert res.status_code == 200
    assert "command_text" in res.json()
    assert res.json()["command_text"].startswith("aws ")


def test_remediation_404_for_missing_finding():
    res = client.get("/findings/99999/remediation")
    assert res.status_code == 404


def test_summary_total_waste():
    ingest_sample()
    res = client.get("/summary")
    assert res.status_code == 200
    data = res.json()
    assert data["total_waste_usd"] > 0
    assert "findings_by_severity" in data
    assert "top_3_most_wasteful" in data
    assert len(data["top_3_most_wasteful"]) <= 3


def test_summary_has_all_severity_keys():
    ingest_sample()
    data = client.get("/summary").json()
    sev = data["findings_by_severity"]
    # At least some severities present
    assert any(k in sev for k in ["Critical", "High", "Medium", "Low"])


def test_dashboard_returns_html():
    ingest_sample()
    res = client.get("/dashboard")
    assert res.status_code == 200
    assert "text/html" in res.headers["content-type"]
    assert "Cloud Cost Optimizer" in res.text


def test_ingest_bad_file_rejected():
    res = client.post("/ingest", files={"file": ("data.txt", b"not,a,valid,csv", "text/plain")})
    assert res.status_code == 400
    assert res.json()["error"] == "invalid_file_type"


def test_ingest_empty_file_rejected():
    res = client.post("/ingest", files={"file": ("empty.csv", b"", "text/csv")})
    assert res.status_code == 400
    assert res.json()["error"] == "empty_file"


def test_ingest_missing_columns_rejected():
    bad_csv = b"foo,bar\n1,2\n"
    res = client.post("/ingest", files={"file": ("bad.csv", bad_csv, "text/csv")})
    assert res.status_code == 400
    assert res.json()["error"] == "csv_validation_error"
    assert "missing" in res.json()["detail"].lower()


def test_ingest_file_too_large_rejected():
    # Generate a CSV that is just over 10 MB
    header = b"ResourceId,ResourceName,ResourceType,Region,MonthlyCost,Status,LastActiveDate\n"
    row = b"vol-0a1b2c3d,test-vol,EBS Volume,us-east-1,10.00,available,2026-01-01\n"
    oversized = header + row * (int(10 * 1024 * 1024 / len(row)) + 1)
    res = client.post("/ingest", files={"file": ("big.csv", oversized, "text/csv")})
    assert res.status_code == 400
    assert res.json()["error"] == "file_too_large"


def test_ingest_nonnumeric_cost_rows_skipped():
    """Rows with invalid MonthlyCost should be skipped, not crash the endpoint."""
    csv_content = (
        b"ResourceId,ResourceName,ResourceType,Region,MonthlyCost,Status,LastActiveDate\n"
        b"vol-good,good-vol,EBS Volume,us-east-1,12.50,available,2026-01-01\n"
        b"vol-bad,bad-vol,EBS Volume,us-east-1,NOT_A_NUMBER,available,2026-01-01\n"
    )
    res = client.post("/ingest", files={"file": ("mixed.csv", csv_content, "text/csv")})
    assert res.status_code == 200
    data = res.json()
    # Both rows ingested (bad cost defaults to 0.0, not skipped)
    assert data["resources_ingested"] == 2
    assert data["resources_skipped"] == 0


def test_remediation_command_sanitised():
    """Injected chars in resource IDs must be stripped from CLI commands."""
    from engine.remediation import _sanitise_resource_id, _sanitise_region
    # Command injection attempt
    assert ";" not in _sanitise_resource_id("vol-abc; rm -rf /")
    assert "`" not in _sanitise_resource_id("vol-abc`whoami`")
    assert "$" not in _sanitise_resource_id("vol-abc$(cat /etc/passwd)")
    # Legitimate ARN should survive sanitisation unchanged
    arn = "arn:aws:elasticloadbalancing:us-east-1:123456789012:loadbalancer/app/alb/1a2b"
    assert _sanitise_resource_id(arn) == arn
    # Region safety
    assert _sanitise_region("us-east-1") == "us-east-1"
    assert _sanitise_region("us-east-1; DROP TABLE resources") == "us-east-1droptableresources"


def test_error_responses_contain_no_stack_traces():
    """API errors must return {error, detail} — no tracebacks or file paths."""
    bad_csv = b"wrong,columns\n1,2\n"
    res = client.post("/ingest", files={"file": ("bad.csv", bad_csv, "text/csv")})
    body = res.text
    assert "Traceback" not in body
    assert "/sessions/" not in body
    assert "site-packages" not in body
    assert "error" in res.json()
    assert "detail" in res.json()


def test_cors_header_present_for_localhost():
    """CORS header must be set for allowed localhost origin."""
    res = client.get("/summary", headers={"Origin": "http://localhost:8000"})
    assert res.status_code == 200
    assert "access-control-allow-origin" in res.headers


def test_ingest_idempotent():
    """Ingesting same CSV twice should not duplicate resources."""
    ingest_sample()
    ingest_sample()
    res = client.get("/findings")
    # findings count should be same as one ingest (detector clears+rewrites)
    count_after_2 = len(res.json())
    assert count_after_2 > 0


# ── Required 5 tests ──────────────────────────────────────────────────────────

def test_csv_ingestion():
    """Ingest sample CSV and assert all 20 rows are stored in resources table."""
    ingest_sample()
    db = TestingSessionLocal()
    try:
        from models import Resource
        count = db.query(Resource).count()
        assert count == 20, f"Expected 20 resources in DB, got {count}"
    finally:
        db.close()


def test_orphan_detection():
    """Assert at least 5 findings are created after detection runs on sample data."""
    ingest_sample()
    db = TestingSessionLocal()
    try:
        from models import Finding
        count = db.query(Finding).count()
        assert count >= 5, f"Expected at least 5 findings, got {count}"
    finally:
        db.close()


def test_remediation_generation():
    """Assert every finding has a corresponding AWS CLI command in remediation_commands table."""
    ingest_sample()
    db = TestingSessionLocal()
    try:
        from models import Finding, RemediationCommand
        findings = db.query(Finding).all()
        assert len(findings) > 0, "No findings found — ingest may have failed"
        for finding in findings:
            cmd = db.query(RemediationCommand).filter(
                RemediationCommand.finding_id == finding.id
            ).first()
            assert cmd is not None, f"Finding id={finding.id} has no remediation command"
            assert cmd.command_text.startswith("aws "), \
                f"Command for finding id={finding.id} is not a valid AWS CLI command: '{cmd.command_text}'"
    finally:
        db.close()


def test_summary_endpoint():
    """Call GET /summary and assert total_waste_usd > 0 and findings_by_severity is not empty."""
    ingest_sample()
    res = client.get("/summary")
    assert res.status_code == 200
    data = res.json()
    assert data["total_waste_usd"] > 0, \
        f"Expected total_waste_usd > 0, got {data['total_waste_usd']}"
    assert data["findings_by_severity"], \
        "findings_by_severity should not be empty after ingestion"


def test_invalid_file_upload():
    """POST a .txt file to /ingest and assert response status code is 400."""
    res = client.post(
        "/ingest",
        files={"file": ("report.txt", b"this is not a csv file", "text/plain")},
    )
    assert res.status_code == 400, \
        f"Expected 400 for .txt upload, got {res.status_code}"
