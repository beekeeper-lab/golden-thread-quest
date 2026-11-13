// Runs Playwright tests one at a time in a chosen order, for the data-isolation quest: forward (as
// written), reversed, or random. Playwright itself always runs a file's tests top to bottom, so
// this asks Playwright for the list of tests, puts them in the chosen order, and runs each one on
// its own in that order. A test that only passes after another one has run is caught out.
//
// For a random order it prints the seed (the number the shuffle came from); giving the same seed
// again repeats exactly the same order, so a failure seen in a random order can be reproduced.
//
// The whole ordered run behaves like one normal run: one copy of the demo app, one run marker for
// every test, and the run-end safety net (support/global-teardown.ts) once, after the last test,
// not after each one. The copy of the app is started here on TIXLY_DEMO_PORT (default 4173); if
// something is already using that port, the tool stops rather than borrow it. To use an app that is
// already running, say so with TIXLY_BASE_URL.
//
// A test counts as PASSED only if Playwright recorded it as passed AND its run finished cleanly; a
// skipped test is shown as SKIPPED and not counted as a pass. Each test keeps its own results
// folder (test-results/ordered/<number>), so one test's run can't wipe another's failure
// screenshot or trace. If the run is interrupted (Ctrl+C, or the terminal closing), the test that
// is running finishes, no more start, and the safety net still runs before the app is stopped. If
// the output can't be written any more (piped into a "head" that has closed), the remaining tests
// still run and the safety net still runs; only the printing stops. Only a hard kill (or a power
// cut) can skip the safety net, and then the data-isolation check still reports the leftover.
//
// Run it from participant/tests/playwright:
//   node tools/run-in-order.ts forward isolated.spec.ts
//   node tools/run-in-order.ts reversed coupled.spec.ts
//   node tools/run-in-order.ts random isolated.spec.ts            (a new seed each time)
//   node tools/run-in-order.ts random isolated.spec.ts --seed 1234 (the same order as before)
// It exits with 0 only if every test ran and passed.

