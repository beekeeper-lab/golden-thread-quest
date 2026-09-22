# Release Audit — Round 6

Status: **in progress.** Three lenses are running against the merge commit. Their findings,
the verification pass over them, the gates and the verdict follow.

Commit under audit: `ad629a2` on `main`, the merge of `chore/round-04-completion`. This is the
first round to run against a merge commit, which is what round 5 said round 6 should do: the
tree here is what a clone of `main` now gets.
Range of newest work: `ff0c63d..ad629a2`.
Predecessor: `docs/audits/round-05-independent-audit.md`.

## Why this round exists

`docs/ACCEPTANCE-CRITERIA.md` leaves **DH7** open. Five rounds have run and each one found
something. The criterion closes on a round that reports no unresolved blocking or high
findings, which is a round that finds nothing, not a round whose findings are all fixed.

## Method

Three lenses, each given the repository paths and the commit range and nothing else: no
summary of what the author believed, no sight of each other's findings, and no access to
`docs/audits/`, which would have told them what earlier rounds concluded.

| Lens | Scope |
|---|---|
| Curriculum | The eight quests as curriculum, regions, badges, tracks, the participant journey walked end to end, and what the built pages actually say |
| Engine | Code correctness, the state model, the action layer, the local service, the validator subsystem, and the architecture rules in `CLAUDE.md` |
| Documentation | Traceability, acceptance criteria, ADR accuracy, cross-document consistency, and clean-clone reproducibility from `main` |

The engine lens is pointed at the four mechanisms round 5 introduced or left open, because its
own tests are the only ones that have ever looked at them:

- the build lock, new enforcement in the path of every publish;
- the service port file, new state written outside the participant's directory;
- the unlocked fall-through in `ProgressStore.exclusive`, the first path in this application
  that deliberately proceeds without a guarantee it asked for;
- the `Content-Length` stall, which round 5 recorded as open rather than fixing.

It also carries one instruction earned the hard way: this package is installed in editable
mode, so a scratch copy still imports `quest_app` from the original repository under pytest.
Round 5's first mutation run reported three false negatives for exactly that reason. The
probe must prove, with `inspect.getsource`, that the mutation is in the module the test
imports.

Every finding requires file:line or a command and its output. A claimed defect that could not
be triggered is recorded as unverified rather than as a finding. Findings returned by a lens
are re-verified here before they are accepted; a lens is a source, not a verdict.

## Lens findings

### Curriculum

| # | Finding | Severity | Verification | Disposition |
|---|---|---|---|---|
| CUR-1 | `content/quests/base-camp/repository-safety.md` criterion 6 requires that rerunning the demonstrated workflow creates no duplicate of the simulated external item. The only evidence of it, `recovery-demonstration`, sat under `proof.optional`, and the registered validator checks ignore rules, `PROOF.md` completeness and secrets, not rerun behaviour. A reviewer had nothing required to check the criterion against. | High | Confirmed in the front matter and on the rendered quest page, where the criterion appears under "How this is judged" and its only evidence under "Optional evidence" | **Fixed.** A required `rerun-record` command-record, on the pattern every sibling synchronization quest has used since it was written. |
| CUR-2 | `content/quests/ba-ruins/ingest-transcript.md` criterion 7 requires that re-ingesting the same transcript produces an identical source record and duplicates no utterance. No proof item addressed it, required or optional, and the required-evidence prose did not mention it either. | High | Confirmed: the `proof` block holds four required and one optional item, none about re-ingestion | **Fixed** the same way, and the required-evidence prose now names it. |
| CUR-3 | `content/regions/jira-jungle.yaml` offered work "assigned and queried". The shipped quest is scoped to work assigned to the authenticated user; `jira-query-stories`, "run a configurable saved query with pagination", is a backlog item. | Medium | Confirmed against the quest's criteria and `docs/CURRICULUM-BACKLOG.md`. This reviewer wrote the phrase in round 5 while correcting the same file's other two outcomes, and judged "queried" defensible because criterion 2 documents the query used. It is not: what it documents is which query the quest runs, not the participant's ability to run their own | **Fixed.** |
| CUR-4 | `content/regions/github-caverns.yaml` offered to "preserve repository conventions and human review authority". The region's only quest is read-only issue synchronization and never mentions conventions. | Medium | Confirmed: `grep -i convention` over the quest returns nothing. Round 5 corrected this file's first outcome and left this one | **Fixed.** It now describes what the quest does: report what could not be read, and what disappeared between runs, instead of dropping it silently. |

Raised as unverified by the lens, and not accepted as findings: that `context-scout` is awarded
for a Base Camp quest despite its name, and that `jira-jungle`'s "records that it did not
write" has no field named for it. Both are worth a look and neither is a defect.

