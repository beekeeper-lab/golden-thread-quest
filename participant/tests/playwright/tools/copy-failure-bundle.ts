// Copies one failing test's evidence out of test-results/ on purpose (the failure-evidence quest:
// test-results/ is emptied at the start of every run, so a bundle that should outlive the next run is
// copied out), and hides the computer's home-folder address on the way. Nothing is changed in
// test-results/.
//
// Run it from participant/tests/playwright:
//   node tools/copy-failure-bundle.ts <the test's folder in test-results> <a new or empty folder>
//
// What it changes in the copy:
//   - In every text file, and in every text member of trace.zip (UTF-8 or UTF-16), the home-folder
//     address (for example /Users/<name>) becomes ~, so the bundle doesn't show the computer's user
//     name: as it is, URL-encoded (as in file:///Users/Jane%20Doe/…), or inside a JSON string
//     however it is escaped.
//   - Inside trace.zip, src/ holds a copy of each test file named by the sha1 of its full address; the
//     trace viewer finds a file's source by that name. Each one is renamed to the sha1 of the
//     shortened address, so the viewer's Source tab still works (and the old name, which could
//     confirm a guessed user name, is gone).
// Images (the screenshot, the trace's page snapshots) are copied as they are: check them by eye.
// It reports how many places it changed, never the addresses themselves, and shows the home folder
// as ~ in every path it prints. If it fails part-way, it says so and the partial copy should be
// deleted. Then scan the copy:
//   node tools/failure-evidence-check.ts <the copy>

import { createHash } from "node:crypto";
import { existsSync, mkdirSync, readdirSync, readFileSync, statSync, writeFileSync } from "node:fs";
import { homedir } from "node:os";
import { join, relative, resolve } from "node:path";
import { jsonDocuments, jsonStrings } from "./json-places.ts";
import { decodeText, encodeText, readZip, writeZip } from "./zip-lite.ts";

const [from, to] = process.argv.slice(2);
if (!from || !to) {
  console.error("Usage: node tools/copy-failure-bundle.ts <the test's folder in test-results> <a new or empty folder>");
  process.exit(2);
}

const home = homedir();
if (home.length < 2) {
  console.error("Couldn't tell which folder is the home folder, so nothing would be hidden.");
  process.exit(1);
}
// The home-folder address in every form it could be stored in: as it is, URL-encoded as in a file
// address (file:///Users/Jane%20Doe/…), fully URL-encoded, and escaped as in JSON. Longest first, so
// a longer form is replaced before a shorter one inside it.
const homeForms = [...new Set([home, encodeURI(home), encodeURIComponent(home), JSON.stringify(home).slice(1, -1)])].sort(
  (a, b) => b.length - a.length,
);
const sha1 = (text: string) => createHash("sha1").update(text).digest("hex");
const shorten = (text: string) => homeForms.reduce((out, form) => out.replaceAll(form, "~"), text);
const places = (text: string) => homeForms.reduce((count, form) => count + text.split(form).length - 1, 0);
// What this tool prints: paths relative to where it runs, with the home folder shown as ~.
const shownPath = (path: string) => shorten(relative(process.cwd(), path).startsWith("..") ? path : relative(process.cwd(), path));

const source = resolve(from);
const target = resolve(to);
if (!existsSync(join(source, "trace.zip"))) {
  console.error(`${shownPath(source)} has no trace.zip: give the folder of one failing test, inside test-results/.`);
  process.exit(2);
}
if (target === source || target.startsWith(`${source}/`) || source.startsWith(`${target}/`)) {
  console.error("The copy and the original can't be inside each other.");
  process.exit(2);
}
if (existsSync(target) && readdirSync(target).length > 0) {
  console.error(`${shownPath(target)} isn't empty; give a new or empty folder, so nothing there is overwritten.`);
  process.exit(2);
}

let changed = 0;
const report: string[] = [];

