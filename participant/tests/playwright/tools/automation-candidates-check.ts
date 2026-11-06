// automation-candidates-check: checks the Tixly automation decisions against their criteria.
//
// Reads three files:
//   participant/context/playwright/automation-criteria.md  the criteria and the decision rule
//   participant/context/playwright/candidate-decisions.md  the ideas and my decision on each
//   participant/context/playwright/second-person-decisions.md  a second person's decisions
// and the brief the second person was given (participant/context/playwright/second-person-brief.md),
// and checks that:
//   - there are at least twelve ideas, each with one decision (automate, manual or drop), a reason
//     and its answers to the criteria;
//   - every decision is the one the written rule gives for those answers, at the step it names, so
//     the criteria are used consistently;
//   - at least three ideas are not automated;
//   - every manual idea says how it will be checked instead, and no other idea does;
//   - no decision rests on how easy a test is to automate alone: every rule step that decides
//     automate or manual names a criterion other than cost;
//   - the brief gives the second person the criteria and rule word for word and each idea's facts
//     exactly as decided, with none of my answers, decisions or reasons;
//   - a second person decided at least six of the ideas independently, and reports the share that
//     match mine (the quest asks for at least three of every four).
//
// The rule is read from the criteria file, not built into this script, so the check applies the
// rule as written. The files are read against an allowlist: every heading, entry and field must be
// in the exact form the format allows, and markup that would make the rendered page differ from
// the text (HTML, comments, escapes, links, code fences) is refused.
//
// It checks that the decisions follow from the criteria, not that the answers are right: whether
// an idea really is stable or valuable is for the person reading the facts.
//
// Run from the repository root (Node 22.18 or later runs TypeScript directly, nothing to install):
//   node participant/tests/playwright/tools/automation-candidates-check.ts
// Optional: --criteria <path> --decisions <path> --brief <path> --second <path>
// Exit status: 0 passed, 1 failed, 2 a required file couldn't be read or the arguments were wrong.

import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const VERSION = "1.0.0";
const DEFAULT_CRITERIA = "participant/context/playwright/automation-criteria.md";
const DEFAULT_DECISIONS = "participant/context/playwright/candidate-decisions.md";
const DEFAULT_SECOND = "participant/context/playwright/second-person-decisions.md";
const DEFAULT_BRIEF = "participant/context/playwright/second-person-brief.md";

const DECISIONS = ["automate", "manual", "drop"] as const;
type Decision = (typeof DECISIONS)[number];
const MIN_IDEAS = 12;
const MIN_NOT_AUTOMATED = 3;
const MIN_SECOND = 6;
// The quest's bar: the second person reaches the same decision for at least three of every four.
const MIN_MATCH_SHARE = 3 / 4;
const MIN_REASON_WORDS = 8;
// The most answer combinations the cost-only check will work through (six criteria give 96).
const MAX_COMBINATIONS = 100000;
// The criterion that measures how easy a test is to automate. No deciding step may rest on it alone.
const EASE_CRITERION = "Cost";

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
// fences, tables, and lines that underline the line above into a heading or draw a rule. None of
// it is part of the format, so nothing in these files can be hidden from, or disguised to, a reader.
const HIDING = /[<>&\\[\]|]|^ {0,3}(?:```|~~~|=+ *$|-{2,} *$|(?:[-*_] *){3,}$)/;

// The only list form the format uses is "- " at the very start of a line. Any other list marker
// ("*", "+", a number, or an indented "-") would show as a list item the check doesn't read.
const OTHER_LIST = /^\s*(?:[*+]|\d+[.)])\s|^\s+-\s/;

// The field names entries use. A line with one of them belongs inside an entry; anywhere else it is
// an entry in the wrong place, and is reported rather than dropped with the surrounding prose.
const ENTRY_FIELD = new RegExp(
  "^- \\*\\*(?:Question|Answers|If|Then|Idea|Facts|Criteria|Decision|Rule step|Reason|Checked instead):\\*\\*",
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
      problem(`${path} line ${index + 1}: contains markup the format doesn't allow (HTML, <, >, &, \\, [ ], |, a code fence or a heading underline)`);
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

interface Section {
  start: number;
  lines: string[];
}

// Splits a file into its sections. The file must open with one "# " title, then have exactly the
// given "## " sections in order; "### " entries may appear only in the entry sections. Any other
// heading, or an entry field outside an entry, is reported, so nothing written in an unexpected
// form is silently left out of the check.
function sections(
  path: string,
  lines: string[],
  expected: string[],
  entrySections: string[],
): Map<string, Section> {
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
      } else if (level === 2 && expected.includes(text)) {
        if (found.has(text)) problem(`${path}: the section "${text}" appears more than once`);
        name = text;
        inEntry = false;
        current = { start: index + 2, lines: [] };
        found.set(text, current);
        order.push(text);
      } else if (level === 3 && entrySections.includes(name)) {
        inEntry = true;
        current?.lines.push(line);
      } else {
        problem(`${at}: "${line}" is not a heading this file's format allows here`);
      }
      return;
    }
    if (current) current.lines.push(line);
  });
  if (!titled) problem(`${path}: the file should open with a "# " title`);
  if (order.join("\n") !== expected.join("\n")) {
    problem(`${path}: the sections should be exactly these, in this order: ${expected.map((s) => `"${s}"`).join(", ")}`);
  }
  return found;
}

