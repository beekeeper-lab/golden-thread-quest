# Phase 2A.1 Verify Pass

**Date:** 2026-09-30
**Checks:** Phase 2A.1's done-when list (`docs/design/07-status-and-remaining-work.md`), and
nothing else.
**Method:** Section 7.3, step 3. One independent reviewer in a fresh context read the diff,
ran the new tests, and played a non-developer following `docs/guides/PILOT.md`. Local bare
repositories stood in for GitHub, and a script stood in for the GitHub CLI.
**Result:** cycle 1 found two high findings. Both are fixed, with tests that reproduce the
sequence the reviewer ran.

## Cycle 1

The main path worked end to end: install, quest, hand-in, needs changes, fix, hand-in,
approve, get-review, and "Verified" after a reload. So did an install path with spaces, and
a second hand-in with nothing new.

| # | Severity | Finding | Fix |
|---|---|---|---|
| V1 | High | Editing after hand-in, once the reviewer had pushed, left the branch ahead 1 and behind 1. Hand-in's push was refused with advice about the internet, and get-review said "both changed" | Hand-in and get-review now combine with GitHub first: a fast-forward, else a merge, and on a real conflict the merge is undone with a plain message. The push failure no longer blames the connection. Tests: `test_an_edit_after_hand_in_is_combined_with_the_review`, `test_a_real_conflict_changes_nothing` |
| V2 | High | Running setup again with the name typed differently made a new branch at the tag, and every quest seemed to vanish | A copy that already has a `pilot/` branch keeps it and its name. Test: `test_running_install_again_keeps_the_branch_whatever_name_is_typed` |
| V3 | Medium | Hand-in before submitting opened a pull request and said a quest was ready | Refused unless an attempt is `submitted`, with a plain message. Test: `test_hand_in_refuses_when_nothing_is_submitted` |
| V4 | Low | Get-review before any hand-in blamed the internet | It says nothing has been handed in yet. Test: `test_get_review_before_any_hand_in_says_so` |
| V5 | Low | The Mac wait for Apple's tools had no limit | 30 minutes, then a plain failure |
| V6 | Low | Three setup steps could fail without the friendly message | Each has one |
| V7 | Low | No PATH line when neither `.bashrc` nor `.zshrc` exists | Also `.bash_profile` and `.profile`; `~/.profile` is created if none exists |
| V8 | Low | The invitation said "a Mac" only; Linux users were not told how to open the folder; resubmitting left out two buttons | All three fixed |

Six observations outside the scope went to `docs/PARKING-LOT.md`.

## Cycle 2, re-checking V1 and V2 only

| Check | Result |
|---|---|
| V1 | Pass: hand-in after an edit brings in the review, pushes, and leaves the branch even with GitHub |
| V2 | Pass: a rerun with another name, or from `main`, returns to the same `pilot/` branch and name |
| A real conflict | Pass: refused, no merge left in progress, the participant's file intact |

No new blocking or high finding. Three of its four low notes were fixed at once. The
conflict message now says the work is saved rather than that nothing changed. A hand-in
that brings in a review rebuilds the site. The branch lookup cannot trip `pipefail`. The
fourth note needed no change.

`make check` passes. `install.sh` was run again in a bare Ubuntu 24.04 container.
