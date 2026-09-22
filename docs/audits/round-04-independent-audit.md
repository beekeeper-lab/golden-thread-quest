# Release Audit — Round 4

Status: **in progress.** The gates, the reviewer's own findings and two of the three lenses
are recorded below. The engine lens is still running; its findings, the verification pass over
them, and the verdict follow.

Commit under audit: `207a7b3` on `main`, the tip of the work this round covers. The round
opened against `0c1ef85` and five commits landed after it — the browserless reviewer path,
Python 3.10 support, the relicence, the front-page correction and the `quest-app` command
registration — so the range was restated and every gate rerun at the tip rather than auditing
a commit nobody will install.
Predecessor: `docs/audits/external-review-2026-09-17.md`, which audited `a69a8b8`.
Range: `a69a8b8..207a7b3`, seventeen commits.

## Why this round exists

`docs/ACCEPTANCE-CRITERIA.md` leaves **DH7** open: three release rounds and one external
review have each found something, the findings are fixed, and no round has run since. The
criterion closes on a round that reports no unresolved blocking or high findings. Everything
between `a69a8b8` and `0c1ef85` — the CLI action layer, Python 3.10 support, five new quests,
the brand marks, the Cowork-first guide rewrite — has never been audited.

## Method

Three lenses, each given the repository paths and the commit range and nothing else: no
summary of what the author believed, and no sight of each other's findings.

| Lens | Scope |
|---|---|
| Curriculum | The eight quests as curriculum, the content model, regions, badges, tracks, and the participant journey walked end to end |
| Engine | Code correctness, the state model, the action allowlist, the local service, the validator subsystem, and the architecture rules in `CLAUDE.md` |
| Documentation | Traceability, acceptance criteria, cross-document consistency, packaging, clean-clone reproducibility and build determinism |

Every finding requires file:line or a command and its output. A claimed defect that could not
be triggered is recorded as unverified rather than as a finding. Findings returned by a lens
are re-verified here before they are accepted; a lens is a source, not a verdict.

## Gates, rerun at `207a7b3`

| Gate | Result |
|---|---|
| `make check` at `207a7b3`, unmodified | **fail** — `format-check` rejects `tests/integration/test_cli_actions.py:325`. See R4-8. |
| `make check` after the fixes in this round | pass — 533 passed, 42 deselected |
| `make test-ui` | pass — 42 passed, 17.9s |
| Clean clone from `origin`, `make setup`, `make validate-content`, `make build` | pass, and it is what caught R4-8 |
| The suite on Python 3.10, the declared floor | **fail** at `207a7b3` — see R4-10 |

The browser suite is included. The external review could not run it, because the Playwright
download timed out in their environment; it runs here, so the gap that review left open is
closed for this round.

The suite grew from 517 to 533: sixteen tests, each one written against a finding in this
round and each one failing without its fix.

The gate result that matters most this round is the first row. Three previous rounds recorded
`make check` as passing, and it does pass on a machine that has been building this repository
for weeks. It does not pass on a clean clone, because nothing pins the formatter. An audit
that only ever runs in the author's environment cannot see that.

## Findings from the reviewer's own pass

These were found before the lenses returned and are already fixed on the branch.

