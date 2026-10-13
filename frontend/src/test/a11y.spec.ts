import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

test.describe("Accessibility and Core UX", () => {
  test("Canvas page should pass automated axe a11y scan without critical or serious violations", async ({
    page,
  }) => {
    await page.goto("http://127.0.0.1:5173/");
    await page.waitForLoadState("networkidle");

    const accessibilityScanResults = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
      .disableRules(["color-contrast"]) // Canvas nodes have custom graphite tokens
      .analyze();

    const criticalOrSerious = accessibilityScanResults.violations.filter(
      (v) => v.impact === "critical" || v.impact === "serious"
    );

    expect(criticalOrSerious).toEqual([]);
  });

  test("BriefDialog opens and supports keyboard closing via Escape", async ({
    page,
  }) => {
    await page.goto("http://127.0.0.1:5173/");
    await page.waitForLoadState("networkidle");

    const configureBtn = page.locator("button:has-text('Configure brief')");
    await configureBtn.click();

    const dialog = page.locator("[role='dialog']");
    await expect(dialog).toBeVisible();

    await page.keyboard.press("Escape");
    await expect(dialog).not.toBeVisible();
  });
});
