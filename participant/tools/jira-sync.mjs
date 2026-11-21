// Synchronizes the Jira stories assigned to the authenticated user into local files, for the
// jira-read-assigned-stories quest. Read-only towards Jira. In this repository it only ever talks
// to the pretend Jira (participant/tools/fake-jira.mjs) serving one of the quest's practice data
// sets; it never connects to a real Jira.
//
//   node participant/tools/jira-sync.mjs --fixture <name> [--phase previous|current] [--out <folder>]
//
//   --fixture  happy-path, pagination, stale-item or duplicate-comment
//   --phase    "previous" serves the stale-item set as it was on the earlier run (default current)
//   --out      where the synchronized files go (default participant/context/jira/assigned in this
//              repository, wherever it is run from)
//   --check-only  only check that the output folder may be written (ordinary folders, files this
//              tool wrote or none); contacts nothing and writes nothing (exit 0 fine, 2 not)
//
// What it writes into <folder>, the three published together (see "writing" below):
//   stories.json        the normalized stories, and the stories that stopped being assigned
//   index.md            a readable index of the same
//   sync-summary.json   what this run did: pages read, totals, new, changed, removed
// and, for a story seen for the first time, an empty notes file notes/<KEY>.md, created only if
// none exists. It never opens an existing notes file for writing: notes belong to the person.
// Everything Jira sends is checked before anything is written; a run that stops with an error
// leaves the folder as it was.
//
// How a run works:
//   1. Ask Jira who the authenticated user is (myself); nothing about the user is hard-coded here
//      (the made-up account lives only in the pretend Jira, as the server's own user).
//   2. Search for stories assigned to that user, page after page, until Jira says isLast (and
//      the stories counted match Jira's total). A story assigned to anyone else is not kept.
//   3. Read each story's comments, page after page, keeping each comment id once.
//   4. Normalize each story; keep Jira-only fields under "jira_fields", apart from the normal ones.
//   5. Merge with the previous stories.json by key: a story no longer returned is moved to
//      "removed" with its last known state, never deleted; a story that comes back leaves it.
//   6. Create the missing notes files, then publish the three files together.
//
// Exit codes: 0 synchronized, 1 incomplete or unexpected answer from Jira (paging that doesn't add
// up, a key that isn't a Jira key; nothing was written), 2 usage, file or other error.

