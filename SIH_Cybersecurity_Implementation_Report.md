# SIH MPLADS AI Monitoring and Audit Intelligence Platform
## Cybersecurity Implementation & Security Hardening Report

**Project:** SIH MPLADS AI Monitoring and Audit Intelligence Platform  
**Document purpose:** Technical record of the cybersecurity controls implemented and verified across Stages 1–8.  
**Cybersecurity scope:** Dataset integrity, audit integrity, upload security, API protection, privacy, application-level encryption, security scanning, and security monitoring.  
**Verification status:** All focused Stage 1–8 cybersecurity tests pass: **67 passed, 0 failed**.  
**Overall security status:** **8/8 cybersecurity stages complete and verified**, with documented prototype and external-tool limitations.

> This report describes the implementation present in the repository. It does not claim blanket database encryption, guaranteed malware detection, legal privacy certification, or enterprise SIEM capability.

## 1. Executive Summary

The platform uses a layered security model around an existing FastAPI, SQLAlchemy, SQLite, React, TypeScript, and Vite application. Security controls are implemented at the backend boundary, where authentication, authorization, upload validation, scanning, hashing, privacy classification, audit recording, and security-alert workflows are enforced.

The completed roadmap is:

1. Dataset SHA-256 integrity
2. Tamper-evident audit logs
3. Secure file upload hardening
4. API security, rate limiting, and request protection
5. Data privacy and PII protection
6. Encryption and key management
7. Malware, vulnerability, and security scanning
8. Security monitoring, alerts, and incident response foundation

The current application database was preserved during the security work. The original large analysis Run 1 is active and contains 1,130 projects. The database contains 1,162 projects, 436 project-analysis alerts, 5 analysis runs, 4 users, and 0 security alerts at the time of this report.

## 2. Project Security Context

The application processes MPLADS-related CSV and Excel datasets, creates run-scoped project records, calculates anomaly and risk signals, and supports audit workflows. The primary security boundary is the authenticated API. The frontend provides workflow and display controls, but backend validation and authorization remain authoritative.

Important existing concepts are deliberately kept separate:

- `AlertModel` stores normal MPLADS project-analysis alerts.
- `SecurityAlertModel` stores cybersecurity events and incident-response alerts.
- `AuditLogModel` stores the tamper-evident audit chain.
- `DatasetModel.sha256_hash` stores dataset integrity metadata.
- Privacy results contain classifications and metadata, not raw PII.

## 3. Cybersecurity Objectives

The implementation objectives were to:

- Detect modification of stored dataset files.
- Make audit-log tampering evident.
- Treat uploads as untrusted input.
- Limit authentication abuse and expensive API use.
- Avoid unnecessary exposure of PII and credentials.
- Provide reusable authenticated encryption for future sensitive values.
- Detect supported malware-like and suspicious upload indicators without executing files.
- Monitor important security events and provide a scoped incident workflow.
- Preserve existing analysis behavior, data, RBAC, and audit-chain semantics.

## 4. Security Architecture Overview

The following is a conceptual representation of the implemented application architecture, not a claim that every component is a separate deployed service.

```text
User
  |
  v
Authentication / JWT
  |
  v
RBAC + Jurisdiction Checks
  |
  +-------------------------------+
  |                               |
  v                               v
API Security                 Security Monitoring
Rate Limiting                Security Alerts
Request Protection           Incident Lifecycle
  |
  v
Upload Security
  |
  v
Malware/Security Scanner
  |
  v
SHA-256 Integrity
  |
  v
Dataset Processing / Analysis
  |
  +--------------------+
  |                    |
  v                    v
Privacy Protection   Audit Logging
  |                    |
  v                    v
PII Metadata        Hash Chain
                       |
                       v
                 Audit Integrity

Encryption & Key Management operates as a cross-cutting service for future
sensitive application values.
```

## 5. Stage 1 — Dataset SHA-256 Integrity

### Objective

Provide a reproducible file digest so the system can detect modification of an uploaded or stored dataset.

### Security Risk Addressed

Unauthorized or accidental changes to a dataset after upload could make analysis results inconsistent with the original source. Integrity verification detects byte-level changes.

### Implementation

The reusable utilities in `backend/app/ml/integrity.py` calculate and compare SHA-256 digests of actual file bytes. Dataset records retain integrity and provenance metadata including:

- `sha256_hash`
- `uploaded_by_user_id`
- `run_id`
- `storage_name` where available

The original file is not modified merely to calculate its digest.

### Architecture / Technical Approach

