import { defineConfig } from "@playwright/test";
import base from "./playwright.config.ts";

// Evidence on failure (the failure-evidence quest). Run it with:
//   npx playwright test --config evidence.config.ts
// It is the normal configuration (playwright.config.ts: the local demo app, the run marker and
// cleanup, the browser kept on this computer) with only what is kept, where and for how long changed.
// It runs the tests in evidence-tests/, which use the recorder in support/evidence-fixture.ts. They are
// named *.evidence.ts, not *.spec.ts, because the normal configuration runs every *.spec.ts in any
// folder; this way it never picks them up.
//
// WHAT IS KEPT
//   A failing test, in test-results/<test's folder>/:
//     trace.zip            every step, with a snapshot of the page, its network and console (open it
//                          with: npx playwright show-trace <path>)
//     test-failed-1.png    the page at the moment it failed
//     console.txt          the page's console messages and uncaught errors   (the recorder)
//     failed-requests.txt  answers of 400 or more, and requests with no answer (the recorder)
//     error.txt            the error message, the test's name and file      (the recorder)
//     error-context.md     Playwright's own note of the page's contents when it failed
//   A passing test: nothing. Its folder is removed (preserveOutput "failures-only"), no trace and no
//   screenshot are kept, and the recorder drops its notes.
//   Never: a video (decided against: the trace's snapshots are enough, and a video means more frames
//   to check for personal data), and never the HTML report, which would keep a second copy of every
//   trace and screenshot in playwright-report/.
//
// HOW LONG
//   Until the next run. Playwright empties test-results/ at the start of every run, with this
//   configuration or the normal one, so evidence lasts only until someone runs the tests again.
//   test-results/ is ignored by Git, so nothing here is committed by accident. To keep a bundle (for
//   a hand-in or a bug report), copy it out on purpose, and scan the copy first:
//     node tools/failure-evidence-check.ts <the copied folder>

export default defineConfig(base, {
  testDir: "./evidence-tests",
  testMatch: "*.evidence.ts",
  outputDir: "./test-results",
  preserveOutput: "failures-only",
  reporter: [["list"]],
  use: {
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "off",
  },
});
