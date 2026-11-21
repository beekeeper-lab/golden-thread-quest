#!/bin/bash
# Demonstrates the Jira synchronization (participant/tools/jira-sync.mjs) for the
# jira-read-assigned-stories quest, against the pretend Jira and the quest's practice data only.
#
#   bash participant/tools/jira-sync-demo.sh <logs folder>   (from the repository's top folder)
#
# Part A, in a new temp folder:
#   - every practice set synchronized twice, with a person's note in place: the second run changes
#     nothing and the note stays byte-identical;
#   - the eleven practice faults, each refused with its own message and no output folder made;
#   - a ticket summary full of Markdown, shown as plain characters;
#   - things in the output folder the synchronization must not write over, each refused and left
#     as it was: three stories.json files it didn't write, another run's lock, an index.md the
#     person wrote, a named pipe at stories.json (under a 10-second limit), a folder where a notes
#     file should be, and a folder where index.md should be;
#   - a notes folder that is a link, and a repository copy whose participant/context is a link.
# Part B, in the real folder (participant/context/jira/assigned), only if all of Part A came out as
# expected:
#   - it first takes the synchronization's lock (.jira-sync.lock) and holds it throughout, passing
#     its token to its own runs, so no other run can write there meanwhile;
#   - every folder from the repository down to the real notes folder must be an ordinary folder,
#     and the synchronization itself (--check-only) must accept the real folder;
#   - the real notes are fingerprinted and the three generated files copied;
#   - each practice set is synchronized twice and checked by the app's own validator
#     (`quest-app action run-validator`), ending with stale-item, whose result is the one kept;
#   - the notes that existed before are compared after.
# On any unsuccessful end (something unexpected, a record not written to its end, an interruption)
# the copies are put back, any notes file Part B's own runs are recorded as creating (the
# synchronization's notes list, written as it makes each one) that is still empty is removed,
# and the lock is released; if putting back fails, the copies and the lock are kept and named.
# Existing notes files are never written by this script.
#
# Writes sync-run.txt into <logs folder>, which can't be inside the real output folder, only if
# everything came out as expected. Exit codes: 0 all as expected, 1 something unexpected (the log
# isn't written; the real files are put back), 2 setup error.
set -u -o pipefail
# Settings the synchronization reads from the environment are cleared, so nothing in the person's
# shell (a notes list, a lock token, a practice fault) reaches a run here; each run that needs one
# is given it explicitly.
unset JIRA_SYNC_NOTES_LEDGER JIRA_SYNC_LOCK_TOKEN JIRA_PRACTICE_FAULT
REPO=$(cd -P . && printf '%s/.' "$PWD") || exit 2
REPO=${REPO%/.}
SYNC="$REPO/participant/tools/jira-sync.mjs"
APP="$REPO/.venv/bin/quest-app"
REAL="$REPO/participant/context/jira/assigned"
[ -f "$SYNC" ] && [ -x "$APP" ] && [ -d "$REAL/notes" ] || { echo "Run this from the repository's top folder (with the app installed and the notes folder present)."; exit 2; }
[ $# -eq 1 ] || { echo "Usage: bash participant/tools/jira-sync-demo.sh <logs folder>"; exit 2; }
# Every folder from the repository down to the real notes folder must be an ordinary folder, so
# nothing this script copies, removes or puts back can reach through a link to somewhere else.
for d in participant participant/context participant/context/jira participant/context/jira/assigned participant/context/jira/assigned/notes; do
  if [ -L "$REPO/$d" ] || [ ! -d "$REPO/$d" ]; then echo "$d isn't an ordinary folder (it is a link or missing); stopping."; exit 2; fi
done
# The log must not land among the files this script checks and replaces: not in the real output
# folder or its notes folder (compared as real paths, so a link to them is caught too). This is
# checked before the logs folder is made: the nearest folder that already exists is resolved and
# the rest of the path added to it.
REAL_P=$(cd -P -- "$REAL" && printf '%s/.' "$PWD") || exit 2
REAL_P=${REAL_P%/.}
WANT=$(node -e '
  const fs = require("fs"), path = require("path");
  let p = path.resolve(process.argv[1]), rest = [];
  while (!fs.existsSync(p)) { rest.unshift(path.basename(p)); p = path.dirname(p); }
  console.log(path.join(fs.realpathSync(p), ...rest));
' "$1") || exit 2
case "$WANT/" in
  "$REAL_P/"*) echo "The logs folder is inside participant/context/jira/assigned; choose another one."; exit 2 ;;
esac
mkdir -p "$1" || exit 2
LOGS=$(cd -P -- "$1" && printf '%s/.' "$PWD") || exit 2
LOGS=${LOGS%/.}
case "$LOGS/" in
  "$REAL_P/"*) echo "The logs folder is inside participant/context/jira/assigned; choose another one."; exit 2 ;;