Accepted uploads pass Stage 3 validation, are hashed from their stored bytes, and retain the digest with the dataset record. Verification resolves the safe upload path, supports the stored UUID name, and falls back to the original filename for legacy records where appropriate.

### Files Created

- `backend/app/ml/integrity.py`
- `backend/tests/test_integrity.py`

### Files Modified

- `backend/app/database/models.py`
- `backend/app/main.py`
- Relevant frontend dataset/integrity display code already present in `frontend/src/`

### Backend Changes

The dataset integrity endpoint checks authentication, `analysis:read` permission, dataset visibility, ownership/jurisdiction constraints, stored hash availability, path safety, and current file bytes.

### Frontend Changes

The existing upload/analysis UI displays dataset integrity status. No separate security dashboard was required for this stage.

### API / Endpoint Changes

`GET /api/datasets/{dataset_id}/integrity`

- Requires authentication.
- Requires `analysis:read`.
- Applies dataset visibility and jurisdiction checks.
- Returns `VERIFIED`, `FAILED`, or `INTEGRITY_CHECK_NOT_AVAILABLE`, the algorithm, stored/current hashes where safe, and verification time.

### Security Controls

- SHA-256 over actual file bytes.
- Safe upload-root path resolution.
- Legacy dataset fallback behavior.
- Authenticated and scoped verification.
- No mutation of the source file during hashing.

### Testing

`backend/tests/test_integrity.py` covers hashing, verification, modified data, legacy behavior, endpoint access, and integration behavior.

### Verification Results

Stage 1 contributed to the final full regression result of **67 passed, 0 failed**. Backend compilation and live integrity behavior were also verified during implementation.

### Data Safety / Regression Impact

No project, alert, dataset, user, or analysis-run records were deleted or reset. Stage 1 does not alter dataset contents.

### Known Limitations

- Legacy datasets may lack stored hashes.
- Legacy filename fallback can report integrity unavailable when the source file is absent.
- SHA-256 detects changes but is not encryption or malware detection.

## 6. Stage 2 — Tamper-Evident Audit Logs

### Objective

Make changes, deletions, and chain discontinuities in audit records detectable.

### Security Risk Addressed

An attacker or faulty process could modify audit history, remove events, or alter event order without detection if logs were stored as ordinary independent rows.

### Implementation

`backend/app/ml/audit_integrity.py` provides deterministic canonicalization and SHA-256 audit hashing. Each new `AuditLogModel` record contains:

- `previous_hash`
- `record_hash`
- `actor_user_id`
- `actor_role`
- `action`
- safe `metadata_json`
- timestamp

The centralized `_audit()` helper in `backend/app/main.py` serializes chain creation for the SQLite deployment.

### Architecture / Technical Approach

Each record hashes its canonical fields and the previous record hash. Verification processes records in ID order and reports:

- `RECORD_HASH_MISMATCH`
- `CHAIN_BROKEN`
- `HASH_NOT_AVAILABLE`

Pre-Stage-2 records without hashes are reported as integrity unavailable rather than incorrectly declared valid.

### Files Created

- `backend/app/ml/audit_integrity.py`
- `backend/tests/test_audit_integrity.py`

### Files Modified

- `backend/app/database/models.py`
- `backend/app/main.py`
- `backend/app/auth.py` for the Ministry-only integrity permission

### Backend Changes

Startup performs additive compatibility changes for audit hash columns. New security and lifecycle actions use `_audit()` and therefore remain part of the chain.

### Frontend Changes

The existing Ministry-facing audit integrity control displays chain validation results. No new frontend security workflow was required for Stage 2.

### API / Endpoint Changes

`GET /api/auth/audit-log/integrity`

- Requires authentication.
- Requires `audit:integrity`.
- The permission is Ministry-only.
- Returns chain status and safe failure metadata without exposing sensitive audit contents.

### Security Controls

- Deterministic canonical audit serialization.
- Previous-record hash chaining.
- Record hash verification.
- Chain-order verification.
- SQLite writer serialization in the current single-process service.
- Safe metadata-only audit content.

### Testing

`backend/tests/test_audit_integrity.py` covers new chains, modified fields, modified previous hashes, deleted records, legacy records, empty chains, permission boundaries, and endpoint authentication.

### Verification Results

Stage 2 passed as part of the final **67-test** Stage 1–8 regression suite. Live audit-chain verification was also performed.

### Data Safety / Regression Impact

The audit implementation does not delete project-analysis data. Lifecycle events add audit records; they do not alter project, dataset, alert, or analysis-run records.

### Known Limitations

This is tamper-evident logging, not an absolute guarantee against an attacker with full database control. A privileged attacker who can alter both records and hashes may evade detection without an external immutable copy. Multi-worker/distributed chain coordination is not implemented.