| # | Finding | Severity | Evidence | Disposition |
|---|---|---|---|---|
| R4-1 | Five of the eight quests declare no validators, and nothing in the suite walked any of them. Whether `_require_qualifying_validation` stranded them at `evidence_ready` was untested either way. | High | No test named any of the five; no test covered the early return at `quest_app/actions.py:300` | **Verified not a defect, then covered.** All five reach `submitted`. Tests added that walk every validator-less quest to `submitted` and assert every validator-declaring quest is still refused, both lists derived from the content tree. Mutation-checked. |
| R4-2 | Three of the five diagrams in `docs/USER-GUIDE.md` were the superseded round-1 takes. Section 4 showed `locally validated` in the reviewer column — the opposite of the rule the image exists to state — while its alt text described the corrected version, so sighted and screen-reader readers were told different things. Section 11 read `claimed 10601 / verified 10602`, verified exceeding claimed, which the application cannot produce. | High | `docs/USER-GUIDE.md:161`, `:330`; `docs/media/images/02-state-authority.png`, `05-passport-outcome.png` | **Fixed.** Both now reference the v2 takes. |
| R4-3 | Nothing compared the diagrams the guide renders against the corrections the image plan had generated, so R4-2 was invisible to every gate. | Medium | No check referenced `docs/media/images/` | **Fixed.** Two tests in `tests/test_release_facts.py`: every referenced file exists, and the guide's list matches the plan's shipped-take table in order. |
| R4-4 | A global replacement had turned two `IMAGE-PLAN.md` entries into corrections that changed nothing — "v1 labeled the left zone *program* … the label is now *program*". | Low | `IMAGE-PLAN.md:351`, `:360`, `:384` | **Fixed.** The British spelling is restored where the text means it. |
| R4-5 | Three statements in `IMAGE-PLAN.md` were stale and contradicted an entry in the same file: the approval state omitted round 3, the cost table said the first-hour flow was waiting on a change that had landed, and a section explained why image 6 would not be generated without noting image 14 replaced it. | Low | `IMAGE-PLAN.md`, Cost / Approval state / "Why the first-hour flow is not regenerated" | **Fixed.** |
| R4-8 | `make check` fails at `207a7b3`, the commit on `main`. `format-check` rejects one line in `tests/integration/test_cli_actions.py`. | High | Reproduced on a `git clone` of `origin/main` into an empty directory, with a venv built by `make setup`: `make: *** [Makefile:25: format-check] Error 1` | **Fixed.** The line is reformatted. The cause is R4-9. |
| R4-9 | The formatter is unpinned. `pyproject.toml` allowed `ruff>=0.6,<1`; today that resolves 0.16.8, whose formatter disagrees with the version that formatted the committed line. The same commit therefore passes or fails its own gate depending on the day it is installed, and `docs/SETUP.md` tells a new participant to run `make check` immediately after `make setup`. | High | `pyproject.toml:25` before the fix; `ruff --version` in the clean clone reports 0.16.8 | **Fixed.** Pinned to `ruff>=0.16,<0.17`, with the reason recorded beside it. A formatter is a gate, not a resolution, so pinning it does not contradict the no-lockfile policy. The unused, untracked-by-any-tool `uv.lock` is deleted and ignored, which is what that policy said was true all along. |
| R4-10 | `requires-python` has said `>=3.10` since 76b77b9, but CI runs only 3.12 and 3.13, so the floor was a claim nothing tested. It was broken: `tests/integration/test_cli_actions.py` imports `tomllib`, which arrived in 3.11. | High | `.github/workflows/ci.yml:22` before the fix; on a 3.10 interpreter: `ModuleNotFoundError: No module named 'tomllib'` | **Fixed.** `tomli` is a dev dependency below 3.11 with a fallback import, and 3.10 is added to the CI matrix so the floor is asserted rather than assumed. The suite passes on a real 3.10 interpreter. |
| R4-11 | `tests/integration/test_cli_validate.py::test_json_output_is_machine_readable_and_sorted` validated the shipped curriculum and asserted `warning_count > 0`. A green suite therefore depended on the content staying imperfect. Numbering the acceptance criteria in three quests — the correction the validator itself asks for — turned the test red. | Medium | The test failed with `assert 0 > 0` the moment the last warning in `content/` was fixed | **Fixed.** The warning is manufactured in a copy of the content tree, the pattern the neighbouring warning test already used and explained in its own docstring. Nothing about the assertion is weakened; it no longer rewards leaving a warning in the curriculum. |

### Decided, having needed a decision rather than a fix

