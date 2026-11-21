// Checks the decision log for the context-decision-log quest, one acceptance criterion at a time,
// and builds its "Current decisions" view. It reads three files in one folder (default
// participant/context/decisions): log.md (the entries), rules.md (who may approve what) and
// sources.md (the written records the entries cite, and the work items).
//
//   node participant/tools/decision-check.mjs [--dir <folder>] [--previous <earlier log.md>]
//                                             [--write-view | --print-view]
//
//   --previous   also checks that the log was only added to since that earlier copy: its entries
//                are still the first ones, in the same order, each with the same lines in the same
//                order, and the only lines added to them are "Became" and "Replaced by".
//   --write-view writes log.md.new: log.md with the Current decisions list (only the lines between
//                its two markers) rebuilt from the entries, every other byte, line ending and the
//                file's permissions kept. Only if every check of the entries, sources and work
//                items passes. The checker never replaces log.md: it prints the SHA-256 of the
//                log.md it read, and a person moves log.md.new into place after checking log.md
//                still has that SHA-256 (otherwise they run --write-view again).
//   --print-view prints the list the entries call for, without checking or writing anything.
//
// An approval is a line in a source, "- Approved by <name> (area: <area>[; promotes: P-nn]
// [; replaces: D-nn]): <words>". The record, not the log entry, says what the approval covers: an
// entry must agree with its record's approver, area, promoted proposal, replaced decision and date.
// The list shows each decision's approved words, so what is shown as decided is what was approved.
//
// The three files must be valid UTF-8 and use only simple Markdown: headings at the start of a line,
// text, "- " bullets, "|" tables and inline code (plus, in log.md, the two marker comments).
// Anything else (code blocks, indented lines, underlined headings, quote blocks, HTML, other
// comments) is reported, not interpreted (fail closed), so a reader and the checker can't see
// different things. Comments and code are still set aside when reading, as a second guard.
//
// Exit codes: 0 every check passed, 1 at least one problem, 2 a file couldn't be read or the
// arguments were wrong.

import { createHash } from "node:crypto";
import { closeSync, openSync, readFileSync, statSync, unlinkSync, writeSync } from "node:fs";
import { basename, isAbsolute, join } from "node:path";

const usage = () => {
  console.error("Usage: node participant/tools/decision-check.mjs [--dir <folder>] [--previous <earlier log.md>] [--write-view | --print-view]");
  process.exit(2);
};
let dir = "participant/context/decisions";
let previous = null;
let mode = "check";
const args = process.argv.slice(2);
for (let i = 0; i < args.length; i++) {
  if (args[i] === "--dir" && i + 1 < args.length) dir = args[++i];
  else if (args[i] === "--previous" && i + 1 < args.length) previous = args[++i];
  else if ((args[i] === "--write-view" || args[i] === "--print-view") && mode === "check") mode = args[i].slice(2);
  else usage();
}
// Folders are shown as given, except an absolute one (it could show this computer's folders).
const shownDir = isAbsolute(dir) ? `(folder ${basename(dir)})` : dir;
const utf8 = new TextDecoder("utf-8", { fatal: true, ignoreBOM: true });
const readRaw = (path, what) => {
  let bytes;
  try {
    bytes = readFileSync(path);
  } catch {
    console.error(`Couldn't read ${what}.`);
    process.exit(2);
  }
  let text;
  try {
    text = utf8.decode(bytes);
  } catch {
    console.error(`${what} is not valid UTF-8 text; nothing was checked or written.`);
    process.exit(2);
  }
  // Lines end in LF or CRLF; a lone CR (an old Mac line break) would be a line break to some
  // readers and not to this checker, so it is refused.
  if (/\r(?!\n)/.test(text)) {
    console.error(`${what} has a carriage return that isn't followed by a line feed; nothing was checked or written.`);
    process.exit(2);
  }
  return text;
};

