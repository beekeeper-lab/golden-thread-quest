# Phase 2A Verify Pass

**Date:** 2026-09-29
**Checks:** Phase 2A's done-when list (`docs/design/07-status-and-remaining-work.md`), and
nothing else.
**Method:** Section 7.3, step 3. One independent reviewer in a fresh context, in a real
browser, with dialogs accepted as a person would. It played a first-time participant
following `docs/guides/PILOT.md`, and the pilot lead following `docs/guides/PILOT-LEAD.md`.
The GitHub fork and pull request were simulated with two local clones, one fetching the
other's branch.
**Result:** cycle 1 at `ee6cc1c` found two high findings. Both were fixed, and cycle 2 at
`56dc47f` found no blocking or high finding.

## Cycle 1 (`ee6cc1c`)

| Check | Result |
|---|---|
| A. Submission refused while required proof is missing | Fail: the refusal was cut short and named 2 of 3 files |
| B. Untouched `PROOF.md` fails the Base Camp check | Pass |
| C. A participant following `PILOT.md` | Pass, with one medium and two low findings |
| D. The lead reviewing from a clone, then needs changes, resubmit, approve | Fail: a false "evidence changed" banner on every hand-in |
| E. Release text and version agree | Pass |

| # | Severity | Finding | Fix |
|---|---|---|---|
| V1 | High | The refusal was cut at 300 characters (redirect) and again at 400 (page), dropping a missing file | Both limits are now `PROBLEM_LIMIT` (4000). A test checks every missing file appears on the page and fails with the fix reverted |
| V2 | High | The evidence hash counted the empty `screenshots/` folder, which Git does not carry, so a reviewer's clone always read "changed since submitted" and approval was refused | Plain directories are not hashed (ADR-031, amended). A test fails with the fix reverted. Records from 0.1.x read as changed once, as the release notes say |
| V3 | Medium | An ordinary redaction wrapped in parentheses is flagged as a secret | `PILOT.md` names a form that passes. The scanner change is in the parking lot |
| V4 | Low | `PILOT.md` did not mention ticking the confirmation box before **Start quest** | Fixed |
| V5 | Low | The evidence page said "commit before submitting", while the guides say to commit after | The page now says to commit after |

Four observations outside the scope went to `docs/PARKING-LOT.md`.

## Cycle 2 (`56dc47f`), re-checking V1 and V2 only

| Check | Result |
|---|---|
| A | Pass: all three missing files are named in full, and the state stays `evidence_ready` |
| D | Pass: no banner, approval works on the first try, and the participant pulls cleanly and sees 20 verified XP |

## Not covered

The GitHub part of the hand-in was not exercised: forking, the pull request, and the lead
pushing to a fork's branch through "allow edits by maintainers". It needs two GitHub
accounts. `PILOT-LEAD.md` says what to ask for if that push is refused.