// A text with the home-folder address replaced, and how many places changed. In JSON (the whole text,
// or each line), every string is read as its real value, whatever its escapes (\/ or \u002f), and
// rewritten if that value holds the address; the rest of the text is then shortened as it is.
function shortenText(text: string): { text: string; count: number } {
  let count = 0;
  const edits: { start: number; end: number; with: string }[] = [];
  for (const { node, offset } of jsonDocuments(text)) {
    for (const s of jsonStrings(node)) {
      const n = places(s.value);
      if (n === 0) continue;
      count += n;
      edits.push({ start: offset + s.start, end: offset + s.end, with: JSON.stringify(shorten(s.value)) });
    }
  }
  let out = text;
  for (const edit of edits.sort((a, b) => b.start - a.start)) out = `${out.slice(0, edit.start)}${edit.with}${out.slice(edit.end)}`;
  count += places(out);
  return { text: shorten(out), count };
}

// Every full file address in the trace's records that starts in the home folder, read from its JSON
// as real values, so an address with spaces, brackets or escapes in it is taken whole.
function homeAddresses(text: string): string[] {
  return jsonDocuments(text)
    .flatMap(({ node }) => jsonStrings(node))
    .map((s) => s.value)
    .filter((value) => value.startsWith(`${home}/`));
}

function copyTrace(zip: Buffer): Buffer {
  const entries = readZip(zip);
  // The trace viewer finds a file's source under src/ by the sha1 of its full address: map each old
  // name to the sha1 of the shortened address.
  const renames = new Map<string, string>();
  for (const { data } of entries) {
    const decoded = decodeText(data);
    for (const address of decoded ? homeAddresses(decoded.text) : []) renames.set(sha1(address), sha1(shorten(address)));
  }
  let members = 0;
  let renamed = 0;
  const copied = entries.map(({ name, data }) => {
    let newName = name;
    const sourceFile = /^src\/([0-9a-f]{40})(\.[^/]*)?$/.exec(name);
    if (sourceFile && renames.has(sourceFile[1])) {
      newName = `src/${renames.get(sourceFile[1])}${sourceFile[2] ?? ""}`;
      renamed++;
    }
    const decoded = decodeText(data);
    if (decoded === null) return { name: newName, data };
    const shortened = shortenText(decoded.text);
    if (shortened.count === 0) return { name: newName, data };
    members++;
    changed += shortened.count;
    return { name: newName, data: encodeText(shortened.text, decoded.encoding) };
  });
  report.push(`  trace.zip: ${members} member(s) changed, ${renamed} source file(s) renamed in src/`);
  return writeZip(copied);
}

function copy(from: string, to: string): void {
  mkdirSync(to, { recursive: true });
  for (const name of readdirSync(from).sort()) {
    const path = join(from, name);
    const out = join(to, name);
    if (statSync(path).isDirectory()) {
      copy(path, out);
      continue;
    }
    const data = readFileSync(path);
    const shown = shorten(relative(source, path));
    if (name.endsWith(".zip")) {
      writeFileSync(out, copyTrace(data));
      continue;
    }
    const decoded = decodeText(data);
    if (decoded === null) {
      writeFileSync(out, data);
      report.push(`  ${shown}: copied as it is (not text: check it by eye)`);
      continue;
    }
    const shortened = shortenText(decoded.text);
    changed += shortened.count;
    writeFileSync(out, shortened.count > 0 ? encodeText(shortened.text, decoded.encoding) : data);
    if (shortened.count > 0) report.push(`  ${shown}: ${shortened.count} place(s) changed`);
  }
}

try {
  copy(source, target);
} catch (error) {
  console.error(`Couldn't copy the bundle: ${shorten(error instanceof Error ? error.message : String(error))}`);
  console.error(`Part of it may have been written to ${shownPath(target)}; delete that folder before trying again.`);
  process.exit(1);
}
console.log(`Copied ${shownPath(source)} to ${shownPath(target)}.`);
console.log(`The home-folder address was replaced with ~ in ${changed} place(s):`);
for (const line of report) console.log(line);
