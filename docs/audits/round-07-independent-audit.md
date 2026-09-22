# Release Audit — Round 7

Status: **in progress.** Three lenses are running against the merge commit. Their findings, the
verification pass over them, the gates and the verdict follow.

Commit under audit: `31a74cb` on `main`, the merge of `chore/round-06-audit`. The tree here is
what a clone of `main` now gets.
Range of newest work: `ad629a2..31a74cb`.
Predecessor: `docs/audits/round-06-independent-audit.md`.

## Why this round exists

`docs/ACCEPTANCE-CRITERIA.md` leaves **DH7** open. Six rounds have run and each one found
something. The criterion closes on a round that reports no unresolved blocking or high
findings, which is a round that finds nothing, not a round whose findings are all fixed.

## Method

Three lenses, each given the repository paths and the commit range and nothing else: no summary
of what the author believed, no sight of each other's findings, and no access to
`docs/audits/`, which would have told them what earlier rounds concluded.

| Lens | Scope |
|---|---|
| Curriculum | The eight quests as curriculum, regions, badges, tracks, the participant journey walked end to end, and what the built pages actually say |
| Engine | Code correctness, concurrency, the state model, the local service, the validator subsystem, and the architecture rules in `CLAUDE.md` |
| Documentation | Traceability, acceptance criteria, ADR accuracy, cross-document consistency, and clean-clone reproducibility from the remote |

The engine lens is pointed at what round 6 built or left unreached: the service port directory,
the refusal path that now closes connections, the rebuild advisory, and the validator
subsystem, action allowlist, `content_loader`, `view_models` and the evidence and review paths,
which round 6 did not reach. It also carries round 5's lesson about the editable install: a
mutation experiment must prove with `inspect.getsource` that the mutated module is the one the
test imports.

Every finding requires file:line or a command and its output. A claimed defect that could not be
triggered is recorded as unverified rather than as a finding. Findings returned by a lens are
re-verified here before they are accepted; a lens is a source, not a verdict.

## Lens findings

### Curriculum

| # | Finding | Severity | Verification | Disposition |
|---|---|---|---|---|
| CUR-1 | A validator could not tell one attempt's evidence from another's. `validators/repository_foundation.py` globbed `participant/evidence/**/PROOF.md` and judged whichever file was newest anywhere in the participant tree, because nothing in the validator contract carried the quest or the attempt under test. | Blocking | Reproduced: a complete `PROOF.md` in the base-camp attempt, a blank one written a second later under `ba-ingest-transcript`, and the run reports `outcome: fail`, `proof-answers-reviewer-questions`, `artifact: participant/evidence/ba-ingest-transcript/attempt-001/PROOF.md` | **Fixed.** The workspace now carries the attempt's evidence root, taken from the attempt's own record, and the check reads `workspace.attempt_files("PROOF.md")`. Records are connected by their identifiers, which is the rule this broke. |
| CUR-2 | The same defect in `validators/playwright_quality.py`, in the direction of a false pass: `_check_failure_evidence` accepted any `.json`, `.txt`, `.log` or `.xml` file anywhere under `participant/evidence`, so a log belonging to another quest satisfied "failure is diagnosable" for this one. | High | Confirmed at `validators/playwright_quality.py:159-161` and by the same root cause; asserted now by a test in which only a stranger quest's log exists | **Fixed** by the same mechanism, and the check was tightened: see CUR-4. |
| CUR-3 | Two of the four Jira fixture sets did not exercise the behaviour they are named for. `duplicate-comment.json` described a comment arriving on two pages and carried no comment at all, and the only duplicate check reconciles stories by key, which cannot see a comment. `stale-item.json` described a story that must be reported rather than dropped and carried no trace of one; the presence check only asks whether currently expected keys appear. | High | Confirmed by reading both fixtures and every check in `validators/jira_read_assigned.py`. A participant choosing either fixture to demonstrate criterion 7 or criterion 8 demonstrated neither, and the run passed | **Fixed.** Both fixtures now carry what they describe, and two checks read them: `no-duplicate-comments` reconciles comments by identifier, `disappearances-reported` requires a story that vanished between runs to be reported with its last known state. Five tests, including one proving the happy path still judges neither. |
| CUR-4 | `playwright-first-independent-test` criterion 9 requires failure evidence — trace, screenshot and a reproduction summary — and no required proof item produced any of it. The only run record is a successful run, the only screenshot is optional and captures a success, and the validator passed on the mere existence of a log. | High | Confirmed against the quest's `proof` block and the rendered page: criterion 9 appears under "How this is judged" with nothing under required evidence that could answer it | **Fixed.** Two required items, `failure-record` and `failure-screenshot`, and the check now asks for evidence of a failure by name rather than for any file. Quest at version 2. |
| CUR-5 | Three quests state an edge-case reporting obligation as a numbered criterion with no evidence, required or optional, and no validator: `github-caverns` criterion 10 (issues closed, transferred or unreadable between runs reported with their last known state), `ba-ruins` criterion 11 (an unparseable transcript reported with its reason and no partial record), `context-library` criterion 11 (an unmappable item reported with its reason). A reviewer had only the participant's prose. | High | Confirmed in all three `proof` blocks and in the required-evidence prose of each | **Fixed.** One required command-record each, on the pattern round 6 established, and each quest's required-evidence prose now names it. Versions 2, 3 and 2. |
| CUR-6 | The Jira validator's `records-are-normalized` check reported "Every record carries the normalized fields" while checking five of the twelve fields criterion 4 names. | Low | Confirmed: `REQUIRED_FIELDS` against criterion 4. The seven it omits are the ones criterion 4 qualifies with "when available", so requiring them would be wrong; claiming them is what was wrong | **Fixed** by saying what it checked and that the rest is the reviewer's to judge. |

