# MPLADS AI Monitoring and Audit Intelligence Platform

MPLADS AI Monitoring is a local audit-intelligence platform for analysing public works data.  
It combines dynamic data upload, schema mapping, machine-learning anomaly detection, risk scoring, and evidence-oriented audit workflows.

## Major features

- **Executive overview dashboard**  
  Summarises the active analysis run with project totals, financial values, utilisation, risk distribution, and alerts.  
  State, category, delay, and risk charts are calculated from backend data rather than fixed frontend values.

- **Dynamic dataset upload**  
  Accepts CSV files and Excel workbooks without requiring a fixed filename or fixed five-file upload.  
  Every upload creates an isolated analysis run that can be switched without restarting the application.

- **Multi-source MPLADS integration**  
  Connects sanctioned works, completed works, expenditure, MP allocation, and calamity information when those sources are supplied.  
  Source lineage and cross-dataset conflicts are preserved for audit review.

- **Schema detection and mapping**  
  Detects workbook roles, sheets, uploaded columns, canonical fields, and mapping confidence.  
  Low-confidence mappings are reported as requiring confirmation instead of being silently treated as valid.

- **Data validation and data quality**  
  Checks required fields, missing financial values, invalid records, duplicate project IDs, and source completeness.  
  Data-quality review records remain visible and are scoped to the active dataset.

- **Feature engineering**  
  Calculates utilisation, elapsed time, completion delay, peer context, cost deviation, missing model inputs, and related signals.  
  Features are derived from uploaded values and degrade gracefully when optional fields are unavailable.

- **Isolation Forest anomaly detection**  
  Uses the existing trained/inference pipeline to identify unusual project patterns.  
  Model outputs are stored with each project and shown as explainable review signals.

- **Risk scoring and prioritisation**  
  Combines machine-learning, financial, utilisation, delay, peer, duplicate, and data-quality signals.  
  Projects are classified into LOW, MEDIUM, HIGH, CRITICAL, or DATA_QUALITY_REVIEW levels.

- **Risk Intelligence workspace**  
  Provides risk-level summaries, filters, search, pagination, and project-level triage.  
  Totals represent all matching records while the table displays only the current page.

- **Project register and filters**  
  Supports filtering by state, category, risk, source, status, district, and search text.  
  Filters query the canonical active-run dataset and do not mix records from older uploads.

- **Project Digital Audit File**  
  Presents project identity, financials, timeline, implementation details, risk signals, alerts, and source lineage.  
  The page also provides deterministic explanations, auditor recommendations, similar projects, and audit actions.

- **AI explanation / Why flagged**  
  Generates human-readable explanations from actual project features such as over-expenditure, peer deviation, delay, and anomaly flags.  
  Language is deliberately limited to potential anomalies and review recommendations, never accusations.

- **Auditor verification recommendations**  
  Suggests evidence to verify, including sanction orders, estimates, invoices, payment records, completion certificates, and site evidence.  
  Recommendations are tied to the signals that are actually available for the selected project.

- **Audit status and audit cases**  
  Supports review states including Not Reviewed, Under Review, Requires Evidence, Escalated, Cleared, and Closed.  
  Existing audit cases remain supported and are associated with both the project and its analysis run.

- **Audit notes and checklist persistence**  
  Stores auditor notes with author, project, run, and timestamp information.  
  Stores document-checklist items such as sanction orders, invoices, measurement books, and completion certificates.

- **Find similar projects**  
  Ranks projects using work-description similarity, location context, category, agency, and sanction-amount proximity.  
  Similarity results are comparisons for review and do not automatically merge or label projects.

- **Agency Intelligence**  
  Aggregates projects, sanctioned value, expenditure, utilisation, completion, delays, high risk, critical risk, and anomaly counts by agency.  
  Metrics are recalculated from the current analysis run and handle unavailable agency information safely.

- **Fund Reconciliation**  
  Compares financial fields that actually exist in the uploaded dataset, such as sanctioned amount and expenditure.  
  Flags mathematically supported inconsistencies, including expenditure exceeding sanction, without inventing missing fields.

- **Duplicate work detection**  
  Finds potential duplicate candidates using structured context, work-description similarity, category, location, and financial similarity.  
  Candidates are review signals only; projects are never deleted or merged automatically.

