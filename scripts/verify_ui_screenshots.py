import os
import time
from playwright.sync_api import sync_playwright

ARTIFACT_DIR = r"C:\Users\anura\.gemini\antigravity-ide\brain\1e10aa62-9fe7-4557-a0f1-6195bb0951ab"
os.makedirs(ARTIFACT_DIR, exist_ok=True)

def verify_and_capture():
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=True, channel="msedge")
        except Exception:
            try:
                browser = p.chromium.launch(headless=True, channel="chrome")
            except Exception:
                print("No system msedge/chrome channel found.")
                return
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        print("Navigating to http://localhost:5173...")
        page.goto("http://localhost:5173", wait_until="networkidle")
        time.sleep(1)

        # 1. Capture light mode
        light_path = os.path.join(ARTIFACT_DIR, "single_page_ui_light.png")
        page.screenshot(path=light_path)
        print(f"Captured light mode: {light_path}")

        # 2. Toggle dark mode
        theme_btn = page.locator("button[aria-label='Toggle theme']")
        if theme_btn.count() > 0:
            theme_btn.click()
            time.sleep(0.5)
            dark_path = os.path.join(ARTIFACT_DIR, "single_page_ui_dark.png")
            page.screenshot(path=dark_path)
            print(f"Captured dark mode: {dark_path}")
            theme_btn.click()  # switch back to light
            time.sleep(0.5)

        # 3. Open System Check Dialog
        sys_btn = page.locator("button:has-text('System check')")
        if sys_btn.count() > 0:
            sys_btn.click()
            time.sleep(1)
            sys_path = os.path.join(ARTIFACT_DIR, "system_check_dialog.png")
            page.screenshot(path=sys_path)
            print(f"Captured system check dialog: {sys_path}")
            # Close dialog
            close_btn = page.locator("button:has-text('Close')")
            if close_btn.count() > 0:
                close_btn.click()
                time.sleep(0.5)

        browser.close()
        print("Visual verification completed successfully!")

if __name__ == "__main__":
    verify_and_capture()
