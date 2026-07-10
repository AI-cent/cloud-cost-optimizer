# Cloud Cost Optimizer & Remediation Engine

An API-first Python backend with a Chart.js dashboard that detects orphaned AWS resources, quantifies monthly waste, and remediates findings with one click. Built in Lead Architect Mode — architecture designed by a human, all code written by AI, zero manual edits across 35 prompts.

> **Demo mode** (`DEMO_MODE=true`) runs a 10-second simulation with no AWS credentials required — safe for local demos and recruiter walkthroughs.

---

## Table of Contents

1. [Overview](#1-overview)
2. [Architecture](#2-architecture)
3. [Quick Start](#3-quick-start)
4. [Authentication](#4-authentication)
5. [Upload & Ingest](#5-upload--ingest)
6. [API Reference](#6-api-reference)
7. [AWS Testing](#7-aws-testing)
8. [Tests](#8-tests)
9. [Stack](#9-stack)
10. [Security](#10-security)
11. [What's Next](#11-whats-next)

---

## 1. Overview

Cloud teams routinely waste 30–35% of their AWS budget on idle EC2 instances, unattached EBS volumes, orphaned Elastic IPs, forgotten load balancers, and stale snapshots. This tool ingests an AWS billing CSV, runs five orphan-detection rules, and surfaces findings in a role-aware dashboard where admins can remediate resources with one click while viewers get read-only access and copyable AWS CLI commands. Every action is gated by JWT authentication, logged to a rotating file, and followed by an SMTP email notification.

---

## 2. Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                         SYSTEM ARCHITECTURE                          │
│                                                                      │
│   Browser — Chart.js Dashboard (Jinja2)                              │
│        │                                                             │
│        │  HTTPS · JWT Bearer Token · Role-based UI                   │
│        ▼                                                             │
│   ┌─────────────────────────────────────────────────────────────┐   │
│   │                    FastAPI  (main.py)                        │   │
│   │   CORSMiddleware · RequestValidationError · 500 handler      │   │
│   └────┬─────────────────┬──────────────────┬───────────────────┘   │
│        │                 │                  │                        │
│        ▼                 ▼                  ▼                        │
│   ┌──────────┐    ┌────────────┐    ┌───────────────────┐           │
│   │  Auth    │    │ CSV Parser │    │  API Routes       │           │
│   │  JWT +   │    │ aws_parser │    │  routes.py        │           │
│   │  bcrypt  │    │ .py        │    │  (11 endpoints)   │           │
│   └──────────┘    └─────┬──────┘    └────────┬──────────┘           │
│                         │                    │                       │
│                         ▼                    ▼                       │
│                   ┌───────────┐      ┌──────────────────┐           │
│                   │  Orphan   │      │  Remediation     │           │
│                   │  Detector │─────▶│  Engine          │           │
│                   │  5 rules  │      │  Demo + AWS API  │           │
│                   └─────┬─────┘      └────────┬─────────┘           │
│                         │                     │                      │
│                         ▼                     ▼                      │
│                   ┌────────────────────────────────────┐            │
│                   │  SQLite · SQLAlchemy ORM            │            │
│                   │  users · resources · findings ·     │            │
│                   │  remediation_log  (4 tables)        │            │
│                   └────────────────────────────────────┘            │
│                                                                      │
│                   ┌────────────────────────────────────┐            │
│                   │  Email · smtplib STARTTLS           │            │
│                   │  Sent via BackgroundTasks           │            │
│                   └────────────────────────────────────┘            │
└──────────────────────────────────────────────────────────────────────┘
```

### Detection Rules

| Rule | Resource Type | Trigger Condition | Severity |
|---|---|---|---|
| `unattached_ebs` | EBS Volume | `status = available` | High |
| `idle_ec2` | EC2 Instance | No activity > 30 days | Critical |
| `orphaned_eip` | Elastic IP | `status = unassociated` | Medium |
| `idle_alb` | Load Balancer | `status = idle` | High |
| `old_snapshot` | Snapshot | Created > 90 days ago | Low |

### Project Structure

```
cloud-cost-optimizer/
├── main.py                      # FastAPI app, dual logging, CORS, error handlers
├── database.py                  # SQLAlchemy engine & session factory
├── models.py                    # ORM models (users, resources, findings, remediation_log)
├── auth/
│   ├── auth_handler.py          # JWT sign/verify, bcrypt, startup secret guard
│   └── auth_bearer.py           # FastAPI HTTPBearer dependency
├── parser/
│   └── aws_parser.py            # AWS CSV ingestion, row-level error skipping
├── engine/
│   ├── orphan_detector.py       # 5 detection rules, per-rule try/except
│   └── remediation.py           # Demo simulation + live AWS API dispatch
├── api/
│   └── routes.py                # All 11 endpoints, rate limiter, require_admin guard
├── notifications/
│   └── email_sender.py          # smtplib STARTTLS email notification
├── dashboard/
│   └── templates/
│       └── index.html           # Single-page Chart.js dashboard
├── sample_data/
│   └── aws_billing.csv          # 20-row realistic sample (10 findings, ~$1,812/month waste)
├── tests/
│   └── test_pipeline.py         # 17 pytest tests across 8 test classes
├── .env                         # Secrets — gitignored, never committed
├── .env.example                 # Safe template — copy and fill in values
├── generate_pptx.js             # PptxGenJS script → PRESENTATION.pptx (9 slides)
├── PRESENTATION.md              # 7-slide markdown deck for stakeholder review
├── requirements.txt
└── README.md
```

---

## 3. Quick Start

### Prerequisites

- Python 3.9+
- pip

### Clone and install

```bash
git clone https://github.com/your-username/cloud-cost-optimizer.git
cd cloud-cost-optimizer
pip install -r requirements.txt
```

### Configure environment

```bash
cp .env.example .env
```

Open `.env` and set the required values:

```env
# Generate a strong random key — server refuses to start without this
JWT_SECRET_KEY=<run: python3 -c "import secrets; print(secrets.token_hex(32))">

# Leave DEMO_MODE=true for local demo — no AWS credentials needed
DEMO_MODE=true

# Optional: SMTP for email notifications after remediation
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=xxxx xxxx xxxx xxxx
SMTP_FROM_EMAIL=your-email@gmail.com
NOTIFICATION_EMAIL=recipient@example.com
```

> **Gmail App Password:** Go to **Google Account → Security → 2-Step Verification → App Passwords**. Select "Mail", copy the 16-character password into `SMTP_PASSWORD`.

### Run the server

```bash
uvicorn main:app --reload --port 8000
```

Open the dashboard: [http://localhost:8000/dashboard](http://localhost:8000/dashboard)

---

## 4. Authentication

The API uses JWT Bearer tokens. Passwords are hashed with bcrypt (cost factor 12) and never stored or returned in plaintext.

### Register

```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "email": "admin@example.com", "password": "SecurePass1"}'
```

```json
{"message": "User 'admin' registered successfully. Your role is: admin"}
```

> The **first registered user is always assigned the `admin` role**. All subsequent users default to `viewer`.

### Login

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "SecurePass1"}'
```

```json
{"access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...", "token_type": "bearer"}
```

### Use the token

Pass the token as a Bearer header on all protected endpoints:

```bash
curl http://localhost:8000/findings \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

### Role-based access

| Role | Permissions |
|---|---|
| `admin` | Upload CSV, view findings, remediate (single + bulk), clear data, view users |
| `viewer` | View findings, copy CLI commands — no remediation |

---

## 5. Upload & Ingest

### Via the dashboard

Drag and drop a CSV file onto the upload zone in the sidebar. Findings are detected automatically and the dashboard refreshes.

### Via curl

```bash
curl -X POST http://localhost:8000/ingest \
  -H "Authorization: Bearer <token>" \
  -F "file=@sample_data/aws_billing.csv"
```

```json
{
  "message": "Ingest complete",
  "resources_ingested": 20,
  "findings_detected": 10,
  "ingest_warnings": 0
}
```

### CSV format

The file must be `.csv`, under 10 MB, and include these columns (case-insensitive, snake_case or CamelCase accepted):

```
resource_id, resource_name, resource_type, region, monthly_cost_usd, status, last_active_date
```

See `sample_data/aws_billing.csv` for a ready-to-use example with 20 rows and ~$1,812/month in simulated waste.

---

## 6. API Reference

All protected endpoints require `Authorization: Bearer <token>`.

### Auth

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/auth/register` | None | Register a new user. First user → admin; subsequent → viewer. |
| `POST` | `/auth/login` | None | Returns JWT access token. Rate-limited: 5 attempts/min/IP. |
| `GET` | `/auth/me` | Bearer | Returns `{username, email, role}` for the current token. |

### Resources & Findings

| Method | Path | Auth | Role | Description |
|---|---|---|---|---|
| `POST` | `/ingest` | Bearer | Any | Upload AWS billing CSV. Runs detection after ingest. |
| `GET` | `/findings` | Bearer | Any | All findings, sorted by monthly waste descending. |
| `GET` | `/findings/{id}/status` | Bearer | Any | Returns `{status, remediated_at}` for a single finding. |
| `GET` | `/findings/{id}/remediation` | Bearer | Any | Returns pre-built AWS CLI command for the finding. |
| `GET` | `/summary` | Bearer | Any | Total waste, findings by severity, top 3 wasteful resources. |

### Remediation

| Method | Path | Auth | Role | Description |
|---|---|---|---|---|
| `POST` | `/remediate/{id}` | Bearer | Admin | Remediate one finding. Demo: simulated. Live: calls AWS API. |
| `POST` | `/remediate/bulk` | Bearer | Admin | Remediate a list of finding IDs. Returns per-ID results. |

### Admin

| Method | Path | Auth | Role | Description |
|---|---|---|---|---|
| `GET` | `/users` | Bearer | Admin | List all registered users with roles. |
| `DELETE` | `/data` | Bearer | Admin | Clear all resources, findings, and remediation logs. |
| `GET` | `/dashboard` | None | — | Serves the HTML dashboard. |

### Example responses

**`GET /summary`**
```json
{
  "total_resources": 20,
  "total_findings": 10,
  "total_waste_usd": 1812.20,
  "findings_by_severity": {"Critical": 4, "High": 3, "Medium": 2, "Low": 1},
  "top_3_wasteful_resources": [
    {"resource_id": "i-0a1b2c3d", "resource_type": "EC2 Instance", "monthly_cost": 350.00}
  ]
}
```

**`POST /remediate/{id}`** (demo mode)
```json
{
  "success": true,
  "finding_id": 3,
  "resource_id": "i-0a1b2c3d",
  "action_taken": "stopped",
  "status": "remediated",
  "email_sent": true,
  "notification_email": "admin@example.com",
  "timestamp": "2026-07-08T14:23:01Z"
}
```

**`POST /remediate/{id}`** (no AWS credentials)
```json
{
  "success": false,
  "message": "AWS credentials not configured. Use the CLI command to remediate manually.",
  "cli_alternative": "aws ec2 stop-instances --instance-ids i-0a1b2c3d --region us-east-1"
}
```

---

## 7. AWS Testing

### Credentials setup

For live remediation, configure AWS credentials before starting the server:

```bash
export AWS_ACCESS_KEY_ID=your-access-key-id
export AWS_SECRET_ACCESS_KEY=your-secret-access-key
export AWS_DEFAULT_REGION=us-east-1
```

Then set `DEMO_MODE=false` in `.env`.

### Generating a real billing export (read-only)

To test with your own AWS data instead of the sample CSV:

```bash
# Install AWS CLI (if not already installed)
pip install awscli

# List idle EC2 instances (read-only, no changes made)
aws ec2 describe-instances \
  --filters "Name=instance-state-name,Values=stopped" \
  --query "Reservations[*].Instances[*].{ID:InstanceId,State:State.Name,Region:Placement.AvailabilityZone}" \
  --output table

# List unattached EBS volumes
aws ec2 describe-volumes \
  --filters "Name=status,Values=available" \
  --query "Volumes[*].{ID:VolumeId,Size:Size,Region:AvailabilityZone,Cost:''}" \
  --output table

# List unassociated Elastic IPs
aws ec2 describe-addresses \
  --query "Addresses[?AssociationId==null].{AllocationId:AllocationId,IP:PublicIp}" \
  --output table
```

Export results to CSV, format to match the required column schema, and upload via `/ingest`. No write permissions are needed for detection — only for live remediation.

### IAM minimum permissions for live remediation

```json
{
  "Effect": "Allow",
  "Action": [
    "ec2:StopInstances",
    "ec2:DeleteVolume",
    "ec2:ReleaseAddress",
    "elasticloadbalancing:DeleteLoadBalancer",
    "ec2:DeleteSnapshot"
  ],
  "Resource": "*"
}
```

---

## 8. Tests

```bash
pytest tests/ -v
```

17 tests across 8 classes covering the full pipeline:

| Test Class | What It Covers |
|---|---|
| `TestAuth` | Register, duplicate detection, login, wrong password, `/auth/me`, unauthenticated access |
| `TestIngest` | CSV upload (valid), wrong file format rejected (`.txt` → 400) |
| `TestFindings` | All findings returned, sorted by waste descending, status check, CLI command retrieval |
| `TestSummary` | Total waste > 0, findings_by_severity present, top 3 resources present |
| `TestRemediation` | Single remediate (demo + no-creds graceful fallback), bulk remediate |
| `TestClearData` | DELETE /data success, findings empty after clear |
| `TestDashboard` | Dashboard HTML served without auth, contains expected content |

Tests use an in-memory SQLite database (`/tmp/test_cost_optimizer.db`) and a test-only JWT secret — no `.env` values required to run tests.

---

## 9. Stack

| Layer | Technology | Purpose |
|---|---|---|
| **API** | [FastAPI](https://fastapi.tiangolo.com/) 0.104+ | REST endpoints, request validation, background tasks |
| **Database** | [SQLite](https://sqlite.org/) + [SQLAlchemy](https://www.sqlalchemy.org/) ORM | 4-table schema — users, resources, findings, remediation_log |
| **Auth** | [python-jose](https://python-jose.readthedocs.io/) + [passlib/bcrypt](https://passlib.readthedocs.io/) | JWT HS256 tokens, bcrypt password hashing (cost 12) |
| **Cloud SDK** | [boto3](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html) | Live AWS API remediation (EC2, EBS, EIP, ALB, Snapshot) |
| **Frontend** | [Jinja2](https://jinja.palletsprojects.com/) templates + [Chart.js](https://www.chartjs.org/) 4.4.0 | Single-page dashboard with bar + doughnut charts |
| **Email** | `smtplib` (stdlib) + STARTTLS | Post-remediation notifications, no extra dependencies |
| **Logging** | `logging` (stdlib) + `RotatingFileHandler` | Dual output: console + `app.log` (5 MB, 3 backups) |
| **Testing** | [pytest](https://docs.pytest.org/) + `httpx` (via Starlette TestClient) | 17 tests, isolated DB, no live AWS calls |
| **Config** | [python-dotenv](https://github.com/theskumar/python-dotenv) | `.env` loading, 12 configurable variables |

---

## 10. Security

### JWT

- Tokens signed with HS256 using a 64-character random hex secret
- Server **refuses to start** if `JWT_SECRET_KEY` is absent or matches any known insecure default (`""`, `"secret"`, `"changeme"`, etc.)
- Tokens expire after 24 hours (configurable via `JWT_EXPIRY_HOURS`)

### Passwords

- Hashed with bcrypt at cost factor 12
- Plaintext passwords are never stored, logged, or returned in any API response
- Login error message is identical for wrong username and wrong password — no enumeration

### Input Sanitization

- Resource IDs stripped to `[A-Za-z0-9\-_:/]` before CLI command generation
- Region values stripped to `[A-Za-z0-9\-]` — prevents shell injection in CLI templates
- Pydantic validators on all inputs: username format, email format, password strength (min 8 chars, 1 uppercase, 1 digit), file type, file size (10 MB cap), finding ID lists

### Rate Limiting

- `POST /auth/login` limited to 5 attempts per IP per minute
- Exceeded attempts return HTTP 429 with a descriptive message
- In-memory sliding-window implementation — no Redis or external dependency required

### CORS & Error Handling

- CORS restricted to `http://localhost:8000` and `http://127.0.0.1:8000` only
- Stack traces and file paths never exposed in API responses — full tracebacks logged server-side only
- All error responses use the shape `{"error": "...", "detail": "..."}` consistently

### Secrets Management

- All credentials in `.env` — gitignored, never committed
- `.env.example` provided with safe placeholder values and generation instructions
- `git log --all --full-history -- .env` confirmed empty — no accidental commits

---

## 11. What's Next

### Authentication & Identity
- **AWS SSO (Identity Center)** — federated login, IAM groups mapped to Admin/Viewer roles, no local password management
- MFA enforcement for Admin remediation actions via SSO policy

### Data Ingestion
- **AWS Cost Explorer API** — scheduled daily pulls replacing manual CSV upload, real-time cost data
- AWS Organizations support for multi-account visibility from a single dashboard

### Remediation
- **Approval workflow** for Critical findings — require a second Admin confirmation before execution
- **Dry-run mode** — generate a projected savings report before executing any changes
- Live AWS API already wired: set `DEMO_MODE=false` and supply credentials to activate

### Alerting
- **Slack and Microsoft Teams webhooks** for new Critical findings
- PagerDuty integration for findings exceeding a configurable monthly waste threshold

### Infrastructure
- **Docker + Kubernetes** — containerized FastAPI, persistent volume for SQLite or swap to PostgreSQL/RDS
- Terraform module for one-command deployment to AWS
- Scheduled scans via AWS EventBridge (daily/weekly)

### Analytics
- Cost forecasting with 30/60/90-day trend lines using historical Cost Explorer data
- Per-team or per-tag cost attribution
- **Multi-cloud support** — Azure Cost Management API as a second data source

---

*Built in Lead Architect Mode — architecture by human, all code by AI, zero manual edits.*  
*35 prompts · 15+ files · ~2,500 lines of code · ~4 hours 30 minutes*
