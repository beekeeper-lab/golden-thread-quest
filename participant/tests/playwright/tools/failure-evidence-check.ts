// The secret check for a failure bundle (the failure-evidence quest, criteria 3 and 4). Run it from
// participant/tests/playwright, with the run's API key in TIXLY_API_KEY (the same made-up key the
// tests used):
//   node tools/failure-evidence-check.ts <bundle folder>              scan the bundle
//   node tools/failure-evidence-check.ts --self-test <bundle folder>  prove the scan finds planted fakes
//
// SCAN: reads every file in the folder and every member of every .zip in it (trace.zip), and their
// names too, and looks for:
//   - the run's actual API key: as it is, URL-encoded, base64-encoded or escaped as in JSON (a key
//     as short as the project allows matches ordinary text often, so expect more findings);
//   - the shapes of secrets: a bearer token, a JSON web token, an Authorization, Cookie, Set-Cookie
//     or API-key header with any value (as text, "Cookie: …", or as JSON, in either order and over
//     several lines), a cookie record with a value (as in a browser's saved cookies), a password,
//     secret, token or key given any value however short, a private key, a password inside an
//     address (user:password@), and the prefixes of well-known token kinds;
//   - the computer's home-folder address, which shows its user name (a personal detail, not a
//     secret: the bundle is meant to have it replaced with ~ by tools/copy-failure-bundle.ts), as it
//     is, URL-encoded or escaped as in JSON.
// Text is read as UTF-8 or UTF-16, and JSON strings are also checked as their real values, after
// escapes such as \u0061. The zip's comments and extra fields are scanned too. Each finding is
// reported as file (and zip member), line and kind, never the value; every name and path it prints
// has the key and the home-folder address hidden, so the report itself can be shared. Files that
// aren't text (the screenshot, the trace's page images) are still searched for the key and the
// home-folder address, byte for byte in UTF-8 and UTF-16, and are listed to be checked by eye for
// personal data. A zip it can't fully read stops the check. Exit 0 when nothing is found, 1 when
// something is, 2 when it couldn't check everything.
//
// SELF-TEST: copies the bundle to a new temporary folder, first scans the untouched copy (it must be
// clean, or nothing is planted and the self-test fails), then plants three fake values there (a
// made-up bearer token in console.txt, a made-up session cookie inside trace.zip, and the run's API
// key in error.txt), scans the copy and passes only if each one is found at the exact file and line where it
// was planted and nothing else is found. The fakes are made up at random each time, so none is ever
// written into a file that could be committed. The temporary copy is deleted afterwards, whatever
// happens; the bundle itself is only read.

import { randomBytes } from "node:crypto";
import { mkdirSync, mkdtempSync, readdirSync, readFileSync, rmSync, statSync, writeFileSync } from "node:fs";
import { homedir, tmpdir } from "node:os";
import { join, relative, resolve } from "node:path";
import { type JsonNode, jsonDocuments, jsonStrings } from "./json-places.ts";
import { decodeText, readZip, readZipWithMetadata, writeZip } from "./zip-lite.ts";

type Finding = { place: string; line: number | null; kind: string };

const args = process.argv.slice(2);
const selfTest = args[0] === "--self-test";
const folderArg = selfTest ? args[1] : args[0];
if (!folderArg || args.length !== (selfTest ? 2 : 1)) {
  console.error("Usage: node tools/failure-evidence-check.ts [--self-test] <bundle folder>");
  process.exit(2);
}
const apiKey = process.env.TIXLY_API_KEY ?? "";
// The same rule as the demo app and the tests (1 to 256 visible characters, no spaces).
if (!/^[\x21-\x7e]{1,256}$/.test(apiKey)) {
  console.error("TIXLY_API_KEY must hold the run's API key (1 to 256 visible characters, no spaces), so the scan can look for it.");
  process.exit(2);
}
const home = homedir();
if (home.length < 2) {
  console.error("Couldn't tell which folder is the home folder, so it couldn't be looked for.");
  process.exit(2);
}

const jsonEscaped = (value: string) => JSON.stringify(value).slice(1, -1);
const unique = (values: string[]) => [...new Set(values)];
const keyForms = unique([apiKey, encodeURIComponent(apiKey), Buffer.from(apiKey).toString("base64"), jsonEscaped(apiKey)]);
const homeForms = unique([home, encodeURI(home), encodeURIComponent(home), jsonEscaped(home)]);

// The exact values this run must never leave behind, in the forms they could be stored in.
const exactValues: [string, string][] = [
  ...keyForms.map((form): [string, string] => [form, "the run's API key"]),
  ...homeForms.map((form): [string, string] => [form, "the home-folder address (shows the user name)"]),
];