// ---- Markdown in context ----------------------------------------------------------------------
// Inline code spans as Markdown reads them: a run of backticks, then text, then a run of exactly the
// same length (``a|b`` as well as `a`). `blank` replaces each span, keeping or dropping its length.
// A backslash before a backtick makes it a plain character, so it never opens a span.
const CODE_SPAN = /(?<![`\\])(`+)(?!`)([\s\S]*?[^`])\1(?!`)/g;
const maskCode = (line, keepLength) => line.replace(CODE_SPAN, (m) => (keepLength ? " ".repeat(m.length) : ""));
// Each line of the text (split on LF; a CR before it is dropped) with its kind: "text", "code"
// (fenced or indented) or "comment". Code and comment lines are not part of the record.
const classify = (raw) => {
  const lines = raw.split("\n").map((l) => l.replace(/\r$/, ""));
  const out = [];
  let fence = null;
  let comment = false;
  let indented = false; // inside an indented code block
  let prevBlank = true;
  for (const line of lines) {
    const blank = line.trim() === "";
    if (fence) {
      out.push({ line: "", kind: "code" });
      const close = /^ {0,3}(`{3,}|~{3,})\s*$/.exec(line);
      if (close && close[1][0] === fence[0] && close[1].length >= fence.length) fence = null;
      prevBlank = false;
      continue;
    }
    // Indented code: a line indented four spaces (or a tab) after a blank line, and every line
    // after it that is indented or blank, until a line that isn't.
    if (!comment && /^( {4}|\t)/.test(line) && !blank && (prevBlank || indented)) {
      indented = true;
      out.push({ line: "", kind: "code" });
      prevBlank = false;
      continue;
    }
    if (indented && !blank) indented = false;
    const open = !comment && /^ {0,3}(`{3,}|~{3,})/.exec(line);
    if (open) {
      fence = open[1];
      out.push({ line: "", kind: "code" });
      prevBlank = false;
      continue;
    }
    // Comments: every "<!--" and "-->" on the line, in order. What is outside them stays.
    // Comment delimiters are found on a masked copy, where inline code (outside a comment) is
    // blanked so a "<!--" inside backticks opens nothing; the text kept is always cut from the
    // original line, character for character.
    const masked = maskCode(line, true);
    let visible = "";
    let at = 0;
    let touched = comment;
    while (at < line.length) {
      if (comment) {
        const close = line.indexOf("-->", at);
        if (close === -1) at = line.length;
        else {
          at = close + 3;
          comment = false;
        }
      } else {
        const openAt = masked.indexOf("<!--", at);
        if (openAt === -1) {
          visible += line.slice(at);
          at = line.length;
        } else {
          visible += line.slice(at, openAt);
          at = openAt + 4;
          comment = true;
          touched = true;
        }
      }
    }
    // A line any part of which was a comment is kept apart from the record's own lines: its visible
    // text isn't what was written there, word for word.
    if (touched && visible.trim() === "") out.push({ line: "", kind: "comment", raw: line });
    else out.push({ line: visible, kind: touched ? "mixed" : "text" });
    prevBlank = blank;
  }
  return out;
};
// Fail closed: the three files may use only simple Markdown (headings starting at the beginning of
// a line, text, "- " bullets, "|" tables, inline code), and in log.md the two marker comments.
// Anything else (code blocks, indented or tab-indented lines, headings not at the start of the
// line, underlined headings, HTML or other comments) is reported rather than interpreted, so no
// Markdown corner case can make a reader and the checker see different things.
const lint = (raw, file, markers) => {
  const problems = [];
  raw.split("\n").forEach((l, i) => {
    const line = l.replace(/\r$/, "");
    const where = `${file} line ${i + 1}`;
    const masked = maskCode(line, false); // inline code is text, whatever it holds
    if (/^ {0,3}(`{3,}|~{3,})/.test(line)) problems.push(`${where}: code blocks aren't used in the decision files`);
    else if (line.includes("\\`")) problems.push(`${where}: an escaped backtick (\\\`) isn't used in the decision files (it changes what counts as code)`);
    else if (/^ *\t/.test(line)) problems.push(`${where}: a tab at the start of a line (it can turn a line into code)`);
    else if (/^ {4,}\S/.test(line)) problems.push(`${where}: a line indented four or more spaces (that is code in Markdown)`);
    else if (/^ {1,3}#/.test(line)) problems.push(`${where}: a heading must start at the beginning of the line`);
    else if (/^ {0,3}>/.test(line)) problems.push(`${where}: quote blocks (">") aren't used in the decision files`);
    else if (/^ {0,3}(=+|-+|(\* *){3,}|(_ *){3,})\s*$/.test(line)) problems.push(`${where}: underlined headings and horizontal rules aren't used in the decision files`);
    else if (masked.includes("<!--") || masked.includes("-->")) {
      if (!(markers && (line.trim() === START || line.trim() === END))) problems.push(`${where}: comments aren't used in the decision files (only the two current-decisions markers in log.md)`);
    } else if (/<[A-Za-z!?\/]/.test(masked)) problems.push(`${where}: HTML isn't used in the decision files`);
    else if (/^#{1,6}(\t|$)/.test(line) || /^#{1,6} +#* *$/.test(line)) problems.push(`${where}: a heading needs a space and a title after its #'s`);
    // Markdown also makes a table from rows without a leading "|" ("a | b" over "--- | ---"), so
    // any line with a "|" outside inline code must be a "|"-led table row, which the checks see.
    else if (/(^|[^\\])\|/.test(masked) && !line.trim().startsWith("|")) problems.push(`${where}: a line with "|" that isn't a table row starting with "|" (it could render as an unchecked table)`);
  });
  return problems;
};
const visibleLines = (classified) => classified.map((c) => (c.kind === "text" || c.kind === "mixed" ? c.line : ""));
// The lines written exactly as they are (no comment inside), for word-for-word matching.
const exactLines = (classified) => classified.map((c) => (c.kind === "text" ? c.line : ""));

const logPath = join(dir, "log.md");
const logRaw = readRaw(logPath, `${shownDir}/log.md`);
const rulesRaw = readRaw(join(dir, "rules.md"), `${shownDir}/rules.md`);
const sourcesRaw = readRaw(join(dir, "sources.md"), `${shownDir}/sources.md`);
const rulesLines = visibleLines(classify(rulesRaw));
const sourcesClassified = classify(sourcesRaw);
const sourcesLines = visibleLines(sourcesClassified);
const sourcesExact = exactLines(sourcesClassified);

