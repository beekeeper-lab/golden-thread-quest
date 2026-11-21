// Safety checks for the Jira synchronization and its demonstration (jira-read-assigned-stories
// quest): the failure paths that the ordinary demonstration (jira-sync-demo.sh) can't show on the
// real folder, rebuilt here so a reviewer can run them again.
//
//   node participant/tools/jira-sync-safety-demo.mjs <logs folder>   (from the repository's top folder)
//
// Everything happens inside one new temp folder. Each case builds its own throwaway copy of the
// repository there (the three tools, the practice data, and a copy of the real
// participant/context/jira/assigned folder), so the real folder is only read, never written to. Where a case needs a failure that can't be caused from outside (a rename that fails,
// a run killed at one exact point, a validator that fails), it uses a copy of a tool with one
// marked line added, made here and checked to apply exactly once; the tools themselves are not
// changed. A stand-in validator replaces the app (the app writes its results into the real
// repository, so it isn't run on copies).
//
// Writes safety-checks.txt into <logs folder> only if every case came out as expected. Exit codes:
// 0 all as expected, 1 something unexpected (nothing written), 2 setup error.

import { spawn, spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import {
  chmodSync, copyFileSync, cpSync, existsSync, linkSync, lstatSync, mkdirSync, mkdtempSync,
  readFileSync, readdirSync, realpathSync, renameSync, rmSync, symlinkSync, unlinkSync, writeFileSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { basename, join, resolve } from "node:path";

const REPO = realpathSync(process.cwd());
const TOOLS = join(REPO, "participant", "tools");
const NAME = "safety-checks.txt";
if (!existsSync(join(TOOLS, "jira-sync.mjs")) || !existsSync(join(REPO, "participant", "context", "jira", "assigned", "notes"))) {
  console.error("Run this from the repository's top folder.");
  process.exit(2);
}
if (process.argv.length !== 3) {
  console.error("Usage: node participant/tools/jira-sync-safety-demo.mjs <logs folder>");
  process.exit(2);
}
// The record must not land in the real assigned folder or its notes (compared as real paths, so
// a link to them is caught), checked before the logs folder is made.
const realOf = (p) => {
  const rest = [];
  while (!existsSync(p) && resolve(p, "..") !== p) {
    rest.unshift(basename(p));
    p = resolve(p, "..");
  }
  return join(realpathSync(p), ...rest);
};
const REAL_P = realpathSync(join(REPO, "participant", "context", "jira", "assigned"));
const inReal = (p) => p === REAL_P || p.startsWith(`${REAL_P}/`);
if (inReal(realOf(resolve(process.argv[2])))) {
  console.error("The logs folder is inside participant/context/jira/assigned; choose another one.");
  process.exit(2);
}
mkdirSync(process.argv[2], { recursive: true });
const LOGS = realpathSync(process.argv[2]);
if (inReal(LOGS)) {
  console.error("The logs folder is inside participant/context/jira/assigned; choose another one.");
  process.exit(2);
}
const target = join(LOGS, NAME);
if (existsSync(target) && (lstatSync(target).isSymbolicLink() || !lstatSync(target).isFile())) {
  console.error(`${NAME} in the logs folder is not an ordinary file; stopping.`);
  process.exit(2);
}

// Everything copied into the throwaway repositories must be ordinary files and folders: a link
// copied from the real assigned folder would still point at real data, and a case that changes
// its copy could reach through it. Checked before anything is made.
const onlyOrdinary = (dir) => {
  for (const e of readdirSync(dir)) {
    const p = join(dir, e), st = lstatSync(p);
    if (st.isDirectory()) { if (!onlyOrdinary(p)) return false; }
    else if (st.isSymbolicLink() || !st.isFile()) return false;
  }
  return true;
};
for (const d of [join(REPO, "participant", "context", "jira", "assigned"), join(REPO, "validators", "fixtures", "jira")]) {
  if (lstatSync(d).isSymbolicLink() || !onlyOrdinary(d)) {
    console.error(`${d.slice(REPO.length + 1)} holds a link or something other than ordinary files and folders; stopping.`);
    process.exit(2);
  }
}
// A path inside a stand-in validator (a bash script), quoted so spaces or quotes in it stay whole.
const sh = (p) => `'${p.replace(/'/g, "'\\''")}'`;

// The one temp folder: a fresh, validated name; removed at the end however the script ends.
const T = realpathSync(mkdtempSync(join(tmpdir(), "jira-sync-safety.")));
if (!/^jira-sync-safety\.[A-Za-z0-9]{6}$/.test(basename(T)) || readdirSync(T).length !== 0) {
  console.error("Unexpected temp folder; stopping.");
  process.exit(2);
}
const cleanup = () => {
  try {
    for (const d of walkDirs(T)) chmodSync(d, 0o755); // a case may leave a folder read-only
    rmSync(T, { recursive: true, force: true });
  } catch { /* best effort */ }
};
process.on("exit", cleanup);
for (const sig of ["SIGINT", "SIGTERM", "SIGHUP"]) process.on(sig, () => process.exit(130));

// Settings the synchronization reads are cleared, so nothing from the person's shell reaches a run.
const ENV = { ...process.env };
delete ENV.JIRA_SYNC_NOTES_LEDGER;
delete ENV.JIRA_SYNC_LOCK_TOKEN;
delete ENV.JIRA_PRACTICE_FAULT;
ENV.TMPDIR = join(T, "tmp"); // the nested demonstrations make their temp folders in here
mkdirSync(ENV.TMPDIR);

const lines = [];
let unexpected = 0;
const say = (s = "") => lines.push(s.split(T).join("<temp>"));
const expect = (what, actual, wanted) => {
  const ok = actual === wanted;
  if (!ok) unexpected++;
  say(`  ${ok ? "as expected" : "UNEXPECTED"}: ${what} = ${actual}${ok ? "" : `, expected ${wanted}`}`);
};

function walkDirs(d) {
  const out = [d];
  for (const e of readdirSync(d, { withFileTypes: true })) if (e.isDirectory()) out.push(...walkDirs(join(d, e.name)));
  return out;
}
// Fingerprint of a folder: every entry (files, folders, links, the lock) with its kind and, for
// files, its SHA-256; equal fingerprints mean byte-identical contents.
const fingerprint = (dir) => {
  const rows = [];
  const visit = (d, rel) => {
    for (const e of readdirSync(d).sort()) {
      const p = join(d, e), r = rel ? `${rel}/${e}` : e, st = lstatSync(p);
      if (st.isSymbolicLink()) rows.push(`link ${r}`);
      else if (st.isDirectory()) { rows.push(`dir ${r}`); visit(p, r); }
      else if (st.isFile()) rows.push(`file ${r} ${createHash("sha256").update(readFileSync(p)).digest("hex")}`);
      else rows.push(`other ${r}`);
    }
  };
  visit(dir, "");
  return rows.join("\n");
};
const diff = (a, b) => {
  const A = new Set(a.split("\n")), B = new Set(b.split("\n"));
  return [...[...A].filter((x) => !B.has(x)).map((x) => `- ${x}`), ...[...B].filter((x) => !A.has(x)).map((x) => `+ ${x}`)].join("; ") || "none";
};

// A copy of a tool with one marked line added: `find` must occur exactly once.
const variant = (src, find, add, dest) => {
  const text = readFileSync(src, "utf8");
  if (text.split(find).length !== 2) throw new Error(`the marked line for ${basename(dest)} doesn't apply exactly once`);
  writeFileSync(dest, text.replace(find, `${add}\n${find}`));
};
// A throwaway repository: the tools, the practice data, a copy of the real assigned folder, and a
// stand-in validator (a shell script) in place of the app.
let copies = 0;
const repoCopy = (stub = 'echo "{\\"result_path\\": \\"\\"}"') => {
  const R = join(T, `repo-${++copies}`);
  mkdirSync(join(R, "participant", "tools"), { recursive: true });
  for (const f of ["fake-jira.mjs", "jira-sync.mjs", "jira-sync-demo.sh"]) copyFileSync(join(TOOLS, f), join(R, "participant", "tools", f));
  cpSync(join(REPO, "validators", "fixtures", "jira"), join(R, "validators", "fixtures", "jira"), { recursive: true });
  cpSync(join(REPO, "participant", "context", "jira", "assigned"), join(R, "participant", "context", "jira", "assigned"), { recursive: true });
  const lock = join(R, "participant", "context", "jira", "assigned", ".jira-sync.lock");
  if (existsSync(lock)) unlinkSync(lock);
  mkdirSync(join(R, ".venv", "bin"), { recursive: true });
  writeFileSync(join(R, ".venv", "bin", "quest-app"), `#!/bin/bash\n${stub}\n`, { mode: 0o755 });
  return { R, A: join(R, "participant", "context", "jira", "assigned") };
};
const run = (cmd, args, opts = {}) => spawnSync(cmd, args, { encoding: "utf8", timeout: 120000, env: { ...ENV, ...(opts.env ?? {}) }, cwd: opts.cwd ?? REPO });
const sync = (tool, args, env = {}) => run("node", [tool, ...args], { env });
const firstLine = (r) => (r.stderr || r.stdout || "").trim().split("\n")[0];
// Runs a demonstration copy and sends `signal` once Part B has started: the stand-in validator
// (SLOW) leaves a marker file the moment it is first called.
const runSignalled = (R, logs, signal) => new Promise((done) => {
  const marker = join(R, "validator-started");
  const p = spawn("bash", ["participant/tools/jira-sync-demo.sh", logs], { cwd: R, env: ENV, stdio: ["ignore", "pipe", "pipe"] });
  let out = "";
  p.stdout.on("data", (d) => (out += d));
  p.stderr.on("data", (d) => (out += d));
  const poll = setInterval(() => {
    if (existsSync(marker)) {
      clearInterval(poll);
      p.kill(signal);
    }
  }, 200);
  p.on("exit", (code) => {
    clearInterval(poll);
    done({ code, out, reachedPartB: existsSync(marker) });
  });
});
const nestedTemps = () => readdirSync(ENV.TMPDIR).filter((n) => n.startsWith("jira-sync-demo.")).length;
const SLOW = 'touch validator-started\nsleep 20\necho "{}"';

const cases = [];
const add = (title, fn) => cases.push([title, fn]);

// ---- the demonstration, on repository copies ---------------------------------------------------
add("a validator that fails: the copy's real folder is put back byte-identical", () => {
  const { R, A } = repoCopy();
  const before = fingerprint(A);
  const r = run("bash", ["participant/tools/jira-sync-demo.sh", join(T, "logs-1")], { cwd: R });
  expect("exit code", r.status, 1);
  expect("changes to the folder", diff(before, fingerprint(A)), "none");
  expect("log written", existsSync(join(T, "logs-1", "sync-run.txt")), false);
});
add("notes made by Part B's runs are removed; a person's new note is kept", () => {
  const { R, A } = repoCopy('printf "# Notes: GTQ-777\\n\\nYour own notes on GTQ-777. The synchronization never changes this file.\\n" > participant/context/jira/assigned/notes/GTQ-777.md\necho "{\\"result_path\\": \\"\\"}"');
  for (const k of ["GTQ-201", "GTQ-202"]) unlinkSync(join(A, "notes", `${k}.md`));
  const before = fingerprint(A);
  const r = run("bash", ["participant/tools/jira-sync-demo.sh", join(T, "logs-2")], { cwd: R });
  expect("exit code", r.status, 1);
  expect("changes to the folder", diff(before, fingerprint(A)).replace(/ [0-9a-f]{64}/, ""), "+ file notes/GTQ-777.md");
  expect("says new notes were left", /left for you to check/.test(r.stdout), true);
});
add("putting back made to fail: copies and lock kept, a recovery note written", () => {
  const { R, A } = repoCopy();
  variant(join(TOOLS, "jira-sync-demo.sh"), '  [ "$PARTB" = 1 ] || return 0\n  node -e \'', "  [ \"$PARTB\" = 1 ] && return 1 # TEST ONLY: putting back fails", join(R, "participant", "tools", "jira-sync-demo.sh"));
  const r = run("bash", ["participant/tools/jira-sync-demo.sh", join(T, "logs-3")], { cwd: R });
  expect("exit code", r.status, 1);
  expect("lock left in the folder", existsSync(join(A, ".jira-sync.lock")), true);
  expect("recovery note names the saved copies", /saved copies are in: .*real-saved/.test(readFileSync(join(T, "logs-3", "sync-run.RECOVERY.txt"), "utf8")), true);
  expect("saved copies kept", nestedTemps() >= 1, true);
});
add("interrupted (TERM) during Part B: put back byte-identical", async () => {
  const { R, A } = repoCopy(SLOW);
  const before = fingerprint(A);
  const r = await runSignalled(R, join(T, "logs-4"), "SIGTERM");
  expect("signal sent during Part B", r.reachedPartB, true);
  expect("exit code", r.code, 130);
  expect("changes to the folder", diff(before, fingerprint(A)), "none");
});
add("terminal closed (HUP) during Part B: put back byte-identical", async () => {
  const { R, A } = repoCopy(SLOW);
  const before = fingerprint(A);
  const r = await runSignalled(R, join(T, "logs-5"), "SIGHUP");
  expect("signal sent during Part B", r.reachedPartB, true);
  expect("exit code", r.code, 129);
  expect("changes to the folder", diff(before, fingerprint(A)), "none");
});
add("another synchronization started during Part B is refused", () => {
  const exits = join(T, "other-exits.txt");
  const { R, A } = repoCopy(`node participant/tools/jira-sync.mjs --fixture happy-path > /dev/null 2>&1; echo "$?" >> ${sh(exits)}\necho "{\\"result_path\\": \\"\\"}"`);
  const before = fingerprint(A);
  run("bash", ["participant/tools/jira-sync-demo.sh", join(T, "logs-6")], { cwd: R });
  expect("exit codes of the other runs", readFileSync(exits, "utf8").trim().split("\n").join(","), "2,2,2,2");
  expect("changes to the folder", diff(before, fingerprint(A)), "none");
});
add("a hand-written index.md, or a stories.json with a key twice: Part B leaves the folder alone", () => {
  for (const [n, spoil] of [["7", (A) => writeFileSync(join(A, "index.md"), "# My own index\n")], ["8", (A) => {
    const d = JSON.parse(readFileSync(join(A, "stories.json"), "utf8"));
    d.stories.push(d.stories[0]);
    writeFileSync(join(A, "stories.json"), `${JSON.stringify(d, null, 2)}\n`);
  }]]) {
    const { R, A } = repoCopy();
    spoil(A);
    const before = fingerprint(A);
    const r = run("bash", ["participant/tools/jira-sync-demo.sh", join(T, `logs-${n}`)], { cwd: R });
    expect(`exit code (${n === "7" ? "index.md" : "stories.json"})`, r.status, 1);
    expect("Part B left the folder alone", /the synchronization wouldn't write to the real folder/.test(r.stdout), true);
    expect("changes to the folder", diff(before, fingerprint(A)), "none");
  }
});

// ---- the synchronization itself, on scratch folders ---------------------------------------------
const tools = join(T, "tools");
mkdirSync(join(tools, "participant", "tools"), { recursive: true });
cpSync(join(REPO, "validators", "fixtures", "jira"), join(tools, "validators", "fixtures", "jira"), { recursive: true });
copyFileSync(join(TOOLS, "fake-jira.mjs"), join(tools, "participant", "tools", "fake-jira.mjs"));
const SYNC = join(TOOLS, "jira-sync.mjs");
const toolVariant = (name, find, addLine) => {
  const dest = join(tools, "participant", "tools", `${name}.mjs`);
  variant(SYNC, find, addLine, dest);
  return dest;
};
const prepared = (name) => {
  const d = join(T, name);
  sync(SYNC, ["--fixture", "stale-item", "--phase", "previous", "--out", d]);
  return d;
};

add("the second rename forced to fail: the folder is put back byte-identical", () => {
  const v = toolVariant("rename-fails", "      renameSync(tmp, path);\n      entry[2] = true;", '      if (swapped.length === 2) throw Object.assign(new Error("forced for the test"), { code: "ETEST" }); // TEST ONLY');
  const d = prepared("s1");
  unlinkSync(join(d, "notes", "GTQ-101.md"));
  const before = fingerprint(d);
  const r = sync(v, ["--fixture", "pagination", "--out", d]);
  expect("exit code", r.status, 2);
  expect("changes to the folder", diff(before, fingerprint(d)), "none");
});
add("the put-back of a previous file forced to fail: the lock stays and the kept copy is named", () => {
  const v = join(tools, "participant", "tools", "putback-fails.mjs");
  const text = readFileSync(SYNC, "utf8")
    .replace("      renameSync(tmp, path);\n      entry[2] = true;", '      if (swapped.length === 2) throw Object.assign(new Error("forced for the test"), { code: "ETEST" }); // TEST ONLY\n      renameSync(tmp, path);\n      entry[2] = true;')
    .replace("        if (replaced && kept) renameSync(kept, path);", '        if (replaced && kept) throw new Error("put back forced to fail"); // TEST ONLY');
  writeFileSync(v, text);
  const d = prepared("s2");
  const r = sync(v, ["--fixture", "pagination", "--out", d]);
  expect("exit code", r.status, 2);
  expect("message names the kept copy", /kept as stories\.json\.\d+\.old/.test(r.stderr), true);
  expect("lock left", existsSync(join(d, ".jira-sync.lock")), true);
  expect("next run refused", sync(SYNC, ["--fixture", "pagination", "--out", d]).status, 2);
});
add("killed outright after making notes: the notes list records every notes file made", () => {
  const v = toolVariant("killed", "const summary = {", 'process.kill(process.pid, "SIGKILL"); // TEST ONLY');
  const d = join(T, "s3"), led = join(T, "s3-list.txt");
  const r = sync(v, ["--fixture", "pagination", "--out", d], { JIRA_SYNC_NOTES_LEDGER: led });
  expect("killed", r.signal, "SIGKILL");
  const made = readdirSync(join(d, "notes")).map((f) => f.replace(/\.md$/, "")).sort().join(",");
  const listed = readFileSync(led, "utf8").split("\n").filter((l) => l.startsWith("created ")).map((l) => l.slice(8)).sort().join(",");
  expect("notes made", made, "GTQ-101,GTQ-102,GTQ-201,GTQ-202");
  expect("listed as created", listed, made);
});
add("a notes list that would alias a notes file is refused, and the note is unchanged", () => {
  const d = join(T, "s4"), side = join(T, "s4-side");
  mkdirSync(join(d, "notes"), { recursive: true });
  mkdirSync(side);
  writeFileSync(join(d, "notes", "GTQ-101.md"), "# My note\n");
  symlinkSync(join(d, "notes", "GTQ-101.md"), join(side, "link.txt"));
  linkSync(join(d, "notes", "GTQ-101.md"), join(side, "hard.txt"));
  symlinkSync(join(d, "notes"), join(side, "notesdir"));
  writeFileSync(join(side, "other.txt"), "hello\n");
  const codes = ["notes/GTQ-101.md", "link", "hard link", "through a linked folder", "an unrelated file"].map((what, i) => {
    const p = [join(d, "notes", "GTQ-101.md"), join(side, "link.txt"), join(side, "hard.txt"), join(side, "notesdir", "new.txt"), join(side, "other.txt")][i];
    return sync(SYNC, ["--fixture", "happy-path", "--out", d], { JIRA_SYNC_NOTES_LEDGER: p }).status;
  });
  expect("exit codes (the note, a link, a hard link, a linked folder, another file)", codes.join(","), "2,2,2,2,2");
  expect("the note unchanged", readFileSync(join(d, "notes", "GTQ-101.md"), "utf8") === "# My note\n", true);
});
add("twenty pairs of runs started together on one folder: never both refused, never mixed", async () => {
  const d = prepared("s5");
  const one = (fixture) => new Promise((done) => {
    const p = spawn("node", [SYNC, "--fixture", fixture, "--out", d], { env: ENV, stdio: "ignore" });
    p.on("exit", (code) => done(code));
  });
  // Started together, two runs usually meet at the lock (one finishes, the other refuses), but
  // one may also finish before the other starts, and then both finish, one after the other; both
  // outcomes are correct. Never correct: neither finishing, another exit code, or a folder
  // holding files from two runs.
  let met = 0, oneAfterOther = 0, wrong = 0, mixed = 0;
  for (let i = 0; i < 20; i++) {
    const codes = (await Promise.all([one("stale-item"), one("pagination")])).sort().join(",");
    if (codes === "0,2") met++;
    else if (codes === "0,0") oneAfterOther++;
    else wrong++;
    const s = JSON.parse(readFileSync(join(d, "stories.json"), "utf8")), m = JSON.parse(readFileSync(join(d, "sync-summary.json"), "utf8"));
    if (s.synchronized_at !== m.retrieved_at) mixed++;
  }
  say(`  (pairs that met at the lock: ${met}; pairs that ran one after the other: ${oneAfterOther})`);
  expect("pairs where neither finished, or another exit code", wrong, 0);
  expect("pairs that met at the lock, at least one", met > 0, true);
  expect("times the folder held files from two runs", mixed, 0);
  expect("lock left", existsSync(join(d, ".jira-sync.lock")), false);
});
add("changes made between the first checks and the lock are caught", () => {
  for (const [name, addLine, msg] of [
    ["notes-swapped", 'renameSync(join(out, "notes"), join(out, "notes-moved")); symlinkSync(SIDE, join(out, "notes")); // TEST ONLY', /notes folder changed/],
    ["index-replaced", 'writeFileSync(targets[1], "# My own index\\n"); // TEST ONLY', /index\.md in the output folder isn't one this tool wrote/],
    ["stories-changed", 'writeFileSync(storiesPath, readFileSync(storiesPath, "utf8").replace("synchronized_at", "synchronized_at_other")); // TEST ONLY', /stories\.json changed while this run was reading Jira/],
  ]) {
    const side = join(T, `${name}-elsewhere`);
    mkdirSync(side);
    const v = join(tools, "participant", "tools", `${name}.mjs`);
    const text = readFileSync(SYNC, "utf8");
    const find = 'const token = process.env.JIRA_SYNC_LOCK_TOKEN ?? "";';
    if (text.split(find).length !== 2) throw new Error(`the marked line for ${name} doesn't apply exactly once`);
    writeFileSync(v, `import { symlinkSync, writeFileSync } from "node:fs";\nconst SIDE = ${JSON.stringify(side)};\n${text.replace(find, `${addLine}\n${find}`)}`);
    const d = prepared(name);
    unlinkSync(join(d, "notes", "GTQ-102.md"));
    const r = sync(v, ["--fixture", "stale-item", "--out", d]);
    expect(`${name}: exit code`, r.status, 2);
    expect(`${name}: message`, msg.test(r.stderr), true);
    expect(`${name}: notes/GTQ-102.md made`, existsSync(join(d, "notes", "GTQ-102.md")) || existsSync(join(d, "notes-moved", "GTQ-102.md")), false);
    expect(`${name}: files written where a link points`, readdirSync(side).length, 0);
  }
});
add("a notes file that fails partway, and a read-only notes folder: the folder is unchanged", () => {
  const v = toolVariant("partial-note", "      while (done < bytes.length) done += writeSync(fd, bytes, done, bytes.length - done);", '      if (path.endsWith("GTQ-102.md")) { writeSync(fd, bytes, 0, 5); throw Object.assign(new Error("forced for the test"), { code: "ENOSPC" }); } // TEST ONLY');
  const d = prepared("s6");
  unlinkSync(join(d, "notes", "GTQ-102.md"));
  const before = fingerprint(d);
  expect("partial write: exit code", sync(v, ["--fixture", "stale-item", "--out", d]).status, 2);
  expect("partial write: changes to the folder", diff(before, fingerprint(d)), "none");
  const d2 = prepared("s7");
  chmodSync(join(d2, "notes"), 0o555);
  const before2 = fingerprint(d2);
  const r = sync(SYNC, ["--fixture", "pagination", "--out", d2]);
  chmodSync(join(d2, "notes"), 0o755);
  expect("read-only notes: exit code", r.status, 2);
  expect("read-only notes: changes to the folder", diff(before2, fingerprint(d2)), "none");
});

add("folders a failed run made are removed, and a folder that can't be made leaves nothing", () => {
  const v = toolVariant("rename-fails-fresh", "      renameSync(tmp, path);\n      entry[2] = true;", '      if (swapped.length === 2) throw Object.assign(new Error("forced for the test"), { code: "ETEST" }); // TEST ONLY');
  const parent = join(T, "s8");
  mkdirSync(parent);
  const r = sync(v, ["--fixture", "happy-path", "--out", join(parent, "new", "assigned")]);
  expect("failure after making new folders: exit code", r.status, 2);
  expect("failure after making new folders: entries left", readdirSync(parent).length, 0);
  const ro = join(T, "s9");
  mkdirSync(ro);
  chmodSync(ro, 0o555);
  const r2 = sync(SYNC, ["--fixture", "happy-path", "--out", join(ro, "x", "assigned")]);
  chmodSync(ro, 0o755);
  expect("a folder that can't be made: exit code", r2.status, 2);
  expect("a folder that can't be made: entries left", readdirSync(ro).length, 0);
});

// ---- run every case ---------------------------------------------------------------------------
say("jira-read-assigned-stories: safety checks of the synchronization and its demonstration");
const now = new Date();
const h = now.getHours() % 12 || 12;
say(`Recorded ${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}-${now.getFullYear()} ${h}:${String(now.getMinutes()).padStart(2, "0")} ${now.getHours() < 12 ? "AM" : "PM"} with Node ${process.version}, by participant/tools/jira-sync-safety-demo.mjs.`);
say("Every case runs on throwaway copies inside one temp folder (shown as <temp>); the real folder is not changed.");
say("Cases that need a failure at one exact point use a copy of a tool with one marked TEST ONLY line added.");
let n = 0;
for (const [title, fn] of cases) {
  say();
  say(`== ${++n}. ${title} ==`);
  try {
    await fn();
  } catch (err) {
    unexpected++;
    say(`  UNEXPECTED: the case stopped: ${err.message}`);
  }
}
say();
say(`${lines.filter((l) => l.includes("as expected:")).length} expectations, ${unexpected} unexpected.`);
say("End of record.");

const text = `${lines.join("\n")}\n`;
if (text.includes(T) || text.includes(REPO) || (process.env.HOME && text.includes(process.env.HOME))) {
  console.log("The record contains a temp, repository or home folder address; it is not written.");
  process.exit(1);
}
if (unexpected) {
  console.log(text);
  console.log("Something unexpected happened; safety-checks.txt was not written.");
  process.exit(1);
}
const tmp = join(LOGS, `.${NAME}.${process.pid}.new`);
writeFileSync(tmp, text, { flag: "wx" });
renameSync(tmp, target);
console.log(`Written: ${NAME}`);
