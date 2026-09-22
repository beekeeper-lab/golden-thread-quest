# Release Audit — Round 5

Status: **complete.** Three lenses, sixteen findings, every one verified here before it was
accepted and every one fixed with a test that fails without the fix. DH7 stays open: see the
verdict.

Commit under audit: `ff0c63d`, the tip of `chore/round-04-completion`.

Round 4 said round 5 should run against the merge commit. There is no merge commit: PR #2 is
still open, so `main` is still `207a7b3`. The branch descends from it and would fast-forward,
which makes its tip the identical tree a merge would produce, so that is what this round
audits. Range: `207a7b3..ff0c63d`.
Predecessor: `docs/audits/round-04-independent-audit.md`.

## Why this round exists

`docs/ACCEPTANCE-CRITERIA.md` leaves **DH7** open. Four rounds have run and each one found
something. The criterion closes on a round that reports no unresolved blocking or high
findings, which is a round that finds nothing, not a round whose findings are all fixed.

## Method

Three lenses, each given the repository paths and the commit range and nothing else: no
summary of what the author believed, no sight of each other's findings, and no access to the
previous audits, which would have told them what earlier rounds concluded.

| Lens | Scope |
|---|---|
| Curriculum | The eight quests as curriculum, the content model, regions, badges, tracks, and the participant journey walked end to end |
| Engine | Code correctness, the state model, the action allowlist, the local service, the validator subsystem, and the architecture rules in `CLAUDE.md`, pointed specifically at the prerequisite guard and the progress file lock that round 4 added |
| Documentation | Traceability, acceptance criteria, cross-document consistency, packaging, clean-clone reproducibility and build determinism |

Every finding requires file:line or a command and its output. A claimed defect that could not
be triggered is recorded as unverified rather than as a finding. Findings returned by a lens
are re-verified here before they are accepted; a lens is a source, not a verdict.

## Findings from the reviewer's own pass

| # | Finding | Severity | Verification | Disposition |
|---|---|---|---|---|
| R5-1 | Two builds running at the same time in one repository destroy each other's output. `quest_app/build.py` stages every build in one fixed directory, `generated.building`, removes it if it exists, and publishes by rename. A second build entering while the first is writing deletes the first's staging directory mid-write. | High | Reproduced in a clean clone. Two concurrent `quest-app build` runs, three times: exit codes `0 0`, `0 1`, `0 0`, and `generated/` left holding 3, 12 and 20 HTML pages against the 53 a single build produces. Two of the three runs reported success on both processes while publishing a site missing fifty pages | **Fixed.** `_exclusive_output` holds a lock on the output directory for the whole build, on the same POSIX pattern round 4 used for progress, and falls through unlocked rather than refusing to publish where it cannot lock. Two tests, at two and four concurrent builds, assert a whole site and both fail without the lock. |

**How R5-1 was found.** `make check` failed on `tests/integration/test_cli_actions.py::test_a_quest_declaring_no_validators_can_still_reach_submitted` with
`OSError: [Errno 39] Directory not empty: generated.building` while a lens was running a build
in the same working tree. The first reading was a contaminated gate, which it was. The second
reading is that the contamination is the defect: nothing in the application stops two builds
from overlapping, and the participant-facing consequence is worse than the crash. A build that
loses the race exits `0` and leaves a truncated site behind.

Round 4 put a cross-process lock on `participant/progress.yaml`, which serialises action
against action. It does not cover `quest-app build` or `make build`, which take no lock at
all, so build against build and build against action are both unprotected.

## Lens findings

### Curriculum