interface Entry {
  id: string;
  line: number;
  fields: string[];
}

// Splits a section into "### ID" entries. A heading or a list line before the first entry is an
// entry in the wrong form, so it is reported rather than read as introduction.
function entries(path: string, section: Section, idPattern: RegExp): Entry[] {
  const result: Entry[] = [];
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
    } else if (line.trim() !== "" && /^\s*(#|- )/.test(line)) {
      problem(`${path} line ${lineNumber}: "${line}" is before the first entry heading`);
    }
  });
  const seen = new Set<string>();
  for (const entry of result) {
    if (seen.has(entry.id)) problem(`${path} ${entry.id} (line ${entry.line}): the id is used more than once`);
    seen.add(entry.id);
  }
  return result;
}

// Reads an entry's fields in order. Required fields must be present and non-empty; an optional
// field may be left out. Any line that isn't the next expected field is reported.
function readFields(
  where: string,
  entry: Entry,
  names: { name: string; optional?: boolean }[],
): Map<string, string> {
  const values = new Map<string, string>();
  let i = 0;
  for (const { name, optional } of names) {
    const value = field(entry.fields[i], name);
    if (value !== null) {
      values.set(name, value);
      i += 1;
    } else if (!optional) {
      problem(`${where}: expected the field "- **${name}:** ..." with a value`);
      if (entry.fields[i] !== undefined && !ENTRY_FIELD.test(entry.fields[i] ?? "")) i += 1;
    }
  }
  for (const extra of entry.fields.slice(i)) {
    problem(`${where}: "${extra}" is not a field this entry allows here`);
  }
  return values;
}

function words(text: string): number {
  return text.split(/\s+/).filter((word) => /\p{L}/u.test(word)).length;
}

// ---- The criteria and the rule ----

interface Criterion {
  id: string;
  name: string;
  answers: string[];
}

// One condition of a rule step: "C4 is yes" or "C5 is 3 or 2".
interface Clause {
  criterion: string;
  values: string[];
}

interface Step {
  id: string;
  clauses: Clause[] | null; // null: "none of the steps above applies"
  then: Decision;
}

const CRITERIA_SECTIONS = ["The criteria", "The decision rule", "Why the rule is in this order"];

