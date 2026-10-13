#!/usr/bin/env node
/**
 * Captures visual review screenshots of the React Flow canvas in light and dark mode.
 * Usage: node screenshot_canvas.mjs [url] [outputDir]
 */

import { chromium } from "playwright";
import fs from "fs";
import path from "path";

const targetUrl = process.argv[2] || "http://localhost:5173";
const outputDir = process.argv[3] || path.join(process.cwd(), "screenshots");

if (!fs.existsSync(outputDir)) {
  fs.mkdirSync(outputDir, { recursive: true });
}

async function capture() {
  console.log(`[screenshot_canvas] Launching Chromium to capture canvas at ${targetUrl}...`);
  const browser = await chromium.launch({ headless: true });

  const viewports = [
    { name: "desktop-1440x900", width: 1440, height: 900 },
    { name: "tablet-1024x768", width: 1024, height: 768 },
  ];

  for (const vp of viewports) {
    for (const theme of ["dark", "light"]) {
      const context = await browser.newContext({
        viewport: { width: vp.width, height: vp.height },
        colorScheme: theme,
      });

      const page = await context.newPage();
      try {
        await page.goto(targetUrl, { waitUntil: "networkidle", timeout: 15000 });
      } catch (err) {
        console.warn(`[WARN] Networkidle timeout on ${targetUrl}, proceeding with current DOM: ${err.message}`);
      }

      // Allow React Flow graph layout to settle
      await page.waitForTimeout(1000);

      const filename = path.join(outputDir, `canvas-${vp.name}-${theme}.png`);
      await page.screenshot({ path: filename, fullPage: false });
      console.log(`[SUCCESS] Captured: ${filename}`);

      await context.close();
    }
  }

  await browser.close();
  console.log("[screenshot_canvas] Canvas screenshot capture completed.");
}

capture().catch((err) => {
  console.error(`[ERROR] screenshot_canvas failed: ${err.message}`);
  process.exit(1);
});