| # | Item | Decision |
|---|---|---|
| R4-6 | The ownership-zones diagram has no correct take. v1 labels the left zone "programme"; v3 fixes the word and collides the in-git dots with their labels, rendering "content ●" as "content." and "generated ○" as "generatedo". v1 was shipping as the smaller fault. | **One more generated take, then stop.** `IMAGE-PLAN.md` Image 15 draws `03-ownership-zones-v4`: the Git dots leave the labels entirely and become one chip per zone, because a tiny glyph beside a word is the element both failed rounds broke on. If v4 is also wrong, v1 ships and the item closes rather than buying a fifth. The asset set stays generator-produced; no pixel is hand-edited. |
| R4-7 | `quest_app/review.py:112` builds an advisory when a declared validator has not been run, `create_submission` keeps only the blocking subset, and nothing else in the codebase calls `readiness_problems`. The advisory reaches neither the participant before submitting nor the reviewer after, though the code comment says the reviewer sees it. | **Surface it to both.** The submit action returns the advisories, so a participant sees them at the moment they submit, and the submission record carries them in an optional field, so the reviewer reads them on the record instead of inferring them from an empty `validation_result_ids`. Optional in the schema, so no existing record becomes invalid. Deleting the advisory was the alternative; it loses information the participant has no other way to get. |

## Lens findings

Each lens was given paths and a commit range and nothing else. Every finding below was
re-verified here — by opening the file, running the command, or reproducing the behaviour —
before it was accepted. A lens is a source, not a verdict.

### Curriculum

| # | Finding | Severity | Verification | Disposition |
|---|---|---|---|---|
| CUR-2 | `content/regions/trello-islands.yaml` promised "Create and update cards" and `github-caverns.yaml` "safely manage GitHub Issues", while the only quest in each region is explicitly read-only (`read-board.md:94`, `read-assigned-issues.md:96`). `ba-ruins.yaml` promised creation on the same pattern. | High | Confirmed, and confirmed to reach participants: the text is rendered on the home page, the map and the passport, not only in the source file | **Fixed.** The three outcomes now describe what the shipped quest delivers. The fuller arc stays in `docs/CURRICULUM-BACKLOG.md`, where it is a plan rather than a promise. |
| CUR-1 | `scrum-standup-digest` ships as Builder; `docs/CURRICULUM-BACKLOG.md:133` planned it as Explorer. | Low | Confirmed. The shipped level is the right one: XP and estimate match every other Builder quest and no other quest disagrees | **Fixed** in the backlog, which is the document that was wrong. |
| CUR-3 | The three quests written before this range use bullet acceptance criteria while the five new ones are numbered and tell the participant to cite by number. The validator warned on all three. | Low | Confirmed by `quest-app validate`: three warnings | **Fixed.** All criteria are numbered; validation is now clean. |
| CUR-4 | Raised by the lens as unverified: `context-canonical-work-item` criterion 9 needs items from two source systems, but only the Jira quest is a hard prerequisite. | Medium | Verified as real. The other two systems are `related_quests`, which gate nothing, and nothing in the quest said a second was needed | **Fixed** in the scenario text, which now names the two quests that satisfy it and says why only one is a prerequisite. |

The lens's overall read: the prerequisite graph is sound, every region and badge is reachable,
and the tone holds across the eight quests. Nothing blocking.

### Engine