function readCriteria(path: string): { criteria: Criterion[]; steps: Step[]; text: string } {
  const lines = readLines(path, "criteria");
  const found = sections(path, lines, CRITERIA_SECTIONS, ["The criteria", "The decision rule"]);
  const text = sectionText(found, ["The criteria", "The decision rule"]);
  const criteria: Criterion[] = [];
  const criteriaSection = found.get("The criteria");
  if (criteriaSection) {
    for (const entry of entries(path, criteriaSection, /^C\d+ \S.*$/)) {
      const where = `${path} ${entry.id} (line ${entry.line})`;
      const match = /^(C\d+) (\S.*)$/.exec(entry.id);
      const values = readFields(where, entry, [{ name: "Question" }, { name: "Answers" }]);
      const answers = (values.get("Answers") ?? "").split(", ").filter((a) => a !== "");
      if (new Set(answers).size !== answers.length || answers.length < 2) {
        problem(`${where}: "Answers" should list at least two different answers, separated by ", "`);
      }
      if (match?.[1] && match[2]) criteria.push({ id: match[1], name: match[2], answers });
    }
  }
  criteria.forEach((criterion, i) => {
    if (criterion.id !== `C${i + 1}`) problem(`${path}: criterion ${criterion.id} should be C${i + 1}, numbered in order`);
  });
  if (criteria.length === 0) problem(`${path}: no criteria found`);

  const steps: Step[] = [];
  const ruleSection = found.get("The decision rule");
  if (ruleSection) {
    const ruleEntries = entries(path, ruleSection, /^D\d+$/);
    ruleEntries.forEach((entry, index) => {
      const where = `${path} ${entry.id} (line ${entry.line})`;
      if (entry.id !== `D${index + 1}`) problem(`${where}: steps should be numbered D1, D2, ... in order`);
      const values = readFields(where, entry, [{ name: "If" }, { name: "Then" }]);
      const then = values.get("Then") ?? "";
      if (!(DECISIONS as readonly string[]).includes(then)) {
        problem(`${where}: "Then" should be exactly one of ${DECISIONS.join(", ")}`);
      }
      const condition = values.get("If") ?? "";
      let clauses: Clause[] | null = null;
      if (condition === "none of the steps above applies") {
        if (index !== ruleEntries.length - 1) problem(`${where}: "none of the steps above applies" should be the last step`);
      } else {
        clauses = parseCondition(where, condition, criteria);
      }
      steps.push({ id: entry.id, clauses, then: then as Decision });
    });
  }
  if (steps.length === 0) problem(`${path}: no decision rule found`);
  else if (steps[steps.length - 1]?.clauses !== null) {
    problem(`${path}: the rule's last step should be "none of the steps above applies", so every idea gets a decision`);
  }
  return { criteria, steps, text };
}

// "C4 is yes, C5 is 3 or 2, and C6 is low": clauses joined by ", " with "and " before the last.
function parseCondition(where: string, condition: string, criteria: Criterion[]): Clause[] {
  const parts = condition.split(", ").map((part, i, all) => (i === all.length - 1 && all.length > 1 ? part.replace(/^and /, "") : part));
  const clauses: Clause[] = [];
  for (const part of parts) {
    const match = /^(C\d+) is (\S+(?: or \S+)*)$/.exec(part);
    const criterion = criteria.find((c) => c.id === match?.[1]);
    if (!match?.[1] || !match[2] || !criterion) {
      problem(`${where}: "${part}" is not a condition in the form "Cn is answer" for a listed criterion`);
      continue;
    }
    const values = match[2].split(" or ");
    for (const value of values) {
      if (!criterion.answers.includes(value)) {
        problem(`${where}: "${value}" is not one of ${criterion.id}'s answers (${criterion.answers.join(", ")})`);
      }
    }
    if (criterion.answers.every((answer) => values.includes(answer))) {
      problem(`${where}: "${part}" allows every answer of ${criterion.id}, so it doesn't narrow the step`);
    }
    clauses.push({ criterion: match[1], values });
  }
  if (clauses.length > 1 && !/, and \S/.test(condition)) {
    problem(`${where}: join the last two conditions with ", and "`);
  }
  return clauses;
}

// Applies the rule to one idea's answers: the first step whose conditions all hold. A step with a
// condition the answers already make false is skipped, whatever else it needs. A step that could
// still apply but needs a criterion the idea didn't answer can't be decided, and is reported.
function applyRule(
  steps: Step[],
  answers: Map<string, string>,
): { step: Step | null; missing: string | null } {
  for (const step of steps) {
    if (step.clauses === null) return { step, missing: null };
    let knownFalse = false;
    let missing: string | null = null;
    for (const clause of step.clauses) {
      const answer = answers.get(clause.criterion);
      if (answer === undefined) missing = missing ?? clause.criterion;
      else if (!clause.values.includes(answer)) knownFalse = true;
    }
    if (knownFalse) continue;
    if (missing !== null) return { step: null, missing: `${step.id} needs ${missing}` };
    return { step, missing: null };
  }
  return { step: null, missing: "no step applies" };
}

