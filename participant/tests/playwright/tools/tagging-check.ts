// Checks every test's tags against the tag scheme, for the tagging quest.
//
// The vocabulary is read from the scheme page itself (participant/context/playwright/tag-scheme.md),
// so the page and the check can't disagree: each "## N. <Dimension>" section's table lists that
// dimension's tags, the "## Suite" section lists the optional suite tags, and the duration table
// gives each duration tag's limit in seconds. The tests and their tags come from Playwright itself
// (`npx playwright test --list`), so every test counts, including those normally skipped.
//
// For every test it reports, by name and file:
//   - a dimension with no tag, or with more than one;
//   - more than one suite tag;
//   - any tag that isn't in the scheme.
// Given a Playwright JSON report of a real run (--results <file>), it also compares each test's own
// duration with its duration tag's limit and names every test that ran over; a test that didn't run
// (skipped) is listed as not timed.
//
// Run it from participant/tests/playwright:
//   node tools/tagging-check.ts                          (tags only)
//   PLAYWRIGHT_JSON_OUTPUT_FILE=/tmp/run.json npx playwright test --reporter=json
//   node tools/tagging-check.ts --results /tmp/run.json  (tags and durations)
// It ends with PASS (exit 0) or FAIL (exit 1); 2 means it couldn't run.

import { spawnSync } from "node:child_process";
import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";

type Test = { id: string; title: string; file: string; line: number; tags: string[]; duration?: number; timing?: "timed" | "skipped" | "missing" };
type Suite = { specs?: { id: string; title: string; file: string; line: number; tags?: string[]; tests?: { results?: { duration?: unknown; status?: string }[] }[] }[]; suites?: Suite[] };

const args = process.argv.slice(2);
// The value after a flag, or a stop (exit 2) if it's missing or is another flag.
function valueOf(flag: string, what: string): string | undefined {
  const at = args.indexOf(flag);
  if (at === -1) return undefined;
  const value = args[at + 1];
  if (!value || value.startsWith("--")) {
    console.error(`${flag} needs ${what}.`);
    process.exit(2);
  }
  return value;
}
for (let i = 0; i < args.length; i += 2) {
  if (args[i] !== "--results" && args[i] !== "--scheme") {
    console.error(`Unknown argument "${args[i]}". Use: node tools/tagging-check.ts [--results <Playwright JSON report>] [--scheme <tag scheme page>]`);
    process.exit(2);
  }
}
const resultsFile = valueOf("--results", "the path of a Playwright JSON report");
const schemeValue = valueOf("--scheme", "the path of a tag scheme page");
const schemeFile = schemeValue === undefined ? fileURLToPath(new URL("../../../context/playwright/tag-scheme.md", import.meta.url)) : resolve(schemeValue);

