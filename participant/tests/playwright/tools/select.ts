// Runs one named tag selection, for the multi-tag-run quest, and only after checking it.
//
// The selections live in participant/context/playwright/selections.md: each "## <name>" section
// gives an expression, a purpose and the exact tests expected. For the selection named, this:
//   1. prints its name, purpose and expression, and the exact Playwright command it becomes;
//   2. lists the tests Playwright would choose, without running anything;
//   3. compares that list with the expected tests, and stops (exit 1) if they differ;
//   4. stops (exit 1) if the selection matches no test at all, even when none is expected: an empty
//      selection is never a pass;
//   5. only then runs exactly those tests, and checks that what ran is what was listed.
//
// Expressions use whole tags joined by plain words, in one of these forms:
//   @a                          a single tag
//   @a and @b [and ...]         every named tag (an intersection)
//   @a or @b [or ...]           any of the named tags (a union)
//   not @a [and not @b ...]     none of the named tags (an exclusion)
//   @a [and @b ...] and not @c  every one of some tags and none of others
// Each tag must be in the tag scheme (participant/context/playwright/tag-scheme.md), and matches
// only as a whole tag: "@risk" never matches "@risk-high", and a word in a test's title isn't a tag.
//
// Run it from participant/tests/playwright:
//   node tools/select.ts <name>              list, check, then run
//   node tools/select.ts <name> --list-only  list and check, but don't run
// Exit 0 when the check (and the run) passed, 1 when they didn't, 2 when it couldn't start.