// The lines under the one visible heading `<#…> <exact>`, up to the next heading of that level or
// higher. Returns { lines, start } (start: the heading's line number) or { problem }.
const section = (lines, level, exact, file) => {
  const head = `${"#".repeat(level)} ${exact}`;
  const at = lines.flatMap((l, i) => (l.trimEnd() === head ? [i] : []));
  if (at.length !== 1) return { problem: `${file} must have exactly one "${head}" heading (found ${at.length})` };
  const out = [];
  for (let i = at[0] + 1; i < lines.length; i++) {
    const m = /^ {0,3}(#{1,6})(\s|$)/.exec(lines[i]);
    if (m && m[1].length <= level) break;
    out.push(lines[i]);
  }
  return { lines: out, start: at[0] };
};
// A table row's cells: the leading "|" required, the trailing one optional, "\|" an escaped bar.
const cellsOf = (line) => {
  let t = line.trim();
  if (!t.startsWith("|")) return null;
  t = t.slice(1);
  if (/(^|[^\\])\|$/.test(t)) t = t.slice(0, -1);
  return t.split(/(?<!\\)\|/).map((c) => c.trim().replace(/\\\|/g, "|"));
};
// The rows of the section's table. Every line of the table must start with "|" (a row without one
// would show in the table but could be missed), and the table ends at a blank line.
const tableRows = (lines, what, problems, header) => {
  const rows = [];
  let state = "before"; // before, in, after the table
  for (const l of lines ?? []) {
    const t = l.trim();
    if (t === "") {
      if (state === "in") state = "after";
      continue;
    }
    if (state === "after" && t.includes("|")) {
      problems.push(`${what}: a second table, or a table line after the table ended: ${JSON.stringify(t)}`);
    } else if (t.startsWith("|") && state !== "after") {
      state = "in";
      rows.push(t);
    } else if (state === "in" || t.includes("|")) {
      problems.push(`${what}: a table line doesn't start with "|": ${JSON.stringify(t)}`);
    }
  }
  const head = rows[0] ? cellsOf(rows[0]) : null;
  if (!head || head.join("|") !== header.join("|")) problems.push(`${what}: the table's columns must be ${header.join(", ")}`);
  else if (!rows[1] || !cellsOf(rows[1]).every((c) => /^:?-{1,}:?$/.test(c)) || cellsOf(rows[1]).length !== header.length) problems.push(`${what}: the table's second line must be its divider`);
  else return rows.slice(2).map(cellsOf);
  return [];
};
const ticks = (c) => [...c.matchAll(/`([^`]+)`/g)].map((m) => m[1]);

const START = "<!-- current-decisions: start -->";
const END = "<!-- current-decisions: end -->";
const setupProblems = [...lint(logRaw, "log.md", true), ...lint(rulesRaw, "rules.md", false), ...lint(sourcesRaw, "sources.md", false)];
// rules.md: who may approve which areas.
const approvers = new Map();
const who = section(rulesLines, 2, "Who may approve", "rules.md");
if (who.problem) setupProblems.push(who.problem);
for (const row of tableRows(who.lines, 'rules.md "Who may approve"', setupProblems, ["Approver", "Role", "May approve"])) {
  if (!row[0] || row.length < 3) setupProblems.push('rules.md: a "Who may approve" row is incomplete');
  else if (approvers.has(row[0])) setupProblems.push(`rules.md lists ${row[0]} twice`);
  else if (!/^`[^`]+`( `[^`]+`)*$/.test(row[2])) setupProblems.push(`rules.md: ${row[0]}'s "May approve" must be only area names in backticks, nothing else: ${JSON.stringify(row[2])}`);
  else approvers.set(row[0], ticks(row[2]));
}
if (!approvers.size) setupProblems.push('rules.md has no approvers in its "Who may approve" table');
// A table anywhere but its one place is a list nobody checks (it could show a proposal as decided),
// so rules.md may have a table only under "Who may approve", and sources.md only under "Work items".
const tablesOnlyIn = (lines, file, sec) => {
  const inside = (i) => !sec.problem && i > sec.start && i <= sec.start + sec.lines.length;
  lines.forEach((l, i) => {
    if (l.trim().startsWith("|") && !inside(i)) setupProblems.push(`${file} line ${i + 1}: a table outside its one checked table`);
  });
};
tablesOnlyIn(rulesLines, "rules.md", who);

// sources.md: each "## ID · title, MM-DD-YYYY" section (its visible lines, as written), and the
// work-items table.
const sources = new Map();
for (let i = 0; i < sourcesLines.length; i++) {
  const m = /^## ([A-Z]+-\d+) · .+$/.exec(sourcesLines[i]);
  if (!m) continue;
  if (sources.has(m[1])) setupProblems.push(`sources.md has two sections for ${m[1]}`);
  const date = /(\d{2}-\d{2}-\d{4})\s*$/.exec(sourcesLines[i])?.[1] ?? null;
  if (!date) setupProblems.push(`sources.md: ${m[1]}'s heading doesn't end with its date (MM-DD-YYYY)`);
  const body = [];
  for (let j = i + 1; j < sourcesLines.length && !/^ {0,3}#{1,2}(\s|$)/.test(sourcesLines[j]); j++) body.push(sourcesExact[j]);
  sources.set(m[1], { date, body });
}
if (!sources.size) setupProblems.push("sources.md has no sources");
// A bullet whose next line continues it (anything but a blank line, another "- " bullet or a
// heading) reads as one longer item: an approval must be a single line, so that is reported.
// After blank lines, an indented line still belongs to the item (a further paragraph or a nested
// list), so that is reported too.
sourcesLines.forEach((l, i) => {
  if (!/^- Approved by /.test(l)) return;
  const next = sourcesLines[i + 1];
  if (next !== undefined && next.trim() !== "" && !/^- /.test(next) && !/^#{1,6}(\s|$)/.test(next)) {
    setupProblems.push(`sources.md line ${i + 2}: continues the approval on line ${i + 1}; an approval is a single line`);
    return;
  }
  let j = i + 1;
  while (j < sourcesLines.length && sourcesLines[j].trim() === "") j++;
  if (j > i + 1 && j < sourcesLines.length && /^\s/.test(sourcesLines[j])) {
    setupProblems.push(`sources.md line ${j + 1}: an indented line after the approval on line ${i + 1} still belongs to it; an approval is a single line`);
  }
});
const workItems = new Map();
const wi = section(sourcesLines, 2, "Work items", "sources.md");
if (wi.problem) setupProblems.push(wi.problem);
tablesOnlyIn(sourcesLines, "sources.md", wi);
for (const row of tableRows(wi.lines, "sources.md work items", setupProblems, ["Work item", "What it is", "Rests on"])) {
  const [id, , restsOn] = row ?? [];
  if (!/^[A-Z]+-\d+$/.test(id ?? "")) setupProblems.push(`sources.md: a work-items row has no valid ID: ${JSON.stringify(row)}`);
  else if (workItems.has(id)) setupProblems.push(`sources.md lists work item ${id} twice`);
  else {
    const rests = (restsOn ?? "").split(/\s+/).filter(Boolean);
    if (!rests.length) setupProblems.push(`work item ${id} names no decision it rests on`);
    workItems.set(id, rests);
  }
}

// An approval line, split into its parts: { approver, tags: Map, words } or null.
const parseApproval = (line) => {
  const m = /^Approved by (.+?) \(([^()]*)\): (.*\S.*)$/.exec(line);
  if (!m) return null;
  const tags = new Map();
  for (const part of m[2].split(";")) {
    const t = /^\s*(area|promotes|replaces): (.+?)\s*$/.exec(part);
    if (!t || tags.has(t[1])) return null;
    tags.set(t[1], t[2]);
  }
  return tags.has("area") ? { approver: m[1], tags, words: m[3] } : null;
};

// log.md: the entries under "## Entries", each "### ID · title" with "- Field: value" lines.
const FIELDS = {
  decision: { required: ["Status", "Date", "Source", "Area", "Approver", "Approval"], optional: ["Affects", "From", "Replaces", "Replaced by", "Note"] },
  proposal: { required: ["Status", "Date", "Source", "Proposed by"], optional: ["Became", "Note"] },
  question: { required: ["Status", "Date", "Source", "Asked by"], optional: ["Note"] },
};
const PREFIX = { decision: "D", proposal: "P", question: "Q" };
// `raw` is the whole text as written; each entry keeps its non-blank lines exactly as written
// (comments included), for the history check.
const parseEntries = (raw, problems, file) => {
  const cl = classify(raw);
  const lines = visibleLines(cl);
  const rawLines = raw.split("\n").map((l) => l.replace(/\r$/, ""));
  const entries = [];
  const sec = section(lines, 2, "Entries", file);
  if (sec.problem) {
    problems.push(sec.problem);
    return entries;
  }
  // An entry-shaped heading anywhere else would be seen by readers but never checked.
  lines.forEach((l, i) => {
    const inside = i > sec.start && i <= sec.start + sec.lines.length;
    if (!inside && /^ {0,3}#{1,6} +[DPQ]-\d+ · /.test(l)) problems.push(`${file}: an entry heading outside "## Entries": ${JSON.stringify(l.trim())}`);
  });
  let cur = null;
  sec.lines.forEach((line, k) => {
    const n = sec.start + 1 + k;
    if (cur && rawLines[n].trim() !== "" && !/^### /.test(line)) cur.raw.push(rawLines[n]);
    const h = /^### (\S+) · (.+)$/.exec(line);
    if (h) {
      cur = { id: h[1], title: h[2].trim(), fields: new Map(), lines: [], raw: [rawLines[n]] };
      entries.push(cur);
      return;
    }
    if (/^ {0,3}#{1,6}(\s|$)/.test(line)) {
      problems.push(`${file}: a heading inside "## Entries" that isn't an entry: ${JSON.stringify(line.trim())}`);
      cur = null;
      return;
    }
    if (line.trim() === "") return;
    if (!cur) {
      problems.push(`${file}: a line before the first entry: ${JSON.stringify(line)}`);
      return;
    }
    const f = /^- ([A-Za-z ]+?):(?: (.*))?$/.exec(line);
    if (!f) {
      problems.push(`${cur.id}: a line that isn't "- Field: value": ${JSON.stringify(line)}`);
      return;
    }
    const value = (f[2] ?? "").trim();
    if (cur.fields.has(f[1])) problems.push(`${cur.id}: "${f[1]}" is given twice`);
    if (value === "") problems.push(`${cur.id}: "${f[1]}" is empty`);
    cur.fields.set(f[1], value);
    cur.lines.push(`${f[1]}: ${value}`);
  });
  return entries;
};

// ---- the current-decisions view --------------------------------------------------------------
const status = (e) => e.fields.get("Status");
const quoteOf = (e) => /^"(.*)"$/.exec(e.fields.get("Approval") ?? "")?.[1];
const approvedWords = (e) => parseApproval(quoteOf(e) ?? "")?.words ?? quoteOf(e) ?? "";
const cell = (v) => String(v ?? "").replace(/\|/g, "\\|");
const buildView = (list) => {
  const live = list.filter((e) => status(e) === "decision" && !e.fields.has("Replaced by"));
  const rows = live.map((e) => `| ${cell(e.id)} | ${cell(approvedWords(e))} | ${cell(e.fields.get("Area"))} | ${cell(e.fields.get("Approver"))} | ${cell(e.fields.get("Date"))} | ${cell(e.fields.get("Source"))} |`);
  return ["| Decision | What was approved (the approver's words) | Area | Approved by | Date | Where |", "|---|---|---|---|---|---|", ...rows].join("\n");
};
// The view in a log's text: exactly one pair of marker comments (real comments, not inside code),
// both inside the visible "## Current decisions" section, start before end; nothing visible after
// the end marker in that section, and no table before the start marker.
const viewOf = (raw) => {
  const cl = classify(raw);
  const vis = visibleLines(cl);
  const sec = section(vis, 2, "Current decisions", "log.md");
  if (sec.problem) return { problem: sec.problem };
  const marks = (m) => cl.flatMap((c, i) => (c.kind === "comment" && c.raw.trim() === m ? [i] : []));
  const starts = marks(START);
  const ends = marks(END);
  const first = sec.start + 1;
  const last = sec.start + sec.lines.length;
  if (starts.length !== 1 || ends.length !== 1) return { problem: "log.md needs exactly one pair of current-decisions markers" };
  const [s, e] = [starts[0], ends[0]];
  if (!(first <= s && s < e && e <= last)) return { problem: 'both current-decisions markers must be inside "## Current decisions", start before end' };
  // The section holds only the generated list: anything else in it is a list nobody checks.
  for (let i = first; i <= last; i++) {
    if (i >= s && i <= e) continue;
    if (vis[i].trim() !== "") return { problem: `content in "## Current decisions" outside the generated list: ${JSON.stringify(vis[i].trim())}` };
  }
  return { start: s, end: e, inner: cl.slice(s + 1, e).map((c) => c.line).join("\n").replace(/^(\s*\n)+/, "").replace(/(\n\s*)+$/, "") };
};

const parseProblems = [];
// log.md has one title and exactly two sections, so no second "current decisions" list (or any
// other section) can sit outside the checks.
visibleLines(classify(logRaw)).forEach((l, i) => {
  const h = /^ {0,3}(#{1,2})(?:\s+(.*?))?\s*$/.exec(l);
  if (!h) return;
  const ok = h[1] === "#" ? i === visibleLines(classify(logRaw)).findIndex((x) => /^ {0,3}#(\s|$)/.test(x)) : h[2] === "Current decisions" || h[2] === "Entries";
  if (!ok) parseProblems.push(`log.md line ${i + 1}: log.md has only its title, "## Current decisions" and "## Entries"; found ${JSON.stringify(l.trim())}`);
});
{
  const vis = visibleLines(classify(logRaw));
  const cur = vis.findIndex((l) => l.trimEnd() === "## Current decisions");
  const ent = vis.findIndex((l) => l.trimEnd() === "## Entries");
  if (cur !== -1 && ent !== -1 && cur > ent) parseProblems.push('log.md: "## Current decisions" must come before "## Entries", so a reader finds it first');
  // The only table in log.md is the generated list, between its markers.
  const cl = classify(logRaw);
  const s0 = cl.findIndex((c) => c.kind === "comment" && c.raw.trim() === START);
  const e0 = cl.findIndex((c) => c.kind === "comment" && c.raw.trim() === END);
  vis.forEach((l, i) => {
    if (l.trim().startsWith("|") && !(s0 !== -1 && e0 !== -1 && i > s0 && i < e0)) parseProblems.push(`log.md line ${i + 1}: a table outside the generated Current decisions list`);
    // Above the list, no text may name an entry: a claim about a decision belongs in the checked
    // places (the list and the entries), not in prose nobody checks.
    // Compared as displayed: escapes, emphasis, entities and look-alike characters can't hide one.
    const shownAs = l.normalize("NFKC").replace(/[^A-Za-z0-9\s]/g, "");
    if (cur !== -1 && i < cur && /(^|[^A-Za-z0-9])[DPQ]\s*\d/i.test(shownAs)) parseProblems.push(`log.md line ${i + 1}: names an entry above the Current decisions list; entries are named only in the list and under "## Entries"`);
  });
}
const entries = parseEntries(logRaw, parseProblems, "log.md");
if (mode === "print-view") {
  console.log(buildView(entries));
  process.exit(0);
}

// ---- the checks of the entries, sources and work items ---------------------------------------
const byId = new Map();
const index = new Map(entries.map((e, i) => [e.id, i]));
const results = [];
const check = (title, fn) => {
  const r = { title, problems: [] };
  fn(r.problems);
  results.push(r);
  return r;
};
const validDate = (d) => {
  const m = /^(\d{2})-(\d{2})-(\d{4})$/.exec(d ?? "");
  if (!m) return null;
  const t = new Date(Date.UTC(+m[3], +m[1] - 1, +m[2]));
  return t.getUTCMonth() === +m[1] - 1 && t.getUTCDate() === +m[2] ? t.getTime() : null;
};
// True only when both dates are real and `a` is earlier than `b` (a bad date is reported by check 6).
const earlier = (a, b) => {
  const x = validDate(a);
  const y = validDate(b);
  return x !== null && y !== null && x < y;
};
const ids = (value) => (value ?? "").split(/\s+/).filter(Boolean);
const before = (a, b) => index.has(a) && index.has(b) && index.get(a) < index.get(b);
// The record a decision's approval quotes, parsed (null when it can't be found or read).
const recordOf = (e) => {
  const quote = quoteOf(e);
  const src = sources.get(e.fields.get("Source"));
  return quote !== undefined && src && src.body.includes(`- ${quote}`) ? parseApproval(quote) : null;
};

check("0. The files can be read as a log", (p) => {
  p.push(...setupProblems, ...parseProblems);
  for (const e of entries) {
    if (byId.has(e.id)) p.push(`${e.id}: the ID is used twice`);
    byId.set(e.id, e);
  }
  if (entries.length < 10) p.push(`only ${entries.length} entries; at least ten are needed`);
});

check("1. Every entry has exactly one status: decision, proposal or question", (p) => {
  for (const e of entries) {
    const s = status(e);
    if (!Object.hasOwn(FIELDS, s ?? "")) {
      p.push(`${e.id}: status ${JSON.stringify(s ?? "(none)")} is not decision, proposal or question`);
      continue;
    }
    if (!new RegExp(`^${PREFIX[s]}-\\d+$`).test(e.id)) p.push(`${e.id}: a ${s}'s ID is ${PREFIX[s]}- followed by digits`);
    for (const f of FIELDS[s].required) if (!e.fields.has(f)) p.push(`${e.id}: "${f}" is missing`);
    for (const f of e.fields.keys()) if (![...FIELDS[s].required, ...FIELDS[s].optional].includes(f)) p.push(`${e.id}: a ${s} has no "${f}" line`);
  }
});

check("2. A decision records its approver and where it was approved", (p) => {
  const usedBy = new Map(); // approval line -> decision
  for (const e of entries.filter((x) => status(x) === "decision")) {
    const person = e.fields.get("Approver");
    if (!person) {
      p.push(`${e.id}: no approver is recorded`);
      continue;
    }
    const quote = quoteOf(e);
    if (quote === undefined) {
      p.push(`${e.id}: the Approval must be the approver's line, quoted`);
      continue;
    }
    const parsed = parseApproval(quote);
    if (!parsed || parsed.approver !== person) {
      p.push(`${e.id}: the quoted line is not an approval by ${person} ("Approved by ${person} (area: …): …"); agreement is not an approval`);
      continue;
    }
    const src = sources.get(e.fields.get("Source"));
    if (src && !src.body.includes(`- ${quote}`)) p.push(`${e.id}: the approval line isn't in ${e.fields.get("Source")}, word for word`);
    // The record says what the approval covers; the entry must agree, and the approver must hold
    // that area.
    const area = parsed.tags.get("area");
    if (e.fields.get("Area") !== area) p.push(`${e.id}: Area ${JSON.stringify(e.fields.get("Area"))} doesn't match the record's area ${JSON.stringify(area)}`);
    if (!approvers.has(person)) p.push(`${e.id}: ${JSON.stringify(person)} is not in rules.md's "Who may approve" table`);
    else if (!approvers.get(person).includes(area)) p.push(`${e.id}: ${person} may not approve area ${JSON.stringify(area)}`);
    // The heading says exactly what the approval says: its title is the approved words (a capital
    // first letter and a final full stop aside), so no title can add to them or leave a qualifier out.
    const plain = (x) => {
      const t = x.trim().replace(/\.$/, "");
      return t.charAt(0).toLowerCase() + t.slice(1);
    };
    if (plain(e.title) !== plain(parsed.words)) {
      p.push(`${e.id}: its title ${JSON.stringify(e.title)} isn't the approved words ${JSON.stringify(parsed.words)}`);
    }
    // One approval backs one decision: a decision can't borrow another's approval.
    const key = `${e.fields.get("Source")}\n${quote}`;
    if (usedBy.has(key)) p.push(`${e.id}: uses the same approval as ${usedBy.get(key)}; each approval backs one decision`);
    else usedBy.set(key, e.id);
  }
});

const check3 = check("3. A proposal is never shown as a decision", (p) => {
  for (const e of entries.filter((x) => status(x) === "proposal" || status(x) === "question")) {
    for (const f of ["Approver", "Approval", "Area"]) if (e.fields.has(f)) p.push(`${e.id}: a ${status(e)} has "${f}", which only a decision has`);
  }
  for (const [item, rests] of workItems) {
    for (const id of rests) {
      const e = byId.get(id);
      if (!e) p.push(`work item ${item} rests on ${id}, which isn't in the log`);
      else if (status(e) !== "decision") p.push(`work item ${item} rests on ${id}, a ${status(e)}: work must rest on an approved decision`);
    }
  }
});

check("4. Promoting a proposal adds an entry and keeps the history", (p) => {
  for (const e of entries) {
    const from = e.fields.get("From");
    // Compared with the record only when it is a valid approval (check 2 reports one that isn't).
    const recpromotes = status(e) === "decision" ? recordOf(e) : null;
    if (recpromotes) {
      const promotes = recpromotes.tags.get("promotes");
      if (promotes !== from && (promotes || from)) p.push(`${e.id}: From ${from ?? "(none)"}, but its approval record promotes ${promotes ?? "nothing"}`);
    }
    if (from) {
      const src = byId.get(from);
      if (!src) p.push(`${e.id}: From ${from}, which isn't in the log`);
      else {
        if (status(src) !== "proposal") p.push(`${e.id}: From ${from}, which is a ${status(src)}; only a proposal is promoted`);
        if (src.fields.get("Became") !== e.id) p.push(`${e.id}: From ${from}, but ${from} doesn't say "Became: ${e.id}"`);
        if (!before(from, e.id)) p.push(`${e.id}: must come after ${from}, which it came from`);
        if (earlier(e.fields.get("Date"), src.fields.get("Date"))) p.push(`${e.id}: dated before ${from}, which it came from`);
      }
    }
    const became = e.fields.get("Became");
    if (became) {
      const to = byId.get(became);
      if (!to) p.push(`${e.id}: Became ${became}, which isn't in the log`);
      else if (to.fields.get("From") !== e.id) p.push(`${e.id}: Became ${became}, but ${became} doesn't say "From: ${e.id}"`);
    }
  }
});

check("5. A replaced decision links to the one that replaced it", (p) => {
  for (const e of entries) {
    const old = e.fields.get("Replaces");
    // Compared with the record only when it is a valid approval (check 2 reports one that isn't).
    const recreplaces = status(e) === "decision" ? recordOf(e) : null;
    if (recreplaces) {
      const replaces = recreplaces.tags.get("replaces");
      if (replaces !== old && (replaces || old)) p.push(`${e.id}: Replaces ${old ?? "(none)"}, but its approval record replaces ${replaces ?? "nothing"}`);
    }
    const by = e.fields.get("Replaced by");
    if (by) {
      const n = byId.get(by);
      if (!n || status(n) !== "decision") p.push(`${e.id}: Replaced by ${by}, which isn't a decision in the log`);
      else if (n.fields.get("Replaces") !== e.id) p.push(`${e.id}: Replaced by ${by}, but ${by} doesn't say "Replaces: ${e.id}"`);
    }
    if (old) {
      const o = byId.get(old);
      if (!o || status(o) !== "decision") p.push(`${e.id}: Replaces ${old}, which isn't a decision in the log`);
      else {
        if (o.fields.get("Replaced by") !== e.id) p.push(`${e.id}: Replaces ${old}, but ${old} doesn't say "Replaced by: ${e.id}"`);
        // Replacing a decision takes it out of force, so the approver must hold its area too.
        const oldArea = recordOf(o)?.tags.get("area");
        const person = e.fields.get("Approver");
        if (oldArea && approvers.has(person) && !approvers.get(person).includes(oldArea)) p.push(`${e.id}: replaces ${old}, an area "${oldArea}" decision, but ${person} may not approve area "${oldArea}"`);
        // A replacement comes after what it replaces: no decision replaces itself, and no loops.
        if (!before(old, e.id)) p.push(`${e.id}: must come after ${old}, which it replaces`);
        if (earlier(e.fields.get("Date"), o.fields.get("Date"))) p.push(`${e.id}: dated before ${old}, which it replaces`);
      }
    }
  }
});

check("6. Each entry cites its source (and its date)", (p) => {
  for (const e of entries) {
    const s = e.fields.get("Source");
    const d = e.fields.get("Date");
    if (s && !sources.has(s)) p.push(`${e.id}: source ${s} isn't in sources.md`);
    if (d && validDate(d) === null) p.push(`${e.id}: date ${JSON.stringify(d)} is not a real MM-DD-YYYY date`);
    else if (d && sources.get(s)?.date && sources.get(s).date !== d) p.push(`${e.id}: dated ${d}, but ${s} was recorded on ${sources.get(s).date}`);
  }
});

check("Stretch: decisions link to the work items they affect", (p) => {
  // The work-items table holds the links (a new work item is a new row; no decision is rewritten).
  // A decision's own "Affects" line is optional, and when present must agree with the table.
  for (const e of entries.filter((x) => status(x) === "decision" && x.fields.has("Affects"))) {
    const affects = ids(e.fields.get("Affects"));
    if (affects.length === 1 && affects[0] === "none") continue;
    for (const item of affects) {
      if (!workItems.has(item)) p.push(`${e.id}: affects ${item}, which isn't in the work-items table`);
      else if (!e.fields.has("Replaced by") && !workItems.get(item).includes(e.id)) p.push(`${e.id}: affects ${item}, but ${item} doesn't rest on ${e.id}`);
    }
  }
  for (const [item, rests] of workItems) {
    for (const id of rests) {
      const e = byId.get(id);
      if (e && status(e) === "decision" && e.fields.has("Replaced by")) p.push(`work item ${item} rests on ${id}, which was replaced by ${e.fields.get("Replaced by")}`);
    }
  }
});

if (previous !== null) {
  check("History: the log was only added to since the earlier copy", (p) => {
    const baseProblems = [];
    const old = parseEntries(readRaw(previous, "the earlier copy of the log"), baseProblems, "the earlier copy");
    if (baseProblems.length || !old.length || new Set(old.map((e) => e.id)).size !== old.length) {
      p.push(`the earlier copy can't be used as a baseline: ${baseProblems[0] ?? (old.length ? "an ID is used twice" : "it has no entries")}`);
      return;
    }
    // The earlier entries must still be the first ones, in the same order.
    old.forEach((o, i) => {
      const n = entries[i];
      if (!n || n.id !== o.id) {
        p.push(`entry ${i + 1} was ${o.id} and is now ${n ? n.id : "missing"}: earlier entries must stay first, in order`);
        return;
      }
      if (n.title !== o.title) p.push(`${o.id}: its title was changed`);
      // Its earlier lines exactly as written, in order, with only "- Became: …" and
      // "- Replaced by: …" lines added.
      let j = 0;
      for (const line of n.raw) {
        if (j < o.raw.length && line === o.raw[j]) j++;
        else if (!/^- (Became|Replaced by): D-\d+$/.test(line)) p.push(`${o.id}: ${JSON.stringify(line)} was added or changed; only "- Became: …" and "- Replaced by: …" may be added`);
      }
      for (; j < o.raw.length; j++) p.push(`${o.id}: ${JSON.stringify(o.raw[j])} was removed, changed or moved`);
    });
  });
}

// ---- writing the view (only when everything above passes), then checking the file as it is ----
let finalRaw = logRaw;
let writeNote = "";
if (mode === "write-view") {
  const problemsSoFar = results.reduce((n, r) => n + r.problems.length, 0);
  const v = viewOf(logRaw);
  if (problemsSoFar || v.problem) {
    writeNote = "The Current decisions view was NOT written: fix the problems below first.";
  } else if (v.inner === buildView(entries)) {
    writeNote = "Current decisions view already up to date.";
  } else {
    // Only the lines between the markers change. Each line keeps its own line ending; the new
    // lines use the start marker's. The result goes to a new file, log.md.new, never over
    // log.md: the checker never overwrites the log; a person moves the new file into place after
    // checking log.md still has the SHA-256 printed below.
    const parts = logRaw.split(/(?<=\n)/);
    const eol = parts[v.start].endsWith("\r\n") ? "\r\n" : "\n";
    const updated = [...parts.slice(0, v.start + 1), ...buildView(entries).split("\n").map((l) => l + eol), ...parts.slice(v.end)].join("");
    const out = `${logPath}.new`;
    let fd = null;
    let leftover = false;
    try {
      fd = openSync(out, "wx", statSync(logPath).mode & 0o666);
      const bytes = Buffer.from(updated, "utf8");
      let done = 0;
      while (done < bytes.length) done += writeSync(fd, bytes, done, bytes.length - done);
      closeSync(fd);
      fd = null;
    } catch (err) {
      // Only a file this run created is removed; an existing log.md.new is never touched.
      if (fd !== null) {
        try { closeSync(fd); } catch { /* already closed */ }
        try { unlinkSync(out); } catch { leftover = true; }
      }
      console.error(err.code === "EEXIST"
        ? "log.md.new already exists from an earlier run and may be out of date: don't move it into place. Delete it, then run --write-view again. Nothing was written."
        : leftover
          ? "Couldn't write log.md.new, and couldn't remove the incomplete file: delete log.md.new by hand; don't move it into place."
          : "Couldn't write log.md.new; the incomplete file was removed.");
      process.exit(2);
    }
    finalRaw = updated;
    const base = createHash("sha256").update(logRaw, "utf8").digest("hex");
    writeNote = [
      "Wrote log.md.new: log.md with its Current decisions list rebuilt from the entries. log.md itself was not changed.",
      "The checks below are of log.md.new. It was built from log.md as it was when read, SHA-256",
      `  ${base}`,
      "Before moving log.md.new over log.md, check that log.md's SHA-256 is still that; if log.md has changed since, delete log.md.new and run --write-view again.",
    ].join("\n");
  }
}
// The view, as the file now stands: its rows must all be decisions, and it must match the entries.
const view = viewOf(finalRaw);
if (!view.problem) {
  for (const row of view.inner.split("\n").slice(2)) {
    const id = (cellsOf(row) ?? [])[0];
    const e = byId.get(id);
    if (!e || status(e) !== "decision") check3.problems.push(`${id} is in the Current decisions view but is not a decision`);
  }
}
check("7. A reader finds the current decisions without reading the history", (p) => {
  if (view.problem) p.push(view.problem);
  else if (view.inner !== buildView(entries)) p.push("the Current decisions view doesn't match the entries; run with --write-view");
});
// Keep the criteria in order in the report (7 before the stretch and history checks).
const order = (r) => (/^\d/.test(r.title) ? Number.parseInt(r.title, 10) : r.title.startsWith("Stretch") ? 8 : 9);
results.sort((a, b) => order(a) - order(b));

// ---- report -----------------------------------------------------------------------------------
if (writeNote) console.log(`${writeNote}\n`);
const failed = results.reduce((n, r) => n + r.problems.length, 0);
const count = (s) => entries.filter((e) => status(e) === s).length;
console.log(`Decision log check: ${shownDir} (${entries.length} entries: ${count("decision")} decisions, ${count("proposal")} proposals, ${count("question")} questions)`);
// What a passing check 4 or 5 verified, spelled out link by link, so a reader can see each
// promotion and replacement it confirmed, not just the word PASS.
const linkWords = (e) => (status(e) === "decision" ? approvedWords(e) : e.title);
const allPass = results.every((r) => r.problems.length === 0);
const verified = (r) => {
  if (!allPass) return [];
  if (r.title.startsWith("4.")) {
    return entries.filter((e) => status(e) === "decision" && e.fields.has("From")).map((e) => {
      const from = byId.get(e.fields.get("From"));
      if (!from) return null;
      return `verified: proposal ${from.id} "${linkWords(from)}" became decision ${e.id} "${linkWords(e)}"; ${from.id} says "Became: ${e.id}", ${e.id} says "From: ${from.id}", and ${e.id}'s approval record says it promotes ${from.id}`;
    });
  }
  if (r.title.startsWith("5.")) {
    return entries.filter((e) => status(e) === "decision" && e.fields.has("Replaces")).map((e) => {
      const old = byId.get(e.fields.get("Replaces"));
      if (!old) return null;
      return `verified: superseded decision ${old.id} "${linkWords(old)}" links to ${e.id}, the decision that replaced it, "${linkWords(e)}"; ${old.id} says "Replaced by: ${e.id}", ${e.id} says "Replaces: ${old.id}", and ${e.id}'s approval record says it replaces ${old.id}`;
    });
  }
  return [];
};
for (const r of results) {
  console.log(`${r.problems.length ? "FAIL" : "PASS"}  ${r.title}`);
  for (const pr of r.problems) console.log(`      - ${pr}`);
  for (const line of verified(r).filter(Boolean)) console.log(`      ${line}`);
}
// Stretch goal 2: decisions in force with no work resting on them, by their approved words.
const idle = entries.filter((e) => status(e) === "decision" && !e.fields.has("Replaced by") && ![...workItems.values()].some((r) => r.includes(e.id)));
if (allPass) console.log(`Decisions in force with no work resting on them: ${idle.length ? idle.map((e) => `${e.id} (${approvedWords(e)})`).join(", ") : "none"}`);
else console.log("Decisions in force with no work resting on them: not listed, because the log has problems.");
console.log(failed ? `Result: FAIL, ${failed} problem${failed === 1 ? "" : "s"}.` : "Result: PASS, every check passed.");
process.exitCode = failed ? 1 : 0;