Raised by the lens and **not accepted as findings**:

- that the reviewer-awarded badge cannot be earned. It cannot, and that is recorded as a
  known limitation in `docs/IMPLEMENTATION-DETAILS.md` with its reason, the passport says so
  in the participant's own words, and awarding it by arithmetic is what ADR-011 forbids;
- that `base-camp-repository-safety`'s outcome "Record agent actions and recover safely
  after interruption" is unbacked. Criterion 5 is the record, criterion 6 is the recovery
  property that matters, and the required-evidence prose asks for the interruption to be
  explained in `PROOF.md`.

The lens also raised the recommender's treatment of `foundation` and cross-bookend quests as
an unverified suspicion; it is recorded here and not resolved.

### Engine

| # | Finding | Severity | Verification | Disposition |
|---|---|---|---|---|
| ENG-1 | The browser never saw the rebuild advisory. `_handle_form_action` discarded what the action layer returned and redirected with nothing, so the application's one partial-success report reached JSON callers only: a participant whose change landed and whose site did not rebuild was told nothing at all. | High | Confirmed at `serve.py` (the discarded `self._perform(...)` and `_redirect_back(None)`) and reproduced with a failing rebuild: `303` back to a page still showing the old state, no notice anywhere | **Fixed.** The redirect carries a `notice`, the flash renders it as "Recorded, with something to know", and a test reads the `Location` header the browser would follow. |
| ENG-2 | Three of the four paths that rebuild did it bare. Round 6 made a failed rebuild an advisory on a successful transition; `submit-for-review`, `record-review` and `run-validator` still reported the rebuild's failure as the action's. The submission was on disk, the participant was told it had failed, and their retry was refused because the attempt was already submitted. | High | Reproduced: `submit-for-review` answers `500` with a filesystem message while `progress.yaml` says `submitted` and `submission.yaml` exists; the retry answers `409` | **Fixed.** One `_rebuild()` on the action layer, used by every path that rebuilds after a record is written. ADR-038 now holds everywhere it claimed to. |
| ENG-3 | An exception outside `StoreError`, `ValueError` and `OSError` escaped both handlers: no status, no body, a closed connection, and a traceback with absolute paths on stderr — after the state change had landed. A broken template is enough to produce one. | High | Reproduced on both routes: `curl` reports an empty reply, stderr carries the traceback, `progress.yaml` shows the change | **Fixed.** Both routes end in a catch-all that answers with the exception's type and nothing else. The form route's review-field parsing moved inside it, which is where this round put one of its own fixes and found the same hole. |
| ENG-4 | No `Host` validation anywhere. Every page carries the run's request token, so a page at a name that resolves to 127.0.0.1 — DNS rebinding — is same-origin to the browser and can read the token straight out of a page. | Medium | Reproduced: `curl -H 'Host: evil.example.com' http://127.0.0.1:<port>/quests/…/` returns `200` and the live token. The POST that would follow is still refused by the origin check, so the chain is browser-dependent; the token leak is not | **Fixed.** Every request must claim a loopback name, and a GET that does not is refused before a page is rendered. |
| ENG-5 | The body-smuggling hole round 6 closed on refusals was open on `GET`: a GET with a declared body is neither drained nor refused, so on keep-alive the body is parsed as a second request with every header chosen by the sender. | Medium | Reproduced on one socket: a `200` for the health check followed by a `403` for the smuggled POST, two responses to one request | **Fixed.** A GET may not carry a body. |
| ENG-6 | The review form dropped any finding missing one of its three fields, and the refusal that followed said needs-changes requires at least one finding — naming the wrong problem to a reviewer who had just written one. The CLI has an explicit fix for exactly this, with a comment. | Medium | Reproduced: a finding with a severity and a summary and no evidence redirects to `problem=Needs%20changes%20requires%20at%20least%20one%20finding` | **Fixed.** The refusal names the missing field, and the words are the CLI's. |
| ENG-7 | C21 was enforced only in the browser. The confirmation on a consequential action is a `required` checkbox, which is the browser's rule; the service never read `confirm`, so a form post without it performed the action. | Medium | Reproduced: a form POST carrying only the token starts a quest | **Fixed.** The actions that carry a confirmation and the words they confirm live in `state_machine.CONFIRMATIONS`, the page renders them and the service refuses without them, so the page and the service cannot disagree (ADR-033). |
| ENG-8 | The timeout's process-group kill survived downgrade to killing only the child: nothing looked for the grandchild, so a "stopped" run that keeps writing files passed the suite. | Medium | Confirmed by the lens's mutation and again here | **Fixed.** The slow probe's grandchild carries a marker in its argv, and a test proves it dies with its parent. `os.killpg` → `os.kill` now fails that test. |
| ENG-9 | `ValidationResult.qualifies`, the gate for `locally_validated`, survived being widened to accept `inconclusive` and `interrupted`. The only test touching it computed its expectation from the property itself. | Medium | Confirmed: mutated in place, proved live with `inspect.getsourcefile`, suite green | **Fixed.** All six outcomes are asserted by name. |
| ENG-10 | The superseded-review archive had a test whose assertion could not fail: `assert archived or review.yaml exists`, with only one decision recorded. Deleting the archiving entirely left the suite green. | Medium | Confirmed, and the mutation reproduced here | **Fixed.** The test records a second decision and asserts the first one is in the archive and the second in `review.yaml`. |
| ENG-11 | `PurePosixCheck`'s percent-decode branch had no test of its own: every case anyone had written also contained `..`, which the next check catches. | Low | Confirmed: removing the branch left the suite green | **Fixed** by testing it, not by deleting it. A percent-encoded separator without `..` is the case it exists for. |
| ENG-12 | A service killed outright leaves its port entry behind for ever, and `/api/health` advertised an `actions` action that has never been an endpoint. | Low | Reproduced: `kill -9`, entry survives, every later probe pays a connection attempt for it | **Fixed.** A connection *refused* prunes the entry; a timeout does not, because a slow service is not a dead one. The health payload names the actions and the two GET endpoints separately. |
| ENG-13 | The lock-exclusion test — the one round 6 added as the test to keep watching — is timing-based and flaked under concurrent load. | Low | Reproduced by the lens: failed beside a second suite, passed alone | **Fixed.** The hold is longer and the margins are wide, so what is asserted is "waited" against "did not wait", not how loaded the machine is. |
| ENG-14 | A *file* at `generated.building` broke every subsequent build permanently — `rmtree` answers a file with `NotADirectoryError` — and `make clean` could not remove it, because the path was not on its list. | Low | Reproduced; this is how the lens triggered ENG-1 and ENG-2 | **Fixed.** Debris in the wrong shape is removed, both staging paths are on the clean list and in `.gitignore`. |