import { spawnSync } from "node:child_process";
import { existsSync, mkdtempSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

type Spec = { id: string; title: string; file: string; tests?: { results?: { status?: string }[] }[] };
type Suite = { specs?: Spec[]; suites?: Suite[] };

const usage = "Usage: node tools/select.ts <selection name> [--list-only]";
const args = process.argv.slice(2);
const listOnly = args.includes("--list-only");
const rest = args.filter((arg) => arg !== "--list-only");
if (rest.length !== 1 || rest[0].startsWith("--")) {
  console.error(usage);
  process.exit(2);
}
const name = rest[0];
const here = (path: string) => fileURLToPath(new URL(path, import.meta.url));
const selectionsFile = here("../../../context/playwright/selections.md");
const schemeFile = here("../../../context/playwright/tag-scheme.md");
for (const file of [selectionsFile, schemeFile]) {
  if (!existsSync(file)) {
    console.error(`${file} is missing.`);
    process.exit(2);
  }
}

// --- The selection, from the table. --------------------------------------------------------------
const page = readFileSync(selectionsFile, "utf8").split("\n");
const start = page.indexOf(`## ${name}`);
if (start === -1) {
  const names = page.filter((line) => line.startsWith("## ")).map((line) => line.slice(3));
  console.error(`No selection named "${name}". The selections are: ${names.join(", ")}.`);
  process.exit(2);
}
const end = page.findIndex((line, i) => i > start && line.startsWith("## "));
const section = page.slice(start + 1, end === -1 ? undefined : end);
const field = (label: string) => section.find((line) => line.startsWith(`- **${label}:**`))?.slice(`- **${label}:**`.length).trim();
const expression = field("Expression")?.replace(/^`|`$/g, "");
const purpose = field("Purpose");
const listStart = section.findIndex((line) => line.startsWith("- **Expected tests"));
if (!expression || !purpose || listStart === -1) {
  console.error(`The "${name}" section needs an Expression, a Purpose and an Expected tests list.`);
  process.exit(2);
}
// Every "  - " item after the heading, blank lines between items included; the list ends at the
// first line that is neither an item nor blank.
const expected: string[] = [];
for (const line of section.slice(listStart + 1)) {
  if (line.trim() === "") continue;
  if (!line.startsWith("  - ")) break;
  if (line.trim() !== "- none") expected.push(line.slice(4).trim());
}
const writtenTwice = expected.filter((test, n) => expected.indexOf(test) !== n);
if (writtenTwice.length > 0) {
  console.error(`The "${name}" section lists a test more than once: ${[...new Set(writtenTwice)].join("; ")}.`);
  process.exit(2);
}

// --- The expression, into Playwright's --grep and --grep-invert. ------------------------------------
// The scheme's tags, read the same way as tools/tagging-check.ts reads them: the first cell of a
// table row under one of the six tag headings, never inside a fenced example block.
const known = new Set<string>();
{
  const sections = new Set(["Feature", "Risk", "Read or write", "Layer", "Duration", "Suite"]);
  let section = "";
  let fence = "";
  for (const line of readFileSync(schemeFile, "utf8").split("\n")) {
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
    if (line.startsWith("## ")) {
      const heading = /^## (?:\d+\. )?([A-Za-z ]+?)(?::| \(|$)/.exec(line);
      section = heading && sections.has(heading[1].trim()) ? heading[1].trim() : "";
      continue;
    }
    const definition = section ? /^\| `@([a-z0-9-]+)` \|/.exec(line) : null;
    if (definition) known.add(definition[1]);
  }
}
const words = expression.split(/\s+/).filter(Boolean);
const include: string[] = [];
const exclude: string[] = [];
let joiner: "and" | "or" | "" = "";
let i = 0;
const fail = (why: string): never => {
  console.error(`Can't read the expression "${expression}": ${why}.`);
  process.exit(2);
};
const tag = (word: string | undefined) => {
  if (!word || !/^@[a-z0-9-]+$/.test(word)) fail(`expected a tag such as @fast, found "${word ?? "nothing"}"`);
  if (!known.has(word!.slice(1))) fail(`${word} isn't a tag in the scheme`);
  return word!.slice(1);
};
while (i < words.length) {
  if (i > 0) {
    const word = words[i++];
    if (word !== "and" && word !== "or") fail(`expected "and" or "or", found "${word}"`);
    if (joiner && joiner !== word) fail('"and" and "or" can\'t be mixed');
    joiner = word as "and" | "or";
  }
  if (words[i] === "not") {
    if (joiner === "or") fail('"not" can only be joined with "and"');
    i++;
    exclude.push(tag(words[i++]));
  } else {
    if (exclude.length > 0) fail('tags to exclude come last ("@a and not @b")');
    include.push(tag(words[i++]));
  }
}
if (include.length + exclude.length === 0) fail("it's empty");
// A tag only as a whole tag: Playwright's --grep sees the file, the titles and the tags separated by
// spaces, so a tag must have a space (or the start or end) on both sides. "@fast" doesn't match
// "@fast-lane", "@fast.extra", "@fast:nightly" or "x@fast".
const whole = (t: string) => `(?<!\\S)@${t}(?!\\S)`;
const grep =
  include.length === 0 ? undefined
  : include.length === 1 ? whole(include[0])
  : joiner === "or" ? include.map(whole).join("|")
  : `^${include.map((t) => `(?=[\\s\\S]*${whole(t)})`).join("")}`; // [\s\S]* also crosses a line break
const grepInvert = exclude.length === 0 ? undefined : exclude.map(whole).join("|");
const selectArgs = [...(grep ? ["--grep", grep] : []), ...(grepInvert ? ["--grep-invert", grepInvert] : [])];
const shown = `npx playwright test ${selectArgs.map((arg) => (arg.startsWith("--") ? arg : `'${arg}'`)).join(" ")}`;

console.log(`Selection: ${name}`);
console.log(`Purpose:   ${purpose}`);
console.log(`Expression: ${expression}`);
console.log(`Command:   ${shown}\n`);

// --- 1. List, without running. ---------------------------------------------------------------------
// Report-location settings left in the shell would send the JSON elsewhere, so they are cleared.
const env = { ...process.env };
delete env.PLAYWRIGHT_JSON_OUTPUT_FILE;
delete env.PLAYWRIGHT_JSON_OUTPUT_DIR;
delete env.PLAYWRIGHT_JSON_OUTPUT_NAME;
const collect = (suite: Suite, into: Spec[]) => {
  for (const spec of suite.specs ?? []) into.push(spec);
  for (const child of suite.suites ?? []) collect(child, into);
  return into;
};
const specsOf = (json: string): Spec[] => {
  try {
    return ((JSON.parse(json).suites ?? []) as Suite[]).flatMap((suite) => collect(suite, []));
  } catch {
    console.error(`Playwright's answer wasn't a JSON report:\n${json.slice(0, 500)}`);
    process.exit(2);
  }
};
const list = (extra: string[]) => {
  const answer = spawnSync("npx", ["playwright", "test", "--list", "--reporter=json", ...extra], { encoding: "utf8", env });
  if (answer.error || answer.stdout === "") {
    console.error(`Couldn't list the tests: ${answer.error ? answer.error.message : answer.stderr}`);
    process.exit(2);
  }
  return answer;
};

// A word starting with "@" in a test's title, a group's title or a test file's path is a tag to
// Playwright's --grep too (it matches against all three), so it could pull a test into a selection it
// doesn't belong to. The tag scheme forbids it in titles; this enforces it, and for file paths, on
// every test, before any selection is made.
const everything = list([]);
const titled: string[] = [];
const walkTitles = (suite: Suite & { title?: string }, depth: number) => {
  if (depth > 0 && suite.title?.includes("@")) titled.push(`group "${suite.title}"`);
  for (const spec of suite.specs ?? []) {
    if (spec.file.includes("@")) titled.push(`file ${spec.file}`);
    if (spec.title.includes("@")) titled.push(`${spec.file} › ${spec.title}`);
  }
  for (const child of (suite.suites ?? []) as (Suite & { title?: string })[]) walkTitles(child, depth + 1);
};
try {
  for (const suite of (JSON.parse(everything.stdout).suites ?? []) as Suite[]) walkTitles(suite, 0);
} catch {
  console.error("Couldn't read Playwright's list of all tests.");
  process.exit(2);
}
if (titled.length > 0) {
  console.error(`These titles or file paths contain "@", which Playwright would read as a tag, so no selection is made until they are renamed:\n  ${[...new Set(titled)].join("\n  ")}`);
  process.exit(2);
}

const listing = list(selectArgs);
// Playwright reports an empty selection as the error "No tests found"; any other error (a broken
// configuration, a test file that doesn't load) means the tests couldn't be listed at all, which is
// not the same as a selection that matched nothing.
const listingErrors = (() => {
  try {
    return ((JSON.parse(listing.stdout).errors ?? []) as { message?: string }[]).map((error) => error.message ?? "");
  } catch {
    return [];
  }
})().filter((message) => !/^Error: No tests found/.test(message.trim()));
if (listingErrors.length > 0) {
  console.error(`Playwright couldn't list the tests:\n${listingErrors.join("\n")}`);
  process.exit(2);
}
const listed = specsOf(listing.stdout).map((spec) => `${spec.file} › ${spec.title}`);
// A listing that failed is only an empty selection when Playwright said "No tests found" and listed
// nothing; a failed process with tests in its list, or one that listed nothing without saying why, is
// never trusted.
const saidNoTests = (() => {
  try {
    return ((JSON.parse(listing.stdout).errors ?? []) as { message?: string }[]).some((error) => /^Error: No tests found/.test((error.message ?? "").trim()));
  } catch {
    return false;
  }
})();
if (listing.status !== 0 && listed.length === 0 && !saidNoTests) {
  console.error(`Playwright's listing failed (exit ${listing.status}) without saying it found no tests:\n${listing.stderr}`);
  process.exit(2);
}
if (listing.status !== 0 && listed.length > 0) {
  console.error(`Playwright's listing ended with an error (exit ${listing.status}), so it isn't trusted:\n${listing.stderr}`);
  process.exit(2);
}
console.log(`Listed (${listed.length}), without running:`);
for (const test of listed) console.log(`  ${test}`);

// --- 2. Check against the table. ------------------------------------------------------------------
if (listed.length === 0) {
  console.log(`\nERROR: selection "${name}" matched no tests, so nothing was run. An empty selection is never a pass.`);
  process.exit(1);
}
const missing = expected.filter((test) => !listed.includes(test));
const countsDiffer = expected.length !== listed.length;
const extra = listed.filter((test) => !expected.includes(test));
const doubled = listed.filter((test, n) => listed.indexOf(test) !== n);
if (missing.length + extra.length + doubled.length > 0 || countsDiffer) {
  console.log(`\nMISMATCH: the listing doesn't match the ${expected.length} expected tests in selections.md, so nothing was run.`);
  for (const test of missing) console.log(`  expected but not listed: ${test}`);
  for (const test of extra) console.log(`  listed but not expected: ${test}`);
  for (const test of [...new Set(doubled)]) console.log(`  listed more than once: ${test}`);
  process.exit(1);
}
console.log(`\nThe listing matches the ${expected.length} expected tests.`);
if (listOnly) process.exit(0);

// --- 3. Run exactly those, and check that what ran is what was listed. ----------------------------
const folder = mkdtempSync(join(tmpdir(), "tixly-select-"));
const report = join(folder, "run.json");
console.log("Running them now:\n");
const run = spawnSync("npx", ["playwright", "test", "--reporter=list,json", ...selectArgs], {
  stdio: ["ignore", "inherit", "inherit"],
  env: { ...env, PLAYWRIGHT_JSON_OUTPUT_FILE: report },
});
if (run.error) {
  rmSync(folder, { recursive: true, force: true });
  console.error(`Couldn't start the run: ${run.error.message}`);
  process.exit(2);
}
const ranSpecs = existsSync(report) ? specsOf(readFileSync(report, "utf8")) : [];
rmSync(folder, { recursive: true, force: true });
// Each listed test's outcome: passed, failed, skipped, or not run at all (no result, as when the run's
// setup fails before any test starts).
const counts = { passed: 0, failed: 0, skipped: 0, "not run": 0 };
const outcome = new Map<string, keyof typeof counts>();
const ranTwice: string[] = [];
for (const spec of ranSpecs) {
  const status = spec.tests?.[0]?.results?.at(-1)?.status;
  if (outcome.has(`${spec.file} › ${spec.title}`)) ranTwice.push(`${spec.file} › ${spec.title}`);
  outcome.set(`${spec.file} › ${spec.title}`,
    status === undefined ? "not run" : status === "passed" ? "passed" : status === "skipped" ? "skipped" : "failed");
}
for (const test of listed) counts[outcome.get(test) ?? "not run"]++;
const unexpected = [...outcome.keys()].filter((test) => !listed.includes(test));
console.log(`\nSelection "${name}": ${listed.length} listed: ${counts.passed} passed, ${counts.failed} failed, ${counts.skipped} skipped, ${counts["not run"]} not run.`);
if (unexpected.length > 0) console.log(`WARNING: tests that weren't listed appeared in the run:\n  ${unexpected.join("\n  ")}`);
if (ranTwice.length > 0) console.log(`WARNING: the run had more than one test named:\n  ${[...new Set(ranTwice)].join("\n  ")}`);
const accounted = counts["not run"] === 0 && unexpected.length === 0 && ranTwice.length === 0;
console.log(accounted ? "Every listed test is accounted for (it ran or was skipped), and nothing else ran."
  : "WARNING: not every listed test ran or was skipped as listed.");
process.exit(run.status === 0 && accounted ? 0 : 1);
