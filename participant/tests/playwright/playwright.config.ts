import { defineConfig } from "@playwright/test";

const port = Number(process.env.PORT ?? 4791);
if (!Number.isInteger(port) || port < 1 || port > 65535) {
  throw new Error(`PORT must be a whole number from 1 to 65535, not ${JSON.stringify(process.env.PORT)}.`);
}

export default defineConfig({
  testDir: ".",
  // Run artifacts go to the repository's ignored local-data folder, not into participant/,
  // so a hand-in never picks them up. Evidence is copied out of here on purpose.
  outputDir: "../../../local-data/playwright-results",
  retries: 0,
  reporter: [["list"]],
  use: {
    baseURL: `http://127.0.0.1:${port}`,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  webServer: {
    command: "node serve-fixture.mjs",
    url: `http://127.0.0.1:${port}/passport/`,
    reuseExistingServer: false,
    timeout: 120_000,
  },
});