- **Natural-language Audit Copilot**  
  Accepts questions such as “show high-risk delayed projects above sanction” and converts supported phrases into filters.  
  Queries are validated against an allowlisted structure and always execute against the active analysis run.

- **Alerts and audit signals**  
  Generates project-linked alerts for meaningful risk, anomaly, delay, cost, conflict, and data-quality conditions.  
  Alert messages retain evidence context and avoid unsupported claims of fraud or wrongdoing.

- **Analysis-run history and switching**  
  Stores completed analysis runs with project totals, risk summaries, source metadata, and active-run state.  
  Switching runs changes dashboard, projects, agencies, reconciliation, duplicates, alerts, and search together.

- **Source lineage**  
  Records the source files and source roles that contributed to each canonical project.  
  This allows auditors to trace a result back to its uploaded evidence.

- **Responsive audit-intelligence UI**  
  Uses a consistent dashboard design with cards, tables, badges, charts, filters, and responsive layouts.  
  The upload workspace includes a side-by-side Knowledge Context panel explaining required fields and interpretation limits.

## Architecture

```text
CSV / Excel upload
        |
Schema detection and mapping
        |
Validation and canonicalisation
        |
Feature engineering and peer benchmarking
        |
Versioned Isolation Forest baseline inference
        |
Risk scoring and alert generation
        |
Run-scoped dashboards and audit intelligence
```

### Backend

- FastAPI application in `backend/app/main.py`
- SQLite persistence through SQLAlchemy
- Canonical data processing in `backend/app/ml/`
- Isolation Forest model artifacts in `backend/trained_models/`
- Upload files stored under `backend/uploads/`

### Frontend

- React and TypeScript application in `frontend/src/`
- Vite development server
- Axios API integration
- Recharts visualisations
- Existing pages include Overview, Risk Intelligence, Projects, Upload, Alerts, Audit Cases, Analytics, Agency Intelligence, Fund Reconciliation, Duplicate Detection, Audit Copilot, Integration, and Data Quality.

## Quick start

The recommended launcher starts both services:

```powershell
cd C:\Users\athar\OneDrive\Documents\SIH
python start.py
```

The application is then available at:

- Frontend: `http://127.0.0.1:5173`
- Backend: `http://127.0.0.1:8001`
- Health check: `http://127.0.0.1:8001/api/health`

### Manual backend setup

```powershell
cd backend
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8001
```

### Manual frontend setup

```powershell
cd frontend
npm install
npm run dev -- --port 5173
```

## Upload workflow

1. Open **Upload and Analyze**.
2. Select one CSV, one Excel workbook, or a connected set of source workbooks.
3. Select **Detect sheets and roles** to inspect mapping confidence.
4. Review low-confidence fields and source metadata.
5. Select **Run AI analysis** to create a new isolated analysis run.
6. Use the active run across dashboards, intelligence pages, and project audit files.

For a single project-register CSV, useful fields include project ID, project name, state, district, constituency, category, sanction amount, expenditure, status, agency, vendor, and payment status. Optional fields are shown as unavailable when absent.

## API overview

### Core analysis APIs

- `GET /api/health`
- `POST /api/upload`
- `POST /api/inspect-datasets`
- `POST /api/validate`
- `POST /api/analyze`
- `POST /api/analyze-multi`
- `GET /api/data-quality`

### Dataset and project APIs

- `GET /api/dashboard`
- `GET /api/projects`
- `GET /api/projects/{id}`
- `GET /api/projects/{id}/audit-file`
- `GET /api/projects/{id}/explanation`
- `GET /api/projects/{id}/similar`
- `GET /api/alerts`
- `GET /api/risk/high`
- `GET /api/risk/critical`

### Audit and intelligence APIs

- `POST /api/projects/{id}/audit-notes`
- `POST /api/projects/{id}/documents/checklist`
- `PATCH /api/projects/{id}/audit-status`
- `POST /api/audit-cases`
- `GET /api/audit-cases`
- `PATCH /api/audit-cases/{id}`
- `GET /api/agencies`
- `GET /api/reconciliation`
- `GET /api/duplicates`
- `POST /api/audit-search`

### Analysis-run APIs

