# Security Checklist: OWASP Top 10 & LLM Threat Matrix

This checklist maps our application hardening controls against the OWASP Top 10 (2021) and OWASP Top 10 for LLM Applications (2025).

---

## 1. OWASP Top 10 (2021) Mapping

| OWASP Category | Threat Scenario | Implemented Defense | Verification |
|---|---|---|---|
| **A01: Broken Access Control** | Unauthorized seller viewing another seller's live SSE stream or chat session | Cryptographic `X-Run-Token` (`secrets.token_urlsafe(32)`) validated via `hmac.compare_digest` | Automated test in `tests/test_api.py` |
| **A02: Cryptographic Failures** | Exposing OpenRouter key in client bundles or log outputs | Secret stored solely in `backend/.env`, loaded via `SecretStr`, scrubbed from logger with redaction filter | `scripts/grep_secrets_in_dist.sh` |
| **A03: Injection** | SQL injection in SQLite or CSV formula injection on export | Parameterized queries only (`?` bindings); CSV export prefixes `=, +, -, @` with single quotes (`'`) | `test_db.py` & CSV export test |
| **A04: Insecure Design** | Unlimited resource consumption or rapid model quota depletion | Strict token bucket rate limiter ($\le 16$ RPM), slowapi IP throttling (5 runs/min), max 4 agents | Rate limiter unit tests |
| **A05: Security Misconfiguration** | Clickjacking, MIME confusion, unconstrained CORS | `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, CORS strictly bound to `FRONTEND_ORIGIN` | Security headers audit |
| **A06: Vulnerable Components** | Outdated or compromised Python/Node dependencies | Automated scanning with `pip-audit`, `bandit`, and `npm audit --audit-level=high` | `scripts/security_scan.sh` |
| **A07: Identification & Auth Failures** | Brute forcing or session hijacking | Ephemeral single-session runs with high-entropy run IDs (`uuid4`) and random run tokens | Run creation validation |
| **A08: Software & Data Integrity** | Compromised scripts loaded via external CDN | All fonts and icons self-hosted via npm packages (`@fontsource-variable/*`, `lucide-react`); CSP disallows external CDNs | CSP audit |
| **A09: Security Logging & Monitoring** | Leaking credentials or PII in stdout | Redaction filter masks API keys; only lengths and model IDs logged at INFO level | Logger unit tests |
| **A10: Server-Side Request Forgery (SSRF)** | Attacker coercing scraper to fetch internal network metadata | Outbound host allowlist (`amazon.in`, `myntra.com`, `flipkart.com`, `reddit.com`, `openrouter.ai`); Playwright route aborts | SSRF unit tests |

---

## 2. OWASP Top 10 for LLM Applications (2025)

| LLM Threat Category | Threat Scenario | Implemented Defense | Verification |
|---|---|---|---|
| **LLM01: Prompt Injection** | Scraped retail title or Reddit post contains instructions to override analyst behavior | Untrusted input enclosed in `<untrusted_data>` delimiters; model explicitly instructed to treat it strictly as data | `test_prompt_injection.py` |
| **LLM02: Sensitive Information Disclosure** | Prompt injection attempting to extract `OPENROUTER_API_KEY` | Key exists solely in HTTP Authorization header; never placed into system prompt or conversational context | Leakage assertion test |
| **LLM04: Model Denial of Service** | Gigabyte input text triggering massive token processing or timeout | 64 KB HTTP body cap; candidate truncation to top 40 strings before LLM dispatch | Input boundary tests |
| **LLM06: Excessive Agency** | Compromised LLM attempting to trigger code execution or network requests | LLM output is strictly bounded to structured JSON; cannot call tools, invoke shell, or initiate requests | Pipeline design constraint |
| **LLM07: System Prompt Leakage** | User asking chat to repeat system instructions | Chat prompt instructs model to answer only seller queries and ignore meta-prompt inspection | Prompt defense test |
| **LLM09: Overreliance** | Model hallucinating nonexistent brands or invalid pricing | Deterministic scoring and pre-computed product stats enforce ground truth; deterministic fallback ready | Scoring engine tests |
