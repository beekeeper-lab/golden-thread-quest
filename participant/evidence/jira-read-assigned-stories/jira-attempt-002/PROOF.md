# Proof · jira-read-assigned-stories

Attempt: `jira-attempt-002`

Written by Tom Carter with Claude (Claude Code), 11-20-2026. The choices below are Tom's, from
Tom's answers to one question at a time; Claude wrote the code and this page.

## What was built

A reusable, read-only synchronization of the stories assigned to the signed-in user into local,
normalized files, run only against a pretend Jira serving the quest's practice data.

- **The skill** (`participant/skills/jira-read-assigned/SKILL.md`): the workflow and its safety
  rules, reusable for any later synchronization.
- **The pretend Jira** (`participant/tools/fake-jira.mjs`, Tom's choice): it serves a practice
  data set (`validators/fixtures/jira/<name>.json`) the way Jira's REST API answers: `myself` for
  the signed-in user, a search returning one page at a time with `startAt`, `maxResults`, `total`
  and `isLast`, and comments paged the same way. The server sets the page size, as Jira does: the
  pagination set comes two stories a page. Every address is under `.invalid`, a domain reserved
  so it can never resolve (`jira.example.invalid`, plus two made-up names in one practice twist).
- **The synchronization** (`participant/tools/jira-sync.mjs`), writing into
  `participant/context/jira/assigned/`: `stories.json` (the file the validator reads), `index.md`
  (a readable index) and `sync-summary.json` (what each run did: the stretch goal).
- **Notes kept apart** (Tom's choice): `notes/<KEY>.md`, one per story. The synchronization
  creates an empty one for a story it sees for the first time, with an exclusive create, and never
  opens an existing one for writing.

## Pagination, identity and merging

**Identity (criterion 1).** Every run first asks Jira who is signed in (`myself`) and keeps only
stories whose assignee is that account. The synchronization's code holds no name, account or email
address; the made-up account (`fixture-account-0001`, "Fixture User") exists only in the pretend
Jira, standing in for the server's own user, and the synchronization learns it by asking. If Jira
doesn't say who is signed in, or a story's assignee is missing or has no account id (Jira sends
`null` only for an unassigned story), the run stops, rather than treating the story as someone
else's and moving it to `removed`.

**The query (criterion 2):** `assignee = currentUser() AND issuetype = Story ORDER BY key ASC`, so
stories assigned to the signed-in user; the work-item type is Story.

**Pagination (criterion 3).** The synchronization asks for the next page until Jira says the page
was the last (`isLast`), then checks that the stories received equal the `total` Jira reported and
that no key arrived twice. Every page must start where it was asked to, report the same total as
the first page, and say plainly (true or false) whether it is the last. If any of that fails, if a
page that isn't the last is empty, or if more arrive than the total, the run stops and writes
nothing (exit 1), so an incomplete list can never look complete. Comments are paged and counted
the same way, and every comment must have an id and text. Every story must have a Jira key
(`ABC-123`, because keys become notes file names), a summary and a status.

**Normalizing (criteria 4 and 5).** Each story has `key`, `source_url`, `summary`, `status`,
`priority`, `type`, `assignee`, `labels`, `description`, `acceptance_criteria`, `parent`,
`created`, `updated`, `retrieved_at` and `comments`. Fields only Jira has (here
`customfield_10016`) are kept under `jira_fields`, apart from the normal names.

**Merging (criteria 6 to 8).** Each run merges with the previous `stories.json` by key, never by
title:

- notes are never rewritten (criterion 6);
- comments are kept once per comment id, however often Jira returns them (criterion 7); the
  first copy is kept, and a later copy whose text or author differs is listed in
  `sync-summary.json` (`duplicate_comments_differing`), so nothing changes without a trace;
- a story no longer returned moves to `removed` with its last known status and summary, its
  source link, when it was removed and why, and its whole last-known record (description,
  comments and every other field, in `last_known_record`); it is never deleted, and its notes
  file stays (criterion 8). A story that comes back leaves `removed`.

The three output files are published together: each is written whole to a new temporary name, then
each is renamed into place with the previous one kept aside; if any step fails with an error, the
previous files are put back and the empty notes files that run created are removed (tried
separately by forcing the second rename to fail, and by making the notes folder read-only: each
time the folder came out byte-identical). Each destination must be an ordinary file or not exist
yet, and every folder written into must be an ordinary folder or not exist yet, all checked before
anything is written; missing folders are made only after that and removed again if the run then
stops, and a file the run had only partly written is removed (tried by forcing a notes file to
fail partway and by making folder creation fail: nothing was left behind). The previous
`stories.json` must look like this tool's own output (both lists, Jira keys, no key twice) or the
run stops and leaves it alone; the same goes for an existing `index.md` or `sync-summary.json`
that this tool didn't write. One run at a time writes to a folder (a lock file, `.jira-sync.lock`,
removed only while it still holds what that run wrote), and while holding it the run checks that
`stories.json` is still exactly the one it merged against, and repeats its checks of the other two
files; otherwise it stops without writing (tried with 20 pairs of runs started together: never
both refused, and the folder never mixed two runs). The folders written into must be ordinary
folders, not links elsewhere: inside the repository, every folder from the repository down to
`notes`; outside it, the folder named and its `notes` folder. In `index.md`, ticket text is shown
as plain characters: every punctuation mark that Markdown or HTML could act on is escaped.

## What tells me the local copy is complete enough

Tom: **a notification from Jira itself that no other tickets were found**, not the
synchronization deciding on its own that it is done. In this synchronization that is Jira's
`isLast` on the final page, **and** the count adding up: the stories received must equal the total
Jira reported. If either is missing, the run writes nothing and the previous copy stays. Every run
records both in `sync-summary.json` (`pages_read`, `total_reported_by_jira`, `stories_received`,
`complete`), and the index states them in words ("Jira reported 2 stories and 2 arrived, so the
list is complete").

## Choices (Tom's)

1. **Practice data only;** nothing connects to a real Jira, so no real ticket or organization data
   can reach this public repository.
2. **Notes in separate files,** one per story, never written by the synchronization.
3. **A pretend Jira** that behaves like the real API, so identity and paging are shown working, not
   assumed.
4. **All four practice sets, each synchronized twice,** and checked by the app's validator; the
   repository keeps the stale-item result.
5. **One stretch goal:** the machine-readable run summary, `sync-summary.json`.

## Where the important artifacts are

All paths are under `participant/`.

- The skill: `skills/jira-read-assigned/SKILL.md`
- The synchronization: `tools/jira-sync.mjs`; the pretend Jira: `tools/fake-jira.mjs`
- The output (stale-item): `context/jira/assigned/stories.json`, `context/jira/assigned/index.md`,
  `context/jira/assigned/sync-summary.json`
- The notes: `context/jira/assigned/notes/`
- The demonstration: `tools/jira-sync-demo.sh`; its record:
  `evidence/jira-read-assigned-stories/jira-attempt-002/logs/sync-run.txt`
- The safety checks: `tools/jira-sync-safety-demo.mjs`; their record:
  `evidence/jira-read-assigned-stories/jira-attempt-002/logs/safety-checks.txt`
- The validator's results: `evidence/jira-read-assigned-stories/jira-attempt-002/validation/`

## How to reproduce the behavior

From the repository's top folder:

```sh
node participant/tools/jira-sync.mjs --fixture stale-item --phase previous
node participant/tools/jira-sync.mjs --fixture stale-item
.venv/bin/quest-app action run-validator --quest jira-read-assigned-stories \
  --validator validate-jira-read-assigned --param fixture_set=stale-item
bash participant/tools/jira-sync-demo.sh <a new logs folder>
node participant/tools/jira-sync-safety-demo.mjs <a new logs folder>
```

## What was tested or validated

Criterion 10, verified: the practice-data demonstration synchronizes every practice set twice;
the second run adds or changes no story (on stale-item it reports GTQ-100 removed, as it should)
and leaves every notes file byte-identical.

Recorded on 11-20-2026 at 5:38 PM with Node 22.23.3, at commit 69b2de0 with the quest's files
uncommitted (`logs/sync-run.txt`).

**Part A, in a temp folder: each practice set synchronized twice, with a person's note in place.**

- **Every set:** the second run finds no new or changed story, and every notes file is
  byte-identical across it (SHA-256 before and after); the list is complete (stories received
  equal Jira's total, on its last page).
- **happy-path:** 1 page, 3 stories.
- **pagination:** 2 pages, all 4 stories (GTQ-101, GTQ-102, GTQ-201, GTQ-202).
- **duplicate-comment:** GTQ-101's comments are 9001 and 9002, each once; 1 duplicate skipped,
  and listed as differing from the kept copy (the practice data's second copy of 9001 has other
  text).
- **stale-item:** run first in its previous state (GTQ-100 still assigned), then current: GTQ-100
  is listed under `removed` with its last known status, In Progress, and its whole last-known
  record (all 16 fields), and its notes file is kept.
- **The pretend Jira misbehaving, eleven ways:** claiming more pages but sending an empty one;
  reporting 5 stories while sending 4; sending the first page again and again; a last page that
  reports a smaller total and leaves a story out; claiming more comments but sending an empty
  comment page; comments with no id; the key `../GTQ-101`, which tries to leave the notes folder;
  a story with no key; a story with no summary; a story whose assignee has no account id; and a
  comment whose body isn't text. Each run stops with exit 1 and its own message, and its output
  folder is never made.
- **A summary full of Markdown and HTML** (a link, an image, a tag): the run succeeds and
  `index.md` shows every mark escaped, as typed.
- **Three previous `stories.json` files this tool didn't write** (`null`, `{}`, and the same key
  twice): each run stops with exit 2 and leaves that file exactly as it was.
- **Another synchronization's lock in the output folder:** the run stops with exit 2, and every
  file, the other lock included, is unchanged.
- **An `index.md` the person wrote, in the output folder:** the run stops with exit 2 and leaves
  it as it was.
- **A named pipe where `stories.json` should be** (reading one could wait forever): refused at
  once with exit 2, shown with `--check-only` (an ordinary run makes the same check first).
- **A folder where a story's notes file should be** (`notes/GTQ-101.md`): the run stops with
  exit 2 rather than report success with notes that can't be opened; nothing is written.
- **A folder where `index.md` should be:** the run stops with exit 2; `stories.json`,
  `sync-summary.json` and the notes are unchanged.
- **A notes folder that is a link to another folder,** and **a copy of the repository whose
  `participant/context` folder is a link:** each run stops with exit 2 and nothing is written
  where the link points.

**Part B, in the real folder, run only when all of Part A came out as expected: the app's own
validator** (`validate-jira-read-assigned`, run with `quest-app action run-validator`, network
denied) after each set: **pass on all four**, every check passing. What its checks cover, in its
own words: every story in the practice set appears in the output (pagination-handled); each
record carries the five fields it requires, `key`, `source_url`, `status`, `summary` and
`retrieved_at` (records-are-normalized; the other normalized fields of criterion 4 are left to
the reviewer, and are in `stories.json`); every record has an absolute `source_url`
(records-trace-to-source); each story appears once (no-duplicate-records); each comment is
recorded once, by id (no-duplicate-comments, 3 comments in duplicate-comment); the story that
disappeared is still reported (disappearances-reported, stale-item); and no file in the
committed context is named like a raw API response (raw-responses-not-committed). The notes files
that existed before Part B are byte-identical after it (the demonstration's own check, not the
validator's). The repository keeps the stale-item result: GTQ-101 and GTQ-102, with GTQ-100
under `removed`.

How Part B protects the real folder:

- **First the lock.** Part B takes the synchronization's lock before any of its checks, holds it
  throughout, and passes its token to its own runs, so no other run can write there meanwhile
  (tried in a copy: another synchronization started during Part B was refused every time).
- **Then the checks.** Every folder from the repository down to the real notes folder must be an
  ordinary folder, and the synchronization itself (`--check-only`) must accept the folder, so
  Part B replaces only files the synchronization would.
- **Then copies.** The three generated files are copied before anything changes. On any
  unsuccessful end (an unexpected result, a record that can't be written to its end, or an
  interruption, including the terminal closing) the copies are put back. For notes, Part B has the
  synchronization keep a list (`JIRA_SYNC_NOTES_LEDGER`): "intent KEY" before it makes a notes
  file and "created KEY" right after, so even a run killed outright leaves a record; the list must
  lie outside the output folder and hold only list lines, or the run stops before writing. Putting
  back removes only the notes files listed as created that are still empty; any other new notes
  file is kept and named, and the folder is then not reported as it was. If putting back fails,
  the copies and the lock are kept and named.
- **The record must be whole.** It ends with "End of record."; if that line is missing, nothing
  is published and the files are put back. The logs folder can't be inside the real output
  folder, checked before the logs folder is made.

The failure paths that can't be shown on the real folder are recorded separately, so they can be
run again: `participant/tools/jira-sync-safety-demo.mjs` rebuilds each one in throwaway copies of
the repository (a stand-in validator replaces the app there, and a failure at one exact point uses
a copy of a tool with one marked TEST ONLY line) and writes `logs/safety-checks.txt`. Its 15
cases: a validator that fails; notes made by Part B's runs removed while a person's new note is
kept; putting back made to fail; an interruption (TERM) and a closed terminal (HUP) during Part B;
another synchronization started during Part B; a hand-written `index.md` and a `stories.json`
holding a key twice; and, for the synchronization itself, a forced rename failure, a forced
put-back failure, a run killed outright, notes-list paths that alias a note, twenty pairs of
simultaneous runs, changes made between the first checks and the lock, a notes file that fails
partway or a read-only notes folder, and folders a failed run made (removed again) or couldn't
make (nothing left). Every "tried" in this PROOF is one of those cases. Recorded on 11-20-2026 at
5:39 PM: 59 expectations, all as expected, and the real folder unchanged.

99 expectations in the record, all as expected.

## Remaining limitations

- **Practice data, not Jira.** The pretend Jira follows Jira's paging and identity answers, but a
  real connection would also need authentication (a token from the environment), rate limits and
  real field mappings, none of which the practice data exercises.
- **Acceptance criteria.** Jira has no field of its own for them; a project that keeps them in a
  custom field would map it to `acceptance_criteria`. None of the practice data has one, so it is
  always empty here.
- **The three files are switched one after another, not in one step.** A run killed between two
  renames, or a reader looking in that instant, could see files from two runs. A run killed
  outright also leaves its `.jira-sync.lock`; the next run then stops and says to remove it. If
  putting a previous file back ever fails, the run names where that file is kept and leaves the
  lock on purpose, so no later run changes the folder before a person has looked (tried by making
  the put-back fail: the next run refused). The run's time is the same in `stories.json`
  (`synchronized_at`) and `sync-summary.json` (`retrieved_at`), so a mix shows, and the next run
  rewrites all three.
- **Folders are checked, not held.** Each folder is checked again while holding the lock, just
  before writing (tried by swapping `notes` for a link mid-run: refused, nothing written through
  it), but Node has no folder-bound file calls, so a folder swapped in the instant between that
  check and a write would not be caught. That needs someone else writing in the folder at the
  same moment; the practice runs have no such writer.
- **Changes are found by comparing whole records.** Every run fetches everything; it doesn't yet
  fetch only what changed since the last run (delta synchronization was left as a stretch goal).
- **Notes from other practice sets stay.** Because notes are never deleted, the notes folder also
  holds the empty notes files created for the stories of the other three practice sets
  (GTQ-103, GTQ-201, GTQ-202).
- **Only the final validator results are kept.** The validation folder holds the four results
  the final record names (one per practice set). The validator also ran during the first checks
  and each earlier run of the demonstration; every one of those results passed too, and they were
  moved out of the hand-in (to the ignored `local-data` folder) to keep it readable.

## Sensitive values

Criterion 9, verified: only normalized records are committed; no token, password or raw Jira
response is in the hand-in, and the validator's raw-responses-not-committed check passed on all
four practice sets.

No secret, token, password, customer name or real ticket content is here. All data is the quest's
practice data, the account is made up, every address is under the reserved `.invalid` domain, and
no file shows this computer's folders.