import { appendFileSync, closeSync, existsSync, linkSync, lstatSync, mkdirSync, openSync, readFileSync, realpathSync, renameSync, rmdirSync, unlinkSync, writeSync } from "node:fs";
import { basename, dirname, isAbsolute, join, relative, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";
import { FIXTURES, fakeJira } from "./fake-jira.mjs";

// Anything unexpected (a file that can't be read or written) is exit 2, never 1, which means
// "Jira's answer was incomplete".
// Whatever this run created is removed first (see removeCreatedNotes below).
let undoCreated = () => {};
process.on("uncaughtException", (err) => {
  try { undoCreated(); } catch { /* best effort */ }
  console.error(`Stopped: ${err.message}`);
  process.exit(2);
});

const HERE = dirname(fileURLToPath(import.meta.url));
const REPO = join(HERE, "..", "..");
const SITE = "https://jira.example.invalid";
// The search, as it would be sent to Jira: stories assigned to whoever is signed in.
export const JQL = "assignee = currentUser() AND issuetype = Story ORDER BY key ASC";

const usage = () => {
  console.error("Usage: node participant/tools/jira-sync.mjs --fixture <happy-path|pagination|stale-item|duplicate-comment> [--phase previous|current] [--out <folder>]\n       node participant/tools/jira-sync.mjs --check-only [--out <folder>]");
  process.exit(2);
};
let fixture = null;
let phase = "current";
let out = join(REPO, "participant", "context", "jira", "assigned");
let checkOnly = false;
const args = process.argv.slice(2);
for (let i = 0; i < args.length; i++) {
  if (args[i] === "--fixture" && i + 1 < args.length) fixture = args[++i];
  else if (args[i] === "--phase" && i + 1 < args.length) phase = args[++i];
  else if (args[i] === "--out" && i + 1 < args.length) out = args[++i];
  else if (args[i] === "--check-only") checkOnly = true;
  else usage();
}
if (checkOnly ? fixture !== null : !FIXTURES.includes(fixture) || !["previous", "current"].includes(phase)) usage();

const nowDate = new Date();
const now = nowDate.toISOString(); // machine fields keep ISO 8601
// For people: MM-DD-YYYY and a 12-hour time, in this computer's time zone.
const shownTime = (d) => {
  const p2 = (n) => String(n).padStart(2, "0");
  const h = d.getHours() % 12 || 12;
  return `${p2(d.getMonth() + 1)}-${p2(d.getDate())}-${d.getFullYear()} ${h}:${p2(d.getMinutes())} ${d.getHours() < 12 ? "AM" : "PM"}`;
};

// ---- 0. the output folder, checked before Jira is asked anything ---------------------------------
// Everything here is checked again, while holding the lock, just before writing.
// A Jira key: project letters, a hyphen, a number. Keys become file names, so nothing else passes.
const KEY = /^[A-Z][A-Z0-9_]*-[1-9][0-9]*$/;
const storiesPath = join(out, "stories.json");
let before = { stories: [], removed: [] };
// The previous run's file exactly as read: just before publishing, while holding the lock, it
// must still be exactly this, or another run (or a person) changed it meanwhile.
// Files in the output folder are read only after lstat says they are ordinary files: a link is
// not followed, and something special (a named pipe, say) is never opened, since reading one can
// wait forever. readOrdinary gives the text, null if the file is absent, or NOT_ORDINARY.
const NOT_ORDINARY = Symbol("not an ordinary file");
const readOrdinary = (path) => {
  let st;
  try {
    st = lstatSync(path);
  } catch (err) {
    if (err.code === "ENOENT") return null;
    throw err;
  }
  if (st.isSymbolicLink() || !st.isFile()) return NOT_ORDINARY;
  return readFileSync(path, "utf8");
};
const baselineText = readOrdinary(storiesPath);
if (baselineText === NOT_ORDINARY) {
  console.error("stories.json in the output folder isn't an ordinary file (it is a link or something else); nothing was written.");
  process.exit(2);
}
if (baselineText !== null) {
  let parsed;
  try {
    parsed = JSON.parse(baselineText);
  } catch {
    parsed = undefined;
  }
  // It must look like this tool's own output: an object with a list of stories and a list of
  // removed ones, each with a Jira key, no key twice, and no key in both lists. Anything else
  // is left for a person to look at.
  const okList = (l) => Array.isArray(l) && l.every((x) => x && typeof x === "object" && typeof x.key === "string" && KEY.test(x.key));
  const allKeys = parsed && typeof parsed === "object" && okList(parsed.stories) && okList(parsed.removed)
    ? [...parsed.stories, ...parsed.removed].map((x) => x.key) : null;
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed) || allKeys === null || new Set(allKeys).size !== allKeys.length) {
    console.error("The previous stories.json isn't one this tool wrote; nothing was written. Fix or move it, then run again.");
    process.exit(2);
  }
  before = parsed;
}

