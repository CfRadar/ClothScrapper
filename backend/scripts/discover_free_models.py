#!/usr/bin/env python3
"""
backend/scripts/discover_free_models.py

Usage:
    python backend/scripts/discover_free_models.py
    python backend/scripts/discover_free_models.py --api-key YOUR_KEY

Description:
    Queries OpenRouter models endpoint to discover all active :free models,
    inspect context lengths, and generate an updated fallback block for backend/.env.
"""

import argparse
import json
import sys
import urllib.error
import urllib.request

MODELS_API_URL = "https://openrouter.ai/api/v1/models"


def fetch_openrouter_models(api_key: str = None) -> list:
    headers = {
        "User-Agent": "MarketplaceKeywordAgent/1.0",
        "HTTP-Referer": "http://localhost:5173",
        "X-Title": "Marketplace Keyword Agent",
    }
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    req = urllib.request.Request(MODELS_API_URL, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("data", [])
    except Exception as e:
        print(f"[ERROR] Failed to fetch models: {e}", file=sys.stderr)
        sys.exit(1)


def is_free_model(model: dict) -> bool:
    model_id = model.get("id", "")
    pricing = model.get("pricing", {})
    prompt_price = str(pricing.get("prompt", "1")).strip()
    completion_price = str(pricing.get("completion", "1")).strip()

    if model_id.endswith(":free"):
        return True
    if prompt_price in ("0", "0.0") and completion_price in ("0", "0.0"):
        return True
    return False


def main():
    parser = argparse.ArgumentParser(description="Discover active free-tier models on OpenRouter")
    parser.add_argument("--api-key", default=None, help="Optional OpenRouter API key")
    args = parser.parse_args()

    models = fetch_openrouter_models(api_key=args.api_key)
    free_models = [m for m in models if is_free_model(m)]

    print("=" * 80)
    print(f"DISCOVERED {len(free_models)} OPENROUTER FREE TIER (:free) MODELS")
    print("=" * 80)
    print(f"{'Model ID':<50} | {'Context':<8} | {'Modality'}")
    print("-" * 80)

    free_ids = []
    for m in sorted(free_models, key=lambda x: x.get("context_length", 0), reverse=True):
        m_id = m.get("id", "")
        ctx = m.get("context_length", 0)
        arch = m.get("architecture", {})
        modality = arch.get("modality", "text->text")
        print(f"{m_id:<50} | {ctx:<8} | {modality}")
        if m_id.endswith(":free"):
            free_ids.append(m_id)

    print("=" * 80)
    print("\nSuggested backend/.env configuration:")
    planner = free_ids[0] if free_ids else "google/gemini-2.0-flash-exp:free"
    analyst = free_ids[1] if len(free_ids) > 1 else planner
    social = free_ids[2] if len(free_ids) > 2 else planner
    fallbacks = (
        ",".join(free_ids[3:7])
        if len(free_ids) > 3
        else "meta-llama/llama-3.3-70b-instruct:free,mistralai/mistral-7b-instruct:free"
    )

    print(f"MODEL_PLANNER={planner}")
    print(f"MODEL_ANALYST={analyst}")
    print(f"MODEL_SOCIAL={social}")
    print(f"MODEL_FALLBACKS={fallbacks}")


if __name__ == "__main__":
    main()
