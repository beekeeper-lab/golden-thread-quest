# Pilot Log (Phase 2B)

What happened during the 0.2.1 pilot, in order. The pilot report for Gate 2 is written
from this log, the participants' answers to the five questions in `docs/guides/PILOT.md`,
and the 2B rows in `docs/PARKING-LOT.md`.

| Invitation sent | End date | Participants | Reviewer |
|---|---|---|---|
| | | | |

## Before the pilot: rehearsal (2026-09-29)

Two local clones at `v0.2.0`, one playing the participant and one the pilot lead. Each
drove Base Camp with `quest action`: start, evidence, check, submit, commit, review, and
the participant's `git pull`.

| Hand-in path | Result |
|---|---|
| `PILOT.md`: one `pilot/<name>` branch, `git add participant/` | Pass. The pull is clean, and the participant sees the quest as verified |
| The next steps the CLI prints after submitting | Fail. `git pull` refuses, because `participant/ACTIVITY.md` was never committed. Parked: the browser does not show these steps, and `PILOT.md` does not use them |

**Not rehearsed:** the GitHub part. That covers the fork, the pull request from a fork,
and the lead pushing to the fork's branch through **Allow edits by maintainers**. Doing it
needs a second GitHub account. Watch the first hand-in for it. If the lead's push is
refused, `docs/guides/PILOT-LEAD.md` section 3 says what to do.

## Before the pilot: setup for non-developers (2026-09-30)

The program owner confirmed that participants are BAs and manual testers, and Phase 2A.1
added `install.sh` and the `gtq` commands (release 0.2.1).

| Check | Result |
|---|---|
| `install.sh` in a bare Ubuntu 24.04 container, with no Git and no uv | Pass. It installed both, cloned, made `pilot/<name>`, installed the application, and `gtq start` served it |
| The same, run a second time | Pass. It found the copy and changed nothing |
| The GitHub CLI download step, on its own in the same container | Pass (`gh` 2.102.0) |
| Hand-in, needs changes, fix, hand-in, approve, get-review, against local repositories | Pass (`tests/integration/test_handin.py`) |

**Not tested:** the macOS path (the command line tools prompt and the zip download), and
real GitHub sign-in, forking and pull requests. The program owner's own run of
`install.sh` is the first real test of those.

## During the pilot

| Date | Who | What happened | Stuck for | Action |
|---|---|---|---|---|
| | | | | |

## Answers to the five questions

One section per participant, filled in at the end.

## Before the pilot: the Phase 2A.2 demo (2026-10-04 and 05)

The program owner ran the setup line on their own Linux machine, the first run against real
GitHub. At `v0.2.2` it stopped at step 5 for every account (`docs/audits/phase-02a2-verify.md`,
D1). At `v0.2.3` it finished, reused the fork, and the home page offered the transcript
quest first. The invitation points at `v0.2.4`. A real hand-in, and the lead's push to a
participant's fork, are still untested: watch the first one.