// The folders written into must be real folders, not links to somewhere else: creating a notes
// file "only if missing" protects the file, not the folder it lands in. Inside this repository,
// every folder from the repository down to notes is checked, so a link committed to the
// repository can't send the files elsewhere. Outside it, the folder named is used as named (on
// macOS even /tmp is a link), and it and its notes folder are checked.
const absOut = resolve(out);
const rel = relative(REPO, absOut);
const inRepo = rel === "" || (rel !== ".." && !rel.startsWith(`..${sep}`) && !isAbsolute(rel));
const dirs = [];
if (inRepo) {
  let p = REPO;
  for (const part of rel.split(sep).filter(Boolean)) dirs.push((p = join(p, part)));
} else {
  dirs.push(absOut);
}
dirs.push(join(absOut, "notes"));
// First only checked: a folder that exists must be an ordinary one. Missing folders are made
// later, once every check has passed, and removed again if the run can't finish.
const missingDirs = [];
for (const dir of dirs) {
  let st = null;
  try {
    st = lstatSync(dir);
  } catch (err) {
    if (err.code !== "ENOENT") throw err;
  }
  if (st === null) {
    missingDirs.push(dir);
  } else if (st.isSymbolicLink() || !st.isDirectory()) {
    const name = inRepo ? relative(REPO, dir) : dir === absOut ? "The output folder" : "The notes folder";
    console.error(`${inRepo ? `The folder ${name}` : name} isn't an ordinary folder (it is a link or a file); nothing was written.`);
    process.exit(2);
  } else if (missingDirs.length) {
    // An existing folder inside a missing one can't happen; stop rather than guess.
    console.error(`${dir} exists inside a missing folder; nothing was written.`);
    process.exit(2);
  }
}
// Each destination must be an ordinary file or not exist yet; anything else (a folder, a link) is
// found now, before anything is written.
const targets = ["stories.json", "index.md", "sync-summary.json"].map((f) => join(out, f));
// checkTargets runs twice: now, before anything is made, and again while holding the lock, just
// before writing, so nothing put there in between is replaced.
const checkTargets = (stop) => {
  for (const t of targets) {
    let st = null;
    try {
      st = lstatSync(t);
    } catch (err) {
      if (err.code !== "ENOENT") throw err;
    }
    if (st && (st.isSymbolicLink() || !st.isFile())) {
      stop(`${relative(absOut, t)} in the output folder isn't an ordinary file (it is a link or something else); nothing was written.`);
    }
  }
  // A file this tool is about to replace must be one it wrote (stories.json was checked above):
  // anything else in that folder under the same name is the person's, and is never replaced.
  const INDEX_START = "# My assigned Jira stories\n\nGenerated by `participant/tools/jira-sync.mjs`";
  const looksOurs = {
    [targets[1]]: (text) => text.startsWith(INDEX_START),
    [targets[2]]: (text) => {
      try {
        const d = JSON.parse(text);
        return !!d && typeof d === "object" && !Array.isArray(d) && Number.isInteger(d.pages_read) && "total_reported_by_jira" in d && "practice_set" in d;
      } catch {
        return false;
      }
    },
  };
  for (const t of [targets[1], targets[2]]) {
    const text = readOrdinary(t);
    if (text === NOT_ORDINARY) stop(`${relative(absOut, t)} in the output folder isn't an ordinary file; nothing was written.`);
    if (text !== null && !looksOurs[t](text)) {
      stop(`${relative(absOut, t)} in the output folder isn't one this tool wrote; nothing was written. Move it, then run again.`);
    }
  }
};
checkTargets((message) => {
  console.error(message);
  process.exit(2);
});
// The notes list a caller may name (JIRA_SYNC_NOTES_LEDGER, see "notes" below) must never be one
// of the person's files: it must lie outside the output folder (compared as real paths, so a link
// to it is caught), and if it already exists it must be an ordinary file with no second name
// (hard link) that holds only list lines. Checked before anything is written.
const ledger = process.env.JIRA_SYNC_NOTES_LEDGER ?? "";
if (ledger !== "") {
  const realOf = (p) => {
    const rest = [];
    while (!existsSync(p) && dirname(p) !== p) {
      rest.unshift(basename(p));
      p = dirname(p);
    }
    return join(realpathSync(p), ...rest);
  };
  const lr = realOf(resolve(ledger));
  const or = realOf(absOut);
  let bad = lr === or || lr.startsWith(`${or}${sep}`) ? "it is inside the output folder" : "";
  if (!bad) {
    let st = null;
    try { st = lstatSync(resolve(ledger)); } catch (err) { if (err.code !== "ENOENT") throw err; }
    if (st && (st.isSymbolicLink() || !st.isFile())) bad = "it isn't an ordinary file";
    else if (st && st.nlink !== 1) bad = "it has another name (a hard link)";
    else if (st && !readFileSync(resolve(ledger), "utf8").split("\n").filter(Boolean).every((l) => /^(intent|created) [A-Z][A-Z0-9_]*-[1-9][0-9]*$/.test(l))) {
      bad = "it holds something other than notes-list lines";
    }
  }
  if (bad) {
    console.error(`JIRA_SYNC_NOTES_LEDGER can't be used: ${bad}; nothing was written.`);
    process.exit(2);
  }
}

if (checkOnly) {
  console.log("The output folder is fine to write: its folders are ordinary ones and its files were written by this tool (or are absent).");
  process.exit(0);
}

const jira = fakeJira({ fixturesDir: join(REPO, "validators", "fixtures", "jira"), fixture, phase });

// ---- 1. who am I ------------------------------------------------------------------------------
const me = jira.myself();
// Without a known account every story would look "not mine" and be moved to removed: stop instead.
if (typeof me?.accountId !== "string" || me.accountId === "") {
  console.error("Incomplete: Jira didn't say who is signed in; nothing was written.");
  process.exit(1);
}