// ---- The decisions ----

interface Idea {
  id: string;
  idea: string;
  facts: string;
  answers: Map<string, string>;
  decision: string;
  step: string;
  reason: string;
  instead: string | null;
}

function readDecisions(path: string, criteria: Criterion[]): Idea[] {
  const lines = readLines(path, "decisions");
  const found = sections(path, lines, ["Decisions"], ["Decisions"]);
  const ideas: Idea[] = [];
  const section = found.get("Decisions");
  if (!section) return ideas;
  for (const entry of entries(path, section, /^I-\d{2}$/)) {
    const where = `${path} ${entry.id} (line ${entry.line})`;
    const values = readFields(where, entry, [
      { name: "Idea" },
      { name: "Facts" },
      { name: "Criteria" },
      { name: "Decision" },
      { name: "Rule step" },
      { name: "Reason" },
      { name: "Checked instead", optional: true },
    ]);
    ideas.push({
      id: entry.id,
      idea: values.get("Idea") ?? "",
      facts: values.get("Facts") ?? "",
      answers: readAnswers(where, values.get("Criteria") ?? "", criteria),
      decision: values.get("Decision") ?? "",
      step: values.get("Rule step") ?? "",
      reason: values.get("Reason") ?? "",
      instead: values.get("Checked instead") ?? null,
    });
  }
  return ideas;
}

// "C1 yes; C2 yes; C3 no": answers in criterion order, from C1, with no gaps.
function readAnswers(where: string, text: string, criteria: Criterion[]): Map<string, string> {
  const answers = new Map<string, string>();
  const parts = text === "" ? [] : text.split("; ");
  parts.forEach((part, i) => {
    const criterion = criteria[i];
    const match = /^(C\d+) (\S+)$/.exec(part);
    if (!criterion || !match?.[1] || !match[2] || match[1] !== criterion.id) {
      problem(`${where}: criteria answers should run C1, C2, ... in order, each as "Cn answer", separated by "; "`);
      return;
    }
    if (!criterion.answers.includes(match[2])) {
      problem(`${where}: "${match[2]}" is not one of ${criterion.id}'s answers (${criterion.answers.join(", ")})`);
      return;
    }
    answers.set(match[1], match[2]);
  });
  return answers;
}

// ---- The brief ----

const BRIEF_SECTIONS = ["How to take part", "The criteria", "The decision rule", "The test ideas"];
// Field labels that would give the second person my answers. None may appear in the brief.
const ANSWER_FIELDS = /^- \*\*(?:Criteria|Decision|Rule step|Reason|Checked instead):\*\*/;

interface Brief {
  criteriaText: string;
  ideas: Map<string, { idea: string; facts: string }>;
}

// The brief's criteria and rule sections, joined, so they can be compared with the criteria file's.
function sectionText(found: Map<string, Section>, names: string[]): string {
  return names
    .map((name) => (found.get(name)?.lines ?? []).join("\n").trim())
    .join("\n\n");
}