esac
NAME=sync-run.txt
if [ -L "$LOGS/$NAME" ] || { [ -e "$LOGS/$NAME" ] && [ ! -f "$LOGS/$NAME" ]; }; then
  echo "$NAME in the logs folder is not an ordinary file; stopping."; exit 2
fi

# The terminal, kept as file descriptor 3, so messages about putting files back reach the person
# even while the log is being written.
exec 3>&1
T=$(mktemp -d "${TMPDIR:-/tmp}/jira-sync-demo.XXXXXX") || exit 2
[ -n "$T" ] && [ -d "$T" ] && [ ! -L "$T" ] || { echo "Couldn't make the temp folder."; exit 2; }
T=$(cd -P -- "$T" && printf '%s/.' "$PWD") || exit 2
T=${T%/.}
case "$(basename "$T")" in
  jira-sync-demo.??????) ;;
  *) echo "Unexpected temp folder; stopping."; exit 2 ;;
esac
[ -z "$(ls -A "$T")" ] || { echo "The temp folder isn't new; stopping."; exit 2; }
cleanup() { rm -rf -- "$T"; }
GENERATED="stories.json index.md sync-summary.json"
PARTB=0
LOCKTOKEN=""
# release_lock: remove the real folder's .jira-sync.lock if it still holds this script's token.
release_lock() {
  [ -n "$LOCKTOKEN" ] || return 0
  node -e '
    const fs = require("fs"), [lock, token] = process.argv.slice(1);
    try { if (fs.readFileSync(lock, "utf8") === token) fs.unlinkSync(lock); } catch { /* gone */ }
  ' "$REAL/.jira-sync.lock" "$LOCKTOKEN"
  LOCKTOKEN=""
}
# restore_real: put the real folder's three generated files back as they were before Part B (a
# file that didn't exist then is removed). Each copy goes to a new name, then is renamed into place.
# A notes file that didn't exist before Part B was created by its runs: it is removed only if it
# is still exactly the empty file the synchronization writes; anything else in it is kept.
restore_real() {
  [ "$PARTB" = 1 ] || return 0
  node -e '
    const fs = require("fs"), [real, saved, before, created, ...names] = process.argv.slice(1);
    let failed = 0;
    // First the three generated files, each on its own, so one failure never stops the others.
    for (const f of names) {
      const target = `${real}/${f}`, copy = `${saved}/${f}`;
      try {
        if (fs.existsSync(copy)) {
          const tmp = `${target}.${process.pid}.restore`;
          try {
            fs.copyFileSync(copy, tmp, fs.constants.COPYFILE_EXCL);
            fs.renameSync(tmp, target);
          } catch (e) {
            // Only a copy this attempt made is removed; "already exists" means it is not ours.
            if (e.code !== "EEXIST") try { fs.unlinkSync(tmp); } catch { /* not made */ }
            throw e;
          }
        } else {
          try { fs.unlinkSync(target); } catch (e) { if (e.code !== "ENOENT") throw e; }
        }
      } catch (e) {
        failed++;
        console.log(`  couldn'"'"'t put back ${f} (${e.code ?? e.message})`);
      }
    }
    // Then the notes files Part B'"'"'s own runs created: the synchronization writes "created KEY"
    // to the notes list right after making one. Only those, still empty, are removed. Any other
    // new notes file (an "intent" without "created", or one nobody listed) is kept and named, and
    // then the folder is not reported as it was.
    let left = 0;
    try {
      const had = new Set(fs.readFileSync(before, "utf8").split("\n").filter(Boolean).map((l) => JSON.parse(l.slice(l.indexOf(" ") + 1))));
      let ours = new Set();
      try {
        ours = new Set(fs.readFileSync(created, "utf8").split("\n").filter((l) => l.startsWith("created ")).map((l) => l.slice(8)));
      } catch (e) { if (e.code !== "ENOENT") throw e; }
      for (const f of fs.readdirSync(`${real}/notes`)) {
        if (had.has(f)) continue;
        try {
          const m = /^([A-Z][A-Z0-9_]*-[1-9][0-9]*)\.md$/.exec(f);
          const template = m && `# Notes: ${m[1]}\n\nYour own notes on ${m[1]}. The synchronization never changes this file.\n`;
          const st = fs.lstatSync(`${real}/notes/${f}`);
          if (m && ours.has(m[1]) && st.isFile() && fs.readFileSync(`${real}/notes/${f}`, "utf8") === template) fs.unlinkSync(`${real}/notes/${f}`);
          else { left++; console.log(`  kept notes/${f}: it is new since Part B began, but not an empty notes file Part B'"'"'s own runs are recorded as creating.`); }
        } catch (e) {
          failed++;
          console.log(`  couldn'"'"'t check notes/${f} (${e.code ?? e.message})`);
        }
      }
    } catch (e) {
      failed++;
      console.log(`  couldn'"'"'t check the notes folder (${e.code ?? e.message})`);
    }
    process.exit(failed ? 1 : left ? 3 : 0);
  ' "$REAL" "$T/real-saved" "$T/real-notes-before" "$T/partb-created" $GENERATED >&3 2>&3
  case $? in
    0) echo "The real folder was put back as it was." >&3 ;;
    3) echo "The real folder's three generated files were put back; the new notes files named above were left for you to check." >&3 ;;
    *) return 1 ;;
  esac
}
# give_up <code>: on any unsuccessful end, put the real files back first; the temp folder (with the
# saved copies) is removed only if that worked, otherwise it is kept and named.
give_up() {
  if restore_real; then
    release_lock
    cleanup
  else
    echo "Couldn't put the real generated files back; the saved copies are kept in $T/real-saved, and .jira-sync.lock is left in place." >&3
    # Also on disk, beside where the log would go, in case no terminal is there to show it. It is
    # created only if nothing has that name (wx: never through a link, never over a file).
    node -e '
      const fs = require("fs"), [path, saved] = process.argv.slice(1);
      fs.writeFileSync(path, `The demonstration stopped and could not put the real generated files back.\nThe saved copies are in: ${saved}\n.jira-sync.lock was left in participant/context/jira/assigned on purpose.\n`, { flag: "wx" });
    ' "$LOGS/sync-run.RECOVERY.txt" "$T/real-saved" 2>/dev/null \
      || echo "Couldn't write sync-run.RECOVERY.txt (something has that name already); nothing there was changed." >&3
  fi
  exit "$1"
}
trap 'give_up 130' INT TERM
# A closed terminal (HUP) is treated the same way; its messages go nowhere, since the terminal is
# gone, so writing them can't stop the files being put back.
trap 'exec 3>/dev/null; give_up 129' HUP
FAIL=0
OUT="$T/$NAME"
END_LINE="End of record."