// ---- 2. every assigned story, page after page ------------------------------------------------
// Stop on anything that would make the local copy incomplete or unsafe; nothing is written.
const incomplete = (why) => {
  console.error(`Incomplete: ${why}; nothing was written.`);
  process.exit(1);
};
// Every page, of stories or of comments, must be well formed and agree with the first one: the
// same total throughout, starting where it was asked to, saying plainly (true or false) whether it
// is the last. Otherwise a page could quietly shrink the list and still look complete.
const checkPage = (page, list, wantStart, firstTotal, what) => {
  if (!page || typeof page !== "object" || !Array.isArray(page[list])) incomplete(`${what} isn't a page Jira would send`);
  if (!Number.isInteger(page.total) || page.total < 0) incomplete(`${what} gave no usable total`);
  if (firstTotal !== null && page.total !== firstTotal) incomplete(`${what} reported a total of ${page.total}, but the first page reported ${firstTotal}`);
  if (page.startAt !== wantStart) incomplete(`${what} started at ${page.startAt}, not ${wantStart} as asked`);
  if (typeof page.isLast !== "boolean") incomplete(`${what} didn't say whether it was the last`);
};
// What a story needs before it can be kept: a Jira key (it becomes a file name), and the summary
// and status every record must carry.
const checkIssue = (i, what) => {
  if (!i || typeof i !== "object" || !i.fields || typeof i.fields !== "object") incomplete(`${what} has no fields`);
  if (i.key === undefined || i.key === null) incomplete(`Jira returned ${what} with no key`);
  if (typeof i.key !== "string" || !KEY.test(i.key)) incomplete(`Jira returned ${JSON.stringify(i.key)}, which is not a Jira key`);
  if (typeof i.fields.summary !== "string") incomplete(`${i.key} has no summary`);
  if (typeof i.fields.status?.name !== "string") incomplete(`${i.key} has no status`);
  // Jira sends null for an unassigned story. Anything else must name an account: a missing or
  // broken assignee would otherwise look like "assigned to someone else" and move the story to
  // removed.
  const a = i.fields.assignee;
  if (a !== null && (!a || typeof a !== "object" || typeof a.accountId !== "string" || a.accountId === "")) {
    incomplete(`${i.key}'s assignee ${a === undefined ? "is missing" : "has no account id"}`);
  }
};
const issues = [];
let pages = 0;
let total = null;
let startAt = 0;
for (;;) {
  const page = jira.searchAssigned({ startAt, maxResults: 50 });
  pages++;
  checkPage(page, "issues", startAt, total, `page ${pages}`);
  total = page.total;
  page.issues.forEach((i, n) => checkIssue(i, `story ${startAt + n + 1}`));
  issues.push(...page.issues);
  // More than Jira said it has: it is repeating itself, so stop rather than loop forever.
  if (issues.length > total) incomplete(`Jira reported ${total} stories but sent more (${issues.length} after page ${pages})`);
  if (page.isLast) break;
  // Jira says there is more but sent nothing: stop rather than loop.
  if (page.issues.length === 0) incomplete(`Jira reported ${total} stories but page ${pages} was empty`);
  startAt += page.issues.length;
}
const keys = issues.map((i) => i.key);
if (issues.length !== total || new Set(keys).size !== keys.length) {
  incomplete(`Jira reported ${total} stories, ${issues.length} arrived (${new Set(keys).size} distinct)`);
}
const mine = issues.filter((i) => i.fields.assignee?.accountId === me.accountId);
const notMine = issues.filter((i) => i.fields.assignee?.accountId !== me.accountId).map((i) => i.key);

