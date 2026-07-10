# Cloud Cost Optimizer & Remediation Engine
### Engineering Presentation — VP of Engineering Audience

---

## Slide 1 — The Hidden Cost of Cloud Waste

**Problem: Your cloud bill has a silent leak.**

Industry research shows companies waste **30–35% of their cloud budget** on resources no one is using:

- Unattached EBS volumes still billed at full storage rate
- Idle EC2 instances running with zero traffic for 30+ days
- Orphaned Elastic IPs accruing charges with no association
- Forgotten load balancers with no active targets
- Snapshots sitting untouched for 90+ days

**The real cost isn't just money — it's visibility.** Engineering teams find out about waste in the quarterly finance review, not when it starts accumulating. Manual audits require cross-team coordination, AWS console access, and tribal knowledge of which resources are safe to delete. By the time an engineer investigates, the waste has been running for months.

> A mid-size AWS environment with 200+ resources can accumulate $20,000–$50,000/year in preventable waste — entirely from resources that were created and forgotten.

**This is a tooling problem, not a discipline problem.** The solution is automated detection and one-click remediation with appropriate guardrails.

---

## Slide 2 — Cloud Cost Optimizer & Remediation Engine

**An API-first tool that identifies and eliminates cloud waste in minutes, not weeks.**

### Technology Stack

| Layer | Technology |
|---|---|
| API | FastAPI (Python) |
| Database | SQLite + SQLAlchemy ORM |
| Auth | JWT (python-jose) + bcrypt password hashing |
| Frontend | Jinja2 templates + Chart.js 4.4.0 |
| Cloud SDK | AWS SDK — ready for live credentials |
| Notifications | SMTP email notifications via smtplib STARTTLS |
| Logging | Python logging — console + rotating app.log |

### End-to-End Flow

```
┌─────────────┐     ┌─────────────┐     ┌─────────────────────┐
│  CSV Upload │────▶│  Parse &    │────▶│  Orphan Detection   │
│  (drag-drop)│     │  Validate   │     │  (5 rules engine)   │
└─────────────┘     └─────────────┘     └──────────┬──────────┘
                                                    │
                                                    ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────────────┐
│ Email Alert │◀────│  Remediate  │◀────│  Dashboard +        │
│             │     │ (simulated, │     │  Findings Table     │
└─────────────┘     │  API-ready) │     │  + Charts           │
                    └─────────────┘     └─────────────────────┘
```

Every step is gated by JWT authentication and role-based access control. Admins remediate. Viewers get read-only access with copyable CLI commands.

---

## Slide 3 — The Four-Step Pipeline

**From raw CSV to remediated resource in under 30 seconds.**

### Step 1 — Authenticate
JWT-based login with bcrypt password hashing. Two roles enforced at every API endpoint:
- **Admin**: full access — upload, view, remediate
- **Viewer**: read-only — view findings, copy CLI commands

First registered user is always Admin. Subsequent users default to Viewer unless explicitly promoted.

### Step 2 — Ingest
Drag-and-drop CSV upload from the dashboard. The parser validates every row individually — bad rows are skipped with a WARNING log, valid rows are committed. File size capped at 10 MB. Only `.csv` accepted.

**Sample run: 20 resources ingested from `aws_billing.csv`.**

### Step 3 — Detect
5 orphan detection rules run automatically after every ingest:

| Rule | Resource Type | Condition | Severity |
|---|---|---|---|
| `unattached_ebs` | EBS Volume | Status = `available` | High |
| `idle_ec2` | EC2 Instance | No activity > 30 days | Critical |
| `orphaned_eip` | Elastic IP | Status = `unassociated` | Medium |
| `idle_alb` | Load Balancer | Status = `idle` | High |
| `old_snapshot` | Snapshot | Created > 90 days ago | Low |

**Sample run: 10 findings detected across 20 ingested resources.**

### Step 4 — Remediate
Admin clicks Remediate → user confirmation popup (with resource name, type, and action verb) → 10-second simulation → finding marked remediated → email notification sent. Viewer sees the same table but gets Copy CLI only.

---

## Slide 4 — Dashboard in Action

**A purpose-built dashboard with AWS visual identity throughout.**

---

### 📸 Screenshot 1 — Login Screen
*JWT login form with username/password. Register link visible. Role assigned on first login.*

---

### 📸 Screenshot 2 — Admin Dashboard: Summary Cards + Charts
*Four summary cards: Total Waste ($1,844.50), Pending Remediations (10), Resources Ingested (20), Findings Detected (10). Bar chart showing waste by service type (EC2, EBS, EIP, ALB, Snapshot) with distinct colors per bar. Pie chart showing findings by criticality (Critical, High, Medium, Low) with distinct slice colors.*

---

### 📸 Screenshot 3 — Findings Table with CLI Commands
*Table columns: Resource ID, Type, Region, Severity badge, Monthly Waste, Status, CLI Command (copyable), Remediate button (Admin only). Sorted by waste descending. CLI commands pre-populated for each finding (e.g. `aws ec2 stop-instances --instance-ids i-0a1b2c3d --region us-east-1`).*

---

### 📸 Screenshot 4 — User Confirmation Popup
*"Stop EC2 Instance?" confirmation popup with resource name (legacy-reporting-srv), action (will be stopped), and Yes/Cancel buttons. Prevents accidental remediation.*

---

### 📸 Screenshot 5 — Success State After Remediation
*Row turns green. Toast notification: "✓ Remediated — email sent to admin@company.com". 10-second simulation complete.*

---

### 📸 Screenshot 6 — Viewer Dashboard
*Same layout, same charts. Remediate button absent. Copy CLI button present. Role badge shows "Viewer" in header.*

