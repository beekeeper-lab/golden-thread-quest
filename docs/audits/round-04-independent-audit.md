# Release Audit — Round 4

Status: **in progress.** The mechanical gates and the reviewer's own findings are recorded
below. Three independent lenses are still running; their findings, the verification pass over
them, and the verdict follow.

Commit under audit: `0c1ef85` on `feature/golden-thread-implementation`.
Predecessor: `docs/audits/external-review-2026-09-17.md`, which audited `a69a8b8`.

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

## Gates, rerun at `0c1ef85`

| Gate | Result |
|---|---|
| `make check` (format, lint, strict types, YAML safety, secret scan, tests) | pass — 502 passed, 42 deselected, 98s |
| `make test-ui` | pass — 42 passed, 18s |
| Secret scan | pass — 218 files scanned, 0 findings |

The browser suite is included. The external review could not run it, because the Playwright
download timed out in their environment; it runs here, so the gap that review left open is
closed for this round.

## Findings from the reviewer's own pass

These were found before the lenses returned and are already fixed on the branch.

| # | Finding | Severity | Evidence | Disposition |
|---|---|---|---|---|
| R4-1 | Five of the eight quests declare no validators, and nothing in the suite walked any of them. Whether `_require_qualifying_validation` stranded them at `evidence_ready` was untested either way. | High | No test named any of the five; no test covered the early return at `quest_app/actions.py:300` | **Verified not a defect, then covered.** All five reach `submitted`. Tests added that walk every validator-less quest to `submitted` and assert every validator-declaring quest is still refused, both lists derived from the content tree. Mutation-checked. |
| R4-2 | Three of the five diagrams in `docs/USER-GUIDE.md` were the superseded round-1 takes. Section 4 showed `locally validated` in the reviewer column — the opposite of the rule the image exists to state — while its alt text described the corrected version, so sighted and screen-reader readers were told different things. Section 11 read `claimed 10601 / verified 10602`, verified exceeding claimed, which the application cannot produce. | High | `docs/USER-GUIDE.md:161`, `:330`; `docs/media/images/02-state-authority.png`, `05-passport-outcome.png` | **Fixed.** Both now reference the v2 takes. |
| R4-3 | Nothing compared the diagrams the guide renders against the corrections the image plan had generated, so R4-2 was invisible to every gate. | Medium | No check referenced `docs/media/images/` | **Fixed.** Two tests in `tests/test_release_facts.py`: every referenced file exists, and the guide's list matches the plan's shipped-take table in order. |
| R4-4 | A global replacement had turned two `IMAGE-PLAN.md` entries into corrections that changed nothing — "v1 labeled the left zone *program* … the label is now *program*". | Low | `IMAGE-PLAN.md:351`, `:360`, `:384` | **Fixed.** The British spelling is restored where the text means it. |
| R4-5 | Three statements in `IMAGE-PLAN.md` were stale and contradicted an entry in the same file: the approval state omitted round 3, the cost table said the first-hour flow was waiting on a change that had landed, and a section explained why image 6 would not be generated without noting image 14 replaced it. | Low | `IMAGE-PLAN.md`, Cost / Approval state / "Why the first-hour flow is not regenerated" | **Fixed.** |

### Open, needing a decision rather than a fix

| # | Item | Why it is open |
|---|---|---|
| R4-6 | The ownership-zones diagram has no correct take. v1 labels the left zone "programme"; v3 fixes the word and collides the in-git dots with their labels, rendering "content ●" as "content." and "generated ○" as "generatedo". v1 ships, as the smaller fault. | A fourth take costs image budget, and a hand-edit of one label is a judgment about whether the asset set stays generator-produced. Recorded in `IMAGE-PLAN.md`. |
| R4-7 | `quest_app/review.py:112` builds an advisory when a declared validator has not been run, `create_submission` keeps only the blocking subset, and nothing else in the codebase calls `readiness_problems`. The advisory reaches neither the participant before submitting nor the reviewer after. A reviewer can infer it from an empty `validation_result_ids`, but is never told. The code comment says the reviewer sees it. | Whether the advisory should surface, and where, is a product call. Held pending the engine lens, which is reading the same file. |

## Lens findings

Pending.

## Verdict

Pending.
