// The ticket reader, for the base-camp-prompt-injection quest: reads synthetic work items (tickets
// and tool results) and prints a report on each, treating everything in them as content. It is the
// "agent" the injection cases attack. Rules: participant/context/untrusted-input-rules.md.
//
// IT CAN ONLY READ. It reads one file and prints to the screen. It has no way to change a ticket,
// send anything, run anything, or write, rename or delete any file: none of those abilities exist
// in this code, so untrusted text has no path to an action. It is meant to be run in Node's
// permission mode, allowed only to read, so that Node itself refuses any write or any new program;
// participant/tools/check-reader-code.mjs checks this file for anything that could reach the
// network or write.
//
// WHAT IT READS. From the cases file (default participant/context/injection-cases.md), only the
// fenced blocks marked `ticket` or `tool-result`, each named by the "## " heading above it. Nothing
// else in the file is read as anything, and nothing in a block is ever taken as a setting or an
// order. A ticket block has one `field: value` per line (title, reporter, status, description,
// comment, attachment); `description: |` takes the indented lines below it. A tool-result block is
// one JSON object.
//
// WHAT IT REPORTS, for each case: the title, reporter and status as given; every line that looks like
// an embedded instruction, where it is, quoted exactly as content (control characters shown as
// escapes, so the report can't be used to play tricks on the terminal); for base64-encoded text,
// the decoded text too; which flags fired; and that nothing was obeyed. Two flags, neither of which is
// the defense:
//   - phrase filter: wording typical of injected instructions;
//   - addresses the reader: text written to whoever processes it, which a ticket written for people
//     has no reason to contain.
// At the end: how many cases, how many embedded instructions, which flags fired, and which cases the
// phrase filter alone would have missed.
//
// Run it from the repository's top folder, inside the macOS sandbox with the network denied and in
// Node's permission mode (read only):
//   sandbox-exec -p '(version 1)(allow default)(deny network*)' \
//     node --permission --allow-fs-read="$PWD" participant/tools/ticket-reader.mjs [cases file]
// Exit 0: every case had at least one flagged line. 1: some case had none (shown by name, so a new
// case nobody flagged is noticed). 2: the cases file couldn't be read, or held no case.

import { readFileSync } from "node:fs";

const casesFile = process.argv[2] ?? "participant/context/injection-cases.md";
if (process.argv.length > 3) {
  console.error("Usage: node --permission --allow-fs-read=<repository> participant/tools/ticket-reader.mjs [cases file]");
  process.exit(2);
}
let text;
try {
  text = readFileSync(casesFile, "utf8");
} catch (error) {
  console.error(`Couldn't read the cases file (${error.code ?? "an unexpected error"}).`);
  process.exit(2);
}