---

> **Sample data:** `aws_billing.csv` — 20 resources ingested, 10 orphaned findings detected.

---

## Slide 5 — Production-Ready Engineering Practices

**Every layer built with operational discipline, not just functionality.**

### Security
- JWT tokens signed with a 64-character random secret — server refuses to start if key is absent or set to a default value
- bcrypt password hashing (cost factor 12) — plaintext passwords never stored or logged
- CORS restricted to localhost origins only
- Rate limiting on `/auth/login`: 5 attempts/min/IP → HTTP 429
- Resource IDs and region values sanitized before CLI command generation — shell injection prevented
- Stack traces and file paths never exposed in API responses

### Access Control
- Role-based access enforced at every protected endpoint (`require_admin` guard)
- Admin: CSV upload, view findings, one-click remediation with confirmation, bulk remediation
- Viewer: read-only findings view with copyable AWS CLI commands
- First registered user always promoted to Admin; subsequent users default to Viewer

### Reliability
- All 5 detection rules wrapped in individual `try/except` — one bad row never blocks the rest
- CSV parser skips malformed rows individually with WARNING logs
- Global FastAPI exception handler catches all unhandled errors, logs full traceback server-side, returns safe generic message to client
- Pydantic validators on all input: username format, email format, password strength, file type, file size, finding IDs

### Observability
- Structured logging to console, Database, and rotating `app.log` (5 MB, 3 backups)
- `LOGIN_SUCCESS [INFO]`, `LOGIN_FAILURE [WARNING]`, `INGEST_COMPLETE [INFO]`, `FINDING_DETECTED [INFO]`, `REMEDIATION_SUCCESS [INFO]`, `REMEDIATION_ERROR [ERROR]`
- Each log line includes entity IDs and timestamps for traceability

### AWS Remediation
- 10-second demo simulation in `DEMO_MODE=true` — zero AWS API calls
- Live AWS API calls ready: credential check at startup, per-resource-type dispatch, graceful fallback to CLI command if credentials not configured
- Email notification via SMTP (STARTTLS) sent in FastAPI `BackgroundTasks` — never blocks API response

---

## Slide 6 — Lead Architect Mode — Vibe Coding Workflow

**Architecture decided by a human. Code written entirely by AI. No manual edits.**

### The Approach

This project was built using a deliberate "Lead Architect Mode" workflow:

1. **Architecture first** — the full stack, folder structure, database schema, API contract, and UI layout were decided before a single line of code was written
2. **Constraint-driven prompts** — every prompt specified what to change, what not to touch, and the exact behavior expected
3. **Symptom-based debugging** — bugs were described by observed behavior and expected behavior, not by guessing the cause
4. **No manual code editing** — all 30+ turns produced code written entirely by AI

### Example Prompts From This Session

> *"Fix Remediate button in dashboard/templates/index.html only. No Python changes. STEP 1 — On click show confirmation modal with resource name and action type. STEP 2 — On Yes, call POST /remediate/{id}, show 10s processing spinner, update row to green on success. STEP 3 — On failure show red toast with CLI command as fallback."*

> *"Add role-based access control. Backend: add role column to users table, first registered user is always admin, GET /auth/me must return role. Frontend: call /auth/me after login, show Remediate button for admin only, show Copy CLI for viewer only — derive role from API response, never hardcode."*

> *"Add security: sanitize resource IDs in CLI commands — keep only alphanumeric, hyphens, underscores, colons. Validate region values — letters, numbers, hyphens only. CORS localhost only. JWT_SECRET_KEY from .env only — startup error if missing or default. Rate limit POST /auth/login: 5 attempts/min/IP → 429."*

### By The Numbers

| Metric | Value |
|---|---|
| Total prompts | 30+ |
| Files created/modified | 15+ |
| Lines of code | ~2,500 |
| Manual code edits by human | **0** |
| Elapsed build time | ~4 hours 10 minutes |

---

## Slide 7 — From MVP to Production

**The foundation is solid. Here's the roadmap to enterprise-grade.**

### Authentication & Identity
- **AWS SSO (Identity Center)** replacing local JWT — federated login, IAM groups mapped to Admin/Viewer roles, no password management
- MFA enforcement for Admin actions via SSO policy

### Data Ingestion
- **AWS Cost Explorer API** replacing manual CSV upload — scheduled daily pulls, real-time cost data, no manual exports
- AWS Organizations support for multi-account visibility from a single dashboard

### Remediation
- **Live AWS API remediation** with real credentials — the API endpoints and AWS dispatch logic are already built, just swap `DEMO_MODE=false` and configure credentials
- Approval workflow for Critical severity findings — require second Admin confirmation before execution
- Dry-run mode: generate remediation plan with projected savings before executing

### Alerting
- **Slack and Microsoft Teams webhook alerts** for new Critical findings — no need to check the dashboard
- PagerDuty integration for findings exceeding a configurable waste threshold

### Infrastructure
- **Docker + Kubernetes deployment** — containerized FastAPI, persistent volume for SQLite (or swap to PostgreSQL/RDS)
- Scheduled automated scans (daily/weekly) via cron or AWS EventBridge
- Terraform module for one-command deployment to AWS

### Analytics
- Cost forecasting with 30/60/90-day trend analysis using historical Cost Explorer data
- Per-team or per-tag cost attribution — show which team owns the waste
- **Multi-cloud support** — add Azure Cost Management API as a second data source

---

*Built in Lead Architect Mode — architecture by human, code by AI, zero manual edits.*
*Total build time: ~4 hours 10 minutes across 30+ prompts.*