function readBrief(path: string): Brief {
  const lines = readLines(path, "brief");
  // An idea number together with a decision or a criterion answer ("C2 no") in one line gives an
  // answer away. Formatting characters are removed first, so "d*r*op" reads as "drop".
  const answer = String.raw`(?:automate|manual|drop|C\d+:? (?:yes|no|low|high|[1-3]))`;
  const pairRule = new RegExp(String.raw`\bI-\d{2}\b.*\b${answer}\b|\b${answer}\b.*\bI-\d{2}\b`, "i");
  const plain = (line: string): string => line.replace(/[*_`~]/g, "");
  let inEntry = false;
  lines.forEach((line, index) => {
    const at = `${path} line ${index + 1}`;
    if (ANSWER_FIELDS.test(line)) problem(`${at}: the brief must not give my answers ("${line}")`);
    if (line.startsWith("## ")) inEntry = false;
    if (line.startsWith("### ")) inEntry = true;
    if (pairRule.test(plain(line))) {
      problem(`${at}: the brief must not show an answer (a decision or a criterion answer) next to an idea number`);
    }
    if (!inEntry && !line.startsWith("### ")) {
      // Outside the entries the brief is prose and headings (its title and section names). A list
      // line there could carry an answer under any label, and an idea number there could be paired
      // with a decision anywhere else, so neither is allowed: idea numbers belong only in the idea
      // entries and their "### " headings.
      if (/^\s*-\s/.test(line)) problem(`${at}: a list line outside an entry ("${line}")`);
      if (/\bI-\d{2}\b/i.test(plain(line))) problem(`${at}: the brief's prose and headings must not name an idea ("${line}")`);
    }
  });
  const found = sections(path, lines, BRIEF_SECTIONS, ["The criteria", "The decision rule", "The test ideas"]);
  const ideas = new Map<string, { idea: string; facts: string }>();
  const section = found.get("The test ideas");
  if (section) {
    for (const entry of entries(path, section, /^I-\d{2}$/)) {
      const where = `${path} ${entry.id} (line ${entry.line})`;
      const values = readFields(where, entry, [{ name: "Idea" }, { name: "Facts" }]);
      ideas.set(entry.id, { idea: values.get("Idea") ?? "", facts: values.get("Facts") ?? "" });
    }
  }
  return { criteriaText: sectionText(found, ["The criteria", "The decision rule"]), ideas };
}

// ---- The second person ----

interface Second {
  who: string;
  givenOk: boolean;
  date: string;
  given: string;
  decisions: Map<string, string>;
}

function readSecond(path: string, briefPath: string): Second {
  const lines = readLines(path, "second person's decisions");
  const found = sections(path, lines, ["About", "Decisions"], ["Decisions"]);
  const about = found.get("About");
  const info = new Map<string, string>();
  if (about) {
    const fields = about.lines.filter((line) => line.trim() !== "");
    const names = ["Second person", "Decided on", "Given"];
    if (fields.length !== names.length) problem(`${path}: "About" should have exactly the fields ${names.join(", ")}`);
    names.forEach((name, i) => {
      const value = field(fields[i], name);
      if (value === null) problem(`${path}: "About" field ${i + 1} should be "- **${name}:** ..." with a value`);
      else info.set(name, value);
    });
  }
  const decided = info.get("Decided on") ?? "";
  const given = info.get("Given") ?? "";
  // Both paths are taken from the folder the check runs in (the repository root), so the same file
  // written two ways still matches, and a different file with the same name doesn't.
  const givenOk = given !== "" && resolve(given) === resolve(briefPath);
  if (given !== "" && !givenOk) {
    problem(`${path}: "Given" should be exactly one path, that of the brief being checked (${briefPath}), and nothing else`);
  }
  if (decided !== "" && !/^\d{2}-\d{2}-\d{4}$/.test(decided)) problem(`${path}: "Decided on" should be a date as MM-DD-YYYY`);
  const decisions = new Map<string, string>();
  const section = found.get("Decisions");
  if (section) {
    for (const entry of entries(path, section, /^I-\d{2}$/)) {
      const where = `${path} ${entry.id} (line ${entry.line})`;
      const values = readFields(where, entry, [{ name: "Decision" }]);
      const decision = values.get("Decision") ?? "";
      if (!(DECISIONS as readonly string[]).includes(decision)) {
        problem(`${where}: "Decision" should be exactly one of ${DECISIONS.join(", ")}`);
      }
      decisions.set(entry.id, decision);
    }
  }
  return { who: info.get("Second person") ?? "", givenOk, date: decided, given: info.get("Given") ?? "", decisions };
}

// ---- The checks ----