- `GET /api/analysis-runs`
- `GET /api/analysis-runs/active`
- `GET /api/analysis-runs/latest`
- `GET /api/analysis-runs/{id}`
- `POST /api/analysis-runs/{id}/activate`

## Safety and interpretation

Risk levels, anomaly scores, duplicate candidates, and reconciliation mismatches are audit signals.  
They require human verification and must not be interpreted as findings of fraud, corruption, or wrongdoing.

The application preserves uploaded source lineage and uses run isolation so that a newly uploaded dataset does not mix with older project, alert, or analytics records.

## Supabase PostgreSQL

The backend can use Supabase PostgreSQL without changing the React frontend. Install the `psycopg` dependency, then set `DATABASE_URL` in the private `backend/.env` file to a Supabase URI using the `postgresql+psycopg://` driver. Keep the architecture as `React -> FastAPI -> Supabase`; do not put database credentials in Vite environment variables. The default SQLite URL remains available for local development until the Supabase schema migration is complete.

## Upload privacy and retention

Uploaded CSV and Excel files are treated as temporary processing inputs. By default, the application scans the complete uploaded dataset for credential or secret fields before analysis, blocks secret-bearing uploads, stores the SHA-256 hash and privacy summary with the analysis metadata, and deletes the raw file after processing. Set `RETAIN_UPLOADED_FILES=true` only when an approved retention policy requires later raw-file integrity or privacy rescans. When raw files are not retained, those later file-based checks correctly report that verification is unavailable rather than fabricating a result.

## Model governance

The application is an AI-assisted anomaly-screening system, not an automated fraud decision-maker. A fixed baseline model is trained from the configured synthetic demonstration corpus during demo bootstrap. Uploaded datasets are scored against that baseline and do not retrain or overwrite it. Each analysis run stores the model version, training timestamp, feature schema, row count, and fixed score-calibration bounds in its summary. This keeps a given project's ML score independent of the other rows uploaded alongside it.

For a deployment using official MPLADS data, retraining must be an authorized, separately evaluated workflow with held-out evaluation data, investigator outcomes, approval, and a retained model artifact. Risk alerts remain review signals requiring human verification.

## Stage 4 API security

The API adds `nosniff`, frame, referrer, and permissions policy headers. CORS uses the explicit origins in `CORS_ALLOWED_ORIGINS`; credentials are enabled only for those trusted origins. HSTS is disabled for local HTTP development and can be enabled with `HSTS_ENABLED=true` behind HTTPS.

Requests are protected by configurable in-memory rate limits: login attempts default to 5 per minute per IP/login identity, normal authenticated requests to 60 per minute, and upload/analysis operations to 10 per minute. Exceeded limits return HTTP 429 with `Retry-After`. Non-multipart API request bodies over `MAX_REQUEST_BODY_MB` (default 5 MB) return HTTP 413; Stage 3 remains authoritative for multipart file sizes.

The limiter is thread-safe and suitable for the current single-process deployment. Multi-worker or multi-instance production deployments should use a shared store such as Redis for globally consistent limits. Production deployments should also set explicit trusted CORS origins, a strong `AUTH_SECRET`, and HTTPS before enabling HSTS.

## Stage 5 data privacy and PII protection

The platform provides an authenticated, run/owner-scoped privacy scan at `POST /api/datasets/{dataset_id}/privacy-scan`. It detects likely email, phone, Aadhaar-like, PAN-like, bank-account-like, card, address, date-of-birth, GPS, and credential/token columns using normalized headers and conservative value patterns. Results contain only categories, confidence, columns, counts, and scan metadata; raw values are never returned or written to audit metadata.

Privacy statuses are `NO_PII_DETECTED_IN_SCANNED_DATA`, `REVIEW_REQUIRED`, or `BLOCKED` for likely credentials/secrets. Large datasets are sampled using `PII_SAMPLE_SIZE`, and the response states when sampling occurred. Display masking helpers are available for email, phone, Aadhaar-like, PAN-like, account/card, address, GPS, and secret values. Public MPLADS fields such as project name, MP name, district, state, constituency, agency, and financial values are not automatically treated as PII.

Configure with `PII_SCAN_ENABLED=true`, `PII_SAMPLE_SIZE=1000`, and `PII_MASKING_ENABLED=true`. Automated detection is heuristic, can produce false positives or false negatives, and is not legal or compliance certification. Uploaded source files remain unchanged and existing SHA-256 integrity, upload security, RBAC, rate limiting, and audit-chain behavior remain in force.

