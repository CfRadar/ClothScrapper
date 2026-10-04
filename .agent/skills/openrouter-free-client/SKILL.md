---
name: openrouter-free-client
description: Guides resilient interaction with OpenRouter free-tier (:free) models. Use when calling OpenRouter LLMs, configuring model fallback chains, enforcing token-bucket rate limits (<=16 RPM), parsing brittle JSON completions, or handling 429 rate limit errors with exponential backoff.
---

# OpenRouter Free Client

## Purpose
This skill defines the architectural and operational pattern for consuming OpenRouter's free-tier (`:free`) models safely within severe quota constraints (~20 requests/minute, low daily ceiling, no SLAs). It provides a robust, zero-cost LLM client featuring fallback model rotation, token-bucket rate limiting, 429 backoff, and defensive JSON repair.

> [!IMPORTANT]
> Verify current live limits, tier status, and rate thresholds at [https://openrouter.ai/docs/api-reference/limits](https://openrouter.ai/docs/api-reference/limits) before deploying or changing model parameters.

## When to use
- When setting up or modifying backend LLM client code (`OpenRouterClient`).
- When sending prompts from the AI Planner or AI Analyst agents.
- When discovering or updating the model fallback chain using `scripts/discover_free_models.py`.
- When handling `429 Too Many Requests` or context length errors from OpenRouter.
- When parsing structured JSON responses from models that do not reliably support native schema enforcement.

## Step-by-step procedure

1. **Discover and Configure Fallback Chain**:
   - Run `python scripts/discover_free_models.py` to identify operational `:free` models with adequate context length.
   - Configure in backend `.env`:
     ```env
     OPENROUTER_API_KEY=sk-or-v1-...
     OPENROUTER_PRIMARY_MODEL=google/gemini-2.0-flash-exp:free
     OPENROUTER_FALLBACK_MODELS=meta-llama/llama-3.3-70b-instruct:free,mistralai/mistral-7b-instruct:free,qwen/qwen-2.5-72b-instruct:free
     OPENROUTER_MAX_RPM=16
     OPENROUTER_TIMEOUT_SECONDS=45
     ```
   - Build an in-memory list `[OPENROUTER_PRIMARY_MODEL, *OPENROUTER_FALLBACK_MODELS.split(",")]`.

2. **Initialize Token-Bucket Rate Limiter**:
   - Implement an in-process async token bucket:
     - Capacity: 16 tokens (default to keep buffer below 20 req/min limit).
     - Refill rate: 16 tokens per 60.0 seconds (approx 1 token every 3.75s).
   - Before any HTTP dispatch, `await limiter.acquire()` to block gracefully without triggering upstream 429s.

3. **Construct HTTP Request**:
   - Base endpoint: `https://openrouter.ai/api/v1/chat/completions`
   - Mandatory HTTP headers:
     ```python
     headers = {
         "Authorization": f"Bearer {settings.OPENROUTER_API_KEY.get_secret_value()}",
         "HTTP-Referer": "http://localhost:8000",
         "X-Title": "Marketplace Keyword Agent",
         "Content-Type": "application/json",
     }
     ```
   - Set timeout: connect timeout 10s, read timeout 45s.

4. **Execute Call with Fallback and Exponential Backoff**:
   - Iterate through model fallback list:
     - On status `200`: extract `choices[0].message.content`, record call in SQLite quota table, return text.
     - On status `429`:
       1. Read `Retry-After` header if present (default to `2 ** attempt + random.uniform(0.5, 1.5)`).
       2. Log warning: `Model {model_id} returned 429. Backing off for {delay:.2f}s`.
       3. If retry count reaches 2 on current model, switch immediately to next fallback model.
     - On status `500` / `502` / `503`: switch immediately to the next fallback model.
     - On timeout: retry once with next model.

5. **Defensive JSON Extraction and Repair**:
   - Free models frequently disregard `response_format={"type": "json_object"}` and wrap text in conversational prose or markdown fences.
   - Strip markdown code blocks:
     ```python
     clean = re.sub(r"^```(?:json)?\s*", "", raw_text.strip(), flags=re.MULTILINE)
     clean = re.sub(r"```\s*$", "", clean, flags=re.MULTILINE).strip()
     ```
   - Extract outermost braces `{...}` or brackets `[...]` using brace-matching logic.
   - Attempt `json.loads()`. If failed:
     - Retry 1: Run regex-based repair (remove trailing commas `,}`, fix unescaped newlines in strings).
     - Retry 2: Send raw text back to the fast fallback LLM with a 1-shot repair prompt: `Extract ONLY valid JSON matching this schema: {schema}`.
     - Validate output with target Pydantic model.

6. **Batch Prompts to Conserve LLM Budget**:
   - Never make N individual calls for N platforms. Send a unified prompt to the Planner (Amazon + Myntra + Flipkart in 1 call).
   - Send unified scraped outputs to the Analyst (all platform analyses + other factors in 1 call).

## Rules (do / don't)
- **DO** verify current rate limits and model status at `https://openrouter.ai/docs/api-reference/limits`.
- **DO** use an ordered fallback chain of `:free` models so service continues when one free model goes offline.
- **DO** enforce token-bucket rate limiting (<=16 requests/minute) locally before dispatching HTTP calls.
- **DO** strip markdown code blocks and regex-extract JSON defensively before Pydantic validation.
- **DON'T** hardcode a single model ID anywhere in code. Always load from environment configuration.
- **DON'T** use any model ID that does NOT end in `:free`.
- **DON'T** rotate multiple API keys to circumvent rate limits (strictly forbidden; use exactly one API key).
- **DON'T** log, print, or expose the `OPENROUTER_API_KEY` in error messages, logs, or API responses.
- **DON'T** make multiple conversational roundtrips when a single batched prompt achieves the outcome.

## Examples

### Resilient Call & JSON Parsing Implementation Outline
```python
import json
import re
from pydantic import BaseModel, ValidationError

class ExtractedKeywords(BaseModel):
    amazon: list[str]
    myntra: list[str]
    flipkart: list[str]

def extract_json_payload(raw: str) -> dict:
    # 1. Strip markdown fences
    cleaned = re.sub(r"```(?:json)?", "", raw).replace("```", "").strip()
    
    # 2. Extract first outer matching brace pair
    match = re.search(r"(\{.*\})", cleaned, re.DOTALL)
    if match:
        cleaned = match.group(1)
        
    # 3. Clean trailing commas
    cleaned = re.sub(r",\s*([\]}])", r"\1", cleaned)
    return json.loads(cleaned)
```

## Checklist before finishing
- [ ] API key kept strictly in backend `.env` and typed as Pydantic `SecretStr`.
- [ ] Model discovery script tested and confirmed working.
- [ ] Ordered fallback chain specified via environment variables with `:free` suffixes.
- [ ] Token bucket configured for <=16 RPM.
- [ ] 429 exponential backoff with jitter and fallback switching implemented.
- [ ] Defensive fence-stripping and JSON repair implemented before Pydantic validation.
- [ ] Rate limits verified against OpenRouter documentation.
