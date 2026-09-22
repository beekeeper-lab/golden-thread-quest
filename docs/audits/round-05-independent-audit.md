# Release Audit — Round 5

Status: **in progress.** The reviewer's own findings and the curriculum lens are recorded
below. The engine and documentation lenses are still running; their findings, the
verification pass over them, and the verdict follow.

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
| R5-1 | Two builds running at the same time in one repository destroy each other's output. `quest_app/build.py:183` stages every build in one fixed directory, `generated.building`, removes it if it exists, and publishes by rename. A second build entering while the first is writing deletes the first's staging directory mid-write. | High | Reproduced in a clean clone. Two concurrent `quest-app build` runs, three times: exit codes `0 0`, `0 1`, `0 0`, and `generated/` left holding 3, 12 and 20 HTML pages against the 53 a single build produces. Two of the three runs reported success on both processes while publishing a site missing fifty pages | *(pending)* |

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