// Anything printed: the key and the home-folder address hidden, longest form first.
function safe(text: string): string {
  let out = text;
  for (const form of [...keyForms].sort((a, b) => b.length - a.length)) out = out.replaceAll(form, "<the API key>");
  for (const form of [...homeForms].sort((a, b) => b.length - a.length)) out = out.replaceAll(form, "~");
  return out;
}

// Header names that carry credentials, and names that, given any value, are a credential.
const HEADER = "authorization|proxy-authorization|cookie|set-cookie|x-[a-z0-9-]*(?:api-key|token|secret)";
const ASSIGNED =
  "password|passwd|pwd|secret|client[_-]?secret|token|access[_-]?token|refresh[_-]?token|api[_-]?key|access[_-]?key|session[_-]?id";
const isHeaderName = (name: string) => new RegExp(`^(?:${HEADER})$`, "i").test(name);
const isAssignedName = (name: string) => new RegExp(`^(?:${ASSIGNED})$`, "i").test(name);
// A value: anything not empty, quoted or not (a quote, then a character that isn't the closing quote).
const VALUE = `(?:"[^"\\s]|'[^'\\s]|[^\\s"'\`,;(){}\\[\\]])`;

// The shapes of secrets, tested on one line at a time.
const shapes: [RegExp, string][] = [
  [/\bbearer\s+[A-Za-z0-9._~+/-]{8,}/i, "a bearer token"],
  [/\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}/, "a JSON web token"],
  // "Cookie: …", "cookie=…" or "Cookie":"…" (a JSON key).
  [new RegExp(`\\b(?:${HEADER})["']?\\s*[:=]\\s*${VALUE}`, "i"), "a credential header with a value"],
  // Playwright's {"name":"Cookie","value":"…"}, in either order, on one line.
  [new RegExp(`"name"\\s*:\\s*"(?:${HEADER})"\\s*,\\s*"value"\\s*:\\s*"[^"]`, "i"), "a credential header with a value"],
  [new RegExp(`"value"\\s*:\\s*"[^"]+"\\s*,\\s*"name"\\s*:\\s*"(?:${HEADER})"`, "i"), "a credential header with a value"],
  [new RegExp(`\\b(?:${ASSIGNED})["']?\\s*[:=]\\s*${VALUE}`, "i"), "a password, secret, token or key with a value"],
  // Built from two parts so this file doesn't itself look like a private key to a credential scanner.
  [new RegExp(["-----BEGIN[A-Z ]*PRIVATE", "KEY-----"].join(" ")), "a private key"],
  [/[a-z][a-z0-9+.-]*:\/\/[^\s/:@"']+:[^\s/@"']+@/i, "a password inside an address"],
  [/\b(gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|xox[abprs]-[A-Za-z0-9-]{10,}|AKIA[0-9A-Z]{16}|AIza[0-9A-Za-z_-]{30,}|sk-[A-Za-z0-9_-]{20,})/, "a well-known token kind"],
];

// The line a position in a text is on.
const lineAt = (text: string, position: number) => text.slice(0, position).split("\n").length;

// One piece of text (a line, or a JSON string's real value) against the exact values and the shapes.
function kindsIn(piece: string): Set<string> {
  const kinds = new Set<string>();
  for (const [value, kind] of exactValues) if (piece.includes(value)) kinds.add(kind);
  for (const [shape, kind] of shapes) if (shape.test(piece)) kinds.add(kind);
  return kinds;
}

// JSON, whatever its order, line breaks or escapes. Every string's real value (after escapes such as
// \u0061) is checked like a line; and a {name, value} pair naming a credential header, a key naming a
// header or a credential, or a cookie record ({name, value} with a domain, path or expiry, as in a
// browser's saved cookies), with a value that isn't empty, is reported. Each finding is reported on
// the line where it is in the text.
function scanJson(node: JsonNode, offset: number, text: string, place: string, found: Finding[]): void {
  const at = (n: JsonNode) => lineAt(text, offset + n.start);
  for (const s of jsonStrings(node)) for (const kind of kindsIn(s.value)) found.push({ place, line: at(s), kind });
  const filled = (v: JsonNode | undefined) =>
    v !== undefined && ((v.kind === "string" && v.value.trim() !== "") || (v.kind === "other" && typeof v.value === "number"));
  const walk = (n: JsonNode) => {
    if (n.kind === "array") return n.items.forEach(walk);
    if (n.kind !== "object") return;
    const field = (key: string) => n.entries.find((e) => e.key.value.toLowerCase() === key)?.value;
    const name = field("name");
    const value = field("value");
    if (name?.kind === "string" && filled(value)) {
      if (isHeaderName(name.value)) found.push({ place, line: at(value!), kind: "a credential header with a value" });
      else if (name.value !== "" && ["domain", "path", "expires", "httponly", "samesite"].some((k) => field(k) !== undefined)) {
        found.push({ place, line: at(value!), kind: "a cookie with a value" });
      }
    }
    for (const { key, value: v } of n.entries) {
      if (filled(v) && isHeaderName(key.value)) found.push({ place, line: at(v), kind: "a credential header with a value" });
      else if (filled(v) && isAssignedName(key.value)) found.push({ place, line: at(v), kind: "a password, secret, token or key with a value" });
      walk(v);
    }
  };
  walk(node);
}

function scanText(text: string, place: string, found: Finding[]): void {
  text.split(/\r?\n/).forEach((line, index) => {
    for (const kind of kindsIn(line)) found.push({ place, line: index + 1, kind });
  });
  // The whole text as one JSON document (it may span lines), or each line as one (JSON Lines).
  for (const { node, offset } of jsonDocuments(text)) scanJson(node, offset, text, place, found);
}

// Not text: no lines to report, but the exact values are still looked for, byte for byte.
function scanBytes(data: Buffer, place: string, found: Finding[], byEye: string[] | null): void {
  for (const [value, kind] of exactValues) {
    if (data.includes(Buffer.from(value, "utf8")) || data.includes(Buffer.from(value, "utf16le"))) found.push({ place, line: null, kind });
  }
  byEye?.push(place);
}

// A name (a file's path in the bundle or a zip member's) is checked for the exact values too.
function scanName(name: string, place: string, found: Finding[]): void {
  const kinds = new Set(exactValues.filter(([value]) => name.includes(value)).map(([, kind]) => `${kind}, in a name`));
  for (const kind of kinds) found.push({ place, line: null, kind });
}

function scanContent(data: Buffer, place: string, found: Finding[], byEye: string[] | null): void {
  const decoded = decodeText(data);
  if (decoded === null) scanBytes(data, place, found, byEye);
  else scanText(decoded.text, place, found);
}

type Scan = { found: Finding[]; byEye: string[]; counts: { files: number; members: number } };

function scan(folder: string): Scan {
  const result: Scan = { found: [], byEye: [], counts: { files: 0, members: 0 } };
  const walk = (dir: string) => {
    for (const name of readdirSync(dir).sort()) {
      const path = join(dir, name);
      const place = relative(folder, path);
      scanName(place, place, result.found);
      if (statSync(path).isDirectory()) {
        walk(path);
        continue;
      }
      result.counts.files++;
      const data = readFileSync(path);
      if (!name.endsWith(".zip")) {
        scanContent(data, place, result.found, result.byEye);
        continue;
      }
      const { entries, metadata } = readZipWithMetadata(data);
      for (const member of entries) {
        result.counts.members++;
        const memberPlace = `${place} › ${member.name}`;
        scanName(member.name, memberPlace, result.found);
        scanContent(member.data, memberPlace, result.found, result.byEye);
      }
      // Comments and extra fields: not pictures, so not listed to be checked by eye.
      for (const { where, data: bytes } of metadata) scanContent(bytes, `${place} › ${where}`, result.found, null);
    }
  };
  walk(folder);
  // One finding per place, line and kind (a line can match both as text and as JSON).
  const seen = new Set<string>();
  result.found = result.found.filter((f) => {
    const id = `${f.place}\u0000${f.line}\u0000${f.kind}`;
    return seen.has(id) ? false : (seen.add(id), true);
  });
  return result;
}

const shown = (f: Finding) => safe(`${f.place}${f.line === null ? "" : `:${f.line}`}  ${f.kind}`);
const message = (error: unknown) => safe(error instanceof Error ? error.message : String(error));

const folder = resolve(folderArg);
const folderShown = safe(folderArg);
try {
  if (!statSync(folder).isDirectory()) throw new Error("not a folder");
} catch {
  console.error(`${folderShown} isn't a folder.`);
  process.exit(2);
}

if (!selfTest) {
  let result: Scan;
  try {
    result = scan(folder);
  } catch (error) {
    // A file the check can't read (a damaged zip, say) is never a silent pass.
    console.error(`Couldn't check everything: ${message(error)}`);
    process.exit(2);
  }
  const { found, byEye, counts } = result;
  console.log(`Scanned ${counts.files} file(s) in ${folderShown}, including ${counts.members} member(s) inside zip files.`);
  if (found.length === 0) console.log("Found: nothing (no API key, no token, cookie or credential, no home-folder address).");
  else {
    console.log(`Found ${found.length} thing(s) (file:line and kind; the values are never shown):`);
    for (const f of found) console.log(`  ${shown(f)}`);
  }
  console.log("Not text, so check these by eye for personal data:");
  for (const place of byEye) console.log(`  ${safe(place)}`);
  console.log(found.length === 0 ? "PASS" : "FAIL");
  process.exit(found.length === 0 ? 0 : 1);
}

// Copies a folder so that every link becomes a plain file holding what it points to (Node's cpSync
// keeps links inside a folder as links even with dereference), so planting a value in the copy never
// writes through a link to a file outside it.
function copyAsFiles(from: string, to: string): void {
  mkdirSync(to, { recursive: true });
  for (const name of readdirSync(from)) {
    const path = join(from, name);
    if (statSync(path).isDirectory()) copyAsFiles(path, join(to, name));
    else writeFileSync(join(to, name), readFileSync(path));
  }
}

// Ends the self-test early with an exit code, after the temporary copy is deleted.
class SelfTestStop extends Error {
  code: number;
  constructor(code: number) {
    super("self-test stopped");
    this.code = code;
  }
}

// SELF-TEST. Everything happens inside try/finally, so the temporary copy (which holds the planted
// values, the run's key among them) is deleted whatever goes wrong.
const copy = mkdtempSync(join(tmpdir(), "failure-evidence-self-test-"));
let exitCode = 1;
try {
  copyAsFiles(folder, copy);
  // First the untouched copy must be clean: planting rewrites trace.zip (without its comments and
  // extra fields), so a value already in the bundle could otherwise be lost before the scan.
  const baseline = scan(copy);
  if (baseline.found.length > 0) {
    console.log(`Self-test on a temporary copy of ${folderShown}: the bundle itself isn't clean, so nothing was planted.`);
    for (const f of baseline.found) console.log(`  ALREADY THERE ${shown(f)}`);
    console.log("FAIL: run the scan without --self-test, and fix the bundle first.");
    throw new SelfTestStop(1);
  }
  const fake = () => randomBytes(16).toString("hex");
  const planted: { place: string; line: number; kind: string; value: string }[] = [];

  // Adds one line to the end of a text, and gives its line number.
  const appendLine = (text: string, line: string) => {
    const body = text.endsWith("\n") || text === "" ? text : `${text}\n`;
    return { text: `${body}${line}\n`, line: body.split("\n").length };
  };

  const token = `fake${fake()}`;
  const consolePath = join(copy, "console.txt");
  const consoleAdded = appendLine(readFileSync(consolePath, "utf8"), `+9.99s [log] Authorization: Bearer ${token}`);
  writeFileSync(consolePath, consoleAdded.text);
  planted.push({ place: "console.txt", line: consoleAdded.line, kind: "a bearer token", value: token });

  const cookie = `fake${fake()}`;
  const zipPath = join(copy, "trace.zip");
  const members = readZip(readFileSync(zipPath));
  const network = members.find((m) => /^\d+-trace\.network$/.test(m.name));
  if (!network) throw new Error("trace.zip has no network log to plant a cookie in");
  const networkAdded = appendLine(network.data.toString("utf8"), JSON.stringify({ type: "self-test", headers: [{ name: "Cookie", value: `session=${cookie}` }] }));
  network.data = Buffer.from(networkAdded.text, "utf8");
  writeFileSync(zipPath, writeZip(members));
  planted.push({ place: `trace.zip › ${network.name}`, line: networkAdded.line, kind: "a credential header with a value", value: cookie });

  const errorPath = join(copy, "error.txt");
  const errorAdded = appendLine(readFileSync(errorPath, "utf8"), `self-test: ${apiKey}`);
  writeFileSync(errorPath, errorAdded.text);
  planted.push({ place: "error.txt", line: errorAdded.line, kind: "the run's API key", value: apiKey });

  const { found } = scan(copy);
  console.log(`Self-test on a temporary copy of ${folderShown}: planted ${planted.length} fake value(s).`);
  let allFound = true;
  for (const p of planted) {
    const hit = found.some((f) => f.place === p.place && f.line === p.line && f.kind === p.kind);
    allFound &&= hit;
    console.log(`  ${hit ? "found    " : "MISSED   "} ${safe(`${p.place}:${p.line}  ${p.kind}`)}`);
  }
  const extra = found.filter((f) => !planted.some((p) => p.place === f.place && p.line === f.line));
  for (const f of extra) console.log(`  ALSO FOUND ${shown(f)}`);
  // The report must never show a value: none of the planted ones appears in what was printed.
  const printed = found.map(shown).join("\n");
  const leaked = planted.some((p) => printed.includes(p.value));
  if (leaked) console.log("  The report showed a planted value.");
  const passed = allFound && extra.length === 0 && !leaked;
  console.log(passed ? "PASS: every planted value was found at its file and line, and no value was shown." : "FAIL");
  exitCode = passed ? 0 : 1;
} catch (error) {
  if (error instanceof SelfTestStop) exitCode = error.code;
  else {
    console.error(`Couldn't run the self-test: ${message(error)}`);
    exitCode = 2;
  }
} finally {
  rmSync(copy, { recursive: true, force: true });
}
process.exit(exitCode);
