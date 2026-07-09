# Cloud Cost Optimizer & Remediation Engine

An API-first Python tool that ingests AWS billing exports, detects orphaned/idle
resources, generates AWS CLI remediation commands, and displays everything in a
live Chart.js dashboard — all backed by a zero-config SQLite database.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                        CLIENT / BROWSER                       │
│              GET /dashboard  ·  POST /ingest                 │
└───────────────────────────┬──────────────────────────────────┘
                            │ HTTP
┌───────────────────────────▼──────────────────────────────────┐
│                    FastAPI  (main.py)                         │
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │                   api/routes.py                         │  │
│  │  POST /ingest  GET /findings  GET /summary              │  │
│  │  GET /findings/{id}/remediation   GET /dashboard        │  │
│  └────────┬──────────────────────────────┬────────────────┘  │
│           │                              │                    │
│  ┌────────▼─────────┐        ┌──────────▼───────────────┐   │
│  │ parser/           │        │ engine/                   │   │
│  │  aws_parser.py   │        │  orphan_detector.py       │   │
│  │                  │        │  remediation.py            │   │
│  │  • CSV ingest    │        │  • 5 detection rules       │   │
│  │  • upsert rows   │        │  • AWS CLI cmd generation  │   │
│  └────────┬─────────┘        └──────────┬───────────────┘   │
│           │                              │                    │
│  ┌────────▼──────────────────────────────▼───────────────┐   │
│  │               SQLite  (cost_optimizer.db)              │   │
│  │   resources  │  findings  │  remediation_commands      │   │
│  └───────────────────────────────────────────────────────┘   │
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │  dashboard/templates/index.html  (Jinja2 + Chart.js)    │  │
│  │   • Summary cards  • Bar chart  • Doughnut  • Table     │  │
│  └─────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

---

## Quick Start

### 1. Install dependencies
```bash
cd cloud-cost-optimizer
pip install -r requirements.txt
```

### 2. Run the server
```bash
uvicorn main:app --reload --port 8000
```

### 3. Ingest sample AWS billing data
```bash
curl -X POST http://localhost:8000/ingest \
  -F "file=@sample_data/aws_billing.csv"
```

### 4. Open the dashboard
```
http://localhost:8000/dashboard
```

### 5. Explore the API
```bash
# All findings sorted by waste
curl http://localhost:8000/findings

# Summary totals
curl http://localhost:8000/summary

# Remediation command for finding #1
curl http://localhost:8000/findings/1/remediation
```

Interactive API docs: `http://localhost:8000/docs`

---

## Detection Rules

| Rule              | Condition                                      | Severity |
|-------------------|------------------------------------------------|----------|
| Unattached EBS    | EBS Volume with status = `available`           | High     |
| Idle EC2          | EC2 Instance last active > 30 days ago         | Critical |
| Orphaned EIP      | Elastic IP with status = `unassociated`        | Medium   |
| Idle Load Balancer| Load Balancer with status = `idle`             | High     |
| Old Snapshot      | Snapshot last active > 90 days ago             | Low      |

---

## Running Tests
```bash
pip install pytest httpx
pytest tests/test_pipeline.py -v
```

---

## Project Structure
```
cloud-cost-optimizer/
├── main.py                        # FastAPI app entry point
├── database.py                    # SQLAlchemy engine + session
├── models.py                      # ORM models (3 tables)
├── parser/
│   └── aws_parser.py              # CSV ingestion & upsert
├── engine/
│   ├── orphan_detector.py         # 5 detection rules
│   └── remediation.py             # AWS CLI command generator
├── api/
│   └── routes.py                  # All API endpoints
├── dashboard/
│   └── templates/index.html       # Chart.js dashboard (Jinja2)
├── sample_data/
│   └── aws_billing.csv            # 20-row realistic test data
├── tests/
│   └── test_pipeline.py           # End-to-end pytest suite
├── prompts.md                     # Architect prompt audit log
├── requirements.txt
└── README.md
```

---

## Extending to Real AWS Data

Replace sample CSV with an actual AWS Cost & Usage Report export (CUR).
Map the CUR columns to the parser's expected headers, or modify
`parser/aws_parser.py` to accept CUR's native column names.

To execute remediation commands for real:
```bash
# Example: delete an unattached EBS volume
aws ec2 delete-volume --volume-id vol-0a1b2c3d4e5f6a7b8 --region us-east-1
```

> ⚠️ Always review remediation commands before executing in production.
