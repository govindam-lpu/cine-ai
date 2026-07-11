import { defineConfig, devices } from "@playwright/test";
import path from "node:path";

// Full-journey e2e against a seeded, offline backend: the seed builds ./e2e.db with a ready "demo"
// profile + candidate films; CINEREX_E2E=1 forces TMDB offline so recs come from the seeded cache
// (deterministic, no network) and reasons render as real template prose (no LLM needed).
const PY = path.resolve(
  __dirname,
  process.platform === "win32" ? "../.venv/Scripts/python.exe" : "../.venv/bin/python",
);

export default defineConfig({
  testDir: "./e2e",
  timeout: 90_000,
  expect: { timeout: 30_000 },
  fullyParallel: false,
  workers: 1,
  reporter: "list",
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL ?? "http://127.0.0.1:3100",
    trace: "on-first-retry",
    permissions: ["clipboard-read", "clipboard-write"],
  },
  webServer: [
    {
      command: `${PY} scripts/seed_e2e.py && ${PY} -m uvicorn main:app --host 127.0.0.1 --port 8100`,
      cwd: "../backend",
      port: 8100,
      timeout: 180_000,
      reuseExistingServer: false,
      env: {
        PYTHONPATH: ".",
        DATABASE_URL: "sqlite:///./e2e.db",
        E2E_MODE: "1",
        WRITER_BACKEND: "ollama",
        CORS_ORIGINS: "http://127.0.0.1:3100,http://localhost:3100",
      },
    },
    {
      command: "npm run dev -- --port 3100 --hostname 127.0.0.1",
      port: 3100,
      timeout: 120_000,
      reuseExistingServer: false,
      env: { NEXT_PUBLIC_API_URL: "http://127.0.0.1:8100" },
    },
  ],
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
