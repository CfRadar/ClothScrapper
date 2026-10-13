---
name: app-security-hardening
description: Provides application security hardening patterns for FastAPI and React. Covers security headers, strict CORS, slowapi rate limiting, SSRF outbound host allowlists, Playwright sandboxing, secret redaction, and OWASP Top 10 defenses. Use when implementing security controls.
---

# Application Security Hardening

## Purpose
This skill establishes security controls, defensive middleware, host-level isolation, and safe coding standards across the FastAPI backend and React frontend. It protects against Server-Side Request Forgery (SSRF), Denial of Service (DoS), unauthorized token usage, cross-site scripting (XSS), data exfiltration, and credential leaks.

## When to use
- When configuring or auditing FastAPI middleware (security headers, CORS, body size limits).
- When implementing outbound HTTP requests or Playwright browser navigation.
- When handling untrusted input, database queries, or logging.
- When configuring Content Security Policy (CSP) and frontend storage.

## Security Controls Architecture

### 1. Backend Defense-in-Depth (FastAPI)

1. **Security Headers Middleware**:
   - Apply strict headers to all HTTP responses:
     ```python
     @app.middleware("http")
     async def add_security_headers(request: Request, call_next):
         response = await call_next(request)
         response.headers["X-Content-Type-Options"] = "nosniff"
         response.headers["X-Frame-Options"] = "DENY"
         response.headers["Referrer-Policy"] = "no-referrer"
         response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
         response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
         response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
         return response
     ```

2. **Strict CORS & Host Protection**:
   - Never use wildcard (`"*"`) origins, methods, or headers:
     ```python
     app.add_middleware(
         CORSMiddleware,
         allow_origins=[settings.FRONTEND_ORIGIN], # e.g. http://localhost:5173
         allow_credentials=True,
         allow_methods=["GET", "POST", "OPTIONS"],
         allow_headers=["Content-Type", "Authorization", "X-Run-Token"],
     )
     ```

3. **Request Body Size Limit (64 KB)**:
   - Prevent memory exhaustion via malicious payload bloating:
     ```python
     MAX_BODY_SIZE = 64 * 1024  # 64 KB

     @app.middleware("http")
     async def limit_body_size(request: Request, call_next):
         content_length = request.headers.get("Content-Length")
         if content_length and int(content_length) > MAX_BODY_SIZE:
             return Response(content="Payload too large", status_code=413)
         return await call_next(request)
     ```

4. **Rate Limiting with `slowapi`**:
   - Guard against volumetric abuse per client IP:
     - `POST /api/runs`: 5 requests / minute
     - `POST /api/runs/{id}/chat`: 20 requests / minute
     - Global API limit: 120 requests / minute

5. **Per-Run Security Token (`X-Run-Token`)**:
   - Generate `secrets.token_urlsafe(32)` upon run creation. Require `X-Run-Token` on chat and stream endpoints and verify with constant-time `hmac.compare_digest`.

6. **Log Redaction & Safe Error Handling**:
   - Filter all log output to mask OpenRouter API keys (`sk-or-v1-[a-f0-9]{64}`) and authorization headers.
   - Disable interactive OpenAPI `/docs` when `APP_ENV != "dev"`. Return generic JSON errors without internal Python tracebacks.

7. **File & Database Permissions**:
   - Enforce POSIX `600` (`-rw-------`) on `.env` and `app.db` files. Always use parameterized queries (`?` in `aiosqlite`).

---

### 2. SSRF Protection & Outbound Allowlist

1. **Host Allowlist**:
   - Outbound network calls are restricted strictly to approved domains:
     - `openrouter.ai`
     - `amazon.in`, `completion.amazon.in`
     - `myntra.com`
     - `flipkart.com`
     - `reddit.com`
   - Users are never permitted to provide arbitrary target URLs.

2. **DNS & IP Resolution Guard**:
   - Resolve target hosts before connection. Reject private (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`), loopback (`127.0.0.1`), link-local (`169.254.0.0/16`), and AWS metadata (`169.254.169.254`) IP addresses.
   - Re-validate destination host on every HTTP redirect; cap redirects to $\le 3$.

3. **Playwright Route Abort**:
   - Hook `page.route("**/*", ...)` to abort any request resolving outside the allowed retail domains:
     ```python
     async def guard_route(route: Route):
         url = route.request.url
         parsed = urllib.parse.urlparse(url)
         if parsed.hostname not in ALLOWED_HOSTS:
             await route.abort("blockedbyclient")
             return
         await route.continue_()
     ```
   - In Chromium launch: disable dangerous privileges, set `accept_downloads=False`, block service workers, and never specify `--no-sandbox` unless in an isolated container environment (`IN_DOCKER=1`).

---

### 3. Frontend Hardening (React)

1. **Ban `dangerouslySetInnerHTML`**:
   - Enforce ESLint rule `react/no-danger: "error"`.
   - Always render scraped product titles, Reddit posts, and LLM text as plain text React children.

2. **Storage Validation**:
   - Wrap `localStorage` reads (`mka.layout.v1`, `mka.drawer.width.v1`) in Zod schemas with safe fallbacks.

3. **Content Security Policy**:
   - In dev and production servers, serve strict CSP headers:
     `default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; connect-src 'self' http://localhost:8000; img-src 'self' data:; frame-ancestors 'none';`

## Rules (do / don't)
- **DO** verify outbound hostnames against the hardcoded allowlist on every HTTP request and redirect.
- **DO** verify run tokens using `hmac.compare_digest` to prevent timing attacks.
- **DO** enforce 64 KB maximum request body size on FastAPI.
- **DON'T** use `dangerouslySetInnerHTML` under any circumstances.
- **DON'T** expose stack traces or raw exception messages to the client.
- **DON'T** launch Playwright with `--no-sandbox` on bare-metal host operating systems.

## Examples
See `resources/security-checklist.md` for the complete audit matrix mapped against OWASP Top 10 and OWASP LLM Top 10.

## Checklist before finishing
- [ ] Security headers middleware configured on FastAPI app.
- [ ] Host allowlist enforced for httpx and Playwright route intercepts.
- [ ] No private or link-local IPs reachable via SSRF.
- [ ] Log filter redacts `sk-or-*` keys and authentication headers.
- [ ] Request body size capped at 64 KB.
- [ ] `react/no-danger` enforced in frontend linter.
- [ ] Content Security Policy active with `frame-ancestors 'none'`.