**Version handling.** Changing proof rules increments the quest version, which
`docs/CONTENT-MODEL.md` requires, so both quests are at version 2 and the fixture attempt and
its review record moved with them. That exposed a test of its own: the test that proves
editing a verified quest warns rather than failing the build mutated the literal string
`version: 1`, so on the day the quest reached version 2 it mutated nothing and passed on
warnings the fixture already carried. It now bumps from whatever version the quest is on.

**What the lens confirmed.** Prerequisites form a clean directed graph from the one unlocked
start, every quest is reachable, no cycles and no orphans. XP sums to 210 and matches the
rendered total. Level and XP pairs agree across all eight quests. The track's bookend minimums
are satisfied exactly. Badge criteria resolve against what `progress_calc.py` actually
computes. Acceptance criteria are numbered without gaps across all eight quests, and the tone
holds: the same Mission, Scenario, Acceptance criteria, Required evidence, Safety constraints
shape, and the same habit of naming the designed failure and then requiring proof it did not
happen.

### Engine

| # | Finding | Severity | Verification | Disposition |
|---|---|---|---|---|
| ENG-1 | The build lock had the store's shape and not the store's fall-through. `_exclusive_output` handled a missing `fcntl` module and nothing else, so an unwritable `generated.lock` or a filesystem answering `ENOLCK` crashed every publisher — `make build`, `serve`, and every action's rebuild — with a traceback carrying absolute paths. | Blocking | Reproduced twice, independently, by two lenses: `chmod 0444 generated.lock` then `quest-app build` exits 1 with a traceback, and `flock` raising `ENOLCK` does the same. ADR-035 and ADR-036 and round 5's own commit message all claim this parity | **Fixed.** The code now does what the ADRs said: an unopenable lock file and a failing `flock` both fall through to an unlocked build. Two tests, one per case. |
| ENG-2 | An `OSError` from the rebuild that follows an action was reported as a failure to write the participant's directory. The state change had already landed: `progress.yaml` said `in_progress`, `ACTIVITY.md` was written, and the participant was told their change had not happened and pointed at the wrong directory. | High | Reproduced: with the output directory unwritable, `quest-app action start-quest` printed "The change could not be written to your participant directory", exited 1, and the attempt existed | **Fixed.** ADR-038: a failed rebuild is an advisory on a successful action. Generated output is disposable and rebuildable by one command; the participant's record is neither, and the two must not share a failure mode. |
| ENG-3 | The refusal cleanup round 5 added broke mutual exclusion. `_discard_lock_if_nothing_was_written` unlinked `.progress.lock` and removed the directory around it whenever a refused action had created them, with no regard for another process holding that inode: the holder kept a lock on an orphan, the next process created a fresh file and entered immediately, and two writers were in the critical section at once. | High | Reproduced deterministically through the public store API: `C: ENTERED (lock inode 12001387)`, participant root gone, `D: ENTERED after 0.00s (lock inode 12001436)` while C was still inside. The window is a participant's first run in two terminals | **Fixed** by deleting the cleanup. A refused first action now leaves one hidden file in a directory the participant owns, `.gitignore` ignores it wherever the participant root is, and the test that asserted "no trace" now asserts what actually matters: no state, no activity line. |
| ENG-4 | The port file was one slot for a repository that can host several services. The second service overwrote the first's claim, and either service's shutdown deleted it for both: stopping one left the other serving pages while the CLI went back to probing 8765, decided nothing was running, and republished every page with its controls dead. | High | Reproduced: two services on 9101 and 9102, port file holds 9101; `kill -INT` the 9102 service and the file is gone while 9101 still answers with the application's header | **Fixed.** One file per bound port under `local-data/service-ports/`, written by the service that bound it and removed by that service alone. The probe asks at each in turn and still requires the application's own header. |
| ENG-5 | Every early refusal returns before reading the declared body, and HTTP/1.1 keeps the connection open, so the unread bytes were parsed as a second request with every header chosen by the sender. That is a way past the origin check for anyone who can get one ordinary POST through. | Medium | Reproduced on one socket: a `415` refusal followed by a `200` carrying the smuggled request's response, two HTTP responses to one request. No state change follows, because the per-run token gates every mutation | **Fixed.** A refusal ends the connection. |
| ENG-6 | The two mechanisms this range is built on had no test that fails when they are weakened rather than deleted. `LOCK_EX` changed to `LOCK_SH` passed the whole suite while two processes provably sat in the critical section together, and a port file never removed on shutdown passed it too. The four-process barrier test caught a completely removed lock in 3 runs of 5. | Medium | Confirmed by the lens's own mutation run, and again here | **Fixed.** Exclusivity is now asserted the only way it can be — by waiting: one process holds the lock, and a second must be seen to wait for it. That test kills the shared-lock mutant, which nothing did before. |
| ENG-7 | `serve --port` on a port already in use printed a `socketserver` traceback. It is the most ordinary mistake available on the flag that exists to avoid it. | Medium | Reproduced, and now asserted | **Fixed.** It names the address, the reason, and the flag, and exits 2. |
| ENG-8 | `running_service_port` read a whole file whose only valid content is a handful of digits. An entry symlinked at `/dev/zero` hung `quest-app action` until it was killed, with memory climbing. | Low | Reproduced: exit 124 at a 10-second timeout | **Fixed.** The read is bounded to sixteen bytes and the value must be a real port number. |
| ENG-9 | The build lock waited silently where the progress lock announces the wait, and a build queued behind a service rebuild inside a 120-second validator looks hung. | Low | Reproduced: a blocked `quest-app build` printed nothing for eight seconds | **Fixed**, with the same message the store uses. |

