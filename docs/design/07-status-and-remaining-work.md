# Part 7. Status and remaining work

This part says what is finished, what is open, and what is deliberately left for later. Its
status is current to round 17 (`docs/audits/round-17-independent-audit.md`). Section 7.4 keeps
round 12's findings in full as a worked example of a round; every later round's findings are
in its own record.

## 7.1 How the work was staged

`docs/IMPLEMENTATION-PLAN.md` divides the build into eleven stages. Each ends with an audit
by a fresh reviewer, recorded under `docs/audits/`, and a stage is checked off only when its
audit passes after fixes.

| Stage | Scope | State |
|---|---|---|
| 0 | Planning and feasibility audit | Complete |
| 1 | Repository and engineering foundation | Complete |
| 2 | Content contracts and loading | Complete |
| 3 | Deterministic site generation | Complete |
| 4 | Participant state and loopback service | Complete |
| 5 | Evidence workspaces and validator framework | Complete |
| 6 | Participant UI and accessibility | Complete |
| 7 | Submission and reviewer integrity | Complete |
| 8 | Fork updates, versioning and migrations | Complete |
| 9 | Documentation, hardening and release candidate | Complete |
| 10 | Final independent audit and release decision | **Open** |

## 7.2 Why Stage 10 is still open: DH7

Stage 10 closes when every release acceptance criterion in `docs/ACCEPTANCE-CRITERIA.md` is
met. Forty-seven are checked. One is open:

> **DH7**: the final audit reports no unresolved blocking or high findings.

The closing rule, set by the program owner on 2026-09-28: DH7 closes on the first
independent round that **finds no blocking or high finding at all**, with every medium and
low finding from that round fixed or explicitly deferred. A blocking or high finding raised
and then fixed does not count as none found, because the fix is itself unaudited; the next
round runs against the merge commit that contains it. The earlier rule, a round that finds
nothing at any severity, was never met in sixteen rounds.

**Current status.** Seventeen rounds have run and each found at least one blocking or high
finding. Round 17 found one blocking and five high, all fixed with tests; round 18 runs
against its merge commit.

**Method of a round.** Three independent review **lenses**, each in its own worktree at the
commit under audit with `docs/audits/` removed, each given only paths, a commit and areas to
probe, none shown the author's beliefs or another lens's findings. The lenses cover the
curriculum followed literally, the engine, and tooling, tests and documentation. Every
finding is verified by reproduction or by reading the cited code before it is accepted.

## 7.3 Audit history

