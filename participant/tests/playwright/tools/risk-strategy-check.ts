// risk-strategy-check: checks the Tixly layered test strategy against its requirements.
//
// Reads participant/context/playwright/requirements.md and strategy.md and checks that:
//   - the likelihood and impact scales are stated once each, with levels 3, 2 and 1 defined in words;
//   - every risk has exactly one layer (unit, API, UI, manual or untested) and a reason;
//   - every requirement appears in the strategy;
//   - risks that need a browser are kept apart from those that don't;
//   - every untested risk is listed with its reason and who accepted it;
//   - the scoring and ranking rules it applies are the ones the strategy states, and the ranking
//     table is exactly what they produce;
//   - the totals under the table match the risks, and the sentence after them, if present, is true.
//
// It reads only those two files and writes nothing. Both files are read against an allowlist:
// every heading, entry, field, scale level and table line must be in the exact form the format
// allows, and markup that would make the rendered page differ from the text (HTML, comments,
// escapes, code fences) is refused. Anything else is reported, not skipped, so a typo or a
// disguise can't quietly drop something from the check or hide it from a reader.
//
// It checks that the strategy is complete and consistent, not that its judgments are right: it
// can't tell whether a score, a layer or a reason is the right one, or whether other prose
// contradicts the stated rules. Those are for the person reading the strategy.
//
// Run from the repository root (Node 22.18 or later runs TypeScript directly, nothing to install):
//   node participant/tests/playwright/tools/risk-strategy-check.ts
// Optional: --requirements <path> --strategy <path>
// Exit status: 0 passed, 1 failed, 2 a file couldn't be read or the arguments were wrong.

import { readFileSync } from "node:fs";

const VERSION = "1.0.0";
const DEFAULT_REQUIREMENTS = "participant/context/playwright/requirements.md";
const DEFAULT_STRATEGY = "participant/context/playwright/strategy.md";

const LAYERS = ["unit", "API", "UI", "manual", "untested"] as const;
type Layer = (typeof LAYERS)[number];
const IMPORTANCE = new Map<string, number>([["High", 3], ["Medium", 2], ["Low", 1]]);
const MIN_REASON_WORDS = 8;
// A scale level must say what it means in words, so another person can score with it.
const MIN_LEVEL_WORDS = 3;

// The scoring and ranking rules this check applies. The strategy must state each one word for
// word (line breaks aside), so the document can't describe one ranking while the check enforces
// another.
const STATED_RULES = [
  "**Score** = likelihood \u00d7 impact, from 1 to 9.",
  "Risks are ranked by score, highest first.",
  "Ties go to the risk whose requirement has the higher importance (High, then Medium, then Low, " +
    "as defined in `requirements.md`; for a risk with several requirements, the highest of them).",
  "Remaining ties go in risk number order.",
];

const BROWSER_SECTION = "Risks that need a browser";
const NO_BROWSER_SECTION = "Risks that don't need a browser";
const UNTESTED_SECTION = "Accepted as untested";
const RISK_SECTIONS = [BROWSER_SECTION, NO_BROWSER_SECTION, UNTESTED_SECTION];
// Which layers each risk section may hold. A manual check may or may not need a browser.
const SECTION_LAYERS: Record<string, Layer[]> = {
  [BROWSER_SECTION]: ["UI", "manual"],
  [NO_BROWSER_SECTION]: ["unit", "API", "manual"],
  [UNTESTED_SECTION]: ["untested"],
};

interface Requirement {
  id: string;
  importance: string;
}

interface Risk {
  id: string;
  section: string;
  requirements: string[];
  likelihood: number;
  impact: number;
  layer: Layer;
  reason: string;
  acceptedBy: string;
}

class Unreadable extends Error {}

const problems: string[] = [];

function problem(message: string): void {
  problems.push(message);
}

// Characters a reader can't see, or that look like an ordinary space but aren't one. A line with
// any of them is refused, so an entry can't hide text or look different from what is checked.
const INVISIBLE =
  /[\p{Cc}\p{Cf}\p{Co}\p{Cn}\p{Zl}\p{Zp}\p{Default_Ignorable_Code_Point}]|(?! )\p{Zs}/u;

