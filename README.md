# Cloud Cost Optimizer

An API-first AWS Cloud Cost Analysis & Remediation Engine built with FastAPI, SQLite, and a Chart.js dashboard.

```
┌─────────────────────────────────────────────────────────────────┐
│                    CLOUD COST OPTIMIZER                         │
│                                                                 │
│  ┌──────────────┐     ┌──────────────┐     ┌───────────────┐   │
│  │   Browser    │────▶│   FastAPI    │────▶│   SQLite DB   │   │
│  │  Dashboard   │◀────│   Backend    │◀────│  (4 tables)   │   │
│  │  (Chart.js)  │     │  (main.py)   │     └───────────────┘   │
│  └──────────────┘     └──────┬───────┘                         │
│                              │                                  │
│              ┌───────────────┼───────────────┐                  │
│              ▼               ▼               ▼                  │
│       ┌────────────┐  ┌────────────┐  ┌────────────┐           │
│       │   Parser   │  │   Engine   │  │    Auth    │           │
│       │ aws_parser │  │  orphan_   │  │   (JWT +   │           │
│       │   .py      │  │ detector + │  │  bcrypt)   │           │
│       └────────────┘  │remediation │  └────────────┘           │
│                       └────────────┘                            │
│                              │                                  │
│                              ▼                                  │
│                       ┌────────────┐                            │
│                       │   boto3    │                            │
│                       │ (AWS SDK)  │                            │
│                       └────────────┘                            │
└─────────────────────────────────────────────────────────────────┘
```

## Features

- **JWT Authentication** — register, login, protected endpoints
- **CSV Ingest** — parse AWS Cost and Usage Report exports
- **5 Orphan Detection Rules** — EBS volumes, idle EC2, orphaned EIPs, idle load balancers, old snapshots
- **Remediation** — AWS CLI commands generated for every finding; boto3 execution with graceful fallback
- **Dashboard** — live Chart.js charts, drag-and-drop CSV upload, one-click remediation

## Quick Start

### 1. Install dependencies

```bash
cd cloud-cost-optimizer
pip install -r requirements.txt
```

### 2. Configure environment

Edit `.env`:
```
JWT_SECRET_KEY=your-super-secret-key-here
```

### 3. Run the server

```bash
uvicorn main:app --reload
```

- API docs: http://localhost:8000/docs
- Dashboard: http://localhost:8000/dashboard

### 4. First use

1. Open http://localhost:8000/dashboard
2. Register an account
3. Upload `sample_data/aws_billing.csv`
4. View findings and click Remediate

## Running Tests

```bash
pytest tests/test_pipeline.py -v
```

## API Reference

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/auth/register` | No | Register new user |
| POST | `/auth/login` | No | Login, returns JWT |
| GET | `/auth/me` | Yes | Current user info |
| POST | `/ingest` | Yes | Upload AWS billing CSV |
| GET | `/findings` | Yes | All findings, sorted by waste |
| GET | `/findings/{id}/remediation` | Yes | CLI command for finding |
| GET | `/findings/{id}/status` | Yes | Finding status |
| POST | `/remediate/{id}` | Yes | Remediate via boto3 |
| POST | `/remediate/bulk` | Yes | Bulk remediation |
| GET | `/summary` | Yes | Waste totals and breakdowns |
| DELETE | `/data` | Yes | Clear all data |
| GET | `/dashboard` | No | HTML dashboard |

## Database Schema

```
users               resources              findings
─────────────       ─────────────────      ───────────────────
id (PK)             id (PK)                id (PK)
username            resource_id            resource_id (FK)
email               resource_name          finding_type
hashed_password     resource_type          severity
created_at          region                 estimated_waste_usd
is_active           monthly_cost_usd       status
                    status                 remediated_at
                    last_active_date       detected_at
                    ingest_timestamp
                    uploaded_by (FK)       remediation_commands
                                           ────────────────────
                                           id (PK)
                                           finding_id (FK)
                                           command_type
                                           command_text
                                           generated_at
```

## Orphan Detection Rules

| Rule | Condition | Severity |
|------|-----------|----------|
| Unattached EBS Volume | status = available | High |
| Idle EC2 Instance | last_active > 30 days | Critical |
| Orphaned Elastic IP | status = unassociated | Medium |
| Idle Load Balancer | status = idle | High |
| Old Snapshot | last_active > 90 days | Low |

## AWS Credentials (for boto3 remediation)

```bash
aws configure
# or
export AWS_ACCESS_KEY_ID=your-key
export AWS_SECRET_ACCESS_KEY=your-secret
export AWS_DEFAULT_REGION=us-east-1
```

If credentials are not configured, the API returns the equivalent AWS CLI command to run manually.
