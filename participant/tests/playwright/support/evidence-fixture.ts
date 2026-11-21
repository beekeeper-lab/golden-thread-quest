import { writeFileSync } from "node:fs";
import { homedir } from "node:os";
import { dirname } from "node:path";
import { test as base } from "./orders-fixture.ts";

export { expect } from "./orders-fixture.ts";

// The failure-evidence recorder (the failure-evidence quest), on top of the orders helper. For every
// test that uses it, it notes while the test runs:
//   - the page's console: every message the page's code writes (errors, warnings, logs) and every
//     error the page doesn't catch;
//   - the requests that went wrong: any answer of 400 or more (with the start of its body, if it
//     arrives within 2 seconds), and any request that got no answer at all.
// If the test passes, the notes are dropped and nothing is written. If it fails, three small text
// files go into the test's own results folder, next to Playwright's trace and screenshot:
//   console.txt, failed-requests.txt and error.txt (the error message, the test's name and its file).
//
// What is never noted: request or answer headers (they can carry cookies and the API key) and
// request bodies. Addresses are noted without their query (?…) or #… part, which can carry tokens.
// Only answers of 400 or more keep any body text, at most the first 300 characters. The tests'
// own calls to the orders service go from Node (support/global-setup.ts), not through the page, so
// they never appear here. Paths on this computer are shortened in all three files so they don't
// show the computer's user name (see plain). The bundle is still scanned before it is shared
// (tools/failure-evidence-check.ts), because this is a safety net, not a guarantee.

const BODY_LIMIT = 300;
// An error answer whose body never finishes would keep the recorder waiting; after this long, the
// line is written without the body.
const BODY_WAIT_MS = 2000;

// Seconds since the test started, so the console and the requests can be lined up with each other.
function clock(started: number): string {
  return `+${((Date.now() - started) / 1000).toFixed(2)}s`;
}

// The address without its query or fragment.
function where(url: string): string {
  try {
    const parsed = new URL(url);
    return `${parsed.origin}${parsed.pathname}`;
  } catch {
    return "(an address that couldn't be read)";
  }
}

// Playwright colours its error messages for a terminal; the saved file is plain text. Addresses on
// this computer are shortened: paths inside the tests' folder become relative to it, and any other
// path in the home folder starts with ~, so the bundle doesn't show the computer's user name.
function plain(text: string, testsFolder: string): string {
  return text
    .replace(/\x1b\[[0-9;]*m/g, "")
    .replaceAll(`${testsFolder}/`, "")
    .replaceAll(homedir(), "~");
}

export const test = base.extend<{ failureEvidence: void }>({
  failureEvidence: [
    async ({ page }, use, testInfo) => {
      const started = Date.now();
      const consoleLines: string[] = [];
      const requestLines: Promise<string>[] = [];

      page.on("console", (message) => {
        const at = message.location();
        const source = at.url ? ` (${where(at.url)}:${at.lineNumber + 1})` : "";
        consoleLines.push(`${clock(started)} [${message.type()}] ${message.text()}${source}`);
      });
      page.on("pageerror", (error) => {
        consoleLines.push(`${clock(started)} [uncaught] ${error.message}`);
      });
      page.on("response", (response) => {
        if (response.status() < 400) return;
        const line = `${clock(started)} ${response.request().method()} ${where(response.url())} -> ${response.status()} ${response.statusText()}`;
        const body = response
          .text()
          .then((text) => {
            const start = text.slice(0, BODY_LIMIT).replace(/\s+/g, " ").trim();
            return `${line}\n    body: ${start}${text.length > BODY_LIMIT ? " …(cut)" : ""}`;
          })
          .catch(() => `${line}\n    body: (couldn't be read)`);
        let timer: NodeJS.Timeout | undefined;
        const waited = new Promise<string>((done) => {
          timer = setTimeout(() => done(`${line}\n    body: (not complete after ${BODY_WAIT_MS / 1000} s)`), BODY_WAIT_MS);
        });
        requestLines.push(Promise.race([body, waited]).finally(() => clearTimeout(timer)));
      });
      page.on("requestfailed", (request) => {
        requestLines.push(
          Promise.resolve(`${clock(started)} ${request.method()} ${where(request.url())} -> no answer: ${request.failure()?.errorText ?? "unknown"}`),
        );
      });

      await use();

      // A pass (or an expected failure) keeps nothing.
      if (testInfo.status === testInfo.expectedStatus) return;

      const requests = await Promise.all(requestLines);
      const testsFolder = dirname(testInfo.config.configFile ?? testInfo.project.testDir);
      writeFileSync(
        testInfo.outputPath("console.txt"),
        consoleLines.length > 0 ? `${plain(consoleLines.join("\n"), testsFolder)}\n` : "(the page wrote nothing to the console)\n",
      );
      writeFileSync(
        testInfo.outputPath("failed-requests.txt"),
        requests.length > 0 ? `${plain(requests.join("\n"), testsFolder)}\n` : "(no request came back with 400 or more, and none went unanswered)\n",
      );
      const errors = testInfo.errors.map((error) => plain(error.stack ?? error.message ?? error.value ?? "(no message)", testsFolder));
      writeFileSync(
        testInfo.outputPath("error.txt"),
        [
          `Test: ${testInfo.titlePath.slice(1).join(" > ")}`,
          `File: ${testInfo.titlePath[0]}`,
          `Result: ${testInfo.status} (expected ${testInfo.expectedStatus}) after ${(testInfo.duration / 1000).toFixed(1)}s`,
          "",
          ...errors,
          "",
        ].join("\n"),
      );
    },
    { auto: true },
  ],
});
