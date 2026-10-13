# Common Pipeline Failure Modes & Recovery Playbooks

## 1. Playwright Missing Bundled Chromium
- **Symptom**: `Bundled Chromium launch failed (BrowserType.launch: Executable doesn't exist at C:\Users\...\chrome-headless-shell.exe)`
- **Solution**:
  - Run `playwright install chromium` to fetch the standalone binary.
  - Or in `BrowserManager.launch()`, directly specify `channel="msedge"` if edge is detected, avoiding the failed attempt to launch missing bundled chromium.

## 2. OpenRouter Free LLM Prompt Bloat & Schema Parsing Failures
- **Symptom**:
  - `prompt_len > 8000`
  - `Model openrouter/free output failed schema parsing: No balanced JSON object {...} found in response text.`
  - `1-shot repair prompt_len > 14000`
  - Fallback model chain triggers 429 rate limit.
- **Root Cause**:
  - Free models on OpenRouter (:free) often have small effective context windows or fail when overwhelmed with massive raw scraping dumps.
  - Wildcard model ID `openrouter/free` picks random free models with inconsistent JSON capabilities.
- **Solution**:
  1. **Prompt Compaction**: Send only top 10 keywords and top 5 titles per platform. Minify JSON whitespace.
  2. **Model Selection**: Use explicitly capable free models (`meta-llama/llama-3.3-70b-instruct:free`, `google/gemini-2.0-flash-exp:free`, `qwen/qwen-2.5-72b-instruct:free`, `nvidia/nemotron-3-super-120b-a12b:free`).
  3. **Lean Repair**: When repairing JSON, do not resend the entire 9k prompt—only send the malformed output with a concise fix instruction.

## 3. Reddit Unauthenticated 403 Block
- **Symptom**: `Reddit returned 403 Blocked for r/...`
- **Solution**:
  - Return polite `status="blocked"` with available social signals.
  - Use offline cached trends when public search is restricted.