// Markup that would make the rendered page differ from the text checked here: HTML and its
// comments, character references, backslash escapes, links and images (square brackets), code
// fences, and lines that underline the line above into a heading or draw a rule. None of it is
// part of the format, so nothing in either file can be hidden from, or disguised to, a reader.
const HIDING = /[<>&\\[\]]|^ {0,3}(?:```|~~~|=+ *$|-{2,} *$|(?:[-*_] *){3,}$)/;

// The only list form the format uses is "- " at the very start of a line. Any other list marker
// ("*", "+", a number, or an indented "-") would show as a list item the check doesn't read.
const OTHER_LIST = /^\s*(?:[*+]|\d+[.)])\s|^\s+-\s/;

// The field names entries use. A line with one of them belongs inside an entry; anywhere else it is
// an entry in the wrong place, and is reported rather than dropped with the surrounding prose.
const ENTRY_FIELD = new RegExp(
  "^- \\*\\*(?:Importance|Requirement|Assumed answer|Risk|Likelihood|Impact|Layer|Reason|Accepted by):\\*\\*",
);

function readLines(path: string, what: string): string[] {
  let bytes: Buffer;
  try {
    bytes = readFileSync(path);
  } catch (error) {
    const reason = error instanceof Error && "code" in error ? String(error.code) : "unreadable";
    throw new Unreadable(`can't read the ${what} file ${path} (${reason})`);
  }
  let text: string;
  try {
    text = new TextDecoder("utf-8", { fatal: true }).decode(bytes);
  } catch {
    problem(`${path}: the file is not valid UTF-8 text`);
    text = new TextDecoder("utf-8").decode(bytes);
  }
  const lines = text.replace(/\r\n/g, "\n").split("\n");
  lines.forEach((line, index) => {
    if (INVISIBLE.test(line)) {
      problem(`${path} line ${index + 1}: contains an invisible or unusual character`);
    }
    if (HIDING.test(line)) {
      problem(`${path} line ${index + 1}: contains markup the format doesn't allow (HTML, <, >, &, \\, [ ], a code fence or a heading underline)`);
    }
    if (OTHER_LIST.test(line)) {
      problem(`${path} line ${index + 1}: uses a list marker the format doesn't allow (only "- " at the start of a line)`);
    }
  });
  return lines;
}

// A field line looks exactly like "- **Name:** value".
function field(line: string | undefined, name: string): string | null {
  const prefix = `- **${name}:** `;
  if (line === undefined || !line.startsWith(prefix)) return null;
  const value = line.slice(prefix.length).trim();
  return value === "" ? null : value;
}

// What a file may contain: its "## " sections, exactly and in order; which of them hold "### "
// entries; and which one may hold the table.
interface Layout {
  sections: string[];
  entrySections: string[];
  tableSection: string | null;
}

interface Section {
  start: number;
  lines: string[];
}