**Raised and not accepted:** ENG-15, that `compute_states` derives `VERIFIED` from the
recorded state while `verified_ids` in the same function also requires an approval. The
asymmetry is real and it is not a disagreement: an attempt recorded `verified` without a
matching approval is refused during loading, which is why the display can trust what reached
it, and the code says so at the point in question. The lens agreed it is unreachable through
`load_world`.

The lens's unverified suspicions are recorded here and not resolved: the window in `_swap`
where `generated/` briefly does not exist; the pipes a timed-out validator never closes; a
malformed child payload reaching `Check(**entry)`; two review decisions inside one second
colliding in the archive name; `scan_evidence` skipping symbolic links; and a stale entry
naming a port a *different* repository's service later binds.

### Documentation

| # | Finding | Severity | Verification | Disposition |
|---|---|---|---|---|
| DOC-1 | `docs/RELEASE-NOTES.md` stated flatly that two builds of the same inputs are byte-identical. They are not: every page footer carries the build time, so two consecutive `make build` runs differ on all 53 pages. The criterion the claim answers, CG6, is careful to say "excluding documented build metadata", and the test behind it pins `built_at` itself, so nothing ever ran the claim the way a reader would. | High | Reproduced: `make build` twice on a clean tree, `sha256sum` over `generated/`, 53 of 53 pages differ | **Fixed** in both directions. `build.build_stamp` honours `SOURCE_DATE_EPOCH`, so the claim is now true and reproducible on demand, and the release note says what is true without it. Two tests: one builds twice under a fixed epoch and compares the tree, one proves the override is an override. |
| DOC-2 | `docs/TRACEABILITY.md` ended with "Criteria with no row here: CG6" while carrying a CG6 row, unlabelled, in its own table. The document exists so a criterion cannot be matched by prose alone, and its own audit trail was doing exactly that. | Medium | Confirmed: the row at `docs/TRACEABILITY.md:18` is CG6, and the note at line 151 says it has none | **Fixed.** The row carries its ID, and the note now says no criterion is unmapped. |
| DOC-3 | `docs/IMPLEMENTATION-DETAILS.md` presents a file-by-file map of `quest_app/` and omits `validator_child.py`, the subprocess every validator runs in and the concrete implementation of the environment allowlist that `docs/SECURITY-AND-PRIVACY.md` describes. | Medium | Confirmed against `ls quest_app` | **Fixed.** |
| DOC-4 | `PACKAGE-MANIFEST.md` describes `content/` as holding "three representative quests". It holds eight, one per region, and unlike `PLANNING-STATUS.md` this file carries no note marking its text as preserved from planning. | Low | Confirmed against `content/quests/` | **Fixed.** |
| DOC-5 | `docs/RELEASE-NOTES.md` says eleven screens, `README.md` and `docs/TRACEABILITY.md` say thirteen page templates, and no document reconciles the two numbers. | Low | Confirmed: `docs/ui/SCREEN-SPECS.md` specifies U01–U11; `templates/pages/` holds thirteen files, the extras being the tag page and the evidence index | **Fixed** by saying both numbers and what the difference is. |
| DOC-6 | `README.md`'s fact table says "Sample validators: 3, plus a probe". The registry holds five entries — three quest-facing and two probes — and a third probe module is unregistered. | Low | Confirmed against `validators/registry.yaml` | **Fixed.** |