Raised as unverified by the lens and not accepted as findings: the stalled-body thread pin,
which the lens could not reach from a browser-driven path and which pins no lock; the lost
update a genuinely lock-free filesystem permits, which is the deliberate fall-through; and
the `generated.previous` rename race, which it could not trigger with the lock in place.

### Documentation

| # | Finding | Severity | Verification | Disposition |
|---|---|---|---|---|
| DOC-1 | The same defect as ENG-1, found independently from the documents: ADR-035, ADR-036 and round 5's commit message all state a parity between the two locks that the code did not have. | Blocking | The same reproduction | **Fixed** in the code, and both ADRs carry a round-6 amendment saying what was claimed and what was true. |
| DOC-2 | The traceability rows round 5 added reused five criterion IDs that already had rows, pointing at unrelated code, in the same document whose own prose explains that IDs exist so a row cannot match a criterion by prose alone. | High | Confirmed: CG7, PE4, PE5, FS2 and FS3 each appear twice with no note saying which row is which | **Fixed.** The new rows are a section of their own, headed as additional evidence for a criterion that already has a row, and each says what it adds. |
| DOC-3 | Those rows had no header and no delimiter, so they rendered as a paragraph of pipes rather than a table. | Medium | Confirmed with a GFM parser | **Fixed** by the same rewrite. |
| DOC-4 | The documented test count is a collected count; the line `make check` prints adds whatever it skipped, so a contributor checking the number against their terminal saw a different one. | Medium | Confirmed: `544 passed, 3 skipped` against a documented 546, with the difference caused by a module-level `importorskip` in the browser suite | **Fixed** by saying which number it is, in both documents. |

**The lens's clean clone passed:** `make setup`, `make check`, `make validate-content`,
`make build` and the optional guide rebuild from `CONTRIBUTING.md`, which reproduced the
committed HTML artifact byte for byte.

## Gates

| Gate | Result |
|---|---|
| `make check` | pass — 555 passed, 42 deselected |
| `make test-ui` | pass — 42 passed |
| `make validate-content` | pass — 8 quests, 8 regions, 4 badges, 1 track, 0 warnings |
| Clean clone from `origin` at `ad629a2` | pass, run by the documentation lens |
| Every fix in this round, deleted one at a time | 8 of 8 caught by a test |

The suite grew from 546 to 555.

## Verdict

**Round 6 does not close DH7.** Seventeen findings: two rated Blocking by the lens that found
them, six High, and the rest below. Every one is fixed, every fix has a test that fails
without it, and both gates are green.

The round has one theme and it is not flattering to round 5. Every Blocking and High finding
here is in code round 5 wrote, and four of them share a shape: **a mechanism correct in the
case it was written for and one step short everywhere else.** The build lock was given the
progress lock's shape without its fall-through, in the same commit that added that
fall-through and a test for it. The cleanup that made a refused action tidy deleted a lock
another process was holding. The port file that fixed one service's controls broke two
services' controls. The rebuild that follows a change reported its own failure as the
change's.

The second theme is the suite. Round 5 verified every fix by deleting it, and deletion is the
one kind of damage that method catches. A lock downgraded from exclusive to shared, and a
file that is written but never removed, both passed the whole suite. Round 6 added the tests
that fail on degradation rather than only on deletion, and they are the tests to keep
watching, because they are the only ones that would have caught the defects this round found.

Round 7 should run against the merge commit, with the same three lenses and the same rule that
a lens is a source rather than a verdict. Point it at:

- the ports directory, which is new state with a lifecycle in two processes;
- the refusal path that now closes connections, which touches every error response;
- the rebuild advisory, which is the first place this application reports a partial success;
- and the areas round 6's engine lens said it did not reach for budget reasons: the validator
  subsystem, the action allowlist, `content_loader`, `view_models`, and the evidence and
  review paths.
