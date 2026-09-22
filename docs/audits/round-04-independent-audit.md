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
| `make check` after the fixes in this round | pass — see the closing gate table |
| `make test-ui` | pass — 42 passed, 20.9s |
| Clean clone from `origin`, `make setup`, `make validate-content`, `make build` | pass, and it is what caught R4-8 |
| The suite on Python 3.10, the declared floor | **fail** at `207a7b3` — see R4-10 |

The browser suite is included. The external review could not run it, because the Playwright
download timed out in their environment; it runs here, so the gap that review left open is
closed for this round.

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

Pending.

## Verdict

Pending.