# notes_print <folder>: SHA-256 of every notes file, one per line: the hash, a space, then the
# file name as a JSON string (so a name with spaces or anything else stays whole). Exit 1 if any
# entry isn't an ordinary file or can't be read; callers treat that as unexpected.
notes_print() {
  node -e '
    const fs = require("fs"), c = require("crypto"), d = process.argv[1];
    try {
      for (const f of fs.readdirSync(d).sort()) {
        // Only ordinary files are read (a named pipe could make reading wait forever).
        const st = fs.lstatSync(`${d}/${f}`);
        if (st.isSymbolicLink() || !st.isFile()) process.exit(1);
        console.log(c.createHash("sha256").update(fs.readFileSync(`${d}/${f}`)).digest("hex"), JSON.stringify(f));
      }
    } catch { process.exit(1); }
  ' "$1/notes"
}
# field <stories.json> <js expression over d>: a value from a stories or summary file
field() { node -e 'const d = JSON.parse(require("fs").readFileSync(process.argv[1], "utf8")); console.log(eval(process.argv[2]))' "$1" "$2"; }
expect() {  # expect <description> <actual> <wanted>
  if [ "$2" = "$3" ]; then echo "  as expected: $1 = $2"; else echo "  UNEXPECTED: $1 = $2, expected $3"; FAIL=1; fi
}
run_sync() {  # run_sync <folder> <args...>: a synchronization, its output shown without temp paths
  local dir=$1 out code
  shift
  echo "\$ node jira-sync.mjs $* --out $( [ "$dir" = "$REAL" ] && echo participant/context/jira/assigned || echo "${dir#"$T/"}")"
  # In the real folder, Part B holds the lock and passes its token, and has the synchronization
  # list the notes it makes (so putting back can undo exactly those); elsewhere neither is given.
  local tok="" led=""
  [ "$dir" = "$REAL" ] && tok=$LOCKTOKEN && led="$T/partb-created"
  out=$(cd "$REPO" && JIRA_SYNC_LOCK_TOKEN="$tok" JIRA_SYNC_NOTES_LEDGER="$led" node "$SYNC" "$@" --out "$dir" </dev/null 2>&1); code=$?
  printf '%s\n' "${out//"$T/"/}"
  return $code
}
NOTE="# Notes: GTQ-101

A person's note (made-up): asked about the edge case; answer pending.
"

{
  echo "jira-read-assigned-stories: synchronization runs and validator checks"
  echo "Recorded $(date '+%m-%d-%Y %I:%M %p' | sed -E 's/ 0([0-9]:)/ \1/') with Node $(node --version), by participant/tools/jira-sync-demo.sh."
  echo "Source: the pretend Jira (participant/tools/fake-jira.mjs) serving the quest's practice data"
  echo "(validators/fixtures/jira/). No real Jira is contacted. Part A folders are relative to a temp folder."
  echo

  echo "=================== Part A: each practice set, synchronized twice ==================="
  for set in happy-path pagination duplicate-comment stale-item; do
    echo
    echo "== $set =="
    D="$T/$set"
    mkdir -p "$D/notes"
    printf '%s' "$NOTE" > "$D/notes/GTQ-101.md"
    if [ "$set" = stale-item ]; then first="--phase previous"; else first=""; fi
    # shellcheck disable=SC2086
    run_sync "$D" --fixture "$set" $first || { echo "  UNEXPECTED: the first run failed"; FAIL=1; }
    notes_print "$D" > "$T/$set.before" || { echo "  UNEXPECTED: couldn't fingerprint the notes"; FAIL=1; }
    run_sync "$D" --fixture "$set" || { echo "  UNEXPECTED: the second run failed"; FAIL=1; }
    notes_print "$D" > "$T/$set.after" || { echo "  UNEXPECTED: couldn't fingerprint the notes"; FAIL=1; }
    echo "Checked after the second run:"
    if cmp -s "$T/$set.before" "$T/$set.after"; then echo "  as expected: every notes file is byte-identical across the second run (SHA-256 before and after):"; sed 's/^/    /' "$T/$set.after"; else echo "  UNEXPECTED: a notes file changed"; diff "$T/$set.before" "$T/$set.after"; FAIL=1; fi
    expect "the person's note GTQ-101.md" "$(cat "$D/notes/GTQ-101.md")" "$(printf '%s' "$NOTE")"
    S="$D/sync-summary.json"; J="$D/stories.json"
    expect "list complete (stories received = Jira's total, and Jira said it was the last page)" "$(field "$S" 'd.complete')" true
    if [ "$set" = stale-item ]; then
      expect "removed this run" "$(field "$S" 'd.removed_this_run.join(",")')" GTQ-100
      expect "removed story kept with its last known status" "$(field "$J" 'd.removed.map(r => r.key + " " + r.last_known_status).join(",")')" "GTQ-100 In Progress"
      expect "removed story's whole last-known record kept (key, status, fields listed)" "$(field "$J" 'd.removed.map(r => [r.last_known_record.key, r.last_known_record.status, Object.keys(r.last_known_record).length].join(" ")).join(",")')" "GTQ-100 In Progress 16"
      expect "removed story's notes file kept" "$( [ -f "$D/notes/GTQ-100.md" ] && echo kept || echo missing)" kept
    else
      expect "new and changed stories on the second run" "$(field "$S" 'd.new.length + d.changed.length')" 0
    fi
    case "$set" in
      pagination) expect "pages read" "$(field "$S" 'd.pages_read')" 2; expect "stories" "$(field "$J" 'd.stories.map(s => s.key).join(",")')" "GTQ-101,GTQ-102,GTQ-201,GTQ-202" ;;
      duplicate-comment) expect "GTQ-101's comments, each id once" "$(field "$J" 'd.stories.find(s => s.key === "GTQ-101").comments.map(c => c.id).join(",")')" "9001,9002"; expect "duplicate comments skipped" "$(field "$S" 'd.duplicate_comments_skipped')" 1; expect "repeated comments whose later copy differed (first copy kept)" "$(field "$S" 'd.duplicate_comments_differing.join(",")')" "GTQ-101 comment 9001" ;;
      happy-path) expect "pages read" "$(field "$S" 'd.pages_read')" 1 ;;
    esac
  done

  echo
  echo "=================== Part A: the pretend Jira misbehaving ==================="
  # <fault> <practice set> <the message it must give>
  while read -r fault set msg; do
    echo
    echo "== practice fault: $fault =="
    D="$T/fault-$fault"
    echo "\$ JIRA_PRACTICE_FAULT=$fault node jira-sync.mjs --fixture $set --out fault-$fault"
    out=$(cd "$REPO" && JIRA_PRACTICE_FAULT=$fault node "$SYNC" --fixture "$set" --out "$D" </dev/null 2>&1); code=$?
    printf '%s\n' "${out//"$T/"/}"
    expect "exit code" "$code" 1
    expect "message" "$out" "$msg"
    expect "output folder made" "$( [ -e "$D" ] && echo yes || echo no)" no
  done <<'FAULTS'
