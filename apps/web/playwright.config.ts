import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "../../tests/e2e",
  timeout: 60000,
  expect: { timeout: 15000 },
  workers: 1,
  use: {
    baseURL: "http://127.0.0.1:5177",
    viewport: { width: 1600, height: 1100 },
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  reporter: [["list"], ["html", { open: "never" }]],
  webServer: [
    {
      command:
        "python -m uvicorn apps.api.main:app --host 127.0.0.1 --port 8077",
      cwd: "../..",
      url: "http://127.0.0.1:8077/ready",
      timeout: 240000,
      reuseExistingServer: !process.env.CI,
      env: {
        DEMO_SEED: "true",
        WEEKLY_JOBS: "false",
        CONSIGNAI_DB: "var/e2e.db",
      },
    },
    {
      command: "pnpm run dev",
      url: "http://127.0.0.1:5177",
      reuseExistingServer: !process.env.CI,
    },
  ],
});
