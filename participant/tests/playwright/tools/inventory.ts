// Generates the test inventory, for the test-inventory quest: one row per test with its identifier,
// purpose, tags, source requirement, value score, file and line, and how it runs. The inventory is
// never edited by hand; run this again after any change to the tests.
//
// WHERE THE FACTS COME FROM. Each test carries them itself, in Playwright annotations next to its
// tags, so they are changed together with the test:
//   { type: "id", description: "T-07" }               a unique identifier, T- and a number
//   { type: "purpose", description: "…" }             what the test proves (not how it is written)
//   { type: "source", description: "CHK-07" }         the requirement it serves, from
//                                                     participant/context/playwright/requirements.md,
//     or { type: "source", description: "none: …" }   a known gap: no requirement covers it, and why
//   { type: "value", description: "low: …" }          optional: a different value score, with a reason
// The tests are read through Playwright's own listing (`playwright test --list`, the project's own
// installed copy run by Node, never through npx, which could download another), for the main
// settings (playwright.config.ts) and the failure-evidence settings (evidence.config.ts). Listing
// loads the test files to learn their titles, tags and annotations; it runs no test, starts no
// browser and changes nothing. The test files are also read as text for one thing only: a whole file
// skipped unless a setting is switched on (a top-level `test.skip(process.env.NAME !== "1", …)`).
//
// THE VALUE SCORE (high, medium, low). Worked out from two things already written down: the test's
// risk tag (@risk-high, @risk-medium, @risk-low, from tag-scheme.md) and the importance of its source
// requirement (High, Medium, Low, from requirements.md; a known gap counts as Low):
//   high   = @risk-high and a High-importance requirement
//   low    = @risk-low and a Low-importance requirement or none
//   medium = everything else
// A "value" annotation replaces the worked-out score, and must say why ("low: same check as T-18").
//
// WHAT IT CHECKS AND REPORTS.
//   - Two tests with the same identifier (compared by number: T-7 and T-07 are the same): REJECTED.
//     Nothing is written, because the inventory's rows and every reference to a test depend on
//     identifiers being unique.
//   - A test with no identifier, purpose or source, more than one of any, an identifier not of the
//     form T-<number>, a source naming a requirement that doesn't exist, a "none:" with no reason, a
//     value override that isn't "high:", "medium:" or "low:" followed by a reason, or not exactly one
//     risk tag: INCOMPLETE. The inventory is still written, with an Incomplete section naming each.
//   - Two or more tests with the same purpose, once letter case, spaces and punctuation are ignored:
//     POSSIBLE DUPLICATES, listed for a person to decide (it is not an error).
//   - Known gaps ("none: …") are listed apart from incomplete tests: a gap chosen on purpose is not a
//     mistake. Requirements no test serves are listed too.
// The output is the same for the same tests: no date or time is written, and every list is sorted.
// It is written only to a .md file, never over a test, a settings file, the requirements or the
// generator (even under another name for the same file), and only once complete: the page goes
// into a new file first, which then replaces the old inventory.
//
// Run it from participant/tests/playwright:
//   node tools/inventory.ts                    write participant/context/playwright/inventory.md
//   node tools/inventory.ts --out <file>       write somewhere else instead
// Exit 0: written, every test complete. 1: written, but some tests are incomplete. 2: nothing
// written (duplicate identifiers, or it couldn't list the tests or read the requirements).