| Round | Commit | Blocking | High | Record |
|---|---|---:|---:|---|
| 1 (final audit) | `1418b78` | 3 | 4 | `stage-10-final-audit.md` |
| 2 (re-audit) | `128617e` | 1 | 3 | `stage-10-final-re-audit.md` |
| 3 (second re-audit) | `aafce28` | 1 | 2 | `stage-10-final-re-audit.md` |
| External review | `a69a8b8` | n/a | n/a | `external-review-2026-09-17.md`: engine a release candidate, curriculum too thin |
| 4 | `207a7b3` | 0 | 10 | `round-04-independent-audit.md` |
| 5 | `ff0c63d` | 0 | 9 | `round-05-independent-audit.md` |
| 6 | `ad629a2` | 2 | 6 | `round-06-independent-audit.md` |
| 7 | `31a74cb` | 1 | 8 | `round-07-independent-audit.md` |
| 8 | `b0667c0` | 0 | 7 | `round-08-independent-audit.md` |
| 9 | `5248500` | 0 | 8 | `round-09-independent-audit.md` |
| 10 | `8df0ac5` | 1 | 8 | `round-10-independent-audit.md` |
| 11 | `ea36037` | 0 | 3 | `round-11-independent-audit.md` |
| 12 | `16a0b03` | 2 | 4 | `round-12-independent-audit.md`, merged to `main` at `0018e2d` (pull request 10) |
| 13 | `a942237` | 2 | 3 | `round-13-independent-audit.md`, merged to `main` at `3b9b7c2` (round 14's predecessor commit) |
| 14 | `3b9b7c2` | 0 | 3 | `round-14-independent-audit.md`, merged to `main` at `95b173e` (round 15's predecessor commit) |
| 15 | `95b173e` | 0 | 3 | `round-15-independent-audit.md`, merged to `main` at `a31bbf9` |
| 16 | `a31bbf9` | 0 | 2 | `round-16-independent-audit.md`, merged to `main` at `bc190e9` |
| 17 | `bc190e9` | 1 | 5 | `round-17-independent-audit.md`: two passes, the first (the A-series) never recorded until the second merged it |

Every accepted blocking and high finding from rounds 1 to 12 is fixed on `main`, each code fix
with a test that fails without it, except round 12's E9 (Low, a validator grandchild that
starts its own session survives cleanup), which is stated as known limitation 11 below rather
than fixed. The round records say which lower findings were deferred or stated as limitations
instead. The pattern the audits name is consistent: defects live in states no fixture occupied
(no participant yet, a refused action, a second process, a hostile file, a real browser rather
than a test client). Round 12 found the sharpest instance of that pattern yet: C1 (every
browser action form refused) went unseen for eleven rounds because no lens had submitted a
form in a real browser. Rounds 13 through 15 kept finding high-severity issues past round 12's
fixes — `docs/audits/round-13-independent-audit.md`, `round-14-independent-audit.md` and
`round-15-independent-audit.md` record what and why. Round 17's blocking finding is the same
pattern once more: the proof path a page showed was not the path the gates read, which only
a lens that followed the page in a real browser could see.

## 7.4 Round 12: findings and their fixes

Round 12 audited `16a0b03` and found two blocking and four high findings, so it did not close
DH7. All eighteen findings are verified and accepted; seventeen are fixed on `main` at
`0018e2d`, each with a test shown to fail with the fix reverted, and E9 is stated as known
limitation 11 (Section 7.5). `make check` now runs 830 tests to completion and `make test-ui`
runs 45 browser-driven ones, both up from 751 and 43 at round 11 (`docs/RELEASE-NOTES.md`). **DH7 is not closed by fixing a round's findings**, so round 13
must still run against `0018e2d` before Stage 10 can close.

| ID | Severity | Finding | Fix |
|---|---|---|---|
| C1 | Blocking | Every browser action form failed: pages sent `Referrer-Policy: no-referrer`, Chromium then sent `Origin: null`, and the origin check refused it. Only the CLI changed state | The policy is `same-origin` in the header and the meta tag (Part 4, flow 4.8; Part 5, Section 5.2). Two browser tests submit real forms and check the files on disk |
| E1 | Blocking | Three writes could follow a symbolic link out of `participant/`: the activity line, validation results in a linked `validation/` directory, and the review archive. A FIFO `ACTIVITY.md` hung an action while it held both locks | Every participant write goes through `safe_io`'s no-follow, non-blocking path (ADR-042; Part 2, Section 2.7; Part 5, Section 5.4). An unusable `ACTIVITY.md` skips its line with a warning instead |
| C2 | High | CLI tests with `--participant-root` still built into the repository's own `generated/`, so `make check` replaced a participant's site with fixture data until the next build | `GTQ_GENERATED_ROOT` and `GTQ_LOCAL_DATA_ROOT` are configuration too (ADR-018, amended), with a test-suite session guard as backstop (Part 2, Section 2.7) |
| E2 | High | Validation result files were read without a size or file-type bound; a FIFO hung `validate`, `build` and the service | Read through the same bounded reader as `progress.yaml`, up to 8 MB (Part 3, Section 3.2; Part 5, Section 5.9) |
| E3 | High | `review*.yaml` files were globbed and parsed without a bound or error handling; a stray bad `reviewer-notes.yaml` passed `validate` and crashed `build` | One shared definition of a review record, read bounded, used by the loader, the review history and the evidence hash alike (Part 3, Section 3.4; Part 5, Section 5.9) |
| E5 | High | A legitimate `locally_validated` attempt became a load error after an update that added a validator to the quest, and every action was then refused | ADR-017 amended: a version mismatch with at least one qualifying result warns instead of erroring (Part 3, Section 3.5) |
| C3 | Medium | A link leading outside the evidence package made the review page say a secret was found | `evidence.scan_kinds` separates secret, link and oversize findings, worded separately (Part 4, flow 4.4; Part 5, Section 5.7) |
| C4 | Medium | After a pass, local validation and a failing re-run, the evidence page showed "passed" beside "Last run: fail" with nothing connecting them | The evidence page notes when a declared validator's latest run does not match the state it earned; the state logic itself is unchanged (ADR-017) |
| C5 | Medium | When a newer quest version renames a proof path, the review checklist marked the old item "Not detected" with no note that the version changed | Each missing checklist item on a version mismatch now notes that the list follows the published version |
| E4 | Medium | A hand-edited `state: submitted` with no `submission.yaml` loaded and could be approved, skipping the secret-scan gate | A `submitted` attempt with no readable submission record is a load error, and `record_decision` refuses it too (Part 3, Section 3.5; Part 5, Section 5.8) |
| E6 | Medium | The runner capped the output excerpt and check count but not other check fields, so an oversize field discarded the whole run | Check fields are truncated to their own schema limit; a check outside the schema's `id` or `outcome` is replaced and forces `environment_failure` (Part 2, Section 2.6; Part 4, flow 4.3) |
| E7 | Medium | Redaction ran after truncation, so a token cut at the boundary was stored in clear | Redaction runs on the complete text first, then truncation (Part 4, flow 4.3; Part 5, Section 5.7) |
| E8 | Medium | Evidence files had no size ceiling; a very large log made every build slow while it held the locks | Hashing streams a megabyte at a time; the scan reads at most 2 MB of a file and reports the rest as an oversize finding (Part 5, Section 5.4) |
| T1 | Medium | The documentation command test covered five documents and skipped four guides | The test now checks every Markdown file at the root and under `docs/`, except audits and five named planning files |
| E9 | Low | A validator grandchild that starts its own session survives cleanup | **Not fixed.** A reliable fix needs an isolation layer this release does not have. Known limitation 11 (Section 7.5) |
| E10 | Low | `make migrate` rewrote `progress.yaml` without an activity line | `apply_migrations` writes an activity line after a migration it keeps (Part 4, flow 4.7) |
| E11 | Low | A validator that finished but left a non-daemon thread running was reported `interrupted` | Kept and classified when the result channel has closed and the process is still alive a second later (Part 2, Section 2.6; Part 4, flow 4.3) |
| T2 | Low | `PYTHON ?= python3` in the Makefile was never used | Removed; a test fails on any Makefile variable nothing references |

**What this means for a reader of this document.** Parts 2 to 5 now describe the fixed
behavior at `0018e2d`. Where round 12 found the code falling short of the design, the relevant
part names the finding beside the fix rather than beside an open gap.

## 7.5 Known limitations

These are deliberate and documented in `docs/RELEASE-NOTES.md`. They are not defects to be
fixed before release; they are boundaries of release one.

1. Recording a reviewer decision needs the application (the local service or the CLI),
   because it writes files. Reading evidence works from generated pages alone.
2. Reviewer provenance is conventional, not cryptographic (ADR-030).
3. Environment Health reports build-time facts, not live ones (D7).
4. Reviewer-awarded badges cannot be awarded: there is no badge-award record type, so they
   show as pending.
5. Validator isolation is policy plus process boundaries, not a container or seccomp (D9).
6. Catalog filtering needs JavaScript; region and tag pages are the scripting-free routes.
7. No coverage reporting (D2) and no glossary content type (D1).
8. A binary or compressed file (images, PDF, zip and the office formats) is not scanned for
   secrets; a file that only claims such a format by its first bytes is (round 17 E7).
9. Clean-clone installation is tested in CI from a `git archive` export, one step short of a
   real `git clone`; a real clone was run by hand in round 4.
10. Earlier quest versions are not kept. An attempt records its version, but pages show the
    current version's criteria; Git history holds the earlier text.
11. A validator's grandchild that starts a session of its own outlives the timeout (round 12
    finding E9). The runner kills the whole process group on exit and on timeout, which
    reaches anything a validator spawns normally; a descendant that calls `setsid()` leaves
    that group and is not reached by the same `killpg`. Making the service process a Linux
    `PR_SET_CHILD_SUBREAPER` would catch a reparented orphan like that one, but only by
    landing it on the service process itself, mixed in with every other run's, with no cheap
    way to tell which run a reparented PID came from and nothing that ever kills the service
    process the way a per-run child is killed. That trade swaps one unbounded-survivor case
    for another, so this is recorded rather than fixed: every shipped validator is reviewed
    code that does not do this, and the gap only matters against one that is not.
