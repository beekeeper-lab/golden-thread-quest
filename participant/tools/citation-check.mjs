// Checks a meeting's decisions file against its transcript, for the ba-extract-decisions quest:
// every cited utterance exists, every quoted key line is in the utterance it names, every person
// named as agreeing (or committing, or asking) spoke that utterance, the lists are separate, an
// instruction-like line is never treated as a decision, and the transcript itself is unchanged.
//
//   node participant/tools/citation-check.mjs [--transcript <file>] [--decisions <file>] [--original <file>]
//
// Defaults: participant/context/transcripts/sample-meeting.md and its .decisions.md beside it.
// "Not edited" is checked against the transcript's committed version in Git, or, with --original,
// against that file byte for byte (for a copy outside the repository). Exit codes: 0 every check passed,
// 1 at least one problem, 2 a file couldn't be read or the arguments were wrong. It writes nothing.

import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { basename, isAbsolute } from "node:path";

const usage = () => {
  console.error("Usage: node participant/tools/citation-check.mjs [--transcript <file>] [--decisions <file>] [--original <file>]");
  process.exit(2);
};
const DEFAULT_TRANSCRIPT = "participant/context/transcripts/sample-meeting.md";
let transcriptPath = DEFAULT_TRANSCRIPT;
let decisionsPath = null;
let originalPath = null;
const args = process.argv.slice(2);
for (let i = 0; i < args.length; i++) {
  if (args[i] === "--transcript" && i + 1 < args.length) transcriptPath = args[++i];
  else if (args[i] === "--decisions" && i + 1 < args.length) decisionsPath = args[++i];
  else if (args[i] === "--original" && i + 1 < args.length) originalPath = args[++i];
  else usage();
}
decisionsPath ??= transcriptPath.replace(/\.md$/, ".decisions.md");
// Paths are shown as given, except an absolute one (it could show this computer's folders).
const shown = (p) => (isAbsolute(p) ? `(file ${basename(p)})` : p);

const utf8 = new TextDecoder("utf-8", { fatal: true });
const raw = new Map(); // path -> the exact bytes that were checked
const read = (path) => {
  let text;
  try {
    const bytes = readFileSync(path);
    raw.set(path, bytes);
    text = utf8.decode(bytes);
  } catch {
    console.error(`Couldn't read ${shown(path)} as UTF-8 text.`);
    process.exit(2);
  }
  if (/\r(?!\n)/.test(text)) {
    console.error(`${shown(path)} has a carriage return not followed by a line feed; nothing was checked.`);
    process.exit(2);
  }
  return text.replace(/\r\n/g, "\n");
};
const transcriptText = read(transcriptPath);
const decisionsText = read(decisionsPath);

const results = [];
const check = (title, fn) => {
  const r = { title, problems: [], verified: [] };
  fn(r.problems, r.verified);
  results.push(r);
};

