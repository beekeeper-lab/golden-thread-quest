# Phase 1 Verify Pass

**Date:** 2026-09-29
**Checks:** Phase 1's done-when list (`docs/design/07-status-and-remaining-work.md`,
Section 7.4), and nothing else
**Method:** Section 7.3, step 3. One independent reviewer in a fresh context, given only the
checklist, cloned `phase-1/pilot-release` at `edbede9` and followed `docs/guides/DEMO.md`
literally. It drove every browser step in headless Chromium through Playwright and accepted
each confirmation dialog, as a person clicking OK would. It did not call the HTTP API or edit
participant files by hand.
**Result: no blocking or high finding within the checklist's flows.** DH7 closes under the
rule set at Gate 0.

## The release checklist

| Item | Result | Evidence |
|---|---|---|
| 1. Housekeeping | Pass | 7 worktrees, 11 local branches and 29 remote `chore/round-*` and `fix/r*` branches were removed. Each local branch's unmerged commits were checked against `main` first: all were merged in equivalent form or superseded, per `round-17-independent-audit.md`. The remote now holds only `main`, `phase-1/pilot-release` and two `feature/*` branches |
| 2. DH7's closing rule | Pass | `docs/ACCEPTANCE-CRITERIA.md`, Part 7 and the glossary agree |
| 3.1 CI green on `main` | Pass | Run 36615588412 on `751fc4d` failed on 3.10: a Ctrl-C during service start-up skipped the cleanup of the port file. This was fixed in pull request 18, and every job is green on `4ad5368` |
| 3.2 True clone | Pass | `git clone` of `main` at `4ad5368` on Python 3.13. `make setup`, then `make check` (1380 passed, 5 skipped because the UI extras were not yet installed), then `make setup-ui` and `make test-ui` (57 passed) |
| 3.3 Participant flow | Pass | DEMO sections 0, 1 and 3. Start, check, ready, local validation and submit all worked. Claimed XP was 20 and verified XP was 0 until approval |
| 3.4 Reviewer flow | Pass | DEMO sections 2 and 4. A needs-changes decision with a finding, then resume and resubmit, then approval. The passport shows 20 verified XP and 1 verified quest |
| 3.5 Maintainer flow | Pass | DEMO section 5. One new Markdown file, no change under `templates/`, `quest_app/` or `assets/`. The quest appears in search, on its region page and on a new tag page |
| 3.6 Failure flow | Pass | DEMO section 6. The error names the file, the field, the valid values and the likely fix, and the previous site keeps serving |
| 4. Demo walkthrough | Pass | Three Low wording findings, all fixed (below) |

The implementer ran flows 3 to 6 in a real browser before the verify pass, with the same
results.

## Findings within scope

| # | Severity | Step | Finding | Resolution |
|---|---|---|---|---|
| V1 | Low | DEMO 1.4 | "The header shows" the XP totals, but at desktop width they sit in the sidebar | Reworded |
| V2 | Low | DEMO 2.1 | "The top navigation" is a sidebar, and it sits behind **Menu** on a narrow window | Reworded |
| V3 | Low | DEMO 3.5 | Copied files still show *Not detected* until the next action rebuilds the page | The step now says so |

## Outside scope

Five observations went to `docs/PARKING-LOT.md` for Gate 1. Two came from the implementer's
browser run: submission accepts missing proof, and the Base Camp check passes on an empty
package. Three came from the verify pass: the proof path shown before a quest starts, no
signpost while a review is pending, and repeated start-up requests in the service log.
