---
name: security-audit
description: Executes a comprehensive security audit by running pip-audit, bandit, ruff security rules, npm audit, secret leak detection, security pytests, and optional OWASP ZAP baseline scans. Use before production releases or feature merges.
---

# Workflow: security-audit

Execute this workflow before releasing features, merging pull requests, or updating external dependencies to verify zero High or Critical vulnerabilities exist in the codebase.

## Prerequisites
- Python virtual environment with dev/security dependencies (`pip install pip-audit bandit`).
- Node.js dependencies installed (`cd frontend && npm install`).
- Bash shell available (`bash` on Linux/macOS or Git Bash on Windows).

---

## Step-by-Step Execution Procedure

### Step 1: Run Unified Security Scanner
Execute the automated security scanning script:
```bash
bash .agent/skills/vulnerability-scanning/scripts/security_scan.sh
```
This runs:
1. `pip-audit -r backend/requirements.txt` (Python dependency CVE scan)
2. `bandit -r backend/app -ll` (Python static AST security analysis)
3. `ruff check backend/ --select S` (Python security linter rules)
4. `cd frontend && npm audit --omit=dev --audit-level=high` (Node package vulnerability scan)
5. `python .agent/skills/vulnerability-scanning/scripts/check_env_perms.py` (File permission audit)
6. `bash .agent/skills/vulnerability-scanning/scripts/grep_secrets_in_dist.sh` (Secret leakage scan)

Review the generated table in `security-report.md`.

### Step 2: Run Security Pytest Suite
Run backend tests that assert security boundaries, rate limiting, and prompt injection defenses:
```bash
python -m pytest backend/tests/test_limiter.py backend/tests/test_api.py -v
```
Ensure:
- Rate limiter throttles excess requests without leaking server timing.
- No `sk-or` API keys appear in any API response or serialized model dump.
- Prompt injection fixture tests pass with 100% clean output gating.

### Step 3: Run Optional DAST Scan (OWASP ZAP Baseline)
If Docker or OWASP ZAP is installed locally:
1. Ensure the backend is running (`uvicorn backend.app.main:app --port 8000`).
2. Run baseline scan:
   ```bash
   docker run --rm -t ghcr.io/zaproxy/zaproxy:stable zap-baseline.py -t http://host.docker.internal:8000 -r zap_report.html
   ```

### Step 4: Summarize Findings & Triage
1. Classify all reported findings by severity:
   - **Critical / High**: Must be resolved immediately before proceeding.
   - **Medium / Low**: Triage and resolve or document.
2. If High/Critical vulnerabilities exist:
   - Update affected package in `requirements.txt` or `package.json`.
   - Patch code path and re-run Step 1.
3. If a vulnerability is determined to be a false positive or unreachable in our architecture:
   - Document technical justification, non-exploitability proof, and a 90-day expiry date in `SECURITY.md`.
4. Re-run Step 1 and confirm `security-report.md` reports an overall **PASS** with exit code 0.