import { spawn, spawnSync, type ChildProcess } from "node:child_process";
import { randomBytes } from "node:crypto";
import { existsSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

type Order = "forward" | "reversed" | "random";
type Listed = { file: string; line: number; title: string };

const usage = "Usage: node tools/run-in-order.ts forward|reversed|random <test files...> [--seed <whole number>]";
const args = process.argv.slice(2);
const order = args.shift() as Order;
let seed: number | undefined;
const files: string[] = [];
for (let i = 0; i < args.length; i++) {
  if (args[i] === "--seed") {
    const value = args[++i] ?? "";
    if (!/^[0-9]{1,9}$/.test(value)) {
      console.error(`${usage}\nThe seed must be a whole number of up to 9 digits.`);
      process.exit(2);
    }
    seed = Number(value);
  } else {
    files.push(args[i]);
  }
}
if (!["forward", "reversed", "random"].includes(order) || files.length === 0) {
  console.error(usage);
  process.exit(2);
}
if (seed !== undefined && order !== "random") {
  console.error(`${usage}\nA seed only applies to a random order.`);
  process.exit(2);
}

// The tests in the files, as Playwright lists them, in the order they are written.
function listTests(): Listed[] {
  // Report-location settings left in the shell would send the listing to a file instead of stdout
  // (and could overwrite a report there), so they are cleared for this one command.
  const env = { ...process.env };
  delete env.PLAYWRIGHT_JSON_OUTPUT_FILE;
  delete env.PLAYWRIGHT_JSON_OUTPUT_DIR;
  delete env.PLAYWRIGHT_JSON_OUTPUT_NAME;
  const listed = spawnSync("npx", ["playwright", "test", ...files, "--list", "--reporter=json"], {
    encoding: "utf8",
    env,
  });
    if (listed.error || listed.status !== 0) {
    const why = listed.error ? `couldn't start npx: ${listed.error.message}` : `${listed.stdout ?? ""}${listed.stderr ?? ""}`;
    console.error(`Couldn't list the tests:\n${why}`);
    process.exit(2);
  }
  const found: Listed[] = [];
  const walk = (suite: { specs?: { file: string; line: number; title: string }[]; suites?: unknown[] }) => {
    for (const spec of suite.specs ?? []) found.push({ file: spec.file, line: spec.line, title: spec.title });
    for (const child of (suite.suites ?? []) as (typeof suite)[]) walk(child);
  };
  for (const suite of JSON.parse(listed.stdout).suites ?? []) walk(suite);
  // Each test is run by its file and line, so two tests declared on the same line (in a loop) can't
  // be told apart: refuse rather than run both at once.
  const seen = new Set<string>();
  for (const test of found) {
    const where = `${test.file}:${test.line}`;
    if (seen.has(where)) {
      console.error(`More than one test is declared at ${where}, so they can't be run one at a time in order.`);
      process.exit(2);
    }
    seen.add(where);
  }
  return found.sort((a, b) => a.file.localeCompare(b.file) || a.line - b.line);
}

// A small, repeatable shuffle: the same seed always gives the same order.
function shuffled<T>(items: T[], startSeed: number): T[] {
  let state = startSeed >>> 0;
  const next = () => {
    state = (state + 0x6d2b79f5) >>> 0;
    let t = state;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
  const copy = [...items];
  for (let i = copy.length - 1; i > 0; i--) {
    const j = Math.floor(next() * (i + 1));
    [copy[i], copy[j]] = [copy[j], copy[i]];
  }
  return copy;
}

// Whether something answers at an address within 2 seconds (the answer is read to the end, so no
// connection is left idle for a later request, and the time limit covers the whole answer, so a
// stuck app can't hold up startup or an interruption). Redirects are not followed.
async function answers(address: string): Promise<boolean> {
  try {
    await (await fetch(address, { redirect: "manual", signal: AbortSignal.timeout(2000) })).arrayBuffer();
    return true;
  } catch {
    return false;
  }
}

// The result Playwright recorded for the one test in a run: passed, failed, timedOut or skipped.
function resultOf(reportFile: string): string {
  try {
    const statuses: string[] = [];
    const walk = (suite: { specs?: { tests?: { results?: { status: string }[] }[] }[]; suites?: unknown[] }) => {
      for (const spec of suite.specs ?? []) {
        for (const test of spec.tests ?? []) statuses.push(test.results?.at(-1)?.status ?? "skipped");
      }
      for (const child of (suite.suites ?? []) as (typeof suite)[]) walk(child);
    };
    for (const suite of JSON.parse(readFileSync(reportFile, "utf8")).suites ?? []) walk(suite);
    return statuses.length === 1 ? statuses[0] : "failed";
  } catch {
    return "failed";
  }
}

// Runs one test in its own Playwright run and waits for it to finish.
function runOne(test: Listed, number: number, env: NodeJS.ProcessEnv): Promise<{ code: number | null; output: string }> {
  return new Promise((resolve) => {
    const child = spawn(
      "npx",
      ["playwright", "test", `${test.file}:${test.line}`, "--workers=1", "--reporter=line,json",
       `--output=test-results/ordered/${number}`],
      // Its own process group, so Ctrl+C reaches this tool, which then lets the test finish.
      { env, detached: true },
    );
    let output = "";
    child.stdout.on("data", (chunk) => (output += chunk));
    child.stderr.on("data", (chunk) => (output += chunk));
    child.on("close", (code) => resolve({ code, output }));
    // A test run that can't even be started (no npx, out of processes) counts as a failed test, and
    // the run carries on to its cleanup.
    child.on("error", (problem) => resolve({ code: 1, output: `${output}\nCouldn't start the test: ${problem.message}` }));
  });
}

const tests = listTests();
if (tests.length === 0) {
  console.error(`No tests found in: ${files.join(", ")}`);
  process.exit(2);
}
let ordered = tests;
if (order === "reversed") ordered = [...tests].reverse();
if (order === "random") {
  seed ??= Math.floor(Math.random() * 1_000_000_000);
  ordered = shuffled(tests, seed);
}

console.log(`Order: ${order}${order === "random" ? ` (seed ${seed}; repeat with --seed ${seed})` : ""}`);
ordered.forEach((test, i) => console.log(`  ${i + 1}. ${test.title}`));
console.log("");

// Output that can no longer be written (piped into "head" or "less" that has closed) must not
// stop the run before its cleanup; the results still decide the exit code.
process.stdout.on("error", () => {});
process.stderr.on("error", () => {});

// This run's own marker, always a new one (one left in the shell is not reused): two runs sharing a
// marker could sweep each other's orders.
const marker = `qa-${randomBytes(4).toString("hex")}`;
const reportFile = join(tmpdir(), `run-in-order-${process.pid}.json`);
const counts = { passed: 0, failed: 0, skipped: 0 };
let interrupted = false;
const stopSoon = () => {
  if (!interrupted) console.log("\nInterrupted: finishing the test that is running, then cleaning up.");
  interrupted = true;
};
process.on("SIGINT", stopSoon);
process.on("SIGTERM", stopSoon);
process.on("SIGHUP", stopSoon); // the terminal was closed

let server: ChildProcess | undefined;
let base = process.env.TIXLY_BASE_URL;
let preexisting: string | undefined;
try {
  // One copy of the demo app for the whole run: our own, unless TIXLY_BASE_URL names one.
  if (base === undefined) {
    const port = process.env.TIXLY_DEMO_PORT ?? "4173";
    base = `http://127.0.0.1:${port}`;
    if (await answers(base)) {
      throw new Error(`Something is already using port ${port}. Stop it, choose another TIXLY_DEMO_PORT, or set TIXLY_BASE_URL to use that app on purpose.`);
    }
    // Its own process group too, so a Ctrl+C in the terminal doesn't stop the app before the
    // safety net has run; it is stopped explicitly at the end.
    const started = spawn("node", ["demo-app/server.js"], {
      env: { ...process.env, TIXLY_DEMO_PORT: port },
      stdio: ["ignore", "pipe", "pipe"],
      detached: true,
    });
    server = started;
    // Ready only when THIS app says it is listening (it prints "Tixly demo app on ..."), not just
    // because something answers on the port, which could be another run's app. What it prints on
    // its error output (such as a lock left by a crash, or a busy port) is kept to explain a failure.
    let startupErrors = "";
    started.stderr?.on("data", (chunk) => (startupErrors += chunk));
    const ready = await new Promise<boolean>((resolve) => {
      const timer = setTimeout(() => resolve(false), 10_000);
      started.stdout?.on("data", (chunk) => {
        if (String(chunk).includes("Tixly demo app on")) {
          clearTimeout(timer);
          resolve(true);
        }
      });
      started.on("exit", () => {
        clearTimeout(timer);
        resolve(false);
      });
      started.on("error", (problem) => {
        clearTimeout(timer);
        startupErrors += problem.message;
        resolve(false);
      });
    });
    if (!ready) throw new Error(`The demo app didn't start at ${base}.${startupErrors.trim() ? `\n${startupErrors.trim()}` : ""}`);
  }
  // The orders that exist before the first test, which the safety net must never touch.
  process.env.TIXLY_BASE_URL = base;
  const { existingOrderIds } = await import("../support/global-setup.ts");
    preexisting = JSON.stringify(await existingOrderIds());
  console.log(`Run marker: ${marker}\n`);

  for (const [i, test] of ordered.entries()) {
    if (interrupted) break;
    rmSync(reportFile, { force: true });
    // file:line runs exactly that one test, against the shared copy of the app; the safety net
    // waits until the end (TIXLY_SAFETY_NET_LATER).
    const run = await runOne(test, i + 1, {
      ...process.env,
      TIXLY_RUN_MARKER: marker,
      TIXLY_BASE_URL: base,
      TIXLY_PREEXISTING_IDS: preexisting,
      TIXLY_SAFETY_NET_LATER: "1",
      PLAYWRIGHT_JSON_OUTPUT_FILE: reportFile,
    });
    const status = existsSync(reportFile) ? resultOf(reportFile) : "failed";
    const shown = status === "passed" && run.code === 0 ? "PASSED" : status === "skipped" && run.code === 0 ? "SKIPPED" : "FAILED";
    counts[shown === "PASSED" ? "passed" : shown === "SKIPPED" ? "skipped" : "failed"]++;
    console.log(`${i + 1}. ${shown}  ${test.title}`);
    if (shown === "FAILED") {
            const lines = run.output.split("\n").filter((line) => line.trim() !== "");
      const matching = lines.filter((line) => /Error:|Expected|Received|waiting for|locator\./.test(line)).slice(0, 4);
      // When nothing looks like an assertion (the test couldn't even start, say), the last few lines
      // it printed are shown instead, so a failure never comes without a reason.
      const details = (matching.length > 0 ? matching : lines.slice(-4)).map((line) => `     ${line.trim()}`);
      console.log(details.length > 0 ? details.join("\n") : "     (the test printed nothing)");
    }
  }
} catch (problem) {
  console.error(problem instanceof Error ? problem.message : problem);
  counts.failed++;
} finally {
  rmSync(reportFile, { force: true });
  try {
    // The safety net, once, after the last test (or after an interruption or error), while the
    // app is still running.
    if (base !== undefined && preexisting !== undefined) {
      process.env.TIXLY_RUN_MARKER = marker;
      process.env.TIXLY_BASE_URL = base;
      process.env.TIXLY_PREEXISTING_IDS = preexisting;
      delete process.env.TIXLY_SAFETY_NET_LATER;
      const { default: safetyNet } = await import("../support/global-teardown.ts");
      await safetyNet();
    }
  } catch (problem) {
    console.error(problem instanceof Error ? problem.message : problem);
    counts.failed++;
  } finally {
    // Stop our app and wait until it has gone (its port and lock are free), forcing it after 3 s.
    if (server && server.exitCode === null && server.signalCode === null) {
      const stopped = new Promise((resolve) => server?.once("exit", resolve));
      server.kill("SIGTERM");
      const timer = setTimeout(() => server?.kill("SIGKILL"), 3000);
      await stopped;
      clearTimeout(timer);
    }
  }
}
console.log(`\n${counts.passed} passed, ${counts.failed} failed, ${counts.skipped} skipped, in ${order} order.`);
if (counts.skipped > 0) console.log("A skipped test didn't run, so it isn't counted as passing (see its file for how to turn it on).");
const ran = counts.passed + counts.failed + counts.skipped;
if (interrupted) console.log(`The run was interrupted after ${Math.min(ran, ordered.length)} of ${ordered.length} test(s), so it doesn't count as a pass.`);
process.exit(counts.failed === 0 && counts.skipped === 0 && !interrupted ? 0 : 1);