12. Two builds are byte-identical only when `SOURCE_DATE_EPOCH` is set.

## 7.6 Deferred work

From the deferred-work register in `docs/IMPLEMENTATION-PLAN.md`. Items D3 to D6 were
delivered in their stages.

| ID | Work | Why deferred |
|---|---|---|
| D1 | Glossary content type | No schema, sample or screen needs it yet |
| D2 | Coverage reporting | Half-configured is worse than absent |
| D7 | Live Environment Health checks through the service | A generated page cannot inspect the machine when read |
| D8 | A fixture exercising all eight quest states at once | Tests reach the other states by mutation today |
| D9 | Container or seccomp isolation for validators | Release one is policy plus process boundaries |
| D10 | Wider secret-scanner coverage (distant assignments, bare keys, base64, webhooks, personal data) | Widening without a corpus risks false positives that teach people to route around the gate |
| D11 | Role separation between participant and reviewer | The reviewer page is in the primary navigation; ADR-030 already states provenance is conventional |
| D12 | A degraded view for an attempt whose evidence directory is missing | Today one deleted folder makes the site unbuildable until `progress.yaml` is edited |
| D13 | Type-tagged evidence hash chunks | Every approved attempt would read as changed once; the collision it closes hides nothing |
| D14 | Success notices after an action | The rebuilt page already shows the new state |
| D15 | Quest-page section order | The body renders in authored order; a content-model decision |
| D16 | A per-test timeout for the scaling tests | Needs a new test dependency |

