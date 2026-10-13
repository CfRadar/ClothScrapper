import asyncio
import os
from playwright.async_api import async_playwright

async def main():
    os.makedirs("docs/screenshots", exist_ok=True)
    async with async_playwright() as p:
        try:
            browser = await p.chromium.launch(channel="msedge", headless=True)
        except Exception:
            try:
                browser = await p.chromium.launch(channel="chrome", headless=True)
            except Exception:
                browser = await p.chromium.launch(headless=True)
        
        # 1. 1440x900 Light Mode
        context = await browser.new_context(viewport={"width": 1440, "height": 900})
        page = await context.new_page()
        print("Navigating to http://127.0.0.1:5173/ ...")
        await page.goto("http://127.0.0.1:5173/", wait_until="networkidle")
        await asyncio.sleep(2)  # wait for fonts and canvas to settle
        
        # Ensure Light Mode
        await page.evaluate("() => { document.documentElement.setAttribute('data-theme', 'light'); }")
        await asyncio.sleep(0.5)
        await page.screenshot(path="docs/screenshots/canvas_light_1440x900.png")
        print("Captured docs/screenshots/canvas_light_1440x900.png")
        
        # 2. 1440x900 Dark Mode
        await page.evaluate("() => { document.documentElement.setAttribute('data-theme', 'dark'); }")
        await asyncio.sleep(0.5)
        await page.screenshot(path="docs/screenshots/canvas_dark_1440x900.png")
        print("Captured docs/screenshots/canvas_dark_1440x900.png")
        
        # 3. 1024x768 Dark Mode
        await page.set_viewport_size({"width": 1024, "height": 768})
        await asyncio.sleep(0.5)
        await page.screenshot(path="docs/screenshots/canvas_dark_1024x768.png")
        print("Captured docs/screenshots/canvas_dark_1024x768.png")
        
        # 4. 1024x768 Light Mode
        await page.evaluate("() => { document.documentElement.setAttribute('data-theme', 'light'); }")
        await asyncio.sleep(0.5)
        await page.screenshot(path="docs/screenshots/canvas_light_1024x768.png")
        print("Captured docs/screenshots/canvas_light_1024x768.png")
        
        # Reset to 1440x900 for dialogs
        await page.set_viewport_size({"width": 1440, "height": 900})
        
        # 5. Brief Dialog
        edit_brief_btn = page.locator("button:has-text('Configure brief')")
        if await edit_brief_btn.count() > 0:
            await edit_brief_btn.first.click()
            await page.wait_for_selector("[role='dialog']", timeout=5000)
            await asyncio.sleep(0.5)
            await page.screenshot(path="docs/screenshots/brief_dialog_1440x900.png")
            print("Captured docs/screenshots/brief_dialog_1440x900.png")
            # Close dialog via Cancel or Esc
            await page.keyboard.press("Escape")
            await asyncio.sleep(0.5)
            
        # 6. Security Dialog
        sec_btn = page.locator("button[aria-label='Security preflight']")
        if await sec_btn.count() > 0:
            await sec_btn.click()
            await page.wait_for_selector("[role='dialog']", timeout=5000)
            await asyncio.sleep(1.5)  # Wait for preflight fetch
            await page.screenshot(path="docs/screenshots/security_dialog_1440x900.png")
            print("Captured docs/screenshots/security_dialog_1440x900.png")
            await page.keyboard.press("Escape")
            await asyncio.sleep(0.5)
            
        # 7. Check Drawer Toggle
        drawer_handle = page.locator("button[aria-label='Show results'], button[aria-label='Hide results']")
        if await drawer_handle.count() > 0:
            await drawer_handle.first.click()
            await asyncio.sleep(0.5)
            await page.screenshot(path="docs/screenshots/drawer_open_1440x900.png")
            print("Captured docs/screenshots/drawer_open_1440x900.png")
            
        await browser.close()
        print("Screenshots captured successfully.")

if __name__ == "__main__":
    asyncio.run(main())
