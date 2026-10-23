# Phase 2A.2 Verify Pass

**Date:** 2026-10-04
**Checks:** Phase 2A.2's done-when list (`docs/design/07-status-and-remaining-work.md`), and
nothing else.
**Method:** Section 7.3, step 3. One independent reviewer in a fresh context read the diff,
reverted each change in a separate clone to see its test fail, ran `make check` and
`make test-ui`, and played a new participant following `docs/guides/PILOT.md`: setup with
the script's test hooks, the transcript quest through real browser forms, an ignored file in
the evidence folder, `gtq hand-in`, a lead's approval, and `gtq get-review`. Local bare
repositories stood in for GitHub, and a script stood in for the GitHub CLI.
**Result:** cycle 1 found two high and two medium findings inside the scope. All are fixed,
each with a test shown to fail with its fix reverted, and all passed in cycle 2.

## Cycle 1

Items 1, 2 and 4 passed as built. The only `api.github.com` access left in `install.sh` is
`gh api user`, after sign-in; the release redirect parsed a real answer correctly. Version
0.2.2 was consistent everywhere, including the application footer. The transcript quest was
recommended first to a new participant, Base Camp after it was verified, and the end-to-end
flow reached "ba-ingest-transcript: Verified".

| # | Severity | Finding | Fix |
|---|---|---|---|
| V1 | High | A new participant's home page said "Start at Base Camp" directly above "Recommended next: Ingest a Meeting Transcript", contradicting `PILOT.md`. The box always named the first region | The box names the top recommendation's region. Test: `test_a_new_participant_starts_where_the_default_track_does` |
| V2 | High | Every hand-in after a browser action listed the application's own `participant/.progress.lock`, and a Finder `.DS_Store`, as "named like passwords or keys" | Housekeeping files are not listed. Paths are read with `-z`, so a name shows as it was saved. Tests: `test_hand_in_with_nothing_left_out_says_nothing_about_it`, `test_a_left_out_name_is_shown_as_it_was_saved` |
| V3 | Medium | No test failed when the build stopped passing the default track to the recommendation | The same first-run test builds a new participant's home page and fails without it |
| V4 | Medium | Ignored files counted in the evidence hash, so after approval a `.DS_Store` made the quest read as changed, and one present at submission would read as changed in the reviewer's clone | The hash skips files Git ignores (ADR-031, amended). Tests: `test_a_file_git_ignores_is_not_part_of_the_hash`, `test_outside_a_repository_every_file_counts` |
| V5 | Low | `PILOT.md` said the next quest unlocks after a verification, but Base Camp is open from the start | Reworded |

Of five observations outside the scope, two were fixed at once (a stale status line, and
quoted paths in the "Not sent" list), two went to `docs/PARKING-LOT.md`, and one (the
browser's confirm dialogs) is intended behaviour.

## Cycle 2, re-checking V1 to V4 only

A fresh new-participant run at `9405093`, from a new home folder and a new local source.

| Check | Result |
|---|---|
| V1 | Pass: the home page reads "Start at BA Ruins" above "Recommended next: Ingest a Meeting Transcript Without Losing Its Source" |
| V2 | Pass: with the lock file and a `.DS_Store` present, "Not sent" listed only `notes.token`, `my notes.token` (unquoted) and `secrets/env.txt`; none of them was pushed |
| V3 | Pass: removing only the build's `default_track` argument fails the first-run test |
| V4 | Pass: ignored files present at submission left the lead's clone with no "changed" warning; after approval, adding more ignored files kept it clean, and editing `PROOF.md` still raised "changed since it was approved" |

No new blocking or high finding inside the scope.

## Demo (2026-10-04)

The program owner ran the setup line on their own Linux machine, the first run against
real GitHub.

| # | Severity | Finding | Fix |
|---|---|---|---|
| D1 | Blocking | Setup made the participant's fork, then reported "Could not make your copy on GitHub" at step 5. It checked the copy through `gh repo view --json parent` and the field `nameWithOwner`, which that object does not have, so the check read empty for every participant. Every test, and both verify passes, took the test hook around this step | The check reads GitHub's REST `parent.full_name`. `test_setup_finds_the_fork_it_made_on_github` runs the GitHub step against a stand-in `gh` answering from recorded GitHub responses; with the old check it fails with the demo's message. Release 0.2.3 |
| D2 | Low | On the account that owns the repository, the same step said to rename a repository; an account cannot fork its own | Setup says it is the owner's account and to sign in with your own. Test: `test_setup_on_the_owners_account_says_so` |
| D3 | Low | After setup finished and the browser opened, three "Request timed out" lines appeared in the terminal: a browser's spare connections, closed when idle for 30 seconds | An idle connection closing is not logged; other errors are. Test: `test_an_idle_connection_closing_is_not_reported_as_an_error`. Release 0.2.4 |

On the second run, with the fix, setup finished on real GitHub, reusing the fork the first
run had made, and the home page showed "Start at BA Ruins" with the transcript quest as
"Recommended next". A real `gtq hand-in` was not run in the demo.

**What we learned:** a test hook that skips the external system also skips every assumption
about that system's answers. The new test keeps the hook's speed but answers from recorded
real responses, and hand-in's own `gh pr list` fields were checked against real output.
