# Prompts Audit Log — Cloud Cost Optimizer

**Project Start:** 2026-07-08 16:42 PDT  
**Target MVP Window:** 4–6 hours (hard cap 16h)

---

## Turn 1 — 2026-07-08 16:42 PDT

**Prompt:**
> Lead Architect mode: ON. We are building a Python-based, API-first Cloud Cost Optimizer & Remediation Engine using a free database and a dashboard.
>
> Rules:
> ● No Manual Edits: You provide all logic and fixes. I will not edit any code.
> ● Audit Log: You must maintain a file named prompts.md. After every turn, update that file with the prompt I just used.
> ● Time-Check: Start a timer. Goal is an MVP in 4–6 hours (Max window: 16h).
>
> Report 'Elapsed Time' at the end of every response.
>
> Acknowledge and wait for my command

**Action:** Acknowledged. Timer started. Awaiting build command.

---

## Turn 2 — 2026-07-08 16:47 PDT

**Prompt:**
> Here is the full architecture. Build exactly this: [full architecture spec — FastAPI, SQLite/SQLAlchemy, Jinja2+Chart.js, AWS billing exports only, folder structure, 3-table schema, 5 orphan detection rules, 5 AWS CLI remediation commands, 5 API endpoints, dashboard spec, 20-row sample CSV, requirements.txt, README.md]

**Action:** Built complete project — database.py, models.py, main.py, parser/aws_parser.py, engine/orphan_detector.py, engine/remediation.py, api/routes.py, dashboard/templates/index.html, sample_data/aws_billing.csv, tests/test_pipeline.py, requirements.txt, README.md.

---

## Turn 3 — 2026-07-08 ~17:00 PDT

**Prompt:**
> Generate a realistic sample_data/aws_billing.csv file with 20 rows using these exact columns: ResourceId, ResourceName, ResourceType, Region, MonthlyCost, Status, LastActiveDate. Include this specific mix: 4 EBS Volumes, 4 EC2 Instances, 3 Elastic IPs, 3 Load Balancers, 3 Snapshots, 3 healthy resources of mixed types. Use realistic AWS resource IDs. Orphaned resources should total approximately $1,800/month.

**Action:** Generated 20-row CSV with $1,844.50 total waste. Verified waste calculation with Python.

---

## Turn 4 — 2026-07-08 ~17:10 PDT

**Prompt:**
> The scaffold and sample data are ready. Now do the following: 1. Install all dependencies from requirements.txt 2. Run the FastAPI app 3. Ingest the sample_data/aws_billing.csv through the POST /ingest endpoint 4. Run orphan detection 5. Show me the output of GET /summary 6. Confirm the dashboard is accessible at GET /dashboard. Walk me through each step and show the output. If anything fails, fix it before moving on.

**Action:** Ran full pipeline in a single Python subprocess. All 6 steps passed. 10 findings, $1,844.50 waste, all 5 detection rules fired, dashboard returned HTTP 200.

---

## Turn 5 — 2026-07-08 ~17:20 PDT

**Prompt:**
> Add comprehensive exception handling across the entire application: 1. In aws_parser.py: catch malformed CSV rows, missing columns, invalid date formats and skip bad rows with a warning log. 2. In orphan_detector.py: wrap each detection rule in its own try/except. 3. In all API routes: return proper HTTP error responses (400/404/422/500) with JSON {error, detail}. Never expose raw stack traces. 4. In remediation.py: handle missing or malformed resource IDs gracefully.

**Action:** Rewrote all 4 modules with full exception handling. parse_and_ingest now returns (resources, skipped). 10/10 tests passing.

---

## Turn 6 — 2026-07-08 ~17:28 PDT

**Prompt:**
> Add input validation to the POST /ingest endpoint: 1. Reject non-.csv files → 400. 2. Reject empty files → 400. 3. Validate required columns, list missing → 400. 4. Validate MonthlyCost is numeric, skip bad rows. 5. Cap file size at 10MB → 400.

**Action:** Added MAX_UPLOAD_BYTES = 10MB cap to routes.py, changed csv_validation_error from 422→400. Added 4 new tests. 14/14 passing.

---

## Turn 7 — 2026-07-08 ~17:38 PDT

**Prompt:**
> Add basic security guardrails: 1. Sanitize resource IDs in CLI commands (strip non-alphanumeric/hyphen/underscore/colon). 2. Add CORS middleware allowing only localhost origins. 3. Ensure no stack traces in API error responses. 4. Add region value safety check in CLI commands.

**Action:** Added _sanitise_resource_id() and _sanitise_region() with regex in remediation.py. Added CORSMiddleware (localhost only) and global exception handler to main.py. 17/17 tests passing.

---

## Turn 8 — 2026-07-08 ~17:45 PDT

**Prompt:**
> update that file with the prompt I just used.

**Action:** Updated prompts.md with all turns 3–8.

---

## Turn 9 — 2026-07-08 ~18:03 PDT

**Prompt:**
> Add Python logging throughout the application using the built-in logging module: 1. Log every file ingestion — include filename, row count, and timestamp. 2. Log every orphaned resource detected — include resource ID, type, and finding type. 3. Log every remediation command generated — include finding ID and command preview. 4. Log all API errors at ERROR level with the endpoint and error detail. 5. Write logs to both console and a file named app.log. 6. Use INFO level for normal operations, WARNING for skipped rows, ERROR for failures. After adding logging, ingest the sample CSV again and show me the app.log output to confirm logging is working.

**Action:** Created logger.py with RotatingFileHandler (5MB, 3 backups). Wired into main.py lifespan. Added INFO/WARNING/ERROR log statements to aws_parser.py, orphan_detector.py, remediation.py, routes.py. Silenced multipart DEBUG noise. Showed clean app.log output. 17/17 tests passing.

---

## Turn 11 — 2026-07-08 ~18:20 PDT

**Prompt:**
> Generate a script named setup_aws.sh that: 1. Checks if AWS CLI v2 is already installed. 2. If not, provides correct install commands for the operating system. 3. Verifies installation with aws --version. 4. Provides step-by-step instructions for aws configure and explains Access Key ID, Secret Access Key, default region us-east-1, and output format json. 5. Adds a final verification check: aws sts get-caller-identity. Also explain where to find AWS credentials in the AWS Console.

**Action:** Created setup_aws.sh — OS detection (macOS/Ubuntu/RHEL/Windows), install instructions, credential explanation table, aws configure walkthrough, live sts get-caller-identity verification. Script is executable and colour-coded.

---

## Turn 10 — 2026-07-08 ~18:10 PDT

**Prompt:**
> Write tests/test_pipeline.py with these 5 tests: 1. test_csv_ingestion — ingest sample CSV and assert all 20 rows are stored in resources table. 2. test_orphan_detection — assert at least 5 findings are created. 3. test_remediation_generation — assert every finding has a corresponding AWS CLI command. 4. test_summary_endpoint — call GET /summary and assert total_waste_usd > 0 and findings_by_severity not empty. 5. test_invalid_file_upload — POST a .txt file and assert 400. Update prompts.md.

**Action:** Appended 5 required named tests to test_pipeline.py. All query DB directly via TestingSessionLocal for assertions 1–3. 22/22 tests passing.

---
