/**
 * Playwright script to capture the React Flow workflow canvas
 * at 1440x900 in both expanded and collapsed group states.
 *
 * Usage:
 *   node screenshot_canvas.mjs
 */

import { chromium } from "playwright";
import fs from "fs";
import path from "path";

const OUTPUT_DIR = "docs/screenshots";

async function run() {
  if (!fs.existsSync(OUTPUT_DIR)) {
    fs.mkdirSync(OUTPUT_DIR, { recursive: true });
  }

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
  });
  const page = await context.newPage();

  console.log("[*] Navigating to http://127.0.0.1:5173/ ...");
  try {
    await page.goto("http://127.0.0.1:5173/", { waitUntil: "networkidle" });
  } catch (err) {
    console.log("[!] Note: Make sure frontend dev server is running on port 5173.");
  }

  await page.waitForTimeout(1500);

  // 1. Capture All Groups Expanded
  const expandedPath = path.join(OUTPUT_DIR, "canvas_groups_expanded_1440x900.png");
  await page.screenshot({ path: expandedPath });
  console.log(`[+] Captured: ${expandedPath}`);

  // 2. Collapse Group Nodes if collapse toggle is present
  const collapseToggles = page.locator("button[aria-label*='Collapse group'], button:has-text('Collapse')");
  const count = await collapseToggles.count();
  if (count > 0) {
    console.log(`[*] Collapsing ${count} canvas groups...`);
    for (let i = 0; i < count; i++) {
      await collapseToggles.nth(i).click();
      await page.waitForTimeout(200);
    }
    await page.waitForTimeout(500);
    const collapsedPath = path.join(OUTPUT_DIR, "canvas_groups_collapsed_1440x900.png");
    await page.screenshot({ path: collapsedPath });
    console.log(`[+] Captured: ${collapsedPath}`);
  } else {
    console.log("[*] Group collapse toggles not yet rendered or canvas in default view.");
  }

  await browser.close();
  console.log("[+] Screenshot capture completed.");
}

run().catch((e) => {
  console.error("[-] Error capturing canvas screenshots:", e);
  process.exit(1);
});
