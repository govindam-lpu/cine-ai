import { defineConfig, devices } from "@playwright/test";

// e2e harness for the full upload → profile → recs journey (specs land in Phase 6).
// Config present in Phase 0 per the DoD; no specs yet.
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  reporter: "list",
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL ?? "http://127.0.0.1:3000",
    trace: "on-first-retry",
  },
  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"] } },
  ],
});