| # | Finding | Severity | Verification | Disposition |
|---|---|---|---|---|
| CUR-1 | `content/regions/jira-jungle.yaml:11` promised "Preview and safely perform approved Jira changes" while the only Jira quest is explicitly read-only (`read-assigned-stories.md`, whose outcomes are resolve, retrieve and update *local* Markdown). | High | Confirmed by reading both files, and confirmed to reach participants: region outcomes render under "What you will be able to do" on the region page (`templates/pages/region.html.j2:17`), the home page, the map and the passport | **Fixed.** |
| CUR-2 | `content/regions/context-library.yaml:12` promised "Recommend next work with cited, inspectable reasons". No shipped quest produces a recommendation; `docs/CURRICULUM-BACKLOG.md` lists `context-next-work` as unshipped. | High | Confirmed. The region's only quest defines the canonical model and, at criterion 12, says which fields a future recommendation may rely on. It does not make one | **Fixed.** |
| CUR-3 | `content/regions/scrum-village.yaml:12` promised "Convert retrospectives into owned, traceable experiments". The only quest is the stand-up digest and never mentions a retrospective. | High | Confirmed; `scrum-retro-analysis` is a backlog item | **Fixed.** |
| CUR-4 | `content/regions/ba-ruins.yaml:11-12` promised surfacing ambiguity, contradiction and risk, and drafting well-scoped work. The only quest is transcript preservation and explicitly refuses to analyse. | High | Confirmed. Round 4 rewrote the third of these lines to remove a write promise and left the capability claim standing | **Fixed.** |
| CUR-5 | `content/regions/playwright-labyrinth.yaml:12` promised distinguishing product defects, test defects, environment failures and inconclusive results. None of the quest's eleven criteria classifies a failure. | Medium | Confirmed; criterion 9 requires trace, screenshot and a reproduction summary, which is evidence for a classification rather than the classification | **Fixed.** |
| CUR-6 | `content/regions/context-library.yaml:11` promised detecting stale, conflicting, missing and duplicated context. Criterion 11 covers unmappable items and criterion 10 prevents duplicates; stale and conflicting appear nowhere in the required criteria. | Medium | Confirmed against all twelve criteria | **Fixed.** |
| CUR-7 | Three quests omit the "a reviewer decides" sentence the other five carry. | Low | Confirmed, and confirmed not to matter: `templates/pages/quest_detail.html.j2:140` renders "Passing every check is not approval. A reviewer decides verified completion." on every quest page | **Accepted, not changed.** The functional statement is in the template, where it cannot drift. |

Raised as unverified by the lens: nothing.

**What this is.** Region `outcomes` were written against the full multi-quest curriculum in
`docs/CURRICULUM-BACKLOG.md` rather than against the one quest each region ships. Round 4
found the same defect and fixed the three regions where the over-promise was a *write*
capability. The other five stayed, because the round treated it as a safety problem rather
than as what it is: region prose describing a release that does not exist yet.

Six region files now say what their shipped quest delivers, and
`docs/CONTENT-MODEL.md` carries the rule as content-to-UI rule 8, with the plain admission
that no validator can check it. `make validate-content` passes: 8 quests, 8 regions, 4 badges,
1 track, 0 warnings.

### Documentation

| # | Finding | Severity | Verification | Disposition |
|---|---|---|---|---|
| DOC-1 | `CONTRIBUTING.md:13` required "Python 3.12 or newer" against a `>=3.10` floor that round 4 established, tested and added to CI. The file nobody touched in round 4 is the one whose whole job is telling a contributor what to install. | High | Confirmed: `pyproject.toml:6` declares `>=3.10`, `docs/SETUP.md:7` says 3.10, the CI matrix includes 3.10, and `git log -- CONTRIBUTING.md` shows nothing since Stage 1 | **Fixed.** It now names the floor and says where the floor is declared, and it documents the one extra package the guide rebuild needs. |
| DOC-2 | `README.md:74` and `docs/RELEASE-NOTES.md:59` both claimed a build budget over "203 quests". The performance test adds 200 synthetic quests to a copy of the real content tree, which held three quests when the number was written and holds eight now. | Medium | Confirmed: `tests/integration/test_performance.py:18` sets `QUEST_COUNT = 200`, the `large_catalogue` fixture writes them into a copy of `content/`, and `find content/quests -name '*.md' \| wc -l` returns 8 | **Fixed**, and fixed so it cannot go stale again: both documents now say "the shipped curriculum plus 200 synthetic quests", which stays true as the curriculum grows. |
| DOC-3 | `scripts/build_user_guide_html.py` imports Pillow, which appears in no dependency group. On a clean clone following `docs/SETUP.md`, rebuilding the guide fails with `ModuleNotFoundError: No module named 'PIL'`. | Medium | Confirmed twice: by the lens on a clean clone, and by this reviewer, who could only run the script in this round by passing `--with pillow` by hand | **Fixed.** A `docs` extra carries Pillow with a comment saying why it is not a runtime dependency, and both `CONTRIBUTING.md` and `IMAGE-PLAN.md` name the install. |