// ---- 3. comments, each id once ----------------------------------------------------------------
let duplicateComments = 0;
// A repeated comment id is kept once, first copy wins. When a later copy's text or author differs,
// the run says so (in sync-summary.json), so a changed copy is never dropped without a trace.
const differingDuplicates = [];
const commentsOf = (key) => {
  const seen = new Map();
  let at = 0;
  let pageNo = 0;
  let commentTotal = null;
  for (;;) {
    const page = jira.comments(key, { startAt: at });
    pageNo++;
    // The same rules as the stories: well-formed pages, one total, every comment counted.
    checkPage(page, "comments", at, commentTotal, `comment page ${pageNo} of ${key}`);
    commentTotal = page.total;
    for (const c of page.comments) {
      // A comment is kept once per id, so it must have one: two without would look like one.
      if (!c || typeof c !== "object" || typeof c.id !== "string" || c.id === "") incomplete(`a comment on ${key} has no id`);
      if (typeof c.body !== "string") incomplete(`comment ${c.id} on ${key} has no text`);
      if (c.author !== undefined && c.author !== null && (typeof c.author !== "object" || (c.author.displayName !== undefined && typeof c.author.displayName !== "string"))) {
        incomplete(`comment ${c.id} on ${key} has an author that isn't a person`);
      }
      const copy = { id: c.id, author: c.author?.displayName ?? null, body: c.body };
      if (seen.has(c.id)) {
        duplicateComments++;
        const kept = seen.get(c.id);
        if (kept.body !== copy.body || kept.author !== copy.author) differingDuplicates.push(`${key} comment ${c.id}`);
      } else {
        seen.set(c.id, copy);
      }
    }
    at += page.comments.length;
    if (at > page.total) incomplete(`${key}'s comments don't add up (Jira reported ${page.total}, ${at} arrived)`);
    if (page.isLast) {
      if (at !== page.total) incomplete(`Jira reported ${page.total} comments on ${key}, ${at} arrived`);
      break;
    }
    if (page.comments.length === 0) incomplete(`Jira reported ${page.total} comments on ${key} but comment page ${pageNo} was empty`);
  }
  return [...seen.values()];
};

// ---- 4. normalize -----------------------------------------------------------------------------
const NORMAL = new Set(["summary", "status", "priority", "assignee", "labels", "description", "parent", "created", "updated", "issuetype"]);
const normalize = (i) => ({
  key: i.key,
  source_url: `${SITE}/browse/${i.key}`,
  summary: i.fields.summary,
  status: i.fields.status?.name ?? null,
  priority: i.fields.priority?.name ?? null,
  type: i.fields.issuetype?.name ?? null,
  assignee: i.fields.assignee ? { account_id: i.fields.assignee.accountId, display_name: i.fields.assignee.displayName } : null,
  labels: i.fields.labels ?? [],
  description: i.fields.description ?? null,
  // Jira has no acceptance-criteria field of its own; a project that keeps them in a custom
  // field would map it here. None of the practice data has one.
  acceptance_criteria: null,
  parent: i.fields.parent?.key ?? null,
  created: i.fields.created ?? null,
  updated: i.fields.updated ?? null,
  retrieved_at: now,
  comments: commentsOf(i.key),
  jira_fields: Object.fromEntries(Object.entries(i.fields).filter(([k]) => !NORMAL.has(k))),
});
const stories = mine.map(normalize);

// ---- 5. merge with the previous run (read and checked in step 0) ------------------------------
const nowKeys = new Set(stories.map((s) => s.key));
const prevByKey = new Map(before.stories.map((s) => [s.key, s]));
const comparable = (s) => JSON.stringify({ ...s, retrieved_at: null });
const added = stories.filter((s) => !prevByKey.has(s.key)).map((s) => s.key);
const changed = stories.filter((s) => prevByKey.has(s.key) && comparable(prevByKey.get(s.key)) !== comparable(s)).map((s) => s.key);
// Gone now: kept, with its last known state. Already-removed stories stay removed until they
// come back.
const newlyRemoved = before.stories.filter((s) => !nowKeys.has(s.key)).map((s) => ({
  key: s.key,
  last_known_status: s.status ?? null,
  last_known_summary: s.summary ?? null,
  source_url: s.source_url ?? `${SITE}/browse/${s.key}`,
  removed_at: now,
  reason: notMine.includes(s.key) ? "assigned to someone else" : "no longer returned for the authenticated user",
  // The whole story as last synchronized (description, comments and every other field), so the
  // local copy can still say what it was about.
  last_known_record: s,
}));
const stillRemoved = before.removed.filter((r) => !nowKeys.has(r.key) && !newlyRemoved.some((n) => n.key === r.key));
const removed = [...stillRemoved, ...newlyRemoved].sort((a, b) => a.key.localeCompare(b.key, "en", { numeric: true }));
const returned = before.removed.filter((r) => nowKeys.has(r.key)).map((r) => r.key);