function main(argv: string[]): number {
  const paths = { criteria: DEFAULT_CRITERIA, decisions: DEFAULT_DECISIONS, brief: DEFAULT_BRIEF, second: DEFAULT_SECOND };
  for (let i = 0; i < argv.length; i += 2) {
    const value = argv[i + 1];
    const option = argv[i];
    if (value === undefined || value.startsWith("--")) {
      console.error("usage: node automation-candidates-check.ts [--criteria <path>] [--decisions <path>] [--brief <path>] [--second <path>]");
      return 2;
    }
    if (option === "--criteria") paths.criteria = value;
    else if (option === "--decisions") paths.decisions = value;
    else if (option === "--second") paths.second = value;
    else if (option === "--brief") paths.brief = value;
    else {
      console.error(`unknown option ${option}`);
      return 2;
    }
  }

  let criteria: Criterion[];
  let steps: Step[];
  let criteriaText: string;
  let ideas: Idea[];
  let brief: Brief;
  try {
    ({ criteria, steps, text: criteriaText } = readCriteria(paths.criteria));
    ideas = readDecisions(paths.decisions, criteria);
    brief = readBrief(paths.brief);
  } catch (error) {
    if (error instanceof Unreadable) {
      console.error(`automation-candidates-check ${VERSION}: ${error.message}`);
      return 2;
    }
    throw error;
  }
  // The second person's file is read separately: until their answers come in, it doesn't exist,
  // and that is reported as a failed check rather than as a file that couldn't be read.
  let second: Second | null = null;
  let secondMissing: string | null = null;
  try {
    second = readSecond(paths.second, paths.brief);
  } catch (error) {
    if (!(error instanceof Unreadable)) throw error;
    secondMissing = error.message;
  }

  const out: string[] = [];
  const check = (passed: boolean, text: string, details: string[] = []): void => {
    out.push(`${passed ? "PASS" : "FAIL"}  ${text}`);
    for (const line of details) out.push(`      ${line}`);
  };
  const count = (decision: Decision) => ideas.filter((idea) => idea.decision === decision).length;

  out.push(`automation-candidates-check ${VERSION}`);
  out.push(`criteria: ${paths.criteria} (${criteria.length} criteria, ${steps.length} rule steps)`);
  out.push(`decisions: ${paths.decisions} (${ideas.length} ideas: ${DECISIONS.map((d) => `${count(d)} ${d}`).join(", ")})`);
  out.push(`brief: ${paths.brief} (${brief.ideas.size} ideas)`);
  out.push(`second person: ${paths.second}${second ? ` (${second.decisions.size} decisions)` : " (not recorded yet)"}`);

  const readProblems = problems.splice(0);
  check(readProblems.length === 0, "the files are in the expected form", readProblems);

  // Criterion 2: every idea has one decision; the quest asks for at least twelve ideas.
  const undecided = ideas.filter((idea) => !(DECISIONS as readonly string[]).includes(idea.decision));
  check(
    ideas.length >= MIN_IDEAS && undecided.length === 0,
    `there are at least ${MIN_IDEAS} ideas (${ideas.length}), each with exactly one decision of ${DECISIONS.join(", ")}`,
    undecided.map((idea) => `${idea.id}: "${idea.decision}"`),
  );

  // Criterion 3: every decision names at least one criterion, and gives a reason.
  const unnamed = ideas.filter((idea) => idea.answers.size === 0 || words(idea.reason) < MIN_REASON_WORDS);
  check(
    ideas.length > 0 && unnamed.length === 0,
    `every decision names the criteria behind it and gives a reason of at least ${MIN_REASON_WORDS} words`,
    unnamed.map((idea) => `${idea.id}: ${idea.answers.size} criteria answered, reason of ${words(idea.reason)} words`),
  );

  // Criterion 1: the criteria are used consistently: each decision is what the written rule gives.
  const inconsistent: string[] = [];
  for (const idea of ideas) {
    const { step, missing } = applyRule(steps, idea.answers);
    if (!step) {
      inconsistent.push(`${idea.id}: the rule can't decide from these answers (${missing})`);
    } else if (step.id !== idea.step || step.then !== idea.decision) {
      inconsistent.push(`${idea.id}: the rule gives ${step.then} at ${step.id}; the idea says ${idea.decision} at ${idea.step}`);
    }
  }
  check(
    ideas.length > 0 && steps.length > 0 && inconsistent.length === 0,
    "every decision is the one the written rule gives for its answers, at the step it names",
    inconsistent,
  );

  // Criterion 4: at least three ideas are not automated.
  const notAutomated = ideas.filter((idea) => idea.decision === "manual" || idea.decision === "drop");
  check(
    notAutomated.length >= MIN_NOT_AUTOMATED,
    `at least ${MIN_NOT_AUTOMATED} ideas are not automated (${notAutomated.length}: ${notAutomated.map((idea) => idea.id).join(", ") || "none"})`,
  );

  // Criterion 5: a manual decision says how it will be checked instead, and only a manual one does.
  const insteadProblems: string[] = [];
  for (const idea of ideas) {
    if (idea.decision === "manual" && (idea.instead === null || words(idea.instead) < MIN_REASON_WORDS)) {
      insteadProblems.push(`${idea.id} is manual but doesn't say, in at least ${MIN_REASON_WORDS} words, how it is checked instead`);
    } else if (idea.decision !== "manual" && idea.instead !== null) {
      insteadProblems.push(`${idea.id} is ${idea.decision} but has a "Checked instead" line`);
    }
  }
  check(
    ideas.length > 0 && insteadProblems.length === 0,
    `every manual idea says how it will be checked instead (${count("manual")} manual)`,
    insteadProblems,
  );

  // Criterion 7: no decision rests only on how easy a test is to automate. No step that decides
  // (automate, manual or drop) may be one that only cost ever decides, and the ease criterion must
  // exist.
  const ease = criteria.find((c) => c.name === EASE_CRITERION);
  // Every combination of answers, and for each step the combinations that reach it (no earlier step
  // applies), so conditions the earlier steps already settled, alone or together, are taken into
  // account.
  const holds = (clause: Clause, combo: Map<string, string>): boolean =>
    clause.values.includes(combo.get(clause.criterion) ?? "");
  let reaching: Map<string, string>[] = [new Map()];
  for (const criterion of criteria) {
    reaching = reaching.flatMap((combo) => criterion.answers.map((answer) => new Map([...combo, [criterion.id, answer]])));
    if (reaching.length > MAX_COMBINATIONS) break;
  }
  const easeOnly: Step[] = [];
  const alwaysApplies: Step[] = [];
  // Steps that decide no combination at all: earlier steps already catch everything they match.
  const unused: Step[] = [];
  if (reaching.length <= MAX_COMBINATIONS) {
    for (const step of steps) {
      if (step.clauses === null) {
        if (reaching.length === 0) unused.push(step);
        continue;
      }
      const decided = reaching.filter((combo) => (step.clauses ?? []).every((clause) => holds(clause, combo)));
      if (decided.length === 0) unused.push(step);
      const clauses = step.clauses;
      // The step decides on cost alone if, wherever its cost conditions let it apply, its other
      // conditions always hold too: then only cost ever decides whether it applies.
      const cost = clauses.filter((clause) => clause.criterion === ease?.id);
      const other = clauses.filter((clause) => clause.criterion !== ease?.id);
      const costAllows = reaching.filter((combo) => cost.every((clause) => holds(clause, combo)));
      // A step no combination can reach decides nothing, so it is neither cost-only nor always applying.
      const othersAlwaysHold =
        costAllows.length > 0 && costAllows.every((combo) => other.every((clause) => holds(clause, combo)));
      if (cost.length > 0 && othersAlwaysHold) {
        easeOnly.push(step);
      } else if (cost.length === 0 && othersAlwaysHold && step !== steps[steps.length - 1]) {
        // Not a cost question, but a step that applies to every idea reaching it leaves the steps
        // after it with nothing to decide, which is a mistake in the rule.
        alwaysApplies.push(step);
      }
      reaching = reaching.filter((combo) => !clauses.every((clause) => holds(clause, combo)));
    }
  }
  check(
    ease !== undefined && reaching.length <= MAX_COMBINATIONS && easeOnly.length === 0,
    `no rule step decides on ${EASE_CRITERION.toLowerCase()} (how easy it is to automate) alone`,
    [
      ...(ease === undefined ? [`no criterion is named "${EASE_CRITERION}"`] : []),
      ...(reaching.length > MAX_COMBINATIONS ? [`too many answer combinations to check (over ${MAX_COMBINATIONS})`] : []),
      ...easeOnly.map((step) => `${step.id} decides ${step.then} with no narrowing condition other than ${ease?.id ?? "cost"}`),
    ],
  );

  // Every step decides at least one combination of answers. A step that applies to every idea
  // reaching it leaves the steps after it unused; a step whose combinations earlier steps already
  // catch is unused itself.
  check(
    alwaysApplies.length === 0 && unused.length === 0,
    "every rule step decides at least one combination of answers, so none is left unused",
    [
      ...alwaysApplies.map((step) => `${step.id} applies to every idea that reaches it, so the steps after it can never apply`),
      ...unused.map((step) => `${step.id} decides no combination of answers: the steps before it already catch everything it matches`),
    ],
  );

  // Criterion 6, part 1: the second person decided from the same criteria and facts as I did, and
  // was not shown my answers (any answer field in the brief is reported while reading it).
  const briefProblems: string[] = [];
  if (brief.criteriaText !== criteriaText) {
    briefProblems.push("the brief's criteria and rule are not word for word the criteria file's");
  }
  const byId = new Map(ideas.map((idea) => [idea.id, idea]));
  for (const [id, given] of brief.ideas) {
    const mine = byId.get(id);
    if (!mine) briefProblems.push(`${id} is in the brief but not one of the ideas`);
    else if (given.idea !== mine.idea || given.facts !== mine.facts) {
      briefProblems.push(`${id}: the brief's idea or facts differ from the decisions file`);
    }
  }
  if (brief.ideas.size < MIN_SECOND) briefProblems.push(`the brief has ${brief.ideas.size} ideas; the quest asks for at least ${MIN_SECOND}`);
  check(
    briefProblems.length === 0,
    `the brief gives the second person the criteria word for word and ${brief.ideas.size} ideas' facts exactly as decided, with none of my answers`,
    briefProblems,
  );

  // Criterion 6, part 2: a second person's independent decisions, and the share that match mine.
  // They can only have decided ideas they were given in the brief.
  const secondProblems: string[] = [];
  const compared: string[] = [];
  let matches = 0;
  if (!second) {
    secondProblems.push(`not recorded yet (${secondMissing ?? "no file"})`);
  } else {
    // The comparison only counts if the second person decided from the brief, and nothing else.
    if (!second.givenOk) secondProblems.push(`not decided from the brief alone (given: ${second.given || "not stated"})`);
    const known = new Map(ideas.map((idea) => [idea.id, idea]));
    for (const [id, decision] of second.decisions) {
      const mine = known.get(id);
      if (!mine) {
        secondProblems.push(`${id} is not one of the ideas`);
        continue;
      }
      if (!brief.ideas.has(id)) secondProblems.push(`${id} wasn't in the brief, so it couldn't have been decided from it`);
      const same = mine.decision === decision;
      if (same) matches += 1;
      compared.push(`${id}: theirs ${decision}, mine ${mine.decision}${same ? "" : "  (differs)"}`);
    }
    if (second.decisions.size < MIN_SECOND) {
      secondProblems.push(`${second.decisions.size} decisions; the quest asks for at least ${MIN_SECOND}`);
    }
  }
  const total = compared.length;
  const share = total === 0 ? 0 : matches / total;
  const sharePassed = total >= MIN_SECOND && share >= MIN_MATCH_SHARE;
  check(
    secondProblems.length === 0 && sharePassed,
    second && total > 0
      ? `a second person decided ${total} ideas independently; ${matches} of ${total} match mine (${Math.round(share * 100)}%; the quest asks for at least 75%)`
      : "a second person's independent decisions on at least six ideas",
    [
      ...(second ? [`decided by ${second.who} on ${second.date}, given ${second.given}`] : []),
      ...secondProblems,
      ...compared,
    ],
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
  console.error(`automation-candidates-check ${VERSION}: stopped unexpectedly: ${error instanceof Error ? error.message : String(error)}`);
  process.exitCode = 2;
}