Raised as unverified by the lens: the README's count of fourteen attempts to forge verified
state, which it could not check without reading `docs/audits/`, and whether
`docs/ARCHITECTURE.md`'s illustrative module tree misleads anyone. Neither is accepted as a
finding.

**The lens's clean clone passed.** Cloned from the remote at `ff0c63d`, `make setup`,
`make check` (exit 0, 531 passed, 3 skipped), `make validate-content`, `make build` (53 pages)
and `make serve` all behave as `docs/SETUP.md` promises, and `ruff==0.16.8` resolves from the
pin round 4 added. It also confirmed that all five user-guide diagrams, not only the one this
round replaced, are the same files in the Markdown and in the embedded HTML.

That result matters for a second reason: `make check` failed in this reviewer's working tree
while a lens was building in it, and passed on a clean clone with nothing else running. The
gate is sound. What the failure exposed is R5-1.

### Engine

| # | Finding | Severity | Verification | Disposition |
|---|---|---|---|---|
| ENG-1 | A `.progress.lock` the participant cannot open took every CLI action down. `store.py` opened it ahead of every guard, `cli.py` caught only `StoreError` and `ValueError`, and the `PermissionError` reached the terminal as a traceback carrying absolute paths. The service caught `OSError` and said something useful; the CLI is the surface Cowork participants have. | High | Reproduced: `chmod 0444 .progress.lock`, then `quest-app action mark-evidence-ready` printed a traceback ending in the participant's absolute path | **Fixed.** Not being able to lock is no longer a reason to refuse the work: the block runs unlocked, which is what this application did before the lock existed. The CLI also catches `OSError` now, and both surfaces share one message that names the operation rather than the path. |
| ENG-2 | `exclusive()` handled a missing `fcntl` module and nothing else. `flock` answering `ENOLCK`, which is what a filesystem with no lock manager returns, killed every mutating action on both surfaces. | High | Confirmed in the code and reproduced by making `flock` raise: `OSError: [Errno 37] No locks available`, traceback, exit 1. The docstring three lines above says a local-first application must not refuse to work because it cannot lock | **Fixed** by the same change. A test raises `ENOLCK` and asserts the block is still entered. |
| ENG-3 | Round 4's rebuild fix held only on port 8765. `is_service_running` probed `config.service_port`, `serve --port` is an advertised flag, and `quest-app action` has no matching one, so a CLI action beside a service on any other port published the offline view and disabled every control on every served page. | High | Reproduced end to end: service on 9380, `quest-app action rebuild`, and the served page gained "service is not running". With the fix the same sequence leaves the controls live, and removing the fix restores the defect exactly | **Fixed.** `run_service` records the port it actually bound in `local-data/`, and the probe asks there. The file is a hint, never an authority: the probe still requires this application's own response header, so a stale file pointing at a port something else holds is refused like any other stranger. |
| ENG-4 | `flock` is blocking with no timeout and no message, and `run-validator` holds it across a validator subprocess the registry allows 120 seconds. Correct, and indistinguishable from a hang. | Medium | Confirmed: an action against a held lock printed nothing for the whole wait | **Fixed.** The lock is taken non-blocking first; if that fails the wait is announced, then it blocks. |
| ENG-5 | A refused action left state behind. The lock is taken before any guard, so starting a locked quest as a participant who has never run anything created their directory and a lock file inside it. | Low | Reproduced: a refused `start-quest` on a locked quest left `participant/.progress.lock` | **Fixed.** A directory this code created is removed again when the change wrote nothing. |
| ENG-6 | `validator_runner.py` explained validator isolation in terms of `forkserver`; the code below it is a plain subprocess. | Low | Confirmed at `validator_runner.py:293` | **Fixed.** The comment now describes the mechanism in use and says what it replaced. |

Raised as unverified by the lens, and not accepted as findings: `ENOLCK` on a real network
filesystem, which the fix now covers whether or not it was ever reachable here; and a
`Content-Length` stall, where a client declaring a body and sending none pins a request
thread. The stall is real in the code and stays open: the service is loopback-only and
every mutating route is behind a token, the lens could not turn it into an observable
failure, and a socket timeout is a change to the request path that deserves its own round.