empty-page pagination Incomplete: Jira reported 4 stories but page 3 was empty; nothing was written.
wrong-total pagination Incomplete: Jira reported 5 stories, 4 arrived (4 distinct); nothing was written.
repeat-page pagination Incomplete: page 2 started at 0, not 2 as asked; nothing was written.
shrinking-total pagination Incomplete: page 2 reported a total of 3, but the first page reported 4; nothing was written.
comment-gap duplicate-comment Incomplete: Jira reported 3 comments on GTQ-101 but comment page 1 was empty; nothing was written.
comment-no-id duplicate-comment Incomplete: a comment on GTQ-101 has no id; nothing was written.
unsafe-key pagination Incomplete: Jira returned "../GTQ-101", which is not a Jira key; nothing was written.
missing-key pagination Incomplete: Jira returned story 1 with no key; nothing was written.
missing-summary pagination Incomplete: GTQ-101 has no summary; nothing was written.
assignee-no-id pagination Incomplete: GTQ-101's assignee has no account id; nothing was written.
comment-bad-body duplicate-comment Incomplete: comment 9001 on GTQ-101 has no text; nothing was written.
FAULTS

  echo
  echo "== ticket text full of Markdown and HTML (practice twist: markdown-summary) =="
  D="$T/markdown"
  echo "\$ JIRA_PRACTICE_FAULT=markdown-summary node jira-sync.mjs --fixture pagination --out markdown"
  out=$(cd "$REPO" && JIRA_PRACTICE_FAULT=markdown-summary node "$SYNC" --fixture pagination --out "$D" </dev/null 2>&1); code=$?
  printf '%s\n' "${out//"$T/"/}"
  expect "exit code" "$code" 0
  echo "  GTQ-101's row in index.md:"
  grep -F '| GTQ-101 |' "$D/index.md" | sed 's/^/    /'
  expect "the link, image and tag shown as typed (every mark escaped)" "$(node -e '
    const t = require("fs").readFileSync(process.argv[1], "utf8");
    const row = t.split("\n").find((l) => l.startsWith("| GTQ-101 |")) ?? "";
    console.log(row.includes("\\[click me\\]\\(https\\:") && row.includes("\\!\\[x\\]") && row.includes("\\<b\\>") && !/(^|[^\\])[<[!*]/.test(row.replace(/^\| GTQ-101 \|/, "")) ? "yes" : "no");
  ' "$D/index.md")" yes

  # <case name> <previous stories.json content>
  while read -r name content; do
    echo
    echo "== a previous stories.json this tool didn't write ($name): $content =="
    D="$T/not-ours-$name"
    mkdir -p "$D"
    printf '%s\n' "$content" > "$D/stories.json"
    run_sync "$D" --fixture happy-path; code=$?
    expect "exit code" "$code" 2
    expect "the previous stories.json, left as it was" "$(cat "$D/stories.json")" "$content"
    expect "files in the folder (only that stories.json)" "$(ls -A "$D" | tr '\n' ' ')" "stories.json "
  done <<'PREVIOUS'
null null
no-lists {}
same-key-twice {"stories":[{"key":"GTQ-101"},{"key":"GTQ-101"}],"removed":[]}
PREVIOUS

  echo
  echo "== a notes folder that is a link to another folder =="
  D="$T/linked-notes"
  mkdir -p "$D" "$T/somewhere-else"
  ln -s "$T/somewhere-else" "$D/notes"
  run_sync "$D" --fixture happy-path; code=$?
  expect "exit code" "$code" 2
  expect "files written where the link points" "$(ls -A "$T/somewhere-else" | wc -l | tr -d ' ')" 0
  expect "files in the folder (only the link)" "$(ls -A "$D" | tr '\n' ' ')" "notes "

  echo
  echo "== another synchronization's lock in the output folder =="
  D="$T/locked"
  run_sync "$D" --fixture stale-item --phase previous > /dev/null || { echo "  UNEXPECTED: the setup run failed"; FAIL=1; }
  printf 'held by another run (made-up)\n' > "$D/.jira-sync.lock"
  before=$(cd "$D" && find . -type f | LC_ALL=C sort | while IFS= read -r f; do printf '%s ' "$f"; cksum < "$f"; done)
  run_sync "$D" --fixture stale-item; code=$?
  expect "exit code" "$code" 2
  expect "every file in the folder unchanged, the other lock kept" "$( [ "$(cd "$D" && find . -type f | LC_ALL=C sort | while IFS= read -r f; do printf '%s ' "$f"; cksum < "$f"; done)" = "$before" ] && echo yes || echo no)" yes

  echo
  echo "== an index.md the person wrote, in the output folder =="
  D="$T/own-index"
  mkdir -p "$D"
  printf '# My own index\n\nWritten by hand (made-up).\n' > "$D/index.md"
  run_sync "$D" --fixture happy-path; code=$?
  expect "exit code" "$code" 2
  expect "the person's index.md, left as it was" "$(cat "$D/index.md")" "$(printf '# My own index\n\nWritten by hand (made-up).')"
  expect "files in the folder (only that index.md)" "$(ls -A "$D" | tr '\n' ' ')" "index.md "

  echo
  echo "== a named pipe where stories.json should be (reading one could wait forever) =="
  D="$T/pipe"
  mkdir -p "$D"
  mkfifo "$D/stories.json"
  echo "\$ node jira-sync.mjs --check-only --out pipe   (stopped after 10 s if it waits)"
  out=$(cd "$REPO" && node -e '
    const r = require("child_process").spawnSync("node", process.argv.slice(1), { timeout: 10000, encoding: "utf8" });
    if (r.error?.code === "ETIMEDOUT") { console.log("waited 10 s and was stopped"); process.exit(9); }
    process.stdout.write(r.stderr); process.exit(r.status ?? 9);
  ' "$SYNC" --check-only --out "$D" </dev/null 2>&1); code=$?
  printf '%s\n' "${out//"$T/"/}"
  expect "exit code" "$code" 2
  expect "files in the folder (only the pipe)" "$(ls -A "$D" | tr '\n' ' ')" "stories.json "

  echo
  echo "== a folder where a story's notes file should be (notes/GTQ-101.md) =="
  D="$T/notes-folder"
  mkdir -p "$D/notes/GTQ-101.md"
  run_sync "$D" --fixture happy-path; code=$?
  expect "exit code" "$code" 2
  expect "files and folders in the output folder (only notes)" "$(ls -A "$D" | tr '\n' ' ')" "notes "
  expect "entries in notes (only that folder)" "$(ls -A "$D/notes" | tr '\n' ' ')" "GTQ-101.md "

  echo
  echo "== a folder where index.md should be =="
  D="$T/blocked-index"
  run_sync "$D" --fixture stale-item --phase previous > /dev/null || { echo "  UNEXPECTED: the setup run failed"; FAIL=1; }
  node -e 'require("fs").unlinkSync(process.argv[1])' "$D/index.md" && mkdir "$D/index.md"
  notes_print "$D" > "$T/blocked-before" || { echo "  UNEXPECTED: couldn't fingerprint the notes"; FAIL=1; }
  before=$(cat "$D/stories.json" "$D/sync-summary.json")
  run_sync "$D" --fixture stale-item; code=$?
  expect "exit code" "$code" 2
  expect "stories.json and sync-summary.json unchanged" "$( [ "$(cat "$D/stories.json" "$D/sync-summary.json")" = "$before" ] && echo yes || echo no)" yes
  notes_print "$D" > "$T/blocked-after" || { echo "  UNEXPECTED: couldn't fingerprint the notes"; FAIL=1; }
  expect "notes files unchanged" "$(cmp -s "$T/blocked-before" "$T/blocked-after" && echo yes || echo no)" yes
  expect "files in the folder" "$(ls -A "$D" | tr '\n' ' ')" "index.md notes stories.json sync-summary.json "

  echo
  echo "== a copy of the repository whose participant/context folder is a link to another folder =="
  C="$T/repo-copy"
  mkdir -p "$C/participant/tools" "$C/validators/fixtures" "$T/linked-target"
  cp "$SYNC" "$REPO/participant/tools/fake-jira.mjs" "$C/participant/tools/"
  cp -R "$REPO/validators/fixtures/jira" "$C/validators/fixtures/"
  ln -s "$T/linked-target" "$C/participant/context"
  echo "\$ node <copy>/participant/tools/jira-sync.mjs --fixture happy-path   (the default output folder)"
  out=$(cd "$C" && node "$C/participant/tools/jira-sync.mjs" --fixture happy-path </dev/null 2>&1); code=$?
  printf '%s\n' "${out//"$T/"/}"
  expect "exit code" "$code" 2
  expect "message" "$out" "The folder participant/context isn't an ordinary folder (it is a link or a file); nothing was written."
  expect "files written where the link points" "$(find "$T/linked-target" -type f | wc -l | tr -d ' ')" 0

  echo
  echo "=================== Part B: the real folder, checked by the app's own validator ==================="
  if [ "$FAIL" != 0 ]; then
    echo "  UNEXPECTED: Part A didn't all come out as expected, so the real folder is left alone."
  elif ! LOCKTOKEN=$(node -e '
      // Part B takes the synchronization lock first and holds it throughout, so no other run can
      // write here between its checks and its last put-back.
      const fs = require("fs"), c = require("crypto"), lock = process.argv[1];
      const token = `jira-sync-demo ${c.randomBytes(12).toString("hex")}`;
      fs.writeFileSync(lock, token, { flag: "wx" });
      process.stdout.write(token);
    ' "$REAL/.jira-sync.lock"); then
    LOCKTOKEN=""
    echo "  UNEXPECTED: another synchronization holds the real folder (.jira-sync.lock), so it is left alone."; FAIL=1
  elif ! node -e '
      const fs = require("fs"), [real, ...names] = process.argv.slice(1);
      for (const f of names) {
        let st;
        try { st = fs.lstatSync(`${real}/${f}`); } catch (e) { if (e.code === "ENOENT") continue; throw e; }
        if (!st.isFile() || st.isSymbolicLink()) { console.log(`  ${f} is not an ordinary file.`); process.exit(1); }
      }
    ' "$REAL" $GENERATED; then
    echo "  UNEXPECTED: a generated file in the real folder is a link or not a file, so the real folder is left alone."; FAIL=1
    release_lock
  elif ! (cd "$REPO" && JIRA_SYNC_LOCK_TOKEN="$LOCKTOKEN" node "$SYNC" --check-only --out "$REAL" </dev/null 2>&1 | sed "s|^|  |"); then
    # The synchronization's own checks (--check-only), so Part B replaces only what it would.
    echo "  UNEXPECTED: the synchronization wouldn't write to the real folder, so it is left alone."; FAIL=1
    release_lock
  elif ! notes_print "$REAL" > "$T/real-notes-before"; then
    echo "  UNEXPECTED: couldn't fingerprint the real notes, so the real folder is left alone."; FAIL=1
    release_lock
  elif ! node -e '
      const fs = require("fs"), [real, saved, ...names] = process.argv.slice(1);
      fs.mkdirSync(saved);
      for (const f of names) if (fs.existsSync(`${real}/${f}`)) fs.copyFileSync(`${real}/${f}`, `${saved}/${f}`, fs.constants.COPYFILE_EXCL);
    ' "$REAL" "$T/real-saved" $GENERATED; then
    echo "  UNEXPECTED: couldn't copy the real generated files first, so the real folder is left alone."; FAIL=1
    release_lock
  else
  PARTB=1
  echo "The three generated files were copied first, to be put back if anything goes wrong."
  echo "Notes files in participant/context/jira/assigned/notes before Part B (SHA-256):"
  sed 's/^/  /' "$T/real-notes-before"
  for set in happy-path pagination duplicate-comment stale-item; do
    echo
    echo "== $set =="
    # A fresh start for each set: only the three generated files are removed, never the notes.
    node -e 'const fs = require("fs"); for (const f of ["stories.json", "index.md", "sync-summary.json"]) { try { fs.unlinkSync(`${process.argv[1]}/${f}`); } catch (e) { if (e.code !== "ENOENT") throw e; } }' "$REAL" || FAIL=1
    if [ "$set" = stale-item ]; then first="--phase previous"; else first=""; fi
    # shellcheck disable=SC2086
    run_sync "$REAL" --fixture "$set" $first || { echo "  UNEXPECTED: the first run failed"; FAIL=1; }
    run_sync "$REAL" --fixture "$set" || { echo "  UNEXPECTED: the second run failed"; FAIL=1; }
    echo "\$ quest-app action run-validator --quest jira-read-assigned-stories --validator validate-jira-read-assigned --param fixture_set=$set"
    res=$(cd "$REPO" && "$APP" action run-validator --quest jira-read-assigned-stories --validator validate-jira-read-assigned --param "fixture_set=$set" --json 2>&1)
    path=$(printf '%s' "$res" | node -e 'let s="";process.stdin.on("data",c=>s+=c).on("end",()=>{try{const d=JSON.parse(s);console.log(d.result_path||"")}catch{console.log("")}})')
    if [ -z "$path" ] || [ ! -f "$REPO/$path" ]; then echo "  UNEXPECTED: the validator gave no result"; FAIL=1; continue; fi
    echo "  result: $path"
    node -e '
      const d = JSON.parse(require("fs").readFileSync(process.argv[1], "utf8"));
      console.log(`  outcome: ${d.outcome} (fixture_set ${d.environment.parameter_fixture_set}, network ${d.environment.network})`);
      for (const c of d.checks) console.log(`    ${c.outcome.toUpperCase().padEnd(5)} ${c.id}: ${c.summary} (${c.evidence})`);
    ' "$REPO/$path"
    expect "validator outcome" "$(field "$REPO/$path" 'd.outcome')" pass
    expect "checks that didn't pass" "$(field "$REPO/$path" 'd.checks.filter(c => c.outcome !== "pass").length')" 0
  done
  notes_print "$REAL" > "$T/real-notes-after" || { echo "  UNEXPECTED: couldn't fingerprint the real notes after Part B"; FAIL=1; }
  echo
  echo "Notes files that existed before Part B, compared after it:"
  node -e '
    const fs = require("fs"), [a, b] = process.argv.slice(1);
    // Each line: the hash, one space, the file name as a JSON string.
    const parse = (l) => { const i = l.indexOf(" "); return [JSON.parse(l.slice(i + 1)), l.slice(0, i)]; };
    const lines = (p) => fs.readFileSync(p, "utf8").split("\n").filter(Boolean);
    const after = new Map(lines(b).map(parse));
    let bad = 0;
    for (const l of lines(a)) {
      const [f, h] = parse(l);
      const same = after.get(f) === h;
      if (!same) bad++;
      console.log(`  ${same ? "identical" : "CHANGED"}  ${f}`);
    }
    process.exit(bad ? 1 : 0);
  ' "$T/real-notes-before" "$T/real-notes-after" || { echo "  UNEXPECTED: a notes file changed"; FAIL=1; }
  echo
  echo "The repository keeps the stale-item result: stories.json lists GTQ-101 and GTQ-102, and GTQ-100 under \"removed\"."
  expect "kept stories" "$(field "$REAL/stories.json" 'd.stories.map(s => s.key).join(",")')" "GTQ-101,GTQ-102"
  expect "kept removed" "$(field "$REAL/stories.json" 'd.removed.map(r => r.key).join(",")')" "GTQ-100"
  fi
  echo
  echo "$END_LINE"
} > "$OUT" 2>&1
# The record must have been written to its end: if writing it failed partway (a full disk, say),
# the last line is missing and the run counts as unexpected, so the real files are put back.
if [ "$(tail -n 1 "$OUT" 2>/dev/null)" != "$END_LINE" ]; then
  echo "The record wasn't written to its end; nothing is published." >&3
  FAIL=1
fi

if grep -qF -- "$T" "$OUT" || grep -qF -- "$REPO" "$OUT" || { [ -n "${HOME:-}" ] && grep -qF -- "$HOME" "$OUT"; }; then
  echo "The log contains a temp, repository or home folder address; it is not written or shown."
  give_up 1
fi
if [ "$FAIL" != 0 ]; then
  echo "Something unexpected happened; $NAME was not written. The log (temp folder names hidden):"
  while IFS= read -r line || [ -n "$line" ]; do printf '%s\n' "${line//"$T"/<temp>}"; done < "$OUT"
  give_up 1
fi
node -e '
  const fs = require("fs"), [src, dir, name] = process.argv.slice(1);
  const tmp = `${dir}/.${name}.${process.pid}.new`;
  try {
    fs.copyFileSync(src, tmp, fs.constants.COPYFILE_EXCL);
    fs.renameSync(tmp, `${dir}/${name}`);
  } catch (e) {
    // Only a copy this attempt made is removed; "already exists" means it is not ours.
    if (e.code !== "EEXIST") try { fs.unlinkSync(tmp); } catch { /* not made */ }
    throw e;
  }
' "$OUT" "$LOGS" "$NAME" || { echo "Couldn't put $NAME in place."; give_up 2; }
release_lock
cleanup
echo "Written: $NAME"