// ---- writing ----------------------------------------------------------------------------------
// The three generated files are published together: each is written whole to a new temporary
// name first, then each is renamed into place, with the previous one kept aside (a second name
// for the same file). If any step fails with an error, every file already replaced is put back
// and the new ones are removed. Each rename is all-or-nothing for its own file, but the three are
// separate: a run killed between two renames, or a reader looking in that same instant, can see
// files from two runs. stories.json's synchronized_at and sync-summary.json's retrieved_at are
// the same instant for one run, so a mix shows; the next run rewrites all three. Notes files are
// created only when missing ("wx"), never rewritten.
// writeNew creates a file that didn't exist ("wx") and writes it whole; if writing fails, the
// partly written file is its own, so it is removed, never left looking like a finished one.
const writeNew = (path, content) => {
  const fd = openSync(path, "wx", 0o644);
  try {
    try {
      const bytes = Buffer.from(content, "utf8");
      let done = 0;
      while (done < bytes.length) done += writeSync(fd, bytes, done, bytes.length - done);
    } finally {
      closeSync(fd);
    }
  } catch (err) {
    try { unlinkSync(path); } catch { /* already gone */ }
    throw err;
  }
};
const publish = (files) => {
  const staged = []; // [temporary name, final name]
  const swapped = []; // [final name, the previous file's kept name or null, replaced yet?]
  try {
    for (const [path, content] of files) {
      const tmp = `${path}.${process.pid}.new`;
      writeNew(tmp, content);
      staged.push([tmp, path]);
    }
    for (const [tmp, path] of staged) {
      const old = `${path}.${process.pid}.old`;
      let kept = old;
      try {
        linkSync(path, old);
      } catch (err) {
        if (err.code !== "ENOENT") throw err;
        kept = null; // there was no previous file
      }
      const entry = [path, kept, false];
      swapped.push(entry);
      renameSync(tmp, path);
      entry[2] = true;
    }
  } catch (err) {
    const notPutBack = [];
    for (const [path, kept, replaced] of swapped.reverse()) {
      try {
        if (replaced && kept) renameSync(kept, path);
        else if (replaced) unlinkSync(path);
        else if (kept) unlinkSync(kept);
      } catch {
        // The previous file is still there under its kept name; say where.
        if (replaced) notPutBack.push(kept ? `${relative(absOut, path)} (the previous one is kept as ${relative(absOut, kept)})` : relative(absOut, path));
      }
    }
    for (const [tmp] of staged) try { unlinkSync(tmp); } catch { /* already moved or gone */ }
    err.notPutBack = notPutBack;
    throw err;
  }
  for (const [, kept] of swapped) if (kept) try { unlinkSync(kept); } catch { /* already gone */ }
};
const dirsCreated = [];
const notesCreated = [];
// The notes files and folders this run created are removed again if the run can't finish
// (nobody has had a chance to write in them), so a run that stops leaves things as they were.
// rmdir removes only an empty folder.
const noteTemplate = (key) => `# Notes: ${key}\n\nYour own notes on ${key}. The synchronization never changes this file.\n`;
const lockPath = join(out, ".jira-sync.lock");
const lockText = `pid ${process.pid}, started ${now}\n`;
let lockHeld = false;
// The lock is removed only while it still holds exactly what this run wrote: if a person removed
// it and another run took a new one, that one is left alone.
const releaseLock = () => {
  if (lockHeld) {
    try {
      if (readOrdinary(lockPath) === lockText) unlinkSync(lockPath);
    } catch { /* already gone */ }
  }
  lockHeld = false;
};
process.on("exit", releaseLock);
// The order matters: the notes go while this run still holds the lock (so no other run can have
// started using them), then the lock, then the folders (rmdir removes only an empty one, so a
// folder another run has started writing in stays).
const removeCreatedNotes = () => {
  for (const key of notesCreated) {
    const notePath = join(out, "notes", `${key}.md`);
    // Removed only while still exactly the empty file this run wrote; anything else is kept.
    try {
      if (readOrdinary(notePath) === noteTemplate(key)) unlinkSync(notePath);
    } catch { /* already gone */ }
  }
  releaseLock();
  for (const dir of [...dirsCreated].reverse()) try { rmdirSync(dir); } catch { /* not empty or gone: left */ }
};
undoCreated = removeCreatedNotes;
// Now the missing folders are made (the first one outside the repository with its parents).
for (const [n, dir] of missingDirs.entries()) {
  const made = mkdirSync(dir, { recursive: n === 0 && !inRepo });
  // With parents, mkdir returns the first folder it made; every folder from there down is new.
  if (made && made !== dir) {
    for (let d = dir; d.length >= made.length; d = dirname(d)) dirsCreated.unshift(d);
  } else {
    dirsCreated.push(dir);
  }
}
// One run at a time per folder: two at once would each merge against the same previous file, and
// the later one would overwrite what the earlier one recorded (or their renames would interleave).
// A caller that already holds the lock for a longer job (the demonstration) passes the lock's
// exact contents in JIRA_SYNC_LOCK_TOKEN; the run then works under that lock and leaves it.
const token = process.env.JIRA_SYNC_LOCK_TOKEN ?? "";
if (token !== "") {
  let held = null;
  try { held = readOrdinary(lockPath); } catch { /* none */ }
  if (held !== token) {
    removeCreatedNotes();
    console.error("JIRA_SYNC_LOCK_TOKEN was given but .jira-sync.lock doesn't hold it; nothing was written.");
    process.exit(2);
  }
} else {
  try {
    writeNew(lockPath, lockText);
    lockHeld = true;
  } catch (err) {
    if (err.code !== "EEXIST") throw err;
    removeCreatedNotes();
    console.error("Another synchronization is writing to this folder, or one stopped and left it for a person to check (.jira-sync.lock is there, and says which); nothing was written. If none is running and the folder is fine, remove .jira-sync.lock and run again.");
    process.exit(2);
  }
}
// Holding the lock, the previous stories.json must still be the one merged against, and the
// other two files must still be ordinary files this tool wrote (or absent).
if (readOrdinary(storiesPath) !== baselineText) {
  removeCreatedNotes();
  console.error("stories.json changed while this run was reading Jira (another synchronization or an edit); nothing was written. Run again.");
  process.exit(2);
}
checkTargets((message) => {
  removeCreatedNotes();
  console.error(message);
  process.exit(2);
});
// And every folder written into is still an ordinary folder (not swapped for a link since the
// first check). Node has no folder-bound file calls, so a swap in the instant between this check
// and a write is not caught; that needs someone else writing in the folder (PROOF limitations).
for (const dir of dirs) {
  let st = null;
  try { st = lstatSync(dir); } catch { /* checked below */ }
  if (!st || st.isSymbolicLink() || !st.isDirectory()) {
    removeCreatedNotes();
    console.error(`${inRepo ? relative(REPO, dir) : dir === absOut ? "The output folder" : "The notes folder"} changed (it is no longer an ordinary folder); nothing was written.`);
    process.exit(2);
  }
}
// Every story's notes file must be usable: an ordinary file already there (left exactly as it
// is), or absent (an empty one is made). A folder, link or anything else there stops the run, so
// it never reports success with a story whose notes can't be opened.
for (const s of stories) {
  let st = null;
  try { st = lstatSync(join(out, "notes", `${s.key}.md`)); } catch (err) { if (err.code !== "ENOENT") throw err; }
  if (st && (st.isSymbolicLink() || !st.isFile())) {
    removeCreatedNotes();
    console.error(`notes/${s.key}.md isn't an ordinary file (it is a link or something else); nothing was written.`);
    process.exit(2);
  }
}
// A caller that may later need to undo this run's notes (the demonstration) names a list in
// JIRA_SYNC_NOTES_LEDGER: "intent KEY" is added before a notes file is made and "created KEY"
// right after, so even an interrupted run leaves a record of what it may have made. If the list
// can't be written, no notes file is made.
const note = (line) => {
  if (ledger === "") return;
  try {
    appendFileSync(ledger, `${line}\n`);
  } catch (err) {
    removeCreatedNotes();
    console.error(`Couldn't add to the notes list (${err.code ?? err.message}); nothing was written.`);
    process.exit(2);
  }
};
for (const s of stories) {
  const notePath = join(out, "notes", `${s.key}.md`);
  try {
    note(`intent ${s.key}`);
    writeNew(notePath, noteTemplate(s.key));
    notesCreated.push(s.key);
    note(`created ${s.key}`);
  } catch (err) {
    if (err.code === "EEXIST") continue; // an existing notes file is left exactly as it is
    removeCreatedNotes();
    console.error(`Couldn't create notes/${s.key}.md (${err.code ?? err.message}); nothing was written.`);
    process.exit(2);
  }
}

