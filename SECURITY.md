# Security Policy

## 1. Threat Model Summary

Marketplace Keyword Agent is an AI-powered intelligence platform that analyzes Indian e-commerce search patterns and shopper phrasing across Amazon.in, Myntra, and Flipkart.

### Assets Protected
1. **OpenRouter API Key**: High-value credential restricted to free-tier models, stored exclusively in `backend/.env` on the server. Never transmitted to the client, logged, or bundled into frontend assets.
2. **LLM Quota**: Daily quota allocation (45 requests/day) and RPM limit (16 req/min) guarded against exhaustion by malicious actors or runaway automated pipelines.
3. **Local Database & Cache**: SQLite database (`backend/data/app.db`) containing cached search listings, run tokens, and historical analytics.

### Threat Actors & Vectors
- **Malicious Web Content**: Scraped listings, titles, or social comments containing direct or indirect prompt injection, HTML payloads, or SSRF trigger URLs.
- **Unauthorized Local Users**: Local system users attempting to inspect world-readable `.env` credentials or SQLite files.
- **Malicious Dependencies**: Supply chain attacks or vulnerable transitive Node/Python packages.
- **Malicious Clients**: Automated crawlers attempting denial-of-service via large request payloads or high-volume API requests.

---

## 2. Security Controls Matrix

| Control Area | Implementation | Verification Method |
| :--- | :--- | :--- |
| **API Credential Isolation** | Stored strictly in `backend/.env` using Pydantic `SecretStr`; masked in all log outputs using `RedactingFilter`. | `test_no_api_response_leaks_key`, `grep -R "sk-or" frontend/dist` |
| **Prompt Injection Defense** | All untrusted scraped text and social comments wrapped in `<untrusted_data>` blocks. System prompts instruct LLM to treat content strictly as data. Output sanitized with deterministic `gate_keywords()`. | `test_prompt_injection_gate_keywords_fixture` |
| **SSRF Prevention** | Strict host allowlist (`amazon.in`, `myntra.com`, `flipkart.com`, `reddit.com`, `openrouter.ai`) in `backend/app/net/safe_http.py` and Playwright route blocking. Resolves DNS to reject private, loopback (127.0.0.1, ::1), and link-local (169.254.169.254) addresses. | `test_ssrf_safe_http_validation` |
| **Run Token Enforcement** | Monotonic random tokens (`secrets.token_urlsafe(32)`) issued upon run creation; verified via constant-time `hmac.compare_digest` on all run-specific endpoints. | `test_token_enforcement_returns_403` |
| **HTTP Hardening & CSP** | Middlewares enforce `default-src 'none'`, `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer`, and `Cache-Control: no-store`. | `test_security_headers_present_on_response` |
| **Strict CORS** | CORS pinned strictly to exact `FRONTEND_ORIGIN` (no wildcards `*`), restricted to `GET` and `POST` methods. | `test_cors_rejects_unknown_origin` |
| **Payload Limiting** | Strict 64 KB maximum request body limit enforced via `BodySizeLimitMiddleware` (HTTP 413). | `test_body_over_64kb_returns_413` |
| **Rate Limiting** | Slowapi token-bucket rate limiter: runs 5/min, chat 20/min, preflight 10/min, global 120/min per client IP. | `test_health_and_quota_endpoints` |
| **Input Sanitization** | Strict string length limits, control character stripping, `<`/`>` HTML rejection, and URL scheme prohibition in briefs. | `test_brief_validation_rejects_malicious_inputs` |
| **CSV Formula Injection** | Cells beginning with `=`, `+`, `-`, `@`, `\t`, or `\r` automatically prefixed with `'` during export. | `test_prefixes_dangerous_csv_cells` |

---

## 3. Reporting a Vulnerability

If you discover a security vulnerability within this repository, please do not open a public issue. Instead:
1. Email details directly to the project maintainers.
2. Include reproduction steps, affected component, and expected impact.
3. We will acknowledge receipt within 48 hours and provide a remediation timeline.

---

## 4. Accepted Risks & Technical Notes

| Accepted Risk | Rationale | Review / Expiry Date |
| :--- | :--- | :--- |
| **Reddit Public JSON Scrapes** | Reddit public endpoints occasionally rate-limit unauthenticated IP addresses with HTTP 403. Scrapers fail gracefully and continue using marketplace autosuggest signals. | 2026-12-31 |
| **Playwright System Browser Fallback** | When bundled Chromium download times out or fails, browser manager falls back to system `msedge` or `chrome` channel. Hardened launch flags (`--disable-dev-shm-usage`, route filtering) remain active. | 2026-12-31 |

---

## 5. Scraping Ethics & Legal Notice

Marketplace Keyword Agent extracts only public, unauthenticated search result suggestions and product titles to assist marketplace sellers in keyword discovery.
- No user accounts or authentication credentials are created or bypassed.
- Jitter delays (`2-5` seconds) and 1-page domain concurrency limits prevent load spikes on target services.
- Media, fonts, and images are aborted to minimize network transfer.