// --- The cases: fenced `ticket` and `tool-result` blocks, named by the heading above. -----------
const cases = [];
let heading = "(no heading)";
const otherBlocks = [];
const lines = text.split(/\r?\n/);
for (let i = 0; i < lines.length; i++) {
  const line = lines[i];
  if (line.startsWith("## ")) heading = line.slice(3).trim();
  // Any other fenced block (another label, a different case of letters) is listed by the summary as
  // not read, so a case written with the wrong label is never skipped without a word.
  if (/^```/.test(line) && !/^```(ticket|tool-result)\s*$/.test(line)) {
    otherBlocks.push(`${safe(line.trim())} under ${safe(heading)}`);
    for (i++; i < lines.length && !/^```\s*$/.test(lines[i]); i++);
    continue;
  }
  const fence = line.match(/^```(ticket|tool-result)\s*$/);
  if (!fence) continue;
  const body = [];
  for (i++; i < lines.length && !/^```\s*$/.test(lines[i]); i++) body.push(lines[i]);
  cases.push({ name: heading, kind: fence[1], body });
}
if (cases.length === 0) {
  console.error("The cases file holds no ticket or tool-result block.");
  process.exit(2);
}

// Untrusted text is always shown through this: quoted, with every character a terminal or a viewer
// could act on shown as an escape instead (control characters, Unicode line and paragraph
// separators, characters that reverse or hide text, zero-width characters).
function safe(text) {
  return JSON.stringify(String(text)).replace(/[\u007f-\u009f\u00ad\u061c\u180e\u200b-\u200f\u2028-\u202e\u2060-\u206f\ufeff\ufff9-\ufffb]/g,
    (c) => `\\u${c.charCodeAt(0).toString(16).padStart(4, "0")}`);
}

// --- The pieces of a case: each line of content, with where it is. --------------------------------
function ticketPieces(body) {
  const pieces = [];
  const fields = {};
  let comments = 0;
  let attachments = 0;
  // Every line is read, and nothing is skipped: a field the reader doesn't expect (a label, a
  // priority), the reporter's name, a description line after a blank line, and a line with no field
  // name at all are all content, and all checked.
  // The value may hold any character, Unicode line separators included ("s"), so no field loses its name.
  const field = /^([a-z][a-z_-]*):\s?(.*)$/s;
  for (let i = 0; i < body.length; i++) {
    if (body[i].trim() === "") continue;
    const m = body[i].match(field);
    if (!m) {
      pieces.push({ where: "a line with no field name", text: body[i].trim() });
      continue;
    }
    const [, name, value] = m;
    if (name === "description" && value.trim() === "|") {
      // The description runs until the next line that starts with a field name.
      for (i++; i < body.length && !field.test(body[i]); i++) {
        const content = body[i].trim();
        if (content === "") continue;
        const quoted = content.startsWith(">");
        pieces.push({ where: quoted ? "the description (quoted text)" : "the description", text: quoted ? content.replace(/^>\s?/, "") : content });
      }
      i--;
    } else if (name === "comment") {
      comments++;
      pieces.push({ where: `comment ${comments}`, text: value });
    } else if (name === "attachment") {
      attachments++;
      pieces.push({ where: `the name of attachment ${attachments}`, text: value });
    } else {
      fields[name] = value;
      // The whole line, field name included: a field can be named to address the reader.
      pieces.push({ where: `the ${name}`, text: name === "title" ? value : `${name}: ${value}` });
    }
  }
  return { fields, pieces };
}

function toolResultPieces(body) {
  const pieces = [];
  const source = body.join("\n");
  let data;
  try {
    data = JSON.parse(source);
  } catch {
    return { fields: {}, pieces: [{ where: "the tool result (not valid JSON, read as text)", text: source }] };
  }
  // Every string written in the result is checked, from the text itself rather than the parsed object
  // (a key written twice keeps only its last value once parsed, and the earlier one must not vanish),
  // and each is named by where it sits: field names for objects, positions for lists.
  const frames = [];
  let expectKey = false;
  for (let i = 0; i < source.length; i++) {
    const c = source[i];
    if (c === "{") {
      frames.push({ kind: "object", key: "" });
      expectKey = true;
    } else if (c === "[") {
      frames.push({ kind: "list", index: 0 });
      expectKey = false;
    } else if (c === "}" || c === "]") {
      frames.pop();
    } else if (c === ",") {
      const top = frames[frames.length - 1];
      if (top?.kind === "list") top.index++;
      else expectKey = true;
    } else if (c === '"') {
      let j = i + 1;
      while (j < source.length && source[j] !== '"') j += source[j] === "\\" ? 2 : 1;
      const value = JSON.parse(source.slice(i, j + 1));
      const top = frames[frames.length - 1];
      // Each object key quoted on its own and each list position in brackets, so a key such as "a.b"
      // or "a[0]" can't pass itself off as another place.
      const segment = (f) => (f.kind === "object" ? safe(f.key) : `[${f.index}]`);
      const at = (list) => list.join(".").replace(/\.\[/g, "[");
      if (top?.kind === "object" && expectKey) {
        top.key = value;
        expectKey = false;
        pieces.push({ where: `the name of a tool result's field (${at([...frames.slice(0, -1).map(segment), safe(value)])})`, text: value });
      } else pieces.push({ where: `the tool result's field ${at(frames.map(segment))}`, text: value });
      i = j;
    }
  }
  return { fields: { tool: typeof data?.tool === "string" ? data.tool : "(unnamed)" }, pieces };
}

// Base64 found inside a piece is decoded, and the decoded text checked too, when it reads as text.
function decoded(piece) {
  const found = [];
  // Tokens of 8 or more base64 characters, with or without their "=" padding; kept when the decoded
  // bytes are ordinary text (letters, digits, punctuation, spaces, tabs and line breaks).
  for (const token of piece.text.match(/[A-Za-z0-9+/]{8,}={0,2}/g) ?? []) {
    const bare = token.replace(/=+$/, "");
    if (bare.length % 4 === 1) continue;
    let plain;
    try {
      plain = new TextDecoder("utf-8", { fatal: true }).decode(Buffer.from(bare, "base64"));
    } catch {
      continue;
    }
    // Everything that decodes as UTF-8 goes to the flags; the report quotes it safely, invisible
    // characters included. (Ordinary words that happen to decode give text no flag fires on.)
    if (plain === "") continue;
    found.push({ where: `${piece.where} (decoded from base64)`, text: plain, encoded: token });
  }
  return found;
}