const summary = {
  retrieved_at: now,
  practice_set: fixture,
  phase,
  account: { account_id: me.accountId, display_name: me.displayName },
  query: JQL,
  pages_read: pages,
  total_reported_by_jira: total,
  stories_received: issues.length,
  complete: issues.length === total,
  stories: stories.length,
  new: added,
  changed,
  unchanged: stories.filter((s) => !added.includes(s.key) && !changed.includes(s.key)).map((s) => s.key),
  removed_this_run: newlyRemoved.map((r) => r.key),
  returned_this_run: returned,
  removed_total: removed.length,
  not_assigned_to_me: notMine,
  duplicate_comments_skipped: duplicateComments,
  // Repeated comment ids whose later copy differed from the kept (first) copy.
  duplicate_comments_differing: differingDuplicates,
  notes_created: notesCreated,
};

// Ticket text is shown, never trusted: line breaks become spaces, so one cell can't break the
// table, and every ASCII punctuation mark except - , ' is backslash-escaped, so a link, image,
// address, HTML tag or emphasis in a summary shows as the characters typed, never as Markdown.
const text = (v) => String(v ?? "").replace(/\s+/g, " ").trim().replace(/[!-&(-+./:-@[-`{-~]/g, "\\$&");
const row = (cells) => `| ${cells.join(" | ")} |`;
const index = [
  "# My assigned Jira stories",
  "",
  `Generated by \`participant/tools/jira-sync.mjs\` from the practice data set "${fixture}" (${phase} state), not a real Jira. Do not edit: it is rewritten on every run. Your own notes go in \`notes/<KEY>.md\`, which the synchronization never changes.`,
  "",
  `- Signed-in user (asked of Jira, not assumed): ${text(me.displayName)}`,
  `- Query: \`${JQL}\``,
  `- Pages read: ${pages}; Jira reported ${total} stories and ${issues.length} arrived, so the list is ${summary.complete ? "complete" : "INCOMPLETE"}.`,
  `- Retrieved: ${shownTime(nowDate)}`,
  "",
  "## Assigned",
  "",
  row(["Key", "Summary", "Status", "Comments", "Notes"]),
  row(["---", "---", "---", "---", "---"]),
  ...stories.map((s) => row([s.key, text(s.summary), text(s.status), s.comments.length, `notes/${s.key}.md`])),
  "",
  "## No longer assigned",
  "",
  ...(removed.length
    ? [row(["Key", "Last known summary", "Last known status", "Removed at", "Notes"]), row(["---", "---", "---", "---", "---"]), ...removed.map((r) => row([r.key, text(r.last_known_summary), text(r.last_known_status), (Number.isNaN(Date.parse(r.removed_at)) ? "unknown" : shownTime(new Date(r.removed_at))), `notes/${r.key}.md (kept)`]))]
    : ["None."]),
  "",
].join("\n");

try {
  publish([
    [targets[0], `${JSON.stringify({ synchronized_at: now, account_id: me.accountId, stories, removed }, null, 2)}\n`],
    [targets[1], index],
    [targets[2], `${JSON.stringify(summary, null, 2)}\n`],
  ]);
} catch (err) {
  if (err.notPutBack?.length) {
    // The folder now needs a person: the lock stays, so no later run changes what is to be
    // looked at. Nothing else is removed.
    lockHeld = false;
    console.error(`Couldn't put the new files in place (${err.code ?? err.message}), and couldn't put back the previous ${err.notPutBack.join(", ")}; check the folder. .jira-sync.lock is left so no run changes it until you have; remove it afterwards.`);
    process.exit(2);
  }
  removeCreatedNotes();
  console.error(`Couldn't put the new files in place (${err.code ?? err.message}); the previous files were kept and nothing was changed.`);
  process.exit(2);
}

releaseLock();
console.log(`Synchronized "${fixture}" (${phase}): ${pages} page(s), Jira reported ${total}, received ${issues.length}, complete: ${summary.complete}.`);
console.log(`  stories: ${stories.length} (new ${added.length}, changed ${changed.length}, unchanged ${summary.unchanged.length}); removed this run: ${newlyRemoved.map((r) => r.key).join(", ") || "none"}; still removed: ${removed.length}`);
console.log(`  duplicate comments skipped: ${duplicateComments} (of which differing from the kept copy: ${differingDuplicates.join(", ") || "none"}); notes files created: ${notesCreated.join(", ") || "none"} (existing notes untouched)`);