## 7. Stage 3 — Secure File Upload Hardening

### Objective

Prevent unsafe, malformed, oversized, or executable content from entering the dataset-processing pipeline.

### Security Risk Addressed

Uploads are an untrusted input boundary. Risks include path traversal, executable delivery, script content, malformed Office containers, macro payloads, resource exhaustion, and parser abuse.

### Implementation

`backend/app/ml/upload_security.py` validates and stores uploads using:

- Allowed extensions: `.csv`, `.xlsx`, `.xls`.
- Blocked executable, script, archive, and macro-enabled formats including `.exe`, `.dll`, `.bat`, `.cmd`, `.ps1`, `.sh`, `.js`, `.html`, `.php`, `.zip`, `.rar`, `.7z`, and `.xlsm`.
- Maximum upload size of 50 MB.
- Maximum 1,000,000 rows.
- Maximum 500 columns.
- Filename length and control-character validation.
- Slash, backslash, traversal, and absolute-path protection.
- UUID-based storage names.
- Original filename retained as metadata only.
- CSV UTF-8 and parser validation.
- XLSX ZIP/workbook/signature validation.
- XLS legacy signature/parser validation.
- VBA macro detection.
- Executable MIME/content rejection.
- Temporary-file cleanup on rejection.

### Architecture / Technical Approach

The backend performs request limits, filename/type checks, safe temporary storage, parser/content validation, Stage 7 scanning, SHA-256 hashing, and only then continues to dataset persistence or analysis. Backend controls remain authoritative over frontend UX mirrors.

### Files Created

- `backend/app/ml/upload_security.py`
- `backend/tests/test_upload_security.py`

### Files Modified

- `backend/app/main.py`
- `backend/app/config.py`
- `backend/app/database/models.py`
- Frontend upload workflow files under `frontend/src/` for client-side validation and status display

### Backend Changes

Upload rejection paths create metadata-only audit events and remove rejected temporary files. Accepted files keep UUID storage names and continue through the original analysis pipeline.

### Frontend Changes

The upload UI mirrors allowed extensions and size restrictions for user experience. It does not replace backend enforcement.

### API / Endpoint Changes

Existing upload/analysis endpoints were hardened:

- `POST /api/inspect-datasets`
- `POST /api/upload`
- `POST /api/validate`
- `POST /api/analyze`
- `POST /api/analyze-multi`

They require authentication and the existing dataset-upload authorization path.

### Security Controls

Audit actions include events such as `DATASET_UPLOAD_ACCEPTED`, `DATASET_UPLOAD_REJECTED_TYPE`, `DATASET_UPLOAD_REJECTED_FILENAME`, `DATASET_UPLOAD_REJECTED_SIZE`, `DATASET_UPLOAD_REJECTED_PATH`, `DATASET_UPLOAD_REJECTED_CONTENT`, `DATASET_UPLOAD_REJECTED_DIMENSIONS`, `DATASET_UPLOAD_REJECTED_SCHEMA`, and `DATASET_UPLOAD_HASH_FAILED`.

### Testing

`backend/tests/test_upload_security.py` covers valid CSV/XLSX, extension rejection, traversal, filename length, size limits, fake/malformed content, macro-enabled extension rejection, temporary storage, hashing, audit events, and authentication.

### Verification Results

Stage 3 passed in the final full regression: **67 passed, 0 failed**. Upload behavior and frontend build were verified.

### Data Safety / Regression Impact

Rejected temporary files are cleaned up. Existing accepted dataset/project records are not deleted or reset by normal upload validation.

### Known Limitations

Stage 3 does not provide external antivirus or commercial EDR coverage. Stage 7 adds internal heuristic scanning but does not turn the application into a guaranteed malware detector.

## 8. Stage 4 — API Security, Rate Limiting & Request Protection

### Objective

Reduce abuse of authentication and API endpoints and establish secure HTTP response behavior.

### Security Risk Addressed

Risks include login brute force, request flooding, oversized request bodies, cross-origin abuse, browser content sniffing, clickjacking, and excessive use of expensive analysis endpoints.

### Implementation

`backend/app/security.py` implements a thread-safe monotonic-time in-memory fixed-window limiter. Middleware in `backend/app/main.py` applies authentication, authorization, rate limits, request-size checks, CORS, response headers, HSTS configuration, and production-safe errors.

Configured limits are:

- Login identity/IP: 5 per minute.
- IP soft threshold: 20 per minute.
- General authenticated requests: 60 per minute.
- Expensive endpoints: 10 per minute.
- Non-multipart API body: 5 MB.
- Multipart upload authority: Stage 3's 50 MB limit.