// Splits a file into its sections. The file must open with one "# " title, then have exactly the
// layout's "## " sections in order. Any other heading, an entry heading outside the entry
// sections, or a table line outside the table section is reported, so nothing written in an
// unexpected form is silently left out of the check.
function sections(path: string, lines: string[], layout: Layout): Map<string, Section> {
  const found = new Map<string, Section>();
  const order: string[] = [];
  let titled = false;
  let name = "";
  let current: Section | null = null;
  let inEntry = false;
  lines.forEach((line, index) => {
    const at = `${path} line ${index + 1}`;
    if (ENTRY_FIELD.test(line) && !inEntry) {
      problem(`${at}: "${line}" is an entry field outside an entry`);
    }
    if (/^ {0,3}#/.test(line)) {
      const heading = /^(#{1,6}) (\S.*)$/.exec(line);
      const level = heading?.[1]?.length ?? 0;
      const text = (heading?.[2] ?? "").trim();
      if (level === 1 && !titled && current === null) {
        titled = true;
      } else if (level === 2 && layout.sections.includes(text)) {
        if (found.has(text)) problem(`${path}: the section "${text}" appears more than once`);
        name = text;
        inEntry = false;
        current = { start: index + 2, lines: [] };
        found.set(text, current);
        order.push(text);
      } else if (level === 3 && layout.entrySections.includes(name)) {
        inEntry = true;
        current?.lines.push(line);
      } else {
        problem(`${at}: "${line}" is not a heading this file's format allows here`);
      }
      return;
    }
    if (line.includes("|") && name !== layout.tableSection) {
      problem(`${at}: a table line outside the ranking table`);
    }
    if (current) current.lines.push(line);
  });
  if (!titled) problem(`${path}: the file should open with a "# " title`);
  if (order.join("\n") !== layout.sections.join("\n")) {
    problem(`${path}: the sections should be exactly these, in this order: ${layout.sections.map((s) => `"${s}"`).join(", ")}`);
  }
  return found;
}

// Splits a section into "### ID" entries. Any other non-blank line outside an entry is reported,
// unless the section allows prose before its first entry.
function entries(
  path: string,
  section: Section,
  idPattern: RegExp,
  introAllowed: boolean,
): { id: string; line: number; fields: string[] }[] {
  const result: { id: string; line: number; fields: string[] }[] = [];
  section.lines.forEach((line, offset) => {
    const lineNumber = section.start + offset;
    if (line.startsWith("### ")) {
      const id = line.slice(4);
      if (!idPattern.test(id)) {
        problem(`${path} line ${lineNumber}: "${line}" is not an entry heading in the expected form`);
      }
      result.push({ id, line: lineNumber, fields: [] });
    } else if (result.length > 0) {
      const last = result[result.length - 1];
      if (last && line.trim() !== "") last.fields.push(line);
    } else if (line.trim() !== "" && (!introAllowed || /^\s*(#|- )/.test(line))) {
      // An introduction may be prose, but a heading or a list line before the first entry is
      // an entry in the wrong form, so it is reported rather than read as introduction.
      problem(`${path} line ${lineNumber}: "${line}" is before the first entry heading`);
    }
  });
  return result;
}

const REQUIREMENTS_LAYOUT: Layout = {
  sections: ["Requirements"],
  entrySections: ["Requirements"],
  tableSection: null,
};

function readRequirements(path: string): Requirement[] {
  const lines = readLines(path, "requirements");
  const section = sections(path, lines, REQUIREMENTS_LAYOUT).get("Requirements");
  if (!section) return [];
  const requirements: Requirement[] = [];
  const seen = new Set<string>();
  for (const entry of entries(path, section, /^CHK-\d{2}$/, false)) {
    const where = `${path} ${entry.id} (line ${entry.line})`;
    if (seen.has(entry.id)) problem(`${where}: the id is used more than once`);
    seen.add(entry.id);
    const names = ["Importance", "Requirement", "Assumed answer"];
    if (entry.fields.length !== names.length) {
      problem(`${where}: expected exactly ${names.length} fields (${names.join(", ")}), found ${entry.fields.length} lines`);
    }
    const values = names.map((name, i) => field(entry.fields[i], name));
    names.forEach((name, i) => {
      if (values[i] === null) problem(`${where}: field ${i + 1} should be "- **${name}:** ..." with a value`);
    });
    const importance = values[0] ?? "";
    if (values[0] !== null && !IMPORTANCE.has(importance)) {
      problem(`${where}: importance "${importance}" is not High, Medium or Low`);
    }
    requirements.push({ id: entry.id, importance });
  }
  if (requirements.length === 0) problem(`${path}: no requirements found`);
  return requirements;
}

// "3 (a time limit)": a score from 1 to 3 followed by a short explanation in brackets, which must
// contain words. Only the number is checked against the scale; whether the explanation fits it is
// for the reader to judge.
function score(value: string | null, where: string, name: string): number {
  const match = value === null ? null : /^([1-3]) \((.*\p{L}.*)\)$/u.exec(value);
  if (!match) {
    problem(`${where}: ${name} should be 1, 2 or 3 followed by a short explanation in words, in brackets`);
    return 0;
  }
  return Number(match[1]);
}

const SCORING_SECTION = "How risks are scored";
const RANKING_SECTION = "Ranking";
const STRATEGY_LAYOUT: Layout = {
  sections: [
    SCORING_SECTION,
    "The test layers",
    RANKING_SECTION,
    BROWSER_SECTION,
    NO_BROWSER_SECTION,
    UNTESTED_SECTION,
    "Outside this strategy",
  ],
  entrySections: RISK_SECTIONS,
  tableSection: RANKING_SECTION,
};
const TABLE_HEADER = "| Rank | Risk | Requirement | Likelihood | Impact | Score | Layer |";
const TABLE_COLUMNS = 7;

// The cells of a table line, without the outer pipes.
function cells(line: string): string[] {
  return line.split("|").slice(1, -1).map((cell) => cell.trim());
}

function readStrategy(path: string): {
  scalesOk: boolean;
  missingRules: string[] | null;
  risks: Risk[];
  table: string[][];
  totals: string | null;
  totalsClaim: string | null;
} {
  const lines = readLines(path, "strategy");
  const found = sections(path, lines, STRATEGY_LAYOUT);

  // The scales: each stated once, as a "**Likelihood**" or "**Impact**" paragraph followed by its
  // levels. Every list line in this section must be a level of the scale just above it, and each
  // scale must define exactly the levels 3, 2 and 1, in that order.
  let scalesOk = true;
  const scoring = found.get(SCORING_SECTION);
  if (!scoring) {
    scalesOk = false;
  } else {
    const levels = new Map<string, string[]>();
    // Each level's text, with any indented lines that continue it, so a wrapped definition is
    // counted whole.
    const definitions: { scale: string; level: string; at: string; text: string }[] = [];
    let scale: string | null = null;
    // The level an indented line continues: only the one directly above it, in the same scale.
    let continuing: { text: string } | null = null;
    scoring.lines.forEach((line, offset) => {
      const at = `${path} line ${scoring.start + offset}`;
      const opening = /^\*\*(Likelihood|Impact)\*\* /.exec(line);
      if (opening?.[1]) {
        scale = opening[1];
        if (levels.has(scale)) {
          problem(`${at}: the ${scale.toLowerCase()} scale is stated more than once`);
          scalesOk = false;
        }
        levels.set(scale, []);
        continuing = null;
      } else if (line.startsWith("- ")) {
        const level = /^- \*\*([^*]+):\*\* (.*)$/.exec(line);
        if (scale === null || !level?.[1]) {
          problem(`${at}: "${line}" is a list line that isn't a level of a scale`);
          scalesOk = false;
          continuing = null;
        } else {
          const definition = { scale, level: level[1], at, text: level[2] ?? "" };
          definitions.push(definition);
          levels.get(scale)?.push(level[1]);
          continuing = definition;
        }
      } else if (line.startsWith("  ") && line.trim() !== "") {
        if (continuing) continuing.text += ` ${line.trim()}`;
      } else if (line.trim() !== "") {
        // Any other paragraph ends the scale; a blank line or an indented continuation doesn't.
        scale = null;
        continuing = null;
      }
    });
    for (const definition of definitions) {
      if (words(definition.text) < MIN_LEVEL_WORDS) {
        problem(`${definition.at}: level ${definition.level} of the ${definition.scale.toLowerCase()} scale should say what it means in at least ${MIN_LEVEL_WORDS} words`);
        scalesOk = false;
      }
    }
    for (const name of ["Likelihood", "Impact"]) {
      const defined = levels.get(name);
      if (defined === undefined) {
        problem(`${path}: the ${name.toLowerCase()} scale is not stated`);
        scalesOk = false;
      } else if (defined.join(",") !== "3,2,1") {
        problem(`${path}: the ${name.toLowerCase()} scale should define exactly the levels 3, 2 and 1, in that order (found ${defined.join(", ") || "none"})`);
        scalesOk = false;
      }
    }
  }

  // The ranking rules, as stated in the scoring section.
  const missingRules: string[] = [];
  if (scoring) {
    const text = scoring.lines.join(" ").replace(/\s+/g, " ");
    for (const rule of STATED_RULES) {
      if (!text.includes(rule)) missingRules.push(rule);
    }
  }

  // Every risk entry, in whichever risk section it sits.
  const risks: Risk[] = [];
  for (const name of RISK_SECTIONS) {
    const section = found.get(name);
    if (!section) continue;
    for (const entry of entries(path, section, /^R-\d{2}$/, true)) {
      const where = `${path} ${entry.id} (line ${entry.line})`;
      const names = ["Requirement", "Risk", "Likelihood", "Impact", "Layer", "Reason"];
      if (name === UNTESTED_SECTION) names.push("Accepted by");
      if (entry.fields.length !== names.length) {
        problem(`${where}: expected exactly ${names.length} fields (${names.join(", ")}), found ${entry.fields.length} lines`);
      }
      const values = names.map((fieldName, i) => field(entry.fields[i], fieldName));
      names.forEach((fieldName, i) => {
        if (values[i] === null) problem(`${where}: field ${i + 1} should be "- **${fieldName}:** ..." with a value`);
      });
      const requirements = (values[0] ?? "").split(", ").filter((id) => id !== "");
      const layer = values[4] ?? "";
      if (values[4] !== null && !(LAYERS as readonly string[]).includes(layer)) {
        problem(`${where}: layer "${layer}" is not exactly one of ${LAYERS.join(", ")}`);
      }
      risks.push({
        id: entry.id,
        section: name,
        requirements,
        likelihood: score(values[2] ?? null, where, "likelihood"),
        impact: score(values[3] ?? null, where, "impact"),
        layer: layer as Layer,
        reason: values[5] ?? "",
        acceptedBy: values[6] ?? "",
      });
    }
  }

  // The ranking table: one unbroken block of lines, each starting and ending with "|": the
  // header, a divider of exactly seven cells, then one row of seven cells per risk.
  const table: string[][] = [];
  const ranking = found.get(RANKING_SECTION);
  let totals: string | null = null;
  let totalsClaim: string | null = null;
  if (ranking) {
    const rows: { line: string; offset: number }[] = [];
    ranking.lines.forEach((line, offset) => {
      if (!line.includes("|")) return;
      if (!/^\|.*\|$/.test(line)) {
        problem(`${path} line ${ranking.start + offset}: a table line should start and end with "|"`);
        return;
      }
      rows.push({ line, offset });
    });
    rows.forEach((row, i) => {
      const previous = rows[i - 1];
      if (previous && row.offset !== previous.offset + 1) {
        problem(`${path} line ${ranking.start + row.offset}: the ranking table is broken by another line above this one`);
      }
    });
    if (rows[0]?.line !== TABLE_HEADER) {
      problem(`${path}: the ranking table should start with the header ${TABLE_HEADER}`);
    }
    const divider = rows[1] === undefined ? [] : cells(rows[1].line);
    if (divider.length !== TABLE_COLUMNS || !divider.every((cell) => /^:?-+:?$/.test(cell))) {
      problem(`${path}: the ranking table's second line should be a divider of exactly ${TABLE_COLUMNS} cells`);
    }
    for (const row of rows.slice(2)) {
      const values = cells(row.line);
      if (values.length !== TABLE_COLUMNS) {
        problem(`${path} line ${ranking.start + row.offset}: a ranking row should have exactly ${TABLE_COLUMNS} cells`);
      }
      table.push(values);
    }
    // The totals paragraph: exactly one, read whole (it may wrap over several lines). Its first
    // sentence gives the count per layer; anything after it is a claim the check must verify.
    const totalsAt = ranking.lines.flatMap((line, i) => (line.startsWith("Totals: ") ? [i] : []));
    if (totalsAt.length > 1) {
      problem(`${path}: the ranking section has ${totalsAt.length} totals paragraphs; it should have one`);
    }
    const first = totalsAt[0];
    if (first !== undefined) {
      const paragraph: string[] = [];
      for (const line of ranking.lines.slice(first)) {
        if (line.trim() === "") break;
        paragraph.push(line.trim());
      }
      const match = /^Totals: ([^.]*)\.(?: (.+))?$/.exec(paragraph.join(" "));
      totals = match?.[1] ?? "";
      totalsClaim = match?.[2] ?? null;
    }
  }
  return { scalesOk, missingRules: scoring ? missingRules : null, risks, table, totals, totalsClaim };
}

function words(text: string): number {
  return text.split(/\s+/).filter((word) => /\p{L}/u.test(word)).length;
}

function main(argv: string[]): number {
  let requirementsPath = DEFAULT_REQUIREMENTS;
  let strategyPath = DEFAULT_STRATEGY;
  for (let i = 0; i < argv.length; i += 2) {
    const value = argv[i + 1];
    if (value === undefined || value.startsWith("--")) {
      console.error(`usage: node risk-strategy-check.ts [--requirements <path>] [--strategy <path>]`);
      return 2;
    }
    if (argv[i] === "--requirements") requirementsPath = value;
    else if (argv[i] === "--strategy") strategyPath = value;
    else {
      console.error(`unknown option ${argv[i]}`);
      return 2;
    }
  }

  let requirements: Requirement[];
  let strategy: ReturnType<typeof readStrategy>;
  try {
    requirements = readRequirements(requirementsPath);
    strategy = readStrategy(strategyPath);
  } catch (error) {
    if (error instanceof Unreadable) {
      console.error(`risk-strategy-check ${VERSION}: ${error.message}`);
      return 2;
    }
    throw error;
  }
  const { risks, table, totals } = strategy;
  const known = new Map(requirements.map((r) => [r.id, r]));
  const out: string[] = [];
  const check = (passed: boolean, text: string, details: string[] = []): void => {
    out.push(`${passed ? "PASS" : "FAIL"}  ${text}`);
    for (const line of details) out.push(`      ${line}`);
  };

  out.push(`risk-strategy-check ${VERSION}`);
  out.push(`requirements: ${requirementsPath} (${requirements.length} requirements)`);
  out.push(`strategy: ${strategyPath} (${risks.length} risks)`);

  // Problems found while reading come first: the checks below rely on the files being read whole.
  const readProblems = problems.splice(0);
  check(readProblems.length === 0, "both files are in the expected form", readProblems);

  // Criterion 2 and 7: the scales are stated.
  check(strategy.scalesOk, "the likelihood and impact scales are each stated at 3, 2 and 1");

  // Criterion 7: the rules used to rebuild the ranking are the ones the strategy states.
  const missingRules = strategy.missingRules;
  check(
    missingRules !== null && missingRules.length === 0,
    "the strategy states the scoring and ranking rules this check applies",
    missingRules === null ? ["no scoring section"] : missingRules.map((rule) => `not stated: ${rule}`),
  );

  // Risk ids and the requirements each risk names.
  const idProblems: string[] = [];
  const seen = new Set<string>();
  for (const risk of risks) {
    if (seen.has(risk.id)) idProblems.push(`${risk.id} is used more than once`);
    seen.add(risk.id);
    if (risk.requirements.length === 0) idProblems.push(`${risk.id} names no requirement`);
    for (const id of risk.requirements) {
      if (!known.has(id)) idProblems.push(`${risk.id} names ${id}, which is not in the requirements`);
    }
    if (new Set(risk.requirements).size !== risk.requirements.length) {
      idProblems.push(`${risk.id} names the same requirement twice`);
    }
  }
  check(idProblems.length === 0, `every risk has its own id and names only known requirements`, idProblems);

  // Criterion 3: one layer per risk.
  const badLayer = risks.filter((r) => !(LAYERS as readonly string[]).includes(r.layer));
  check(
    risks.length > 0 && badLayer.length === 0,
    `every risk has exactly one layer from ${LAYERS.join(", ")}`,
    badLayer.map((r) => `${r.id}: "${r.layer}"`),
  );

  // Criterion 4: a reason, not only a label.
  const thin = risks.filter((r) => words(r.reason) < MIN_REASON_WORDS);
  check(
    risks.length > 0 && thin.length === 0,
    `every risk gives a reason of at least ${MIN_REASON_WORDS} words for its layer`,
    thin.map((r) => `${r.id}: ${words(r.reason)} words`),
  );

  // Criterion 1: every requirement appears in the strategy.
  const coverage: string[] = [];
  const missing: string[] = [];
  for (const requirement of requirements) {
    const covering = risks
      .filter((r) => r.requirements.includes(requirement.id))
      .sort((a, b) => Number(a.id.slice(2)) - Number(b.id.slice(2)));
    if (covering.length === 0) {
      missing.push(`${requirement.id}: not in the strategy`);
    } else {
      const tested = covering.some((r) => r.layer !== "untested");
      coverage.push(
        `${requirement.id}: ${covering.map((r) => `${r.id} ${r.layer}`).join(", ")}${tested ? "" : " (untested only, listed)"}`,
      );
    }
  }
  check(
    requirements.length > 0 && missing.length === 0,
    `every requirement appears in the strategy (${requirements.length - missing.length} of ${requirements.length})`,
    [...missing, ...coverage],
  );

  // Criterion 5: browser risks kept apart from the rest.
  const misplaced = risks.filter((r) => !(SECTION_LAYERS[r.section] ?? []).includes(r.layer));
  const count = (section: string) => risks.filter((r) => r.section === section).length;
  check(
    misplaced.length === 0,
    `browser risks are separated: ${count(BROWSER_SECTION)} in "${BROWSER_SECTION}", ` +
      `${count(NO_BROWSER_SECTION)} in "${NO_BROWSER_SECTION}", each holding only the layers it allows`,
    misplaced.map((r) => `${r.id} has layer ${r.layer} but is in "${r.section}"`),
  );

  // Criterion 6: every untested risk is listed with a reason and who accepted it.
  const untested = risks.filter((r) => r.layer === "untested");
  const unlisted = untested.filter((r) => r.section !== UNTESTED_SECTION || r.acceptedBy === "");
  check(
    unlisted.length === 0,
    `every untested risk is listed in "${UNTESTED_SECTION}" with a reason and who accepted it ` +
      `(${untested.length}: ${untested.map((r) => r.id).join(", ") || "none"})`,
    [
      ...unlisted.map((r) => `${r.id} is untested but not listed with who accepted it`),
      ...untested.filter((r) => r.acceptedBy !== "").map((r) => `${r.id} accepted by ${r.acceptedBy}`),
    ],
  );

  // Criterion 7: rebuild the ranking from the scales and the tie rules, and compare with the table.
  const importance = (risk: Risk): number =>
    Math.max(0, ...risk.requirements.map((id) => IMPORTANCE.get(known.get(id)?.importance ?? "") ?? 0));
  const number = (risk: Risk): number => Number(risk.id.slice(2));
  const rebuilt = [...risks].sort(
    (a, b) =>
      b.likelihood * b.impact - a.likelihood * a.impact ||
      importance(b) - importance(a) ||
      number(a) - number(b),
  );
  const rankProblems: string[] = [];
  if (table.length !== rebuilt.length) {
    rankProblems.push(`the table has ${table.length} rows; the strategy has ${rebuilt.length} risks`);
  }
  rebuilt.forEach((risk, i) => {
    const expected = [
      String(i + 1),
      risk.id,
      risk.requirements.join(", "),
      String(risk.likelihood),
      String(risk.impact),
      String(risk.likelihood * risk.impact),
      risk.layer,
    ];
    const row = table[i];
    if (row === undefined || row.join(" | ") !== expected.join(" | ")) {
      rankProblems.push(`rank ${i + 1} should be | ${expected.join(" | ")} |, the table has ${row ? `| ${row.join(" | ")} |` : "no row"}`);
    }
  });
  check(
    risks.length > 0 && rankProblems.length === 0,
    `the ranking rebuilt from the stated scales matches the table (${table.length} rows)`,
    rankProblems,
  );

  // The totals paragraph under the table must agree with the risks. If it goes on to say every
  // requirement has a tested risk, that must be the exact sentence below, and it must be true.
  const actualTotals = LAYERS.map((layer) => `${risks.filter((r) => r.layer === layer).length} ${layer}`).join(", ");
  const firstId = requirements[0]?.id ?? "";
  const lastId = requirements[requirements.length - 1]?.id ?? "";
  const claim = `Every requirement from ${firstId} to ${lastId} has at least one tested risk.`;
  const untestedOnly = requirements.filter(
    (requirement) => !risks.some((r) => r.requirements.includes(requirement.id) && r.layer !== "untested"),
  );
  const totalsProblems: string[] = [];
  if (totals !== actualTotals) totalsProblems.push(`the table says: ${totals ?? "no totals paragraph"}`);
  if (strategy.totalsClaim !== null && strategy.totalsClaim !== claim) {
    totalsProblems.push(`the sentence after the totals should be exactly: ${claim}`);
  } else if (strategy.totalsClaim !== null && untestedOnly.length > 0) {
    totalsProblems.push(
      `it says every requirement has a tested risk, but these have none: ${untestedOnly.map((r) => r.id).join(", ")}`,
    );
  }
  check(
    totalsProblems.length === 0,
    `the totals under the table match the risks (${actualTotals})` +
      (strategy.totalsClaim === null ? "" : " and the sentence after them is true"),
    totalsProblems,
  );

  const failed = out.some((line) => line.startsWith("FAIL"));
  out.push(failed ? "RESULT: FAILED" : "RESULT: PASSED");
  console.log(out.join("\n"));
  return failed ? 1 : 0;
}

try {
  process.exitCode = main(process.argv.slice(2));
} catch (error) {
  // Anything unexpected is reported as "couldn't check" (2), never as an ordinary FAIL (1).
  console.error(`risk-strategy-check ${VERSION}: stopped unexpectedly: ${error instanceof Error ? error.message : String(error)}`);
  process.exitCode = 2;
}