// ---- the transcript ---------------------------------------------------------------------------
// Its utterance table: | Id | Time | Speaker | Utterance |. "\|" is a pipe inside a cell, and a
// backslash before a punctuation mark shows that mark as written (as Markdown renders it).
const cellsOf = (line) => {
  let t = line.trim().slice(1);
  if (/(^|[^\\])\|$/.test(t)) t = t.slice(0, -1);
  return t.split(/(?<!\\)\|/).map((c) => c.trim());
};
const rendered = (cell) => cell.replace(/\\([!-/:-@[-`{-~])/g, "$1");
const utterances = new Map();
const transcriptProblems = [];
for (const line of transcriptText.split("\n")) {
  if (!/^\|\s*U\d+\s*\|/.test(line)) continue;
  const cells = cellsOf(line);
  const [id, time, speaker, ...rest] = cells;
  if (cells.length !== 4 || !/^U\d{3}$/.test(id)) {
    transcriptProblems.push(`a transcript row isn't "| Unnn | time | speaker | utterance |": ${JSON.stringify(line.slice(0, 60))}`);
    continue;
  }
  if (utterances.has(id)) transcriptProblems.push(`the transcript has ${id} twice`);
  utterances.set(id, { time, speaker: rendered(speaker), text: rendered(rest[0]) });
}
if (!utterances.size) transcriptProblems.push("the transcript has no utterance table");
const flagged = new Set((/^- Flagged as instruction-like: (.+)$/m.exec(transcriptText)?.[1] ?? "").match(/U\d+/g) ?? []);

// ---- the decisions file -----------------------------------------------------------------------
// Fail closed on Markdown this file doesn't use, so a reader and the checker see the same items.
const SECTIONS = [
  { title: "Decisions", prefix: "D", required: ["Cites", "Key line", "Agreed by"], optional: ["Changed in the meeting", "Not yet confirmed", "See also"] },
  { title: "Proposals", prefix: "P", required: ["Cites", "Key line", "Not accepted"], optional: [] },
  { title: "Open questions", prefix: "O", required: ["Cites", "Key line", "Raised by"], optional: ["See also"] },
  { title: "Commitments", prefix: "C", required: ["Cites", "Key line", "By"], optional: ["Settles"] },
  { title: "Not classified", prefix: "X", required: ["Cites", "Why"], optional: [] },
];
const fileProblems = [];
const items = [];
const counts = new Map();
const intro = []; // the introduction's lines (before the first list), checked for references
let section = null;
let cur = null;
const order = [];
// Inline code as Markdown reads it: a backtick run closed by a run of the same length; a
// backslash-escaped backtick never opens one (and is itself reported).
const CODE_SPAN = /(?<![`\\])(`+)(?!`)([\s\S]*?[^`])\1(?!`)/g;
const lines = decisionsText.split("\n");
const firstHeading = lines.findIndex((l) => /^#/.test(l));
lines.forEach((line, i) => {
  const where = `decisions file line ${i + 1}`;
  const masked = line.replace(CODE_SPAN, "");
  if (/[[\]]/.test(line)) {
    // Links and references aren't used here, and their syntax changes what counts as code.
    fileProblems.push(`${where}: brackets (links or references) aren't used in the decisions file`);
    return;
  }
  if (/^\s*([*+]|\d+[.)])\s/.test(line) || (section === null && /^\s*-\s/.test(line))) {
    fileProblems.push(`${where}: lists are only "- Field: value" lines inside an item (or in Counts)`);
    return;
  }
  if (/^ {0,3}(`{3,}|~{3,})/.test(line) || line.includes("\\`") || /<[A-Za-z!?/]/.test(masked) || /-->/.test(masked)) {
    fileProblems.push(`${where}: code blocks, escaped backticks, HTML and comments aren't used in the decisions file`);
    return;
  }
  if (/&(#\d+|#x[0-9a-f]+|[a-z][a-z0-9]*);/i.test(masked)) {
    // A character reference (&#85; shows as "U") would make the text read differently from what
    // the checker sees.
    fileProblems.push(`${where}: character references (like &#85;) aren't used in the decisions file`);
    return;
  }
  if (/\|/.test(masked) || /^\s*(=+|-+)\s*$/.test(line) || /^[ \t]+\S/.test(line) || /^\s*>/.test(line)) {
    fileProblems.push(`${where}: tables, underlines, rules, quote blocks and indented lines aren't used in the decisions file`);
    return;
  }
  const h2 = /^## (.+)$/.exec(line);
  if (h2) {
    order.push(h2[1].trim());
    section = h2[1].trim();
    cur = null;
    return;
  }
  const h3 = /^### ([A-Z])(\d+) · (.+)$/.exec(line);
  if (h3) {
    const s = SECTIONS.find((x) => x.title === section);
    if (!s) {
      fileProblems.push(`${where}: an item outside the five lists`);
      cur = null;
      return;
    }
    if (h3[1] !== s.prefix) fileProblems.push(`${where}: an item in "${section}" must be ${s.prefix}-numbered, not ${h3[1]}${h3[2]}`);
    cur = { id: `${h3[1]}${h3[2]}`, title: h3[3].trim(), section: s, fields: new Map() };
    items.push(cur);
    return;
  }
  if (/^#/.test(line)) {
    if (!/^# \S/.test(line) || i !== firstHeading) fileProblems.push(`${where}: a heading that isn't the title, one of the lists or an item`);
    // The title is read like the introduction: its references are checked too.
    else intro.push({ line: line.replace(/^# /, ""), where });
    return;
  }
  const f = /^- ([A-Za-z ]+): (.*)$/.exec(line);
  if (section === "Counts") {
    if (f && counts.has(f[1])) fileProblems.push(`${where}: Counts lists "${f[1]}" twice`);
    else if (f) counts.set(f[1], f[2].trim());
    else if (line.trim()) fileProblems.push(`${where}: the Counts list has only "- Name: number" lines`);
    return;
  }
  if (!cur) {
    if (section && line.trim()) fileProblems.push(`${where}: text in "${section}" outside an item`);
    if (!section && line.trim()) intro.push({ line, where });
    return;
  }
  if (line.trim() === "") return;
  if (!f) {
    fileProblems.push(`${cur.id}: a line that isn't "- Field: value": ${JSON.stringify(line)}`);
    return;
  }
  if (cur.fields.has(f[1])) fileProblems.push(`${cur.id}: "${f[1]}" is given twice`);
  if (f[2].trim() === "") fileProblems.push(`${cur.id}: "${f[1]}" is empty`);
  cur.fields.set(f[1], f[2].trim());
});
const wantOrder = ["Counts", ...SECTIONS.map((s) => s.title)];
if (order.join("|") !== wantOrder.join("|")) fileProblems.push(`the decisions file's lists must be, in order: ${wantOrder.join(", ")} (found ${order.join(", ") || "none"})`);
const byId = new Map();
for (const it of items) {
  if (byId.has(it.id)) fileProblems.push(`${it.id} is used twice`);
  byId.set(it.id, it);
}
// Utterance identifiers in a text, wherever they stand (also inside _emphasis_ or **bold**).
const UID = /(?<![A-Za-z0-9])U\d+(?![0-9])/g;
const idsIn = (text) => (text ?? "").match(UID) ?? [];
const cites = (it) => (it.fields.get("Cites") ?? "").split(/\s+/).filter(Boolean);
// "Name at U011, Name at U012" (optionally "via the wrap-up: " first) -> [{name, id}] or null
const people = (value) => {
  const v = (value ?? "").replace(/^via the wrap-up: /, "");
  const parts = v.split(/,\s*/).map((p) => /^(.+) at (U\d+)$/.exec(p.trim()));
  return parts.every(Boolean) ? parts.map((m) => ({ name: m[1], id: m[2] })) : null;
};

// ---- the checks -------------------------------------------------------------------------------
check("0. The transcript and the decisions file can be read", (p) => {
  p.push(...transcriptProblems, ...fileProblems);
  for (const it of items) {
    for (const f of it.section.required) if (!it.fields.has(f)) p.push(`${it.id}: "${f}" is missing`);
    for (const f of it.fields.keys()) if (![...it.section.required, ...it.section.optional].includes(f)) p.push(`${it.id}: an item in "${it.section.title}" has no "${f}" line`);
  }
});

check("1. Each decision cites at least one utterance from the source record", (p, v) => {
  const ds = items.filter((it) => it.section.prefix === "D");
  if (!ds.length) p.push("there are no decisions");
  for (const it of ds) {
    if (!cites(it).length) p.push(`${it.id}: cites no utterance`);
    else if (!cites(it).some((id) => utterances.has(id))) p.push(`${it.id}: cites no utterance that exists in the source record`);
  }
  if (!p.length) v.push(`verified (criterion 1): all ${ds.length} decisions cite utterances of the source record, from ${ds.map((it) => `${it.id} (${cites(it).join(" ")})`).slice(0, 2).join(" and ")} on`);
});

check("2. A proposal nobody accepted is not listed as a decision", (p, v) => {
  for (const it of items.filter((x) => x.section.prefix === "D")) {
    if (/^not stated$/i.test(it.fields.get("Agreed by") ?? "")) p.push(`${it.id}: agreement is not stated, so it is a proposal, not a decision`);
  }
  for (const it of items.filter((x) => x.section.prefix === "P")) {
    const why = it.fields.get("Not accepted") ?? "";
    if (!/^(nobody replied|changed at U\d+ into D\d+)$/.test(why)) p.push(`${it.id}: "Not accepted" must be "nobody replied" or "changed at Unnn into Dn"`);
  }
  if (!p.length) {
    const ps = items.filter((x) => x.section.prefix === "P");
    v.push(`verified (criterion 2): ${ps.length} proposals that nobody accepted are listed as proposals, not decisions: ${ps.map((it) => `${it.id} "${it.title}" (${it.fields.get("Not accepted")})`).join("; ")}`);
  }
});

check("3. A decision records who agreed, at which line", (p, v) => {
  for (const it of items.filter((x) => x.section.prefix === "D")) {
    const who = people(it.fields.get("Agreed by"));
    if (!who) {
      p.push(`${it.id}: "Agreed by" must be "Name at Unnn" (comma-separated, optionally "via the wrap-up: " first)`);
      continue;
    }
    for (const { name, id } of who) {
      const u = utterances.get(id);
      if (!cites(it).includes(id)) p.push(`${it.id}: agreed at ${id}, which it doesn't cite`);
      if (u && u.speaker !== name) p.push(`${it.id}: names ${name} as agreeing at ${id}, but ${id} was spoken by ${u.speaker}`);
    }
  }
  if (!p.length) {
    const d4 = byId.get("D4") ?? items.find((x) => x.section.prefix === "D");
    if (d4) v.push(`verified (criterion 3): every decision names who agreed and at which line, and each named person spoke that line; for example ${d4.id} "${d4.title}" was agreed by ${d4.fields.get("Agreed by")}`);
  }
});

check("4. Open discussion and undecided items are listed separately", (p, v) => {
  for (const it of items.filter((x) => x.section.prefix === "O")) {
    const raised = it.fields.get("Raised by") ?? "";
    const unknown = /^uncertain speaker at (U\d+)$/.exec(raised);
    if (unknown) {
      if (!cites(it).includes(unknown[1])) p.push(`${it.id}: raised at ${unknown[1]}, which it doesn't cite`);
      const u = utterances.get(unknown[1]);
      if (u && !/unknown|uncertain/i.test(u.speaker)) p.push(`${it.id}: says the speaker at ${unknown[1]} is uncertain, but the transcript names ${u.speaker}`);
      continue;
    }
    const who = people(raised);
    if (!who || who.length !== 1) p.push(`${it.id}: "Raised by" must be "Name at Unnn" or "uncertain speaker at Unnn"`);
    else if (!cites(it).includes(who[0].id)) p.push(`${it.id}: raised at ${who[0].id}, which it doesn't cite`);
    else if (utterances.get(who[0].id) && utterances.get(who[0].id).speaker !== who[0].name) p.push(`${it.id}: names ${who[0].name} as raising it at ${who[0].id}, but ${who[0].id} was spoken by ${utterances.get(who[0].id).speaker}`);
  }
  for (const it of items.filter((x) => x.section.prefix === "C")) {
    const who = people(it.fields.get("By"));
    if (!who || who.length !== 1) p.push(`${it.id}: "By" must be "Name at Unnn"`);
    else if (!cites(it).includes(who[0].id)) p.push(`${it.id}: committed at ${who[0].id}, which it doesn't cite`);
    else if (utterances.get(who[0].id) && utterances.get(who[0].id).speaker !== who[0].name) p.push(`${it.id}: names ${who[0].name} as committing at ${who[0].id}, but ${who[0].id} was spoken by ${utterances.get(who[0].id).speaker}`);
  }
  if (!p.length) {
    const os = items.filter((x) => x.section.prefix === "O");
    v.push(`verified (criterion 4): ${os.length} open questions are listed separately from the decisions, under "Open questions": ${os.map((it) => `${it.id} "${it.title}"`).join("; ")}`);
  }
});

check("5. The decisions file is separate from the source record, which is not edited", (p, v) => {
  if (decisionsPath === transcriptPath) p.push("the decisions file is the transcript itself");
  if (decisionsText.includes("| Id | Time | Speaker | Utterance |")) p.push("the decisions file contains the transcript's utterance table");
  const checked = raw.get(transcriptPath);
  if (originalPath !== null) {
    let same = false;
    try {
      same = readFileSync(originalPath).equals(checked);
    } catch {
      p.push("couldn't read the original transcript to compare with");
    }
    if (!same && !p.length) p.push("the transcript has been edited: it differs from the original byte for byte");
    else if (same && !p.length) v.push("verified (criterion 5): the decisions file is separate from the source record, which is byte-identical to the original");
  } else if (transcriptPath === DEFAULT_TRANSCRIPT) {
    // Unchanged since the last commit: the Git object id of the bytes checked must equal the
    // committed one.
    const now = createHash("sha1").update(`blob ${checked.length}\0`).update(checked).digest("hex");
    let committed = null;
    try {
      committed = execFileSync("git", ["rev-parse", `HEAD:${transcriptPath}`], { encoding: "utf8", stdio: ["ignore", "pipe", "ignore"] }).trim();
    } catch {
      p.push("couldn't read the transcript's committed version (run this from the repository's top folder)");
    }
    if (committed && now !== committed) p.push(`the transcript has been edited since it was committed (Git object ${committed.slice(0, 12)} then, ${now.slice(0, 12)} now)`);
    else if (committed && !p.length) v.push(`verified (criterion 5): the decisions file ${shown(decisionsPath)} is separate from the source record ${shown(transcriptPath)}, which is unchanged since it was committed (Git object ${committed})`);
  } else {
    p.push("not compared: give --original <file> to check that this transcript wasn't edited");
  }
});

check("6. A cited identifier that doesn't exist is reported", (p, v) => {
  let n = 0;
  for (const it of items) {
    for (const id of cites(it)) {
      n++;
      if (!/^U\d+$/.test(id)) p.push(`${it.id}: ${JSON.stringify(id)} isn't an utterance identifier`);
      else if (!utterances.has(id)) p.push(`${it.id}: cites ${id}, which isn't in the transcript`);
    }
    for (const field of ["Changed in the meeting", "Not accepted", "Not yet confirmed", "See also", "Agreed by", "Raised by", "By", "Settles", "Why"]) {
      for (const id of idsIn(it.fields.get(field))) if (!utterances.has(id)) p.push(`${it.id}: "${field}" names ${id}, which isn't in the transcript`);
    }
    for (const id of idsIn(it.title)) if (!utterances.has(id)) p.push(`${it.id}: its title names ${id}, which isn't in the transcript`);
  }
  // The introduction may name utterances (they must exist), but never an item: a claim about a
  // decision belongs in the checked lists. Compared as displayed, so emphasis or look-alike
  // characters can't hide one.
  for (const { line, where } of intro) {
    for (const id of idsIn(line)) if (!utterances.has(id)) p.push(`${where}: the introduction names ${id}, which isn't in the transcript`);
    const shownAs = line.normalize("NFKC").replace(/[^A-Za-z0-9\s]/g, " ");
    if (/(^|[^A-Za-z0-9])[DPOCX]\s*\d/.test(shownAs)) p.push(`${where}: the introduction names an item; items are named only in the five lists`);
  }
  if (!p.length) v.push(`verified (criterion 6): all ${n} cited utterance identifiers exist in the source record, which has ${utterances.size} utterances (${[...utterances.keys()][0]} to ${[...utterances.keys()].at(-1)})`);
});

check("7. Every item can be checked against the source: its key line is quoted word for word", (p, v) => {
  for (const it of items.filter((x) => x.fields.has("Key line"))) {
    const m = /^(U\d+) "(.+)"$/.exec(it.fields.get("Key line"));
    if (!m) {
      p.push(`${it.id}: "Key line" must be Unnn "the words quoted"`);
      continue;
    }
    const u = utterances.get(m[1]);
    if (!cites(it).includes(m[1])) p.push(`${it.id}: its key line ${m[1]} isn't one it cites`);
    if (u && !u.text.includes(m[2])) p.push(`${it.id}: the key line isn't in ${m[1]} word for word: ${JSON.stringify(m[2])}`);
  }
  if (!p.length) {
    const d5 = byId.get("D5");
    v.push(`verified (criterion 7): every item's key line is quoted word for word from the utterance it names, so each can be checked against the transcript; for example ${d5 ? `D5's ${d5.fields.get("Key line")}` : "each item"}`);
  }
});

check("Safety: an instruction-like line is never a decision, proposal, question or commitment", (p, v) => {
  for (const { line, where } of intro) {
    for (const id of idsIn(line)) if (flagged.has(id)) p.push(`${where}: the introduction names ${id}, which the transcript flags as instruction-like`);
  }
  for (const it of items.filter((x) => x.section.prefix !== "X")) {
    for (const [field, value] of [["title", it.title], ...it.fields]) {
      for (const id of idsIn(value)) {
        if (flagged.has(id)) p.push(`${it.id}: ${field === "Cites" ? "cites" : field === "title" ? "its title names" : `its "${field}" names`} ${id}, which the transcript flags as instruction-like; it may appear only under "Not classified"`);
      }
    }
  }
  if (!flagged.size) p.push('the transcript names no instruction-like lines ("- Flagged as instruction-like: …")');
  if (!p.length) v.push(`verified (safety): the instruction-like line ${[...flagged].join(", ")} appears only under "Not classified", never as a decision, proposal, question or commitment`);
});

check("Stretch: changes, doubts and counts", (p, v) => {
  for (const it of items) {
    const changed = /^from (P\d+) at (U\d+)$/.exec(it.fields.get("Changed in the meeting") ?? "") ;
    if (it.fields.has("Changed in the meeting") && !changed) p.push(`${it.id}: "Changed in the meeting" must be "from Pn at Unnn"`);
    if (changed) {
      const old = byId.get(changed[1]);
      if (!old || old.fields.get("Not accepted") !== `changed at ${changed[2]} into ${it.id}`) p.push(`${it.id}: changed from ${changed[1]}, but ${changed[1]} doesn't say "Not accepted: changed at ${changed[2]} into ${it.id}"`);
      // The final decision cites every line that led to it: the change and what it changed.
      if (!cites(it).includes(changed[2])) p.push(`${it.id}: changed at ${changed[2]}, which it doesn't cite`);
      for (const id of old ? cites(old) : []) if (!cites(it).includes(id)) p.push(`${it.id}: changed from ${changed[1]}, but doesn't cite ${changed[1]}'s ${id}`);
    }
    const into = /^changed at (U\d+) into (D\d+)$/.exec(it.fields.get("Not accepted") ?? "");
    if (into && byId.get(into[2])?.fields.get("Changed in the meeting") !== `from ${it.id} at ${into[1]}`) p.push(`${it.id}: changed into ${into[2]}, but ${into[2]} doesn't say "Changed in the meeting: from ${it.id} at ${into[1]}"`);
    const doubt = it.fields.get("Not yet confirmed");
    if (doubt !== undefined) {
      const c = /see (C\d+)$/.exec(doubt);
      if (!c || byId.get(c[1])?.section.prefix !== "C") p.push(`${it.id}: "Not yet confirmed" must end with "see Cn", naming the commitment that settles it`);
      else if (byId.get(c[1]).fields.get("Settles") !== it.id) p.push(`${it.id}: is settled by ${c[1]}, but ${c[1]} doesn't say "Settles: ${it.id}"`);
    }
    const settles = it.fields.get("Settles");
    if (settles !== undefined) {
      const d = byId.get(settles);
      if (!d || !/see (C\d+)$/.test(d.fields.get("Not yet confirmed") ?? "") || /see (C\d+)$/.exec(d.fields.get("Not yet confirmed"))[1] !== it.id) p.push(`${it.id}: says it settles ${settles}, but ${settles} isn't marked "Not yet confirmed … see ${it.id}"`);
    }
    for (const id of (it.fields.get("See also") ?? "").split(/[\s,]+/).filter(Boolean)) {
      const other = byId.get(id);
      if (!other) p.push(`${it.id}: "See also" names ${id}, which isn't an item`);
      else if (!(other.fields.get("See also") ?? "").split(/[\s,]+/).includes(it.id)) p.push(`${it.id}: "See also" names ${id}, but ${id} doesn't name ${it.id} back`);
    }
  }
  const n = (prefix) => items.filter((x) => x.section.prefix === prefix).length;
  const changedN = items.filter((x) => x.fields.has("Changed in the meeting")).length;
  const doubtN = items.filter((x) => x.fields.has("Not yet confirmed")).length;
  const want = new Map([
    ["Decisions", `${n("D")} (${changedN} changed in the meeting, ${doubtN} not yet confirmed)`],
    ["Proposals", `${n("P")}`],
    ["Open questions", `${n("O")}`],
    ["Commitments", `${n("C")}`],
  ]);
  for (const [k, val] of want) if (counts.get(k) !== val) p.push(`Counts: "${k}" says ${JSON.stringify(counts.get(k) ?? "(missing)")}, but the file has ${val}`);
  for (const k of counts.keys()) if (!want.has(k)) p.push(`Counts: "${k}" isn't one of the counted lists`);
  if (!p.length) v.push(`verified (stretch): ${n("D")} decisions (${changedN} changed in the meeting, ${doubtN} not yet confirmed), ${n("P")} proposals, ${n("O")} open questions and ${n("C")} commitments, matching the Counts list; every change, doubt and "See also" is linked both ways`);
});

// ---- report -----------------------------------------------------------------------------------
const failed = results.reduce((t, r) => t + r.problems.length, 0);
console.log(`Citation check: ${shown(decisionsPath)} against ${shown(transcriptPath)} (${items.length} items, ${utterances.size} utterances)`);
for (const r of results) {
  console.log(`${r.problems.length ? "FAIL" : "PASS"}  ${r.title}`);
  for (const pr of r.problems) console.log(`      - ${pr}`);
  if (!failed) for (const line of r.verified) console.log(`      ${line}`);
}
console.log(failed ? `Result: FAIL, ${failed} problem${failed === 1 ? "" : "s"}.` : "Result: PASS, every check passed.");
process.exitCode = failed ? 1 : 0;