Expensive endpoints include `/api/upload`, `/api/validate`, `/api/analyze`, `/api/analyze-multi`, and `/api/inspect-datasets`.

### Architecture / Technical Approach

Authentication is applied before protected API handlers. Login counters reset on successful login. Exceeded limits return HTTP 429 with `Retry-After`. CORS uses explicit configured origins rather than a wildcard.

### Files Created

- `backend/app/security.py`
- `backend/tests/test_api_security.py`

### Files Modified

- `backend/app/main.py`
- `backend/app/config.py`
- `backend/.env.example`

### Backend Changes

Security middleware adds request protection and headers:

- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Referrer-Policy: no-referrer`
- `Permissions-Policy: camera=(), microphone=(), geolocation=()`
- Optional HSTS when enabled behind HTTPS

### Frontend Changes

No frontend security mechanism is treated as authoritative. Existing frontend behavior uses the backend API and existing CORS configuration.

### API / Endpoint Changes

The protection applies across authenticated APIs and especially login/upload/analysis paths. No separate anonymous security-management endpoint was introduced.

### Security Controls

- JWT authentication middleware.
- Explicit CORS origins.
- Login brute-force protection.
- General and expensive-endpoint limits.
- Request body limits.
- Safe production error responses.
- Retry-After responses.
- Security headers.

### Testing

`backend/tests/test_api_security.py` covers headers, CORS, limiter isolation, oversized requests, authentication requirements, expensive endpoint protection, and login throttling without password logging.

### Verification Results

Stage 4 passed in the final suite. The full suite result was **67 passed, 0 failed**.

### Data Safety / Regression Impact

Rate limiting and middleware do not delete or reset project data.

### Known Limitations

The limiter is in-memory and suitable primarily for the current single-process deployment. Multi-worker or distributed deployments need shared state such as Redis or an equivalent. Trusted proxy headers are not automatically trusted.

## 9. Stage 5 — Data Privacy & PII Protection

### Objective

Detect likely PII and credentials before they are unnecessarily exposed, while keeping original analytical datasets unchanged.

### Security Risk Addressed

Dataset columns may contain email addresses, phone numbers, government identifiers, financial identifiers, addresses, locations, or credentials. Returning or auditing raw values would create additional exposure.

### Implementation

`backend/app/privacy.py` provides centralized normalized-header, contextual, regex, sampling, classification, and masking helpers. It detects categories including:

- Email
- Indian phone number
- Aadhaar-like value
- PAN-like value
- Bank-account-like value
- Card-like value
- Address
- Date of birth
- GPS/location coordinates
- Passwords
- API keys
- Access tokens
- JWT-like secrets
- Credential columns

Privacy statuses are:

- `NO_PII_DETECTED_IN_SCANNED_DATA`
- `REVIEW_REQUIRED`
- `BLOCKED`

### Architecture / Technical Approach

Large datasets are sampled using `PII_SAMPLE_SIZE`. Results persist categories, confidence, columns, counts, and scan metadata. Raw values are not returned or written into audit metadata. Masking returns partial or redacted representations where display masking is needed.

Normal public MPLADS fields are explicitly excluded from automatic classification, including project name, project ID/code, category, state, district, constituency, agency, vendor, status, sanction amount, expenditure, allocation limit, and MP name.

### Files Created

- `backend/app/privacy.py`
- `backend/tests/test_privacy.py`

### Files Modified

- `backend/app/main.py`
- `backend/app/config.py`
- `backend/app/database/models.py`
- Existing frontend dataset/privacy workflow files under `frontend/src/`

### Backend Changes

The endpoint checks authentication, `analysis:read`, dataset ownership/visibility, and jurisdiction before reading a stored dataset and persisting privacy metadata.

### Frontend Changes

Existing frontend upload/data-quality workflow surfaces privacy and integrity-related dataset status. No separate security dashboard was added.

### API / Endpoint Changes

`POST /api/datasets/{dataset_id}/privacy-scan`

- Requires authentication.
- Requires `analysis:read`.
- Applies run, ownership, and jurisdiction visibility.
- Returns metadata-only findings and scan state.

### Security Controls

- Conservative classification.
- Sampling disclosure.
- Secret-column blocking.
- Display masking.
- No raw PII in responses or audit metadata.
- Original dataset remains unchanged.
- Audit events include `PII_SCAN_STARTED`, `PII_SCAN_COMPLETED`, `PII_SCAN_FAILED`, and `PII_REVIEW_REQUIRED`.

### Testing

`backend/tests/test_privacy.py` covers sensitive-value detection without raw values, secret blocking, public MPLADS fields, sampling, masking, and endpoint authentication.

### Verification Results

Stage 5 passed in the final full suite: **67 passed, 0 failed**.

### Data Safety / Regression Impact

Privacy scanning updates dataset privacy metadata only. It does not alter source file contents, projects, alerts, or analysis runs.

### Known Limitations

Detection is heuristic rather than legal or compliance certification. Sampling is not a guarantee that every row was scanned. False positives and false negatives are possible. Legacy datasets are not automatically retro-scanned.

## 10. Stage 6 — Encryption & Key Management

### Objective

Provide a reusable authenticated-encryption service for future sensitive application values without disrupting queryable analysis data or existing integrity semantics.

### Security Risk Addressed

Future optional sensitive values require confidentiality and tamper detection. Hardcoded or database-stored keys would create a separate key-compromise risk.

### Implementation

`backend/app/crypto.py` uses the established `cryptography` package and AES-256-GCM. Each encryption operation uses a fresh secure 12-byte nonce and returns a stable JSON envelope containing:

- `version`
- `algorithm`
- `nonce`
- `ciphertext`

Configuration uses:

- `APP_ENCRYPTION_KEY`
- `APP_ENCRYPTION_KEY_VERSION`
- Optional `APP_ENCRYPTION_KEYS` for versioned rotation

The service validates 32-byte key material, rejects missing/invalid configurations, rejects unsupported versions and algorithms, validates canonical Base64, detects tampering through GCM authentication, and has no plaintext fallback.

### Architecture / Technical Approach

The service is intentionally independent. No arbitrary database field was invented merely to claim encryption-at-rest. New encrypted values use the active key version; historical envelopes remain decryptable while their configured key versions remain available.

### Files Created

- `backend/app/crypto.py`
- `backend/tests/test_crypto.py`

### Files Modified

- `backend/requirements.txt`
- `backend/.env.example`
- `README.md`
- `.gitignore`

### Backend Changes

No upload, ML, audit, privacy, or authentication data path was encrypted.

### Frontend Changes

No frontend changes were required for this stage.

### API / Endpoint Changes

No API endpoint was added. The service is reusable backend functionality rather than a public encryption API.

### Security Controls

Intentionally not encrypted:

- Uploaded CSV/XLS/XLSX files.
- Dataset SHA-256 fields.
- ML and filtering data.
- User email and `identity_id`.
- `password_hash`.
- JWT/authentication secrets.
- Audit hash-chain metadata.
- Privacy metadata.

### Testing

`backend/tests/test_crypto.py` covers round trips, plaintext exclusion, fresh nonces, wrong keys, tampering, malformed envelopes, versions, rotation, missing keys, invalid keys, and key leakage.

### Verification Results

Stage 6 passed as part of the final full suite. The suite result was **67 passed, 0 failed**. The runtime environment currently uses `cryptography 50.0.1`; the repository requirement remains pinned to `43.0.3` because installing that exact version encountered intermittent package-index TLS/network errors. This is an environment maintenance note, not a failed Stage 6 security result.

### Data Safety / Regression Impact

No database records, uploaded files, analysis results, audit records, or active-run flags were changed by the encryption service.

### Known Limitations

This is not blanket SQLite or filesystem encryption. Production deployments should use a managed secret manager, KMS, or HSM. The dependency runtime/pinned-version mismatch should be normalized through the project’s dependency maintenance process.

## 11. Stage 7 — Malware/Vulnerability & Security Scanning

### Objective

Add practical non-executing security checks for uploaded files, dependencies, source code, and likely secrets.

### Security Risk Addressed

Uploaded files may contain executable signatures, scripts, macros, embedded objects, malformed containers, or decompression-risk structures. Project dependencies and source files may also contain known advisories or accidental secrets.

### Implementation

`backend/app/security_scanner.py` performs internal checks after Stage 3 validation and before SHA-256 hashing/persistence. It detects:

- Executable signatures.
- Script markers.
- Dangerous double extensions.
- Traversal/control-character filename indicators.
- XLSX macro payloads such as `vbaProject.bin`.
- Embedded Office objects.
- Malformed Office containers.
- Excessive decompression ratios.
- File-read errors.

Statuses are `CLEAN`, `SUSPICIOUS`, `BLOCKED`, and `SCAN_ERROR`. Blocked files are removed from temporary storage and are not analyzed or persisted as accepted datasets.

Optional helpers can invoke `pip-audit` and `npm audit`. The source scanner returns masked metadata only.

### Files Created

- `backend/app/security_scanner.py`
- `backend/tests/test_security_scanner.py`

### Files Modified

- `backend/app/main.py`
- `backend/app/config.py`
- `backend/.env.example`
- `backend/requirements.txt`
- `README.md`

### Backend Changes

The `_secure_upload()` path now calls the Stage 7 scanner after Stage 3 validation and before hashing. Scanner actions use metadata-only audit events such as `SECURITY_SCAN_COMPLETED`, `SECURITY_SCAN_SUSPICIOUS`, and `SECURITY_SCAN_BLOCKED`.

### Frontend Changes

No frontend changes were required for this stage. Existing upload behavior remains compatible.

### API / Endpoint Changes

No separate public scanner endpoint was added. Scanning is part of the authenticated upload and analysis flow.

### Security Controls

- Uploads treated as untrusted.
- No execution of uploaded files.
- No macro execution.
- No arbitrary archive extraction.
- Safe Office-container inspection.
- Metadata-only scan logging.
- Optional dependency tooling.
- Masked source secret findings.

### Testing

`backend/tests/test_security_scanner.py` covers safe CSV/XLSX, executable/script detection, double extensions, macros, embedded objects, malformed containers, raw-content exclusion, secret masking, and unavailable dependency tooling.

### Verification Results

Stage 7 tests passed as part of the final full regression: **67 passed, 0 failed**.

Dependency verification found:

- `npm audit`: 1 high, 3 moderate, 0 critical vulnerabilities.
- `pip-audit`: unavailable.

No dependency versions were automatically upgraded or downgraded, and reported frontend vulnerabilities were not claimed as fixed.

### Data Safety / Regression Impact

The scanner only removes rejected temporary upload files. It does not delete existing datasets, projects, alerts, or analysis runs.

### Known Limitations

The internal scanner is heuristic and is not commercial antivirus, EDR, or professional SAST. No external malware engine is configured. `pip-audit` was unavailable. No automatic dependency remediation was performed.

## 12. Stage 8 — Security Monitoring, Alerts & Incident Response

### Objective

Provide an application-level foundation for detecting, classifying, correlating, reviewing, and resolving security events without building an enterprise SIEM/SOC.

### Security Risk Addressed

Without a dedicated security-alert workflow, important authentication, authorization, upload, integrity, privacy, and scan events can be difficult to correlate or investigate. Repeated identical events can also flood storage and obscure meaningful incidents.

### Implementation

`backend/app/security_monitor.py` centralizes security-event classification and deduplication. `SecurityAlertModel` stores cybersecurity alerts in the dedicated `security_alerts` table, separate from normal project-analysis `alerts`.

Monitored events include failed authentication, authentication/API rate limiting, scope mismatch, upload rejection, Stage 7 scan blocks, dataset hash failure, and privacy review. Security alerts use:

- Severity: `INFO`, `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`.
- Lifecycle: `OPEN`, `ACKNOWLEDGED`, `INVESTIGATING`, `RESOLVED`, `FALSE_POSITIVE`.
- `occurrence_count`.
- `first_seen_at` and `last_seen_at`.
- Optional assignment and safe resolution note.
- State/district/constituency scope metadata.

### Architecture / Technical Approach

Matching open, acknowledged, or investigating events against the same event/category/target/scope within `SECURITY_ALERT_DEDUP_WINDOW_SECONDS` increment the existing occurrence count instead of creating another alert. Lifecycle changes are audited through `_audit()`.

### Files Created

- `backend/app/security_monitor.py`
- `backend/tests/test_security_monitor.py`

### Files Modified

- `backend/app/database/models.py`
- `backend/app/main.py`
- `backend/app/auth.py`
- `backend/app/config.py`
- `backend/.env.example`
- `README.md`

### Backend Changes

The security-alert table is created additively through the existing SQLAlchemy startup mechanism. Existing project-analysis `AlertModel` rows are not migrated or replaced.

A startup behavior fix was also made: startup now preserves an explicitly active analysis run and selects the latest completed run only when no active run exists. This prevents an active Run 1 from being replaced by the latest small test run after restart.

### Frontend Changes

No frontend security-alert dashboard was added. The APIs are available for authorized clients, while the existing premium UI remains unchanged.

### API / Endpoint Changes

`GET /api/security/alerts`

- Requires `security:read`.
- Supports status and severity filters.
- Applies jurisdiction scope.
- Returns safe alert metadata only.

`GET /api/security/alerts/{alert_id}`

- Requires `security:read`.
- Returns only alerts visible to the caller's scope.

`GET /api/security/summary`

- Requires `security:read`.
- Returns severity/status/category counts.

`PATCH /api/security/alerts/{alert_id}`

- Requires `security:manage`.
- Supports lifecycle status, resolution note, and assignment.
- Ministry-only assignment is enforced.
- Lifecycle actions are audited.

RBAC currently grants Ministry full security read/manage access, State Nodal Authority and District Authority scoped security read access, and does not grant Member of Parliament security-alert access.

### Security Controls

- Dedicated security-alert storage.
- Separation from analysis alerts.
- Server-side RBAC.
- State/district/constituency filtering.
- Deduplication and occurrence counting.
- Safe descriptions only.
- Audited lifecycle changes.
- No passwords, tokens, keys, raw PII, request bodies, or uploaded payloads in alerts.

### Testing

`backend/tests/test_security_monitor.py` covers event classification, creation, deduplication, time-window behavior, open status, lifecycle auditing, endpoint authentication, and separation from analysis alerts.

### Verification Results

Focused Stage 8 tests passed: **5 passed, 0 failed**. The final Stage 1–8 regression passed **67 tests**.

The current production/project database contains **0 security alerts**. This means no security-monitoring alerts currently exist in that database; it does not mean the monitoring mechanism is inactive.

### Data Safety / Regression Impact

The security-alert table is separate from project-analysis data. Current counts remain:

- Run 1 active.
- 1,130 projects in Run 1.
- 1,162 total projects.
- 436 total project-analysis alerts.
- 5 analysis runs.
- 4 users.
- 0 security alerts.

### Known Limitations

There is no enterprise SIEM, centralized log shipping, email/SMS notification, 24/7 SOC, automatic retention cleanup, or frontend security-alert dashboard. Focused tests do not cover every possible lifecycle and RBAC combination. Stage 6 key/decryption failures are not comprehensively wired as separate monitor events in the current code.

## 13. Overall Security Testing & Verification

| Stage | Focus | Verification |
|---|---|---:|
| Stage 1 | Dataset Integrity | Included in final regression |
| Stage 2 | Audit Integrity | Included in final regression |
| Stage 3 | Upload Security | Included in final regression |
| Stage 4 | API Security | Included in final regression |
| Stage 5 | Privacy | Included in final regression |
| Stage 6 | Encryption | 16 focused tests; included in final regression |
| Stage 7 | Security Scanning | 6 focused tests; included in final regression |
| Stage 8 | Security Monitoring | 5 focused tests; included in final regression |
| Full Regression | Stages 1–8 | **67 passed, 0 failed** |

The repository currently collects exactly 67 tests across the eight cybersecurity test files. Verification also included:

- Backend `compileall app`: passed.
- Frontend `npm run build`: passed.
- `git diff --check`: passed.
- Live dashboard verification: 1,130 projects, 16 states, 97 high-risk projects, 432 project-analysis alerts.
- Live security endpoints: HTTP 200 for Ministry access.
- Read-only database state verification.

## 14. Database and Data Integrity Preservation

During security testing, a smaller 8-project test analysis run temporarily became active, causing the dashboard to display 8 projects. Investigation established that the original 1,130-project records had not been deleted.

The active run was restored using a guarded transaction that changed only `is_active` flags:

- Backup: `backend/mplads_before_active_run_restore_20260912_115955.db`.
- Original database size: 50,835,456 bytes.
- Backup size: 50,835,456 bytes.
- SQLite integrity check: `ok`.
- Run 1 restored as active.
- Run 5 made inactive.
- Exactly one active run verified.
- No analysis rerun.
- No project deletion.
- No alert deletion.
- No database reset.

The later startup preservation fix ensures an existing active run is not replaced by the latest completed run on restart. The current read-only state is:

```text
Active run:        Run 1
Run 1 projects:    1,130
Run 1 alerts:      432
Total projects:    1,162
Total alerts:      436
Analysis runs:     5
Users:             4
Security alerts:   0
```

## 15. Security Limitations

The implementation is intentionally a practical SIH prototype rather than an enterprise security platform:

- Internal malware scanning is heuristic.
- No commercial antivirus or EDR engine is configured.
- `npm audit` reports unresolved frontend dependency findings: 1 high and 3 moderate.
- `pip-audit` was unavailable in the environment.
- No automatic dependency upgrades were performed.
- The rate limiter is in-memory and single-process oriented.
- PII detection is heuristic and sampling-based.
- No legal/privacy certification is claimed.
- Stage 6 does not blanket-encrypt SQLite or uploaded files.
- Runtime cryptography is 50.0.1 while the requirement remains pinned to 43.0.3 because of package-index TLS/network installation issues.
- No enterprise SIEM or centralized log shipping exists.
- No email/SMS security-alert delivery exists.
- No 24/7 SOC exists.
- No automatic security-alert or audit-log retention cleanup exists.
- No frontend security-alert dashboard exists.
- Security-monitoring tests are focused and not exhaustive for every workflow combination.

These are scope boundaries and future hardening opportunities, not claims that the implemented controls are absent.

## 16. Future Security Recommendations

These are future recommendations, not completed Stage 9 work:

1. Integrate an approved external malware/AV engine such as a controlled ClamAV adapter or enterprise service.
2. Use Redis or equivalent shared state for multi-worker rate limiting.
3. Establish dependency update and vulnerability-remediation review for the current npm findings.
4. Add `pip-audit` and `npm audit` to CI/CD.
5. Add professional SAST, DAST, and secret scanning in CI.
6. Use a managed KMS/HSM or secret manager for production encryption keys.
7. Add centralized immutable log shipping and SIEM integration.
8. Add controlled email/SMS/security notification delivery.
9. Create formal incident-response playbooks and escalation procedures.
10. Define retention policies for security alerts separately from immutable audit logs.
11. Deploy production TLS and enable HSTS only behind correctly configured HTTPS.
12. Conduct periodic penetration testing and threat-model reviews.

## 17. Files Created and Modified

The following table consolidates the security-relevant files present in the implementation. Some shared files support multiple stages.

| Stage | Files Created | Files Modified | Purpose |
|---|---|---|---|
| 1 | `backend/app/ml/integrity.py`, `backend/tests/test_integrity.py` | `backend/app/main.py`, `backend/app/database/models.py`, frontend integrity display files | Dataset hashing and verification |
| 2 | `backend/app/ml/audit_integrity.py`, `backend/tests/test_audit_integrity.py` | `backend/app/main.py`, `backend/app/database/models.py`, `backend/app/auth.py` | Hash-chained audit records and verification |
| 3 | `backend/app/ml/upload_security.py`, `backend/tests/test_upload_security.py` | `backend/app/main.py`, `backend/app/config.py`, frontend upload files | Upload validation and safe storage |
| 4 | `backend/app/security.py`, `backend/tests/test_api_security.py` | `backend/app/main.py`, `backend/app/config.py`, `backend/.env.example` | Rate limits, headers, CORS, body protection |
| 5 | `backend/app/privacy.py`, `backend/tests/test_privacy.py` | `backend/app/main.py`, `backend/app/config.py`, `backend/app/database/models.py`, frontend privacy workflow files | PII scanning and masking |
| 6 | `backend/app/crypto.py`, `backend/tests/test_crypto.py` | `backend/requirements.txt`, `backend/.env.example`, `README.md`, `.gitignore` | AES-256-GCM service and key configuration |
| 7 | `backend/app/security_scanner.py`, `backend/tests/test_security_scanner.py` | `backend/app/main.py`, `backend/app/config.py`, `backend/.env.example`, `backend/requirements.txt`, `README.md` | Non-executing upload/source/dependency scanning |
| 8 | `backend/app/security_monitor.py`, `backend/tests/test_security_monitor.py` | `backend/app/main.py`, `backend/app/database/models.py`, `backend/app/auth.py`, `backend/app/config.py`, `backend/.env.example`, `README.md` | Security events, alerts, deduplication, lifecycle, RBAC |

The root report itself is the only file created by this documentation task:

- `SIH_Cybersecurity_Implementation_Report.md`

## 18. Final Cybersecurity Status

All 8 planned cybersecurity implementation stages have been completed and verified.

- 8/8 stages completed.
- 67 passed, 0 failed full cybersecurity regression.
- Backend compilation verified.
- Frontend build verified.
- Git diff check verified.
- Controls implemented across data integrity, auditability, upload security, API protection, privacy, encryption, malware/security scanning, and monitoring/incident response.
- Database state preserved.
- Original 1,130-project analysis Run 1 remains active.
- No project-analysis data was intentionally deleted or reset.
- Known limitations documented.
- Future recommendations identified.

## 19. Conclusion

The SIH MPLADS platform now has a layered application-level defense model. It combines authenticated and scoped access, hardened file intake, dataset integrity, tamper-evident auditability, privacy-aware scanning, reusable authenticated encryption, non-executing security scanning, and a separate security-alert and incident-response foundation.

The implementation is appropriate for the current SIH prototype scope and has been verified without sacrificing the existing analysis dataset. It should be presented accurately: the platform has completed all eight planned cybersecurity stages, while enterprise malware operations, centralized SIEM capabilities, distributed rate limiting, managed key infrastructure, and formal operational security processes remain production recommendations.