**The lens's clean clone passed:** `make setup`, `make check` (553 passed, 3 skipped),
`make validate-content`, `make build` and `make verify-package`, each with the output the
documents describe. It could not run `make test-ui`: the sandbox blocked the Chromium
download, so the 42 browser tests were counted rather than executed. They are run here.

### Found while running the gates

| # | Finding | Severity | Verification | Disposition |
|---|---|---|---|---|
| CI-1 | CI has failed in its first step on every run since 2026-09-18, including both audit merges, and three rounds recorded their gates as green from a developer's machine. `astral-sh/setup-uv@v3` with `enable-cache: true` resolves `**/uv.lock`, this project has no lock file, and the action fails the job when the glob matches nothing. Nothing was ever compiled, linted, typed or tested in CI. | High | `gh run list --branch main` shows `failure` on every run; the job log ends `No file in … matched to [**/uv.lock]`. The one job that passed uses `setup-uv@v5` | **Fixed.** All three jobs use `@v5` with no dependency cache, matching the job that worked. |

This one was not found by a lens. It was found by running the round's own gates through CI
rather than only locally, which is the same lesson round 4 learned about clean clones and had
not finished learning.

## Gates

| Gate | Result |
|---|---|
| `make check` | pass — 598 passed, 42 deselected |
| `make test-ui` | pass — 42 passed |
| `make validate-content` | pass — 8 quests, 8 regions, 4 badges, 1 track, 0 warnings |
| Clean clone from `origin` at `31a74cb` | pass, run by the documentation lens against the commit under audit |
| CI at this branch's head | pass — `check` on 3.10, 3.12 and 3.13, `browser`, and `clean-export`, all green on run 35782449473. The first run of this repository's CI that reached its checks at all (CI-1) |
| Clean clone at this branch's head, run by hand | not run. The `clean-export` job covers it: it exports tracked files only with `git archive`, then installs, validates and builds in a fresh environment |
| Each fix reverted one at a time | 14 of 17 code fixes caught by a test. The three not covered this way are content: the required evidence added to four quests and the two rewritten Jira fixtures, which `make validate-content` and the rendered pages verify instead |