**Curriculum.** Release one ships eight quests, one per region, four badges and one track.
`docs/CURRICULUM-BACKLOG.md` lists about 128 proposed quests across the eight regions plus
seven optional "trap" challenges, from repository safety through Jira, Trello and GitHub
synchronization to Playwright test repair. The backlog is a plan, not a promise, and any
quest that performs an external write must first meet the preview-and-confirm conditions in
`docs/SECURITY-AND-PRIVACY.md`. Several future-facing application capabilities are also named
in the specification and not built: a central opt-in scoreboard, AI-assisted advisory
evaluation, and external-write previews.

## 7.7 What done looks like

Stage 10 completes, and the project can make its release decision, when:

1. a round runs against the latest merge commit and finds no blocking or high finding, with
   every medium and low finding from it fixed or explicitly deferred;
2. DH7 is checked, `docs/audits/final-audit.md` records the decision (`release`,
   `release-with-advisories` or `do-not-release`), and the Stage 10 boxes in
   `docs/IMPLEMENTATION-PLAN.md` are checked.

Round 18 should point at what round 17 named for it: the proof-path mapping, the new
validator run parameters, the approval re-scan, the merged secret scanner as one whole, and
the tests round 17 added, mutated the same way.

This document then gets a minor version for the new status (see `REGENERATING.md`).
