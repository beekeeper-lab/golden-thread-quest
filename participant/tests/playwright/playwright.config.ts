import { defineConfig, devices } from "@playwright/test";

// Where the tests point comes from the environment, never from a test. Left unset, it is the
// local demo app this project starts for itself. TIXLY_BASE_URL may point at another copy of the
// app, but only on this computer: the tests must never reach a public or production site.
// The demo app's port must be a whole number from 1 to 65535: an empty value or 0 would start the
// app on a random port that Playwright then waits for in vain, so those stop the run at once.
const portSetting = process.env.TIXLY_DEMO_PORT ?? "4173";
if (!/^[1-9][0-9]{0,4}$/.test(portSetting) || Number(portSetting) > 65535) {
  throw new Error(`TIXLY_DEMO_PORT must be a whole number from 1 to 65535, not "${portSetting}"`);
}
const port = Number(portSetting);
const baseURL = process.env.TIXLY_BASE_URL ?? `http://127.0.0.1:${port}`;
const host = new URL(baseURL).hostname;
if (!["127.0.0.1", "localhost", "[::1]"].includes(host)) {
  throw new Error(`TIXLY_BASE_URL must point at this computer (127.0.0.1 or localhost), not ${host}`);
}

export default defineConfig({
  // Tests live in tests/ and, for the first-independent-test quest, at this folder's top level
  // (first-independent-test.spec.ts). Playwright never looks inside node_modules.
  testDir: ".",
  testMatch: ["tests/**/*.spec.ts", "*.spec.ts"],
  // Everything a run produces goes here or into playwright-report; both are ignored by Git.
  outputDir: "./test-results",
  forbidOnly: Boolean(process.env.CI),
  // No retries: a test that only passes on a second try is reported as failing, so a flaky test
  // is noticed instead of hidden.
  retries: 0,
  reporter: [["list"], ["html", { outputFolder: "playwright-report", open: "never" }]],
  use: {
    baseURL,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    // Keep the browser on this computer. Checking the starting address isn't enough: a local app
    // could redirect the browser, or load a script or image, from a public site. Every request
    // except to this computer is sent to a proxy that doesn't exist (port 9 on this computer), so
    // it fails instead of reaching the internet; Chromium sends requests to this computer directly.
    // "<-loopback>" turns off Chromium's own list of addresses that skip a proxy, which also covers
    // link-local addresses (169.254.x.x and fe80::), such as the address a cloud machine answers
    // credential requests on; only the three addresses named here skip it.
    proxy: { server: "http://127.0.0.1:9", bypass: "<-loopback>,localhost,127.0.0.1,[::1]" },
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  // Start the local demo app for the run, unless TIXLY_BASE_URL points at a copy already running.
  ...(process.env.TIXLY_BASE_URL
    ? {}
    : {
        webServer: {
          command: "node demo-app/server.js",
          url: baseURL,
          reuseExistingServer: false,
          env: { TIXLY_DEMO_PORT: String(port) },
        },
      }),
});