| # | Finding | Severity | Verification | Disposition |
|---|---|---|---|---|
| ENG-7 | Prerequisites are computed for display and enforced nowhere. The browser disables Start on a locked quest; the CLI starts it. | High | Reproduced independently: one command started `scrum-standup-digest` with nothing verified, three links down its chain | **Fixed.** `_require_met_prerequisites` runs in the action layer both callers share, so the CLI and the no-JavaScript form route refuse it with the same message. Both directions are tested, and the test helper that unlocks a chain walks it through real reviewer approvals rather than writing `verified` into a file. |
| ENG-1 | One `quest-app action` rebuilds `generated/` with the offline service view while a server is running, disabling every control on every served page, with no recovery but a restart. | High | Confirmed in the code path: the CLI passed a constant. `make build` had the same effect | **Fixed.** Both probe for a running service first, matching on the application's own response header rather than a bare TCP connect, which would call anything holding the port this application. |
| ENG-2 | No cross-process lock on `progress.yaml`. The service's lock is held within its own process, and the CLI is a second process performing the same read-modify-write. | High | Confirmed by the lens in 3 runs of 6 — four concurrent starts, four activity lines, three attempts | **Fixed.** `ProgressStore.exclusive()` takes a POSIX file lock, and `ActionRunner.perform` holds it across the load as well as the write, because reading state another process is about to replace is the race. Four concurrent starts now produce one attempt, one line, one success. |
| ENG-3 | `token=é` takes both POST endpoints down: `secrets.compare_digest` raises on a non-ASCII `str`, inside the handler, so there is no HTTP response and a traceback carrying absolute paths reaches stderr. | Medium | Confirmed: `secrets.compare_digest('é','abc')` raises `TypeError` | **Fixed.** Both checks go through one helper that encodes before comparing, so the comparison stays constant-time and a non-ASCII token is an ordinary refusal. The old test missed it because its wrong token was made of the letter x. |
| ENG-4 | Python 3.10 declared, shimmed, and untested; one test imports `tomllib`. | High | The same defect this round already recorded as R4-10 | **Fixed** in `e77cef4`, which landed while the lens was running. |
| ENG-5 | The action allowlist is named in the two callers rather than owned by the layer that enforces it. | Low | Confirmed; `state_machine.check` is what actually refuses an unknown action | **Accepted, not changed.** A test asserts the two callers share one set. Moving it is a refactor with no behaviour to gain. |
| ENG-6 | A comment in `update.py` describes mutating Git commands its allowlist does not contain. | Low | Confirmed | **Open, cosmetic.** Recorded rather than fixed in the same breath as security work. |

**Test quality.** The lens disabled twelve security controls in a scratch copy and reran the
suite. Eleven produced a failure naming the broken control. The miss was the no-JavaScript
form route: every token and allowlist test posted to `/api/action`, so the form route carried
the same guards with nothing asserting them. That route now has three tests of its own.

All six architecture rules in scope were checked against the code rather than against the
comments, and hold.

### Documentation

Nine findings, all verified and all fixed: the "three quests" claim in `README.md:114` and
`PLANNING-STATUS.md:8` after the curriculum reached eight; a `RELEASE-NOTES.md` limitation
saying clean-clone installation is untested when the `clean-export` CI job tests it; the
`TRACEABILITY.md` DH1 row still open while `ACCEPTANCE-CRITERIA.md` recorded the same
criterion closed; `SETUP.md` requiring Python 3.12 against a `>=3.10` floor; ADR-019 never
amended when that floor moved; a "why there is no lockfile" section standing beside a tracked
`uv.lock`; `actions.py` and `compat.py` missing from the module tree; no traceability rows for
the CLI action layer; and a template count of twelve against thirteen files on disk.

The lens's own summary is worth keeping: the machine-checked claims held, and everything left
to prose had drifted.

## Verdict

**The commit under audit, `207a7b3`, does not pass.** Ten findings at High, one at Medium
with a live crash behind it, and the first gate in `docs/SETUP.md` failing on a clean clone.

Every one of them is fixed on `chore/round-04-completion`, with a test that fails without the
fix, and the gates are green again on the result. What the round says about the work is
better than that list reads: three of the High findings are the same kind of defect — a rule
enforced on the surface a reviewer looks at and nowhere else — and the CLI action layer is
what made them visible. Adding a second caller to a system built around one is how you find
out which rules lived in the view.

**DH7 stays open.** The criterion is *a final audit that reports no unresolved blocking or
high findings*, and this round is not that: it reported eleven and then fixed them. A round
closes that criterion by finding nothing, not by fixing everything it found. Round 5 should
run against the merge commit, with the same three lenses and the same rule that a lens is a
source rather than a verdict.

Two things round 5 should be pointed at specifically, because this round changed them and its
own tests are the only ones that have ever looked:

- the prerequisite guard, which is new enforcement on a rule the product has always stated;
- the file lock, which now sits in the path of every mutation on both surfaces.

What is *not* left open: the browser suite ran, the clean clone ran, the declared Python floor
ran, and no finding from any lens is recorded here as fixed without evidence that it is.