import { spawnSync } from "node:child_process";
import { randomBytes } from "node:crypto";
import { closeSync, existsSync, openSync, readFileSync, renameSync, rmSync, statSync, writeSync } from "node:fs";
import { dirname, extname, join, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";

type Annotation = { type: string; description?: string };
type Spec = { title: string; file: string; line: number; tags?: string[]; tests?: { annotations?: Annotation[] }[] };
type Suite = { specs?: Spec[]; suites?: Suite[] };
type Value = "high" | "medium" | "low";
type Row = {
  id: string; ids: string[]; title: string; file: string; line: number; tags: string[]; purpose: string; source: string;
  value: Value | ""; valueNote: string; runs: string; problems: string[];
};

const here = (path: string) => fileURLToPath(new URL(path, import.meta.url));
const projectDir = here("..");
const args = process.argv.slice(2);
let outFile = here("../../../context/playwright/inventory.md");
if (args.length === 2 && args[0] === "--out" && args[1] && !args[1].startsWith("--")) outFile = resolve(args[1]);
else if (args.length !== 0) {
  console.error("Usage: node tools/inventory.ts [--out <file>]");
  process.exit(2);
}
const stop = (message: string): never => {
  console.error(message);
  console.error("Nothing was written.");
  process.exit(2);
};

// --- The requirements and their importance. --------------------------------------------------
const requirementsFile = here("../../../context/playwright/requirements.md");
let requirementsText = "";
try {
  requirementsText = readFileSync(requirementsFile, "utf8");
} catch {
  stop("Couldn't read participant/context/playwright/requirements.md.");
}
const importance = new Map<string, "High" | "Medium" | "Low">();
for (const section of requirementsText.split(/^### /m).slice(1)) {
  const id = section.match(/^(CHK-\d+)\s*$/m)?.[1];
  const level = section.match(/^- \*\*Importance:\*\* (High|Medium|Low)\s*$/m)?.[1] as "High" | "Medium" | "Low" | undefined;
  if (id && level) importance.set(id, level);
}
if (importance.size === 0) stop("No requirements with an importance were found in requirements.md.");

// --- The tests, from Playwright's listing. ---------------------------------------------------
const listEnv = { ...process.env };
for (const name of ["PLAYWRIGHT_JSON_OUTPUT_FILE", "PLAYWRIGHT_JSON_OUTPUT_DIR", "PLAYWRIGHT_JSON_OUTPUT_NAME"]) delete listEnv[name];
const settings: [string, string][] = [
  ["playwright.config.ts", "main suite"],
  ["evidence.config.ts", "only with the evidence settings (evidence.config.ts)"],
];
const specs: { spec: Spec; runs: string }[] = [];
for (const [config, runs] of settings) {
  // The project's own installed Playwright, run by this same Node: never `npx`, which could download
  // and run a different copy when the project's packages aren't installed.
  const cli = resolve(projectDir, "node_modules/@playwright/test/cli.js");
  if (!existsSync(cli)) stop("Playwright isn't installed in this project; run `npm ci` here first.");
  // One settings file with no tests left is fine (--pass-with-no-tests); no tests at all is not.
  const listed = spawnSync(process.execPath, [cli, "test", "--config", config, "--list", "--reporter=json", "--pass-with-no-tests"], {
    cwd: projectDir, encoding: "utf8", env: listEnv,
  });
  let suites: Suite[] = [];
  let rootDir = "";
  try {
    if (listed.error || listed.status !== 0) throw new Error();
    const report = JSON.parse(listed.stdout);
    suites = (report.suites ?? []) as Suite[];
    // Playwright gives each file relative to that settings' own test folder.
    rootDir = String(report.config?.rootDir ?? "");
    if (!rootDir) throw new Error();
  } catch {
    // Playwright's own message isn't passed on: it can name full paths or other details of this
    // computer. The command to see it is given instead.
    stop(`Couldn't list the tests with ${config} (exit ${listed.status ?? "none"}). To see why, run: npx playwright test --config ${config} --list`);
  }
  const walk = (suite: Suite) => {
    for (const spec of suite.specs ?? []) {
      // Playwright's listing gives tags without their "@"; they are shown as written in the tests.
      const tags = (spec.tags ?? []).map((t) => (t.startsWith("@") ? t : `@${t}`));
      specs.push({ spec: { ...spec, tags, file: relative(projectDir, resolve(rootDir, spec.file)).split("\\").join("/") }, runs });
    }
    for (const child of suite.suites ?? []) walk(child);
  };
  suites.forEach(walk);
}
if (specs.length === 0) stop("Playwright listed no tests.");

// A whole file skipped unless a setting is switched on, read from the file's own text.
const fileSkips = new Map<string, string>();
const skipSetting = (file: string): string => {
  if (!fileSkips.has(file)) {
    let text = "";
    try {
      text = readFileSync(resolve(projectDir, file), "utf8");
    } catch {
      stop(`Couldn't read the test file ${file}.`);
    }
    const m = text.match(/^test\.skip\(process\.env\.([A-Z0-9_]+) !== "1"/m);
    fileSkips.set(file, m ? m[1] : "");
  }
  return fileSkips.get(file)!;
};

// --- One row per test. -----------------------------------------------------------------------
const one = (annotations: Annotation[], type: string, problems: string[], required: boolean): string => {
  const found = annotations.filter((a) => a.type === type).map((a) => (a.description ?? "").trim());
  if (found.length > 1) problems.push(`more than one ${type}`);
  if (found.length === 0) {
    if (required) problems.push(`no ${type}`);
    return "";
  }
  if (found[0] === "") {
    problems.push(required ? `no ${type}` : `an empty ${type}`);
    return "";
  }
  return found[0];
};
const rows: Row[] = specs.map(({ spec, runs }) => {
  const annotations = spec.tests?.[0]?.annotations ?? [];
  const problems: string[] = [];
  const file = spec.file;
  const id = one(annotations, "id", problems, true);
  // Every identifier the test declares, so a second one can't hide a clash with another test.
  const ids = [...new Set(annotations.filter((a) => a.type === "id").map((a) => (a.description ?? "").trim()).filter(Boolean))];
  if (id && !/^T-\d+$/.test(id)) problems.push(`identifier "${id}" isn't of the form T-<number>`);
  const purpose = one(annotations, "purpose", problems, true);
  const source = one(annotations, "source", problems, true);
  let sourceImportance: "High" | "Medium" | "Low" | undefined;
  if (source.startsWith("none:")) {
    if (source.slice(5).trim() === "") problems.push(`source "none:" gives no reason`);
    sourceImportance = "Low";
  } else if (source) {
    sourceImportance = importance.get(source);
    if (!sourceImportance) problems.push(`source "${source}" isn't a requirement in requirements.md`);
  }
  const risks = (spec.tags ?? []).filter((t) => /^@risk-(high|medium|low)$/.test(t));
  if (risks.length !== 1) problems.push(risks.length ? "more than one risk tag" : "no risk tag");
  let value: Value | "" = "";
  let valueNote = "";
  if (risks.length === 1 && sourceImportance) {
    const risk = risks[0].slice("@risk-".length);
    value = risk === "high" && sourceImportance === "High" ? "high" : risk === "low" && sourceImportance === "Low" ? "low" : "medium";
  }
  const override = one(annotations, "value", problems, false);
  if (override) {
    const m = override.match(/^(high|medium|low):\s*(\S.*)$/);
    if (!m) problems.push(`value "${override}" isn't "high:", "medium:" or "low:" followed by a reason`);
    else {
      valueNote = `${value ? `worked out ${value}; ` : ""}set to ${m[1]}: ${m[2]}`;
      value = m[1] as Value;
    }
  }
  const skippedBy = skipSetting(file);
  const howItRuns = skippedBy ? `${runs}, but skipped unless ${skippedBy}=1` : runs;
  return { id, ids, title: spec.title, file, line: spec.line, tags: spec.tags ?? [], purpose, source, value, valueNote, runs: howItRuns, problems };
});

// --- Duplicate identifiers: rejected. ---------------------------------------------------------
// Compared by number, so "T-7" and "T-07" count as the same identifier. An identifier not of the
// form T-<number> is compared as written (it is reported as incomplete anyway).
// Leading zeros are dropped as text, not by turning the number into a JavaScript number, which
// would merge very large ones.
const digits = (id: string) => id.slice(2).replace(/^0+(?=\d)/, "");
const idKey = (id: string) => (/^T-\d+$/.test(id) ? `T-${digits(id)}` : id);
const byId = new Map<string, Row[]>();
for (const row of rows) {
  // Each test once per identifier, even if it repeats one ("T-7" and "T-07" on the same test).
  for (const key of new Set(row.ids.map(idKey))) byId.set(key, [...(byId.get(key) ?? []), row]);
}
const clashes = [...byId.entries()].filter(([, list]) => list.length > 1).sort(([a], [b]) => a.localeCompare(b, "en"));
if (clashes.length > 0) {
  console.error("REJECTED: two or more tests share an identifier, so no inventory can be written:");
  for (const [id, list] of clashes) {
    console.error(`  ${id}:`);
    for (const row of list) console.error(`    ${row.ids.join(", ")}: ${row.file}:${row.line} › ${row.title}`);
  }
  console.error("Give each test its own identifier and run this again.");
  console.error("Nothing was written.");
  process.exit(2);
}

// --- Sorting, duplicates and gaps. -----------------------------------------------------------
// By number, compared as text (shorter is smaller, then digit by digit); others after, as written.
const byNumber = (a: string, b: string) => {
  const okA = /^T-\d+$/.test(a);
  const okB = /^T-\d+$/.test(b);
  if (okA !== okB) return okA ? -1 : 1;
  if (!okA) return 0;
  const [x, y] = [digits(a), digits(b)];
  return x.length - y.length || (x < y ? -1 : x > y ? 1 : 0);
};
const where = (row: Row) => `${row.file}:${row.line}`;
rows.sort((a, b) => byNumber(a.id, b.id) || a.id.localeCompare(b.id, "en") || where(a).localeCompare(where(b), "en"));
const label = (row: Row) => row.id || `(no id) ${where(row)}`;
const tidy = (text: string) => text.toLowerCase().replace(/[^\p{L}\p{N}]+/gu, " ").trim();
const byPurpose = new Map<string, Row[]>();
for (const row of rows) if (row.purpose) byPurpose.set(tidy(row.purpose), [...(byPurpose.get(tidy(row.purpose)) ?? []), row]);
const duplicates = [...byPurpose.values()].filter((list) => list.length > 1);
const incomplete = rows.filter((row) => row.problems.length > 0);
const gaps = rows.filter((row) => row.source.startsWith("none:"));
const requirementIds = [...importance.keys()].sort((a, b) => Number(a.slice(4)) - Number(b.slice(4)));

// --- The page. --------------------------------------------------------------------------------
// Text from the tests (titles, purposes, sources, reasons) is shown exactly as written: every
// character Markdown or HTML would treat as formatting is escaped, and a line break becomes a space.
const cell = (text: string) =>
  text.replace(/\r?\n/g, " ").replace(/&/g, "&amp;").replace(/[\\`*_[\]<>|#~]/g, (c) => `\\${c}`);
// Inside `code`, only a table's | needs escaping; text containing a backtick is shown as plain text.
const code = (text: string) => (text.includes("`") ? cell(text) : `\`${text.replace(/\r?\n/g, " ").replace(/\|/g, "\\|")}\``);
const tagsOf = (row: Row) => row.tags.map(code).join(" ");
const valueOf = (row: Row) => (row.value ? `**${row.value}**${row.valueNote ? ` (${cell(row.valueNote)})` : ""}` : "(not worked out)");
const out: string[] = [
  "# Test inventory",
  "",
  "Generated by `participant/tests/playwright/tools/inventory.ts` from the tests themselves; never",
  "edit it by hand. To bring it up to date after changing a test, run, from",
  "`participant/tests/playwright`:",
  "",
  "```sh",
  "node tools/inventory.ts",
  "```",
  "",
  "Each test's identifier, purpose, source requirement and any value override are written in the test,",
  "as Playwright annotations next to its tags. The purpose says what the test proves, not how it is",
  "written. The source is a requirement in `participant/context/playwright/requirements.md`, or",
  "\"none: <reason>\" for a known gap.",
  "",
  "**Value score**, on a three-level scale, worked out from the test's risk tag and its source",
  "requirement's importance (a known gap counts as Low importance):",
  "",
  "- **high:** `@risk-high` and a High-importance requirement",
  "- **low:** `@risk-low` and a Low-importance requirement or none",
  "- **medium:** everything else",
  "",
  "A test can set a different score only with a reason, shown next to its score.",
  "",
  `**${rows.length} tests:** ${["high", "medium", "low"].map((v) => `${rows.filter((r) => r.value === v).length} ${v}`).join(", ")}` +
    `${rows.some((r) => !r.value) ? `, ${rows.filter((r) => !r.value).length} not worked out` : ""}; ` +
    `${incomplete.length} incomplete; ${gaps.length} known gaps; ${duplicates.length} groups of possible duplicates.`,
  "",
  "## Every test",
  "",
  "| ID | Test | Purpose | Tags | Source | Value | File | How it runs |",
  "|---|---|---|---|---|---|---|---|",
  ...rows.map((row) =>
    `| ${cell(label(row))} | ${cell(row.title)} | ${cell(row.purpose || "(none)")} | ${tagsOf(row)} | ${cell(row.source || "(none)")} | ${valueOf(row)} | ${code(where(row))} | ${cell(row.runs)} |`),
  "",
  "## Tests by requirement",
  "",
  "Where to find the tests for a requirement. A requirement with no test is listed as such.",
  "",
  "| Requirement | Importance | Tests |",
  "|---|---|---|",
  ...requirementIds.map((req) => {
    const serving = rows.filter((row) => row.source === req);
    return `| ${req} | ${importance.get(req)} | ${serving.length ? serving.map((row) => `${cell(label(row))} (${row.value || "?"})`).join(", ") : "**no test**"} |`;
  }),
  "",
  "## Known gaps: tests no requirement covers",
  "",
  ...(gaps.length ? gaps.map((row) => `- ${cell(label(row))}: ${cell(row.source.slice(5).trim())} (${code(where(row))})`) : ["None."]),
  "",
  "## Possible duplicates: tests with the same purpose",
  "",
  "Same text once letter case, spaces and punctuation are ignored. A person decides what each group means.",
  "",
  ...(duplicates.length
    ? duplicates.flatMap((list, n) => [
        `${n + 1}. "${cell(list[0].purpose)}"`,
        ...list.map((row) => `   - ${cell(label(row))}: ${cell(row.title)}, value ${valueOf(row)}`),
      ])
    : ["None."]),
  "",
  "## Incomplete tests",
  "",
  ...(incomplete.length ? incomplete.map((row) => `- ${cell(label(row))} (${code(where(row))}): ${cell(row.problems.join("; "))}`) : ["None."]),
  "",
  "## By value",
  "",
  ...(["high", "medium", "low"] as const).map((v) => `- **${v}:** ${rows.filter((r) => r.value === v).map((r) => cell(label(r))).join(", ") || "none"}`),
  "",
];
const page = out.join("\n");

// Writing: only to a Markdown file, and never onto anything the inventory is made from (a test file,
// a settings file, the requirements or this generator), even by another name for the same file.
const sameFile = (a: string, b: string) => {
  try {
    const x = statSync(a);
    const y = statSync(b);
    return x.dev === y.dev && x.ino === y.ino;
  } catch {
    return false;
  }
};
const inputs = [
  requirementsFile, fileURLToPath(import.meta.url),
  ...settings.map(([config]) => resolve(projectDir, config)),
  ...[...new Set(rows.map((row) => row.file))].map((file) => resolve(projectDir, file)),
];
if (extname(outFile).toLowerCase() !== ".md") stop("The inventory can only be written to a .md file.");
if (inputs.some((input) => resolve(input) === outFile || sameFile(input, outFile))) {
  stop("The inventory can't be written over a file it is made from (a test, a settings file, the requirements or the generator).");
}
// The whole page goes into a new file beside the destination first, and replaces the destination
// only once it is complete: a failed write never leaves a half-written inventory.
// Its name is new each time, and only a file this run created is ever removed.
const temporary = join(dirname(outFile), `.inventory-${process.pid}-${randomBytes(6).toString("hex")}.tmp`);
let created = false;
try {
  // Created new ("wx"), and known to be this run's from that moment, so a failure part-way through
  // writing still removes it.
  const fd = openSync(temporary, "wx");
  created = true;
  try {
    const bytes = Buffer.from(page, "utf8");
    let at = 0;
    while (at < bytes.length) at += writeSync(fd, bytes, at, bytes.length - at);
  } finally {
    closeSync(fd);
  }
  renameSync(temporary, outFile);
} catch {
  if (created) {
    try {
      rmSync(temporary, { force: true });
    } catch {
      // Left behind; the message below still says nothing was written to the inventory.
    }
  }
  stop("Couldn't write the inventory.");
}
// The file is named from the repository's top (participant/…), or just as "the --out file" when it is
// elsewhere, so no folder outside the repository (which can show the user name) is printed.
const fromRepo = relative(here("../../../.."), outFile).split("\\").join("/");
const shownOut = fromRepo.startsWith("..") || fromRepo.startsWith("/") ? "the --out file" : fromRepo;
console.log(`Wrote ${shownOut}: ${rows.length} tests; ${incomplete.length} incomplete; ${gaps.length} known gaps; ${duplicates.length} groups of possible duplicates.`);
for (const row of incomplete) console.log(`  INCOMPLETE ${label(row)} (${where(row)}): ${row.problems.join("; ")}`);
for (const list of duplicates) console.log(`  POSSIBLE DUPLICATES: ${list.map(label).join(", ")}: "${list[0].purpose}"`);
process.exit(incomplete.length ? 1 : 0);