## Stage 6 encryption and key management

The reusable backend encryption service in `backend/app/crypto.py` uses AES-256-GCM from the established `cryptography` package. It is intentionally independent from dataset uploads, ML fields, privacy metadata, authentication data, audit metadata, and the existing SHA-256 and audit hash-chain semantics. It is currently a service for future sensitive application values rather than blanket database or uploaded-file encryption.

For the SIH prototype, configure `APP_ENCRYPTION_KEY` with a base64-encoded 32-byte key and set `APP_ENCRYPTION_KEY_VERSION` (for example, `v1`). Generate a key with the command documented in `backend/.env.example`. During rotation, configure `APP_ENCRYPTION_KEYS` as `v1:<base64-key>,v2:<base64-key>` and make `v2` active; envelopes retain their key version so older values remain decryptable while the old key is configured.

In production, keep encryption keys in a proper secret manager or KMS rather than local environment files. The current implementation does not claim that the SQLite database or uploaded files are encrypted at rest.

## Stage 7 malware, vulnerability, and security scanning

Stage 7 adds a non-executing internal scanner for accepted upload candidates. It runs after the existing Stage 3 validation and before SHA-256 hashing, checks executable/script signatures, suspicious filenames, Office macro/embedded-object indicators, malformed containers, and decompression-risk ratios. It never executes uploads or extracts archives. Results are `CLEAN`, `SUSPICIOUS`, `BLOCKED`, or `SCAN_ERROR`; clean means only that configured internal checks found no supported indicator, not that malware is impossible.

Optional dependency helpers can invoke `pip-audit` and `npm audit` when installed, but unavailable tools produce `SCAN_NOT_AVAILABLE` and no fabricated findings. The source scanner returns only masked secret metadata. This is a prototype security aid, not commercial antivirus, EDR, SAST, or vulnerability certification.

## Stage 8 security monitoring and incident response

Stage 8 adds a dedicated security-alert store separate from MPLADS project-analysis alerts. Security events are classified as `INFO`, `LOW`, `MEDIUM`, `HIGH`, or `CRITICAL`, correlated within `SECURITY_ALERT_DEDUP_WINDOW_SECONDS`, and can move through `OPEN`, `ACKNOWLEDGED`, `INVESTIGATING`, `RESOLVED`, or `FALSE_POSITIVE`. Ministry users have full management access; state and district authorities receive scoped read visibility. Lifecycle actions are recorded through the existing tamper-evident audit chain.

This is an application-level monitoring and incident-response foundation, not an enterprise SIEM/SOC. Production deployments should add centralized immutable logging, managed alert delivery, 24/7 monitoring, and formal incident-response procedures. Security alerts have separate retention semantics from immutable audit logs; this prototype does not automatically delete either.

## Verification

The current implementation has been checked with:

- Backend Python compilation using `compileall`
- Frontend TypeScript and Vite production build
- Live backend health checks
- Live frontend HTTP checks
- CSV upload and analysis with a 1,000-row project-register file
- Active-run agency, reconciliation, similar-project, audit-file, and Audit Copilot API checks



Data Flow :



             USER UPLOADS DATASET
                     │
                     ▼
              File Detection
                     │
                     ▼
             CSV / Excel Reader
                     │
                     ▼
          Schema Detection & Mapping
                     │
                     ▼
              Data Validation
                     │
          ┌──────────┴──────────┐
          │                     │
          ▼                     ▼
    Valid Records         Data Quality Issues
          │                     │
          └──────────┬──────────┘
                     ▼
             Canonical Schema
                     │
                     ▼
           Feature Engineering
                     │
                     ▼
             Peer Benchmarking
                     │
                     ▼
             ML Model Inference
                     │
                     ▼
               Risk Engine
                     │
          ┌──────────┼──────────┐
          ▼          ▼          ▼
       Alerts     Analytics   Signals
          │          │          │
          └──────────┼──────────┘
                     ▼
              Analysis Run
                     │
                     ▼
              Active Dataset
                     │
        ┌────────────┼─────────────┐
        ▼            ▼             ▼
   Dashboard     Projects       Audit Tools