// --- The vocabulary, from the scheme page. ---------------------------------------------------
if (!existsSync(schemeFile)) {
  console.error(`The tag scheme isn't at ${schemeFile}.`);
  process.exit(2);
}
const scheme = readFileSync(schemeFile, "utf8");
const dimensions = new Map<string, Set<string>>();
const suiteTags = new Set<string>();
const limits = new Map<string, number>();
const KNOWN_SECTIONS = new Set(["Feature", "Risk", "Read or write", "Layer", "Duration", "Suite"]);
let section = "";
let fence = ""; // the opening fence (``` or ~~~, possibly longer) while inside a fenced block
for (const line of scheme.split("\n")) {
  // Examples in a fenced block are never definitions. A block opens with ``` or ~~~ (or longer)
  // and closes only with a line of the same character, at least as long and with nothing after it.
  const marker = /^ {0,3}(`{3,}|~{3,})(.*)$/.exec(line);
  if (fence === "") {
    if (marker) {
      fence = marker[1];
      continue;
    }
  } else {
    if (marker && marker[1][0] === fence[0] && marker[1].length >= fence.length && marker[2].trim() === "") fence = "";
    continue;
  }
  // Every level-two heading starts a new section; only the five dimensions and the suite group
  // define tags, so rows under any other heading (examples, notes) are not part of the vocabulary.
  if (line.startsWith("## ")) {
    const heading = /^## (?:\d+\. )?([A-Za-z ]+?)(?::| \(|$)/.exec(line);
    section = heading && KNOWN_SECTIONS.has(heading[1].trim()) ? heading[1].trim() : "";
    continue;
  }
  if (!section) continue;
  // Only the first cell of a table row defines a tag (in every section, the suite group included);
  // a tag mentioned in prose, in another cell or in an example is not part of the vocabulary.
  if (!line.startsWith("| `@")) continue;
  const definition = /^\| `@([a-z0-9-]+)` \|/.exec(line);
  if (!definition) {
    console.error(`The scheme has a row that isn't a proper tag definition (its first cell must be one tag, like \`@fast\`): ${line}`);
    process.exit(2);
  }
  const tag = definition[1];
  if (section === "Suite") {
    if ([...dimensions.values()].some((known) => known.has(tag)) || suiteTags.has(tag)) {
      console.error(`The scheme lists @${tag} more than once; each tag must belong to exactly one group.`);
      process.exit(2);
    }
    suiteTags.add(tag);
  } else {
    if ([...dimensions.values()].some((known) => known.has(tag)) || suiteTags.has(tag)) {
      console.error(`The scheme lists @${tag} more than once; each tag must belong to exactly one dimension.`);
      process.exit(2);
    }
    if (!dimensions.has(section)) dimensions.set(section, new Set());
    dimensions.get(section)?.add(tag);
    const limit = /^\| `@[a-z0-9-]+` \| (\d+) seconds?/.exec(line);
    if (limit) limits.set(tag, Number(limit[1]));
  }
}
const allTags = new Map<string, string>(); // tag -> its dimension (or "Suite")
for (const [dimension, tags] of dimensions) for (const tag of tags) allTags.set(tag, dimension);
for (const tag of suiteTags) allTags.set(tag, "Suite");
const expected = ["Feature", "Risk", "Read or write", "Layer", "Duration"];
const missingDimensions = expected.filter((dimension) => !dimensions.has(dimension));
if (missingDimensions.length > 0 || dimensions.size !== expected.length) {
  console.error(`The scheme should define exactly these dimensions: ${expected.join(", ")}; found: ${[...dimensions.keys()].join(", ")}.`);
  process.exit(2);
}
const unlimited = [...(dimensions.get("Duration") ?? [])].filter((tag) => !limits.has(tag));
if (unlimited.length > 0) {
  console.error(`Every duration tag needs a limit in the scheme; none for: ${unlimited.map((t) => `@${t}`).join(", ")}.`);
  process.exit(2);
}

// --- The tests, from Playwright. ---------------------------------------------------------------
// Report-location settings left in the shell would send the listing to a file instead of stdout,
// possibly over the very report being checked, so they are cleared for this one command.
const listEnv = { ...process.env };
delete listEnv.PLAYWRIGHT_JSON_OUTPUT_FILE;
delete listEnv.PLAYWRIGHT_JSON_OUTPUT_DIR;
delete listEnv.PLAYWRIGHT_JSON_OUTPUT_NAME;
const listed = spawnSync("npx", ["playwright", "test", "--list", "--reporter=json"], { encoding: "utf8", env: listEnv });
if (listed.error || listed.status !== 0) {
  console.error(`Couldn't list the tests:\n${listed.error ? listed.error.message : `${listed.stdout ?? ""}${listed.stderr ?? ""}`}`);
  process.exit(2);
}
const collect = (suite: Suite, into: Test[]) => {
  for (const spec of suite.specs ?? []) into.push({ id: spec.id, title: spec.title, file: spec.file, line: spec.line, tags: spec.tags ?? [] });
  for (const child of suite.suites ?? []) collect(child, into);
};
const tests: Test[] = [];
for (const suite of (JSON.parse(listed.stdout).suites ?? []) as Suite[]) collect(suite, tests);
tests.sort((a, b) => a.file.localeCompare(b.file) || a.line - b.line);

// --- Durations, from a real run. --------------------------------------------------------------
if (resultsFile) {
  if (!existsSync(resultsFile)) {
    console.error(`No Playwright report at ${resultsFile}.`);
    process.exit(2);
  }
  let report: { suites?: unknown };
  try {
    report = JSON.parse(readFileSync(resultsFile, "utf8"));
  } catch {
    console.error(`${resultsFile} isn't a JSON file.`);
    process.exit(2);
  }
  if (!Array.isArray(report?.suites) || report.suites.length === 0) {
    console.error(`${resultsFile} isn't a Playwright JSON report of a run (it has no test suites).`);
    process.exit(2);
  }
  // Every attempt of every test in the report (repeats and retries alike), by the spec's own id,
  // which also tells apart two tests with the same title and line in different groups. A test's
  // time is its longest attempt that wasn't skipped.
  const longest = new Map<string, number | "skipped">();
  let results = 0;
  const malformed = (what: string) => {
    console.error(`${resultsFile} isn't a Playwright JSON report of a run (${what}).`);
    process.exit(2);
  };
  const isObject = (value: unknown) => typeof value === "object" && value !== null && !Array.isArray(value);
  const listOf = (value: unknown, what: string): unknown[] => {
    if (value === undefined) return [];
    if (!Array.isArray(value)) malformed(`${what} isn't a list`);
    return value as unknown[];
  };
  const walk = (suite: Suite) => {
    if (!isObject(suite)) malformed("a suite isn't an object");
    for (const spec of listOf(suite.specs, "a suite's specs") as NonNullable<Suite["specs"]>) {
      if (!isObject(spec) || typeof spec.id !== "string") malformed("a spec has no id");
      for (const run of listOf(spec.tests, "a spec's tests") as NonNullable<NonNullable<Suite["specs"]>[number]["tests"]>) {
        if (!isObject(run)) malformed("a test isn't an object");
        for (const result of listOf(run.results, "a test's results") as { duration?: unknown; status?: string }[]) {
          if (!isObject(result)) malformed("a result isn't an object");
          if (!["passed", "failed", "timedOut", "skipped", "interrupted"].includes(String(result.status))) {
            malformed(`a result for "${spec.title}" has no Playwright status (${JSON.stringify(result.status)})`);
          }
          results += 1;
          if (result.status === "skipped") {
            if (!longest.has(spec.id)) longest.set(spec.id, "skipped");
            continue;
          }
          const duration = result.duration;
          if (typeof duration !== "number" || !Number.isFinite(duration) || duration < 0) {
            console.error(`${resultsFile} has a result for "${spec.title}" without a proper duration (${JSON.stringify(duration)}).`);
            process.exit(2);
          }
          const known = longest.get(spec.id);
          longest.set(spec.id, typeof known === "number" ? Math.max(known, duration) : duration);
        }
      }
    }
    for (const child of listOf(suite.suites, "a suite's suites") as Suite[]) walk(child);
  };
  for (const suite of report.suites as Suite[]) walk(suite);
  if (results === 0) malformed("it holds no test results");
  for (const test of tests) {
    const found = longest.get(test.id);
    if (found === undefined) test.timing = "missing";
    else if (found === "skipped") test.timing = "skipped";
    else Object.assign(test, { timing: "timed", duration: found });
  }
}

// --- The checks. -------------------------------------------------------------------------------
let problems = 0;
const timed: string[] = [];
console.log(`Scheme: ${[...dimensions].map(([d, t]) => `${d} (${[...t].map((x) => `@${x}`).join(" ")})`).join("; ")}; suite (optional): ${[...suiteTags].map((x) => `@${x}`).join(" ")}.`);
console.log(`Duration limits: ${[...limits].map(([t, s]) => `@${t} ${s} s`).join(", ")}.`);
console.log(`Tests found: ${tests.length}.\n`);
for (const test of tests) {
  const where = `${test.file}:${test.line} "${test.title}"`;
  const issues: string[] = [];
  for (const tag of test.tags) if (!allTags.has(tag)) issues.push(`unknown tag @${tag} (not in the scheme)`);
  for (const dimension of expected) {
    const found = test.tags.filter((tag) => allTags.get(tag) === dimension);
    if (found.length === 0) issues.push(`no ${dimension.toLowerCase()} tag`);
    if (found.length > 1) issues.push(`more than one ${dimension.toLowerCase()} tag (${found.map((t) => `@${t}`).join(", ")})`);
  }
  const suites = test.tags.filter((tag) => allTags.get(tag) === "Suite");
  if (suites.length > 1) issues.push(`more than one suite tag (${suites.map((t) => `@${t}`).join(", ")})`);
  const durationTag = test.tags.find((tag) => allTags.get(tag) === "Duration");
  if (resultsFile && durationTag) {
    const limit = limits.get(durationTag) ?? 0;
    if (test.timing === "skipped") {
      timed.push(`  skipped in that run, so not timed: ${where}`);
    } else if (test.timing !== "timed" || test.duration === undefined) {
      timed.push(`  not in that report, so not timed: ${where}`);
    } else if (test.duration > limit * 1000) {
      issues.push(`took ${(test.duration / 1000).toFixed(2)} s, over the ${limit} s limit of @${durationTag}`);
    } else {
      timed.push(`  ${(test.duration / 1000).toFixed(2)} s within @${durationTag} (${limit} s): ${where}`);
    }
  }
  if (issues.length > 0) {
    problems += issues.length;
    console.log(`PROBLEM ${where}`);
    for (const issue of issues) console.log(`  - ${issue}`);
  } else {
    console.log(`ok      ${where}  ${test.tags.map((t) => `@${t}`).join(" ")}`);
  }
}
if (resultsFile) {
  console.log(`\nDurations (from ${resultsFile.split("/").pop()}):`);
  for (const line of timed) console.log(line);
}
const count = (kind: Test["timing"]) => tests.filter((test) => test.timing === kind).length;
const coverage = resultsFile
  ? `, and none of the ${count("timed")} timed tests ran over its duration limit (${count("skipped")} skipped and ${count("missing")} not in the report, so not timed)`
  : "";
console.log(problems === 0 ? `\nPASS: all ${tests.length} tests carry one tag from each dimension and only tags from the scheme${coverage}.`
  : `\nFAIL: ${problems} problem(s) in the tests above.`);
process.exit(problems === 0 ? 0 : 1);
