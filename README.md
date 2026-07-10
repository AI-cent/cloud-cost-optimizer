# ☁️ Cloud Cost Optimizer & Remediation Engine

API-first Python backend + Chart.js dashboard for detecting and remediating AWS cost waste.

```
┌─────────────────────────────────────────────────────────────────┐
│                    ARCHITECTURE OVERVIEW                         │
│                                                                  │
│  Browser (Chart.js Dashboard)                                    │
│       │                                                          │
│       │  HTTP + JWT Bearer Token                                 │
│       ▼                                                          │
│  ┌─────────────┐    ┌──────────────┐    ┌──────────────────┐   │
│  │  FastAPI    │───▶│  Auth Module │    │  AWS (boto3)     │   │
│  │  (main.py)  │    │  JWT / bcrypt│    │  EC2 / ELB / EIP │   │
│  └──────┬──────┘    └──────────────┘    └──────────────────┘   │
│         │                                        ▲              │
│         ▼                                        │              │
│  ┌─────────────┐    ┌──────────────┐    ┌───────┴──────────┐   │
│  │  CSV Parser │    │  Orphan      │    │  Remediation     │   │
│  │  (AWS CUR)  │───▶│  Detector    │───▶│  Engine (boto3)  │   │
│  └─────────────┘    │  (5 rules)   │    └──────────────────┘   │
│                     └──────┬───────┘                            │
│                            ▼                                     │
│                   ┌─────────────────┐                           │
│                   │  SQLite via     │                           │
│                   │  SQLAlchemy     │                           │
│                   │  (4 tables)     │                           │
│                   └─────────────────┘                           │
└─────────────────────────────────────────────────────────────────┘
```

## Quick Start

### 1. Clone & install dependencies
```bash
cd cloud-cost-optimizer
pip install -r requirements.txt
```

### 2. Configure environment
```bash
cp .env .env.local   # edit .env with your JWT secret
# Set a strong JWT_SECRET_KEY in .env before running in production
```

### 3. Run the server
```bash
python main.py
# or
uvicorn main:app --reload --port 8000
```

### 4. Open the dashboard
```
http://localhost:8000/dashboard
```

### 5. Register & login
- Click **Register** on the dashboard
- Upload `sample_data/aws_billing.csv` to ingest sample data
- View findings, charts, and remediate resources

---

## API Endpoints

### Auth (no token required)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/auth/register` | Register new user |
| POST | `/auth/login` | Login, get JWT token |
| GET | `/auth/me` | Get current user info |

### Protected (Bearer token required)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/ingest` | Upload AWS billing CSV |
| GET | `/findings` | All findings, sorted by waste |
| GET | `/findings/{id}/remediation` | CLI command for finding |
| GET | `/findings/{id}/status` | Finding status |
| POST | `/remediate/{id}` | Remediate via boto3 |
| POST | `/remediate/bulk` | Bulk remediate |
| GET | `/summary` | Waste summary & stats |
| DELETE | `/data` | Clear all data |
| GET | `/dashboard` | HTML dashboard (no auth) |

---

## Detection Rules

| Rule | Resource Type | Condition | Severity |
|------|--------------|-----------|----------|
| unattached_ebs | EBS Volume | status = available | High |
| idle_ec2 | EC2 Instance | last_active > 30 days ago | Critical |
| orphaned_eip | Elastic IP | status = unassociated | Medium |
| idle_alb | Load Balancer | status = idle | High |
| old_snapshot | Snapshot | last_active > 90 days ago | Low |

---

## CSV Format

Your AWS billing CSV must include these columns (case-insensitive):

```
resource_id, resource_name, resource_type, region,
monthly_cost_usd, status, last_active_date
```

See `sample_data/aws_billing.csv` for an example.

---

## Running Tests

```bash
pytest tests/ -v
```

---

## Project Structure

```
cloud-cost-optimizer/
├── main.py                          # FastAPI app entry point
├── database.py                      # SQLAlchemy engine & session
├── models.py                        # ORM models (4 tables)
├── auth/
│   ├── auth_handler.py              # JWT creation/verification, bcrypt
│   └── auth_bearer.py               # FastAPI JWT dependency
├── parser/
│   └── aws_parser.py                # AWS CUR CSV parser
├── engine/
│   ├── orphan_detector.py           # 5 detection rules
│   └── remediation.py               # boto3 remediation + CLI fallback
├── api/
│   └── routes.py                    # All API endpoints
├── dashboard/
│   └── templates/
│       └── index.html               # Chart.js dashboard
├── sample_data/
│   └── aws_billing.csv              # Sample billing data
├── tests/
│   └── test_pipeline.py             # pytest suite
├── .env                             # Secrets (gitignored)
├── .gitignore
├── requirements.txt
└── README.md
```

---

## AWS Credentials (for live remediation)

```bash
export AWS_ACCESS_KEY_ID=your-key
export AWS_SECRET_ACCESS_KEY=your-secret
export AWS_DEFAULT_REGION=us-east-1
```

Without credentials, the `/remediate` endpoints return the AWS CLI command as a fallback.

---

## Email Notifications

After each successful remediation, an email is sent via Gmail SMTP. Configure in `.env`:

```
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-gmail@gmail.com
SMTP_PASSWORD=xxxx xxxx xxxx xxxx
SMTP_FROM_EMAIL=your-gmail@gmail.com
NOTIFICATION_EMAIL=recipient@example.com
```

> **Gmail requires an App Password** — plain Gmail passwords are rejected.
> Generate one at: **Google Account → Security → 2-Step Verification → App Passwords**
> Select "Mail" + device name, copy the 16-character password into `SMTP_PASSWORD`.
> `smtplib` is part of Python's standard library — no extra dependencies needed.
