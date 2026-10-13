import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="msedge", headless=True)
        page = await browser.new_page(viewport={"width": 1440, "height": 900})
        
        await page.goto("http://127.0.0.1:5173/")
        await page.wait_for_load_state("networkidle")
        await asyncio.sleep(2)
        
        # Click Chat tab
        chat_tab = page.locator("[role='tab']:has-text('Chat')")
        await chat_tab.click()
        await asyncio.sleep(1)
        
        # Click suggestion chip: "Make Myntra keywords more casual"
        chip = page.locator("button:has-text('Make Myntra keywords more casual'), div:has-text('Make Myntra keywords more casual')")
        print("Clicking suggestion chip...")
        await chip.first.click()
        
        print("Waiting for chat response (timeout: 45s)...")
        # Wait for user message and assistant message
        await page.wait_for_selector(".space-y-3 > div", timeout=45000)
        await asyncio.sleep(4)
        
        await page.screenshot(path="docs/screenshots/results_drawer_chat_response.png")
        print("Captured docs/screenshots/results_drawer_chat_response.png")
        
        # Switch back to Keywords tab to verify patched keywords flash
        kw_tab = page.locator("[role='tab']:has-text('Keywords')")
        await kw_tab.click()
        await asyncio.sleep(1)
        await page.screenshot(path="docs/screenshots/results_drawer_keywords_patched.png")
        print("Captured docs/screenshots/results_drawer_keywords_patched.png")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
