import asyncio
import os
import sys
import httpx
from playwright.async_api import async_playwright

async def run():
    print("=== Phase 9: Live E2E Run Verification ===")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="msedge", headless=True)
        page = await browser.new_page(viewport={"width": 1440, "height": 900})
        
        await page.goto("http://127.0.0.1:5173/")
        await page.wait_for_load_state("networkidle")
        await asyncio.sleep(2)
        
        # Check if results drawer is already visible from stored run
        results_header = page.locator("h2:has-text('Results')")
        if await results_header.count() == 0:
            drawer_btn = page.locator("button[aria-label='Show results drawer']")
            if await drawer_btn.count() > 0:
                await drawer_btn.click()
                await asyncio.sleep(1)
        
        if await results_header.count() == 0:
            print("[*] No stored run found. Clicking 'Run workflow'...")
            run_btn = page.locator("button:has-text('Run workflow')")
            await run_btn.click()
            await results_header.wait_for(state="visible", timeout=180000)
            
        print("[+] Results drawer is open and verified!")
        await asyncio.sleep(1)
        
        # 1. Keywords Screenshot
        await page.screenshot(path="docs/screenshots/results_drawer_keywords.png")
        print("[+] Captured docs/screenshots/results_drawer_keywords.png")
        
        # 2. Click "Other factors" tab
        factors_tab = page.locator("[role='tab']:has-text('Other factors')")
        await factors_tab.click()
        await asyncio.sleep(1)
        await page.screenshot(path="docs/screenshots/results_drawer_factors.png")
        print("[+] Captured docs/screenshots/results_drawer_factors.png")
        
        # 3. Click "Run" tab
        run_tab = page.locator("[role='tab']:has-text('Run')")
        await run_tab.click()
        await asyncio.sleep(1)
        await page.screenshot(path="docs/screenshots/results_drawer_run_timeline.png")
        print("[+] Captured docs/screenshots/results_drawer_run_timeline.png")
        
        # 4. Click "Chat" tab
        chat_tab = page.locator("[role='tab']:has-text('Chat')")
        await chat_tab.click()
        await asyncio.sleep(1)
        await page.screenshot(path="docs/screenshots/results_drawer_chat.png")
        print("[+] Captured docs/screenshots/results_drawer_chat.png")
        
        # Test sending a chat message to verify chat patch
        input_field = page.locator("textarea[placeholder*='Ask']")
        if await input_field.count() > 0:
            print("[*] Testing chat message dispatch...")
            await input_field.fill("Make Myntra keywords more casual")
            send_btn = page.locator("button[aria-label='Send message']")
            await send_btn.click()
            print("[*] Waiting for chat response...")
            await asyncio.sleep(6)
            await page.screenshot(path="docs/screenshots/results_drawer_chat_response.png")
            print("[+] Captured docs/screenshots/results_drawer_chat_response.png")
            
        await browser.close()
        print("Live verification complete!")

if __name__ == "__main__":
    asyncio.run(run())
