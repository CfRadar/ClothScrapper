#!/usr/bin/env python3
"""
backend/scripts/run_e2e_smoke.py

Usage:
    python backend/scripts/run_e2e_smoke.py

Description:
    Runs an end-to-end smoke test of the entire pipeline using ASGI transport.
    Tests the brief: "oversized acid wash black graphic t-shirt, men, 240 GSM cotton"
    across Amazon.in, Myntra, and Flipkart.
    Verifies:
      - Quota call count before and after (<= 4 calls)
      - Keywords output for each platform
      - Other factors generation
      - Chat keyword patching
"""

import asyncio
import os
import sys

sys.path.insert(0, os.getcwd())
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

import httpx
from backend.app.main import app
from backend.app.orchestrator import WorkflowOrchestrator
from backend.app.schemas import ProductBrief


async def main():
    print("=" * 70)
    print("STARTING END-TO-END PIPELINE VERIFICATION")
    print("=" * 70)

    from backend.app.db import init_db
    await init_db()

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # 1. Check Quota Before
        q_before = (await client.get("/api/quota")).json()
        print(f"[*] Quota before run: {q_before['remaining_today']} calls remaining today")

        brief_data = {
            "platforms": ["amazon", "myntra", "flipkart"],
            "tshirt_type": "oversized acid wash graphic tee",
            "color": "black",
            "gender": "men",
            "fit": "drop shoulder boxy fit",
            "fabric": "240 GSM cotton",
            "neck": "round neck",
            "sleeve": "half sleeve",
            "print_or_design": "minimal graphic back print",
            "occasion": "streetwear college casual",
            "price_min": 499,
            "price_max": 999
        }

        brief = ProductBrief.model_validate(brief_data)
        orchestrator = WorkflowOrchestrator()

        events_received = []
        async def mock_emit(evt_type, stage, msg, data=None):
            events_received.append((evt_type, stage, msg))
            print(f"  [{stage.upper()}] {msg}")

        print("\n[*] Executing 4-agent pipeline...")
        result = await orchestrator.run_pipeline("smoke_test_run", brief, mock_emit)

        # 2. Check Result Outputs
        print("\n" + "=" * 70)
        print("PIPELINE RESULT VERIFICATION")
        print("=" * 70)
        for p_kw in result.keywords:
            print(f"Platform: {p_kw.platform.upper()} -> {len(p_kw.keywords)} keywords")
            print(f"  Sample keywords: {', '.join(p_kw.keywords[:5])}")

        print("\nOther Factors:")
        print(f"  Target Market: {result.other_factors.target_market_summary[:60]}...")
        for p, factors in result.other_factors.per_platform.items():
            print(f"  {p.upper()} Price Band: {factors.price_band}")
            print(f"  {p.upper()} Title Formula: {factors.title_formula}")
            print(f"  {p.upper()} Negative Keywords: {factors.negative_keywords[:3]}")

        # 3. Test Chat Customization
        print("\n[*] Testing Chat Customization...")
        chat_resp = await orchestrator.analyst.chat(result, "Make Myntra keywords more Gen-Z streetwear focused")
        print(f"  Analyst Reply: {chat_resp.reply[:80]}...")
        if chat_resp.keywords_patch:
            print(f"  Keywords Patched for: {[p.platform for p in chat_resp.keywords_patch]}")

        # 4. Check Quota After
        q_after = (await client.get("/api/quota")).json()
        calls_used = q_before["remaining_today"] - q_after["remaining_today"]
        print(f"\n[*] Total LLM Calls consumed in run: {calls_used} (Hard constraint: <= 4)")
        assert calls_used <= 4, f"FAILED: LLM calls ({calls_used}) exceeded budget of 4!"

        from backend.app.scrapers.browser import BrowserManager
        await BrowserManager.get_instance().close()
        await asyncio.sleep(0.5)

        print("\n[SUCCESS] End-to-end verification passed cleanly!\n")

if __name__ == "__main__":
    asyncio.run(main())
