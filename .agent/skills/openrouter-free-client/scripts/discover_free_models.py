#!/usr/bin/env python3
"""
scripts/discover_free_models.py

Usage:
    python scripts/discover_free_models.py
    python scripts/discover_free_models.py --api-key YOUR_OPENROUTER_KEY

Description:
    Queries the OpenRouter public API (GET https://openrouter.ai/api/v1/models) to discover
    all active models offering zero-cost prompt and completion pricing (i.e. model IDs ending in ':free'
    or pricing.prompt == '0' and pricing.completion == '0').

    Inspects each model's id, context_length, supported parameters (such as structured_outputs /
    response_format), and prints a formatted summary table along with a suggested .env fallback configuration.

Requirements:
    pip install httpx rich (or run with standard library urllib if httpx is unavailable)
"""

import sys
import json
import argparse
import urllib.request
import urllib.error

MODELS_API_URL = "https://openrouter.ai/api/v1/models"

def fetch_openrouter_models(api_key: str = None) -> list:
    headers = {
        "User-Agent": "MarketplaceKeywordAgent/1.0",
        "HTTP-Referer": "https://github.com/marketplace-keyword-agent",
        "X-Title": "Marketplace Keyword Agent Discovery",
    }
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    req = urllib.request.Request(MODELS_API_URL, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("data", [])
    except urllib.error.HTTPError as e:
        print(f"[ERROR] Failed to fetch models: HTTP {e.code} - {e.reason}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] Connection error: {e}", file=sys.stderr)
        sys.exit(1)

def is_free_model(model: dict) -> bool:
    model_id = model.get("id", "")
    pricing = model.get("pricing", {})
    prompt_price = str(pricing.get("prompt", "1")).strip()
    completion_price = str(pricing.get("completion", "1")).strip()
    
    # Check ':free' suffix or zero pricing
    if model_id.endswith(":free"):
        return True
    if prompt_price in ("0", "0.0") and completion_price in ("0", "0.0"):
        return True
    return False

def inspect_and_display(models: list):
    free_models = [m for m in models if is_free_model(m)]
    
    if not free_models:
        print("No zero-cost / :free models found. Verify API availability at https://openrouter.ai/models")
        return

    print("\n" + "=" * 90)
    print(f"DISCOVERED {len(free_models)} OPENROUTER FREE TIER (:free) MODELS")
    print("=" * 90)
    print(f"{'Model ID':<50} | {'Context':<8} | {'Structured Out':<14} | {'Modality'}")
    print("-" * 90)

    recommended_chain = []

    for m in sorted(free_models, key=lambda x: x.get("context_length", 0), reverse=True):
        m_id = m.get("id", "")
        ctx = m.get("context_length", 0)
        arch = m.get("architecture", {})
        modality = arch.get("modality", "text->text")
        
        # Check structured outputs / response format support
        supported_params = m.get("supported_parameters", []) or []
        has_struct = "response_format" in supported_params or "structured_outputs" in supported_params
        struct_label = "YES" if has_struct else "PROMPT_ONLY"

        print(f"{m_id:<50} | {ctx:<8} | {struct_label:<14} | {modality}")
        
        # Filter for text chat models ending in :free
        if m_id.endswith(":free"):
            recommended_chain.append(m_id)

    print("=" * 90)
    print("\n[RECOMMENDED .env FALLBACK CHAIN CONFIGURATION]")
    print("# Place in your backend .env file (ordered by preference and context window):")
    
    primary = recommended_chain[0] if recommended_chain else "google/gemini-2.0-flash-exp:free"
    fallbacks = ",".join(recommended_chain[1:5]) if len(recommended_chain) > 1 else "meta-llama/llama-3.3-70b-instruct:free,mistralai/mistral-7b-instruct:free"

    print(f"OPENROUTER_PRIMARY_MODEL={primary}")
    print(f"OPENROUTER_FALLBACK_MODELS={fallbacks}")
    print("OPENROUTER_MAX_RPM=16")
    print("OPENROUTER_TIMEOUT_SECONDS=45")
    print("\nVerify live rate limits at: https://openrouter.ai/docs/api-reference/limits\n")

def main():
    parser = argparse.ArgumentParser(description="Discover active free-tier models on OpenRouter")
    parser.add_argument("--api-key", default=None, help="Optional OpenRouter API key to include in headers")
    args = parser.parse_args()

    print("[*] Contacting OpenRouter API to discover free models...")
    models = fetch_openrouter_models(api_key=args.api_key)
    inspect_and_display(models)

if __name__ == "__main__":
    main()