The suite grew from 555 to 598.

## Verdict

**Round 7 does not close DH7.** Twenty-six findings: one Blocking, eight High, the rest below.
Every one is fixed, and every code fix has a test that fails without it.

The round has two themes.

The first is the one round 6 named, appearing again in the code round 6 wrote and in code
older than that: **a mechanism correct in the case it was written for and one step short
everywhere else.** ADR-038 made a failed rebuild an advisory on the transition path and left
three other paths rebuilding bare. Round 6 closed the body-smuggling hole on refusals and
left it open on `GET`. The origin check has guarded state changes since round 4 and nothing
ever checked the name a request arrived under, while every page served carries the token.
ADR-033 moved the rules out of the templates and left the one rule that is a checkbox.

The second is new, and it is the one worth carrying into round 8: **a check that cannot see
what it is judging.** The validator contract named read roots, write roots, a timeout, an
environment and a network policy, and never named the attempt. So two validators asked the
filesystem "what is the newest evidence here?" and answered a question about one participant's
work with another's, in both directions — a complete attempt failed by a stranger's blank
template, and a missing failure record satisfied by a stranger's log. The same shape is in
the fixtures: `stale-item` and `duplicate-comment` described behaviours that the fixture data
could not contain and the checks could not see. In each case the machinery around the check
was correct and the check was looking at the wrong thing.

Round 8 should run against the merge commit, with the same three lenses and the same rule
that a lens is a source rather than a verdict. Point it at:

- the four mechanisms this round added to the service — `Host` validation, the `GET` body
  refusal, the catch-all on both handlers, and the confirmation gate — because each one
  touches every request;
- the advisory now carried into the page, which is the first thing this application tells a
  participant about a failure that did not stop their change;
- `Workspace.attempt_files` and the three validators, since a scope that is too narrow fails
  as quietly as one that was too wide;
- the clean-clone gate at the branch head, which this round did not run;
- and the areas no lens has reached yet: `view_models`, `recommend`, `markdown_structure`,
  `update`, `migrations`, and the accessibility of the pages the browser tests do not assert.
