import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./src/test",
  testMatch: "**/*.spec.ts",
  timeout: 30000,
  use: {
    channel: "msedge",
    headless: true,
  },
});