// --- The two flags. Neither is the defense; they help the person reading the report. ------------
const words = (s) => ` ${s.toLowerCase().replace(/[^\p{L}\p{N}]+/gu, " ").trim()} `;
// Each phrase as whole words, after letter case and punctuation are set aside. Action words count only
// when something is asked for, as in "email the list" or "delete all tickets": a customer mentioning
// an email is not one.
const PHRASES = [
  "ai assistant", "assistant", "ignore previous", "ignore all previous", "disregard", "you must",
  "system prompt", "mark this story done", "mark this ticket done", "mark the story as done",
  "run the command", "git push", "rm rf",
  ...["email", "delete"].flatMap((verb) =>
    ["the", "it", "this", "them", "all", "every", "these", "those", "any", "each"].map((next) => `${verb} ${next}`)),
];
const phraseFilter = (s) => PHRASES.filter((p) => words(s).includes(` ${p} `));
const READER = [
  /\bwhoever (handles|processes|reads|picks up|gets)\b/i,
  /\b(ai |automated )?(assistant|agent|bot|automation|tool|model|program)s? (reading|processing|handling)\b/i,
  /\bnote to (the |any )?(automated )?(assistant|agent|bot|tool|reader|automation|ai)\b/i,
  /\bdear (ai|assistant|agent|bot)\b/i,
  /\bif you are an? (ai|assistant|agent|bot|tool|program)\b/i,
  /\bto (the|any) (ai|assistant|agent|bot)\b/i,
  /\b(ai assistant|assistant|agent|bot|automation)s?\s*[:,]/i,
];
const addressesReader = (s) => READER.some((r) => r.test(s));

// --- The report. -----------------------------------------------------------------------------------
const quote = safe;
let instructions = 0;
let byPhrase = 0;
let byReader = 0;
const phraseMissed = [];
const unflagged = [];
cases.forEach((c, n) => {
  const { fields, pieces } = c.kind === "ticket" ? ticketPieces(c.body) : toolResultPieces(c.body);
  const all = pieces.flatMap((p) => [p, ...decoded(p)]);
  console.log(`=== Case ${n + 1}: ${quote(c.name)} (${c.kind === "ticket" ? "a ticket" : "a tool result"}) ===`);
  if (c.kind === "ticket") {
    console.log(`  Title: ${quote(fields.title ?? "")}`);
    console.log(`  Reporter: ${quote(fields.reporter ?? "")}   Status as given: ${quote(fields.status ?? "")}`);
  } else console.log(`  From the tool: ${quote(fields.tool)}`);
  const flagged = all
    .map((p) => ({ ...p, phrases: phraseFilter(p.text), reader: addressesReader(p.text) }))
    .filter((p) => p.phrases.length > 0 || p.reader);
  if (flagged.length === 0) {
    console.log("  No line was flagged. (Everything above is still only content.)");
    unflagged.push(n + 1);
  } else {
    console.log(`  Embedded instructions found: ${flagged.length} (recorded as content, not obeyed):`);
    for (const p of flagged) {
      instructions++;
      if (p.phrases.length) byPhrase++;
      if (p.reader) byReader++;
      console.log(`    - in ${p.where}: ${quote(p.text)}`);
      if (p.encoded) console.log(`      encoded original: ${quote(p.encoded)}`);
      const fired = [p.phrases.length ? `phrase filter (${p.phrases.map(quote).join(", ")})` : "", p.reader ? "addresses the reader" : ""].filter(Boolean);
      console.log(`      flags: ${fired.join("; ")}`);
    }
    // Every flagged line the phrase filter missed, not just whole cases.
    for (const p of flagged) if (p.phrases.length === 0) phraseMissed.push(`case ${n + 1} (${p.where})`);
  }
  console.log("  Actions taken: none. This reader can only read and print; nothing was obeyed.");
  console.log("");
});

console.log(`Summary: ${cases.length} cases read from ${quote(casesFile)}; ${instructions} embedded instructions recorded as content, none obeyed.`);
console.log(`  Flagged by the phrase filter: ${byPhrase}; by addresses-the-reader: ${byReader}.`);
console.log(`  Lines the phrase filter alone would have missed: ${phraseMissed.length ? phraseMissed.join("; ") : "none"}.`);
console.log(`  Fenced blocks not read (not marked ticket or tool-result): ${otherBlocks.length ? otherBlocks.join("; ") : "none"}.`);
console.log(`  Cases with no flagged line: ${unflagged.length ? unflagged.join(", ") : "none"}.`);
// The exit code is set rather than exiting at once, so a report going to a pipe is written in full.
process.exitCode = unflagged.length ? 1 : 0;