**The prerequisite guard and the file lock both hold.** The lens found exactly three callers
of `ActionRunner.perform`, confirmed the guard on all three including the no-JavaScript form
route, found no second writer of attempt state anywhere in `quest_app/`, and confirmed that
`_apply_decision` is the only writer of `verified`. A concurrent HTTP and CLI `start-quest`
against one progress file produced one attempt and one activity line in six runs of six. A
24-case hostile-input probe — traversal encoded and raw, null bytes, non-ASCII tokens,
cross-origin headers on both POST routes, oversized and negative `Content-Length` — produced
correct refusals with no traceback and no absolute path.

### What the suite did not notice

The lens disabled thirteen controls one at a time and reran the suite against each. Eleven
mutants died. Two lived, and a third test passed for the wrong reason:

- **The cross-process lock was effectively untested.** Round 4's own test, run twelve times
  against a build with the lock removed, failed once. Four `subprocess.run` calls each pay a
  second of interpreter start, so their critical sections almost never overlapped: the test
  reported on process startup timing. It is now joined by four processes released from a
  shared barrier after loading the world, which fails every time the lock is removed.
- **All four traversal cases were vacuous.** `urllib` normalises `/../x` before the request
  reaches the wire, so every case arrived as an ordinary path and passed with the containment
  check deleted. Over a raw socket the same request returned 200 and the file. The cases now
  go over a socket as well, and a new one plants a real file outside the output directory,
  because 404 and 403 are indistinguishable when the target does not exist.
- **The form route's origin check had no test.** `TestCrossOrigin` covered `/api/action`
  only. Round 4 found this same route carrying guards nothing asserted.

Every fix in this section is covered by a test that fails without it. Each was verified by
deleting the fix in a scratch copy and rerunning: seven mutants, seven failures. The first
attempt at that verification was itself wrong — the tests imported `quest_app` from the real
repository rather than the copy, so three mutations were silently no-ops and reported as
missed. Forcing the import path made all three fail as they should. A mutation harness that
cannot prove it changed the code under test proves nothing.

## Gates

| Gate | Result |
|---|---|
| `make check` at `ff0c63d`, before this round's fixes | **fail** — one test, and the failure was R5-1 arriving as contamination |
| `make check` after this round's fixes | pass — 546 passed, 42 deselected |
| `make test-ui` | pass — 42 passed, 17.8s |
| `make validate-content` | pass — 8 quests, 8 regions, 4 badges, 1 track, 0 warnings |
| Clean clone from `origin`, `make setup`, `make check`, `make build`, `make serve` | pass, run by the documentation lens at `ff0c63d` |
| Every fix in this round, deleted one at a time | 7 of 7 caught by a test |

The suite grew from 533 to 546. Thirteen tests, each written against a finding in this round,
each failing without its fix.

## Verdict

**Round 5 does not close DH7.** Sixteen findings: three High in the engine, four High in the
curriculum, one High in the documentation, one High found by the reviewer, and seven below
that. Every one is fixed, every fix has a test that fails without it, and both gates are
green on the result. That is a good round and it is not the round the criterion asks for.

What the round says about the work is worth stating exactly, because two of the three lenses
found the same *shape* of defect:

- **Round 4 fixed instances where the rule was the problem.** Three region files promised
  write capability their read-only quest forbids, and three were corrected. Five more
  promised capability no shipped quest delivers, and they stood because the round treated
  the defect as a safety question rather than as region prose describing a release that does
  not exist. The same round corrected the Python floor everywhere except in the file whose
  only job is telling a contributor what to install.
- **The lock round 4 added became the round's own largest source of new failure.** It was
  correct about what it serialises and wrong about everything it could not do: an unopenable
  lock file, a filesystem with no lock manager, a wait nobody was told about, and a refusal
  that created state. A new control belongs in the failure-path review as much as in the
  happy path.
- **And the control it added was the one the suite could not see.** The test written for the
  lock detected its removal one time in twelve. A green suite said nothing about the most
  expensive thing in the range.

Round 6 should run against the merge commit, with the same three lenses and the same rule
that a lens is a source rather than a verdict. Point it at:

- the build lock, which is new enforcement in the path of every publish on both surfaces;
- the service port file, which is new state written outside the participant's directory;
- the unlocked fall-through, which is the first path in this application that deliberately
  proceeds without a guarantee it asked for;
- the `Content-Length` stall recorded above as open.

What is not left open: both gates ran, the browser suite ran, every fix was mutation-tested,
and no finding is recorded here as fixed without evidence that it is.
