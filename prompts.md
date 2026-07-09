# Prompt Audit Log — Cloud Cost Optimizer

## Session Start
**Date:** 2026-07-08
**Timer Start:** Session initiated

---

## Turn 1
**Prompt:**
> Lead Architect mode: ON. We are building a Python-based, API-first Cloud Cost Optimizer & Remediation Engine using a free database and a dashboard.
> Rules:
> ● No Manual Edits: You provide all logic and fixes. I will not edit any code.
> ● Audit Log: You must maintain a file named prompts.md. After every turn, update that file with the prompt I just used.
> ● Time-Check: Start a timer. Goal is an MVP in 4-6 hours (Max window: 16h). Report Elapsed Time at the end of every response.
> Acknowledge and wait for my command.

**Action:** Acknowledged. Created prompts.md. Awaiting command.

---

## Turn 4
**Prompt:**
> Generate a realistic sample_data/aws_billing.csv file with 20 rows using these exact columns: ResourceId, ResourceName, ResourceType, Region, MonthlyCost, Status, LastActiveDate. Include: 4 EBS Volumes, 4 EC2 Instances, 3 Elastic IPs, 3 Load Balancers, 3 Snapshots, 3 mixed healthy. Realistic AWS IDs and costs. Total orphaned waste ~$1,800/month.

**Action:** Updated `aws_parser.py` to accept both CamelCase (`ResourceId`, `MonthlyCost`) and snake_case column names via alias mapping. Generated 20-row CSV. Verified: 20 rows parsed, 10 orphaned resources detected, **$1,812.20/month total waste**. 17/17 tests still passing.

---

## Turn 3
**Prompt:**
> Add all files and commit with the message "feat: initial project scaffold with auth and full architecture" then push to GitHub.

**Action:** Attempted git add/commit/push from sandbox. Blocked by two environment constraints: (1) `.git/index.lock` held by a host process (Claude desktop/editor) — cannot be removed from sandbox; (2) GitHub credentials not available in sandbox. Provided user with the exact 3-command Terminal sequence to complete the push manually.

---

## Turn 2
**Prompt:**
> Here is the full architecture. Build exactly this: [full architecture spec — stack, folder structure, 4 DB tables, 5 orphan detection rules, AWS CLI commands, auth endpoints, protected API endpoints, dashboard spec, JWT implementation, .gitignore, requirements.txt, README]

**Action:** Built complete project. All 17 pytest tests pass.
- Scaffolded all directories and `__init__.py` files
- Wrote: `requirements.txt`, `.env`, `.gitignore`, `database.py`, `models.py`, `main.py`
- Wrote: `auth/auth_handler.py`, `auth/auth_bearer.py`
- Wrote: `parser/aws_parser.py`
- Wrote: `engine/orphan_detector.py`, `engine/remediation.py`
- Wrote: `api/routes.py` (all 11 endpoints)
- Wrote: `dashboard/templates/index.html` (Chart.js dashboard, login/register, upload, charts, findings table)
- Wrote: `sample_data/aws_billing.csv`, `tests/test_pipeline.py`, `README.md`
- Fixed: route ordering (`/remediate/bulk` before `/{finding_id}`), Starlette Jinja2 API compat, test DB patching

---
