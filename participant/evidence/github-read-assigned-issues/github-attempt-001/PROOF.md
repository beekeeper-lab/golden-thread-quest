# PROOF: Synchronize My Assigned GitHub Issues

Quest `github-read-assigned-issues`, attempt `github-attempt-001`.

## How this was made

The skill, its tests, the made-up GitHub and this document were written by an AI assistant (Claude) at the
participant's direction. The participant chose the design in four decisions: build against a made-up GitHub
and run once for real; read GitHub's list and check its count against GitHub's search; use the node ID as the
local identity; keep notes in files the sync never writes. The participant made a private sandbox repository
by hand, made a read-only token limited to it, and ran both real synchronizations in their own terminal. The
assistant never saw the token and sent no request to GitHub.

Words used below: **recorded** means a saved log shows it. **tested** means an automated test checks it.
**observed** means it was seen on real GitHub in the two real runs. **not assessed** means nobody checked it.

## What the quest asks PROOF to explain

**How identity is resolved (criterion 1).** The first request of every run is `GET /user`. The login and user
id in the answer are the identity. No login is in `sync.py`, on the command line, or in a query: the count
check uses `assignee:@me`. The run prints the identity, and the index and `assigned.json` hold it. Observed in
`logs/live-runs.txt`, where it is masked as `[login]`.

**How pull requests were excluded (criterion 3).** GitHub's list of assigned items returns issues and pull
requests together. An item is a pull request when it carries a `pull_request` key, and only then. Those items
are counted and left out. Recorded: 23 left out of 149, and none has a record. Observed: on real GitHub the
list returned 3 items, 1 carried the key and was left out, and 2 issues were kept.

**How pagination was proved complete (criterion 4).** In two ways that do not depend on each other.
The sync asks for the next page for as long as GitHub's answer has a `Link` header with `rel="next"`: recorded
as "149 items in 2 requests (100 + 49). GitHub reported no further page after the last". Then it asks GitHub's
search how many issues are assigned to the user and compares: recorded as "retrieved 126 issues. GitHub's
search declares 126". Part 4 of `logs/second-run.txt` shows a list that ends early being caught by that
comparison, with nothing written. Observed on real GitHub: retrieved 2, declared 2. Paging over more than one
page was not observed on real GitHub, because the sandbox has three items.

**What the second run changed.** Nothing. Recorded in part 2 of `logs/second-run.txt`: 0 new, 0 changed, 126
unchanged, 135 comments read and 0 added, and every one of the 129 generated files byte for byte what the
first run wrote, by SHA-256 taken by the recording script. The notes files have the checksums they started with.

## The criteria, one by one

| # | Criterion | Status | Where |
|---|---|---|---|
| 1 | Login resolved from the API, identity recorded | recorded, tested, observed | `second-run.txt` part 1; tests `Identity`; `live-runs.txt` |
| 2 | Scope documented, unreadable repositories reported | recorded, tested | SKILL.md section 4; `second-run.txt` part 3; tests `Scope`. An unreadable repository was not observed on real GitHub |
| 3 | Pull requests excluded, rule documented | recorded, tested, observed | SKILL.md section 5; `second-run.txt` part 1; tests `PullRequests`; `live-runs.txt` |
| 4 | Pagination followed, retrieved against declared | recorded, tested, observed for the totals | `second-run.txt` parts 1, 2 and 4; tests `Paging` |
| 5 | Every named field recorded | tested | tests `Fields`; any file in `issues/` |
| 6 | Identity cannot collide | recorded, tested | `second-run.txt` part 1: three issues numbered 12 in three repositories, three record files; tests `LocalIdentity` |
| 7 | Comments and material timeline entries, no duplicates | recorded, tested, observed | `second-run.txt` part 2; `disappearance.txt` parts 1 and 2; tests `CommentsAndTimeline`; real run 2 read 1 comment and added 0 |
| 8 | Pull requests, commits and issues kept as links | recorded, tested, observed for a pull request | `delivery-links.md`; `disappearance.txt` part 1; tests `Links`; real run 1 held 1 link to a pull request |
| 9 | Notes survive, stored apart | recorded, tested | three notes files with unchanged SHA-256 through four syncs; tests `Notes` |
| 10 | Closed, transferred, inaccessible reported, not deleted | recorded, tested, observed for closed | `disappearance.txt`; tests `Gone`, `GoneInOtherWays`; real run 2 |
| 11 | Last successful sync per repository and per issue | recorded, tested | index and records; tests `Times` |
| 12 | No token, no raw response, no private detail in evidence | tested, checked by hand | tests `OnlyReads`, `Fields`; "Sensitive values" below |

## Artifacts

| Required item | File |
|---|---|
| The skill | `participant/skills/github-read-assigned/SKILL.md`, with `sync.py`, `fake_github.py`, `tests/test_sync.py` |
| The assigned index | `participant/context/github/assigned/index.md` |
| The issue records | `participant/context/github/assigned/issues/`, 128 files |
| The two-run record | `logs/second-run.txt`, 26 checks |
| The disappearance record | `logs/disappearance.txt`, 24 checks |
| Optional: delivery links | `participant/context/github/assigned/delivery-links.md` |

Also here: `logs/live-runs.txt` (the two real runs, masked), `logs/tests.txt` (103 tests), `logs/planted-bugs.txt`
(44 planted bugs), `scripts/record_evidence.py` and `scripts/planted_bugs.py`.

The index, the records and the links file are generated from the made-up GitHub. Every repository, issue,
comment, commit and login in them is invented, which is why they need no redaction. They are as the sync left
them after `disappearance.txt`: the made-up GitHub at step 1.

## The disappearance record

`logs/disappearance.txt` follows the two runs of `second-run.txt` in the same folder, after the made-up GitHub
changed. It shows:

- **Closed.** `acme-fixture/platform#7` was closed as completed. It is still assigned, so it is still
  returned. The run says "CLOSED since the last sync ... It was open", and its record keeps both states with
  the sync that saw each.
- **Transferred.** `acme-fixture/support#12` moved to `beta-fixture/docs#41` with a new node ID. The old record
  is flagged "transferred", with where it went and the state it was last in. The new record points back.
- **Became unreadable.** The private repository `acme-fixture/legacy-tools` can no longer be seen. Its two
  issues are flagged "not found" with the closed states they were last in, and the repository keeps its older
  last successful sync time.
- Also a reassigned issue and a deleted one.

128 issues are held afterwards, where 126 were held before and 2 are new. None was removed. The notes of two
flagged issues are still there, unchanged.

## Reproduce

    python3 -m unittest discover -s participant/skills/github-read-assigned/tests -v
    python3 participant/evidence/github-read-assigned-issues/github-attempt-001/scripts/record_evidence.py
    python3 participant/evidence/github-read-assigned-issues/github-attempt-001/scripts/planted_bugs.py

None of these contacts GitHub. The second rewrites the two logs and the generated files in
`participant/context/github/assigned/`. The third changes `sync.py` while it runs and restores it, and takes a
few minutes.

## What was tested

| What | Result |
|---|---|
| Automated tests | 103, all pass (`logs/tests.txt`) |
| Planted bugs | 44 put into `sync.py` one at a time. Every one made at least one test fail (`logs/planted-bugs.txt`) |
| Recorded checks | 26 in `second-run.txt`, 24 in `disappearance.txt`, all pass |
| Real runs | 2, both exit 0, 7 requests each, every one a GET (`logs/live-runs.txt`) |

Three faults were found while building, all the assistant's own:

- The first pass of the planted bugs caught 43 of 44. The one missed, a redirect to a host other than GitHub's
  API being followed, showed that the test for it could not fail. The test was fixed and the bug is now caught.
- The sync's final count check wrongly failed on a restricted run into a folder that already held more. It was
  found by a test and fixed in `sync.py`.
- A recording check expected two issues numbered 12. The made-up GitHub has three. The check was corrected.

## Limitations

- **Transfer on real GitHub: not assessed.** Whether a transferred issue keeps its node ID was not checked.
  The sync handles both cases, and both are tested against the made-up GitHub only.
- **Unreadable, deleted and reassigned issues on real GitHub: not assessed.** Only "closed" was observed.
- **Paging beyond one page on real GitHub: not assessed.** The sandbox has three items.
- **Commits as links on real GitHub: not assessed.** The sandbox has a pull request link and no commit link.
- The made-up GitHub's answers are shaped from the assistant's knowledge of GitHub's API. Where real GitHub
  differs from that in a case the sandbox did not exercise, the tests would not show it.
- A repository GitHub's list leaves out, such as a public one the user does not belong to, makes the count
  check disagree and stops the run. `--only-repos` is the way past it.
- Checks and workflow runs are not recorded. The quest's mission mentions them. Criterion 8 does not.
- Every issue's comments and timeline are read at every sync. There is no delta by update time (the first
  stretch goal). The second stretch goal was not done. The third, a delivery summary, is in `delivery-links.md`.
- If two node IDs differ only in upper and lower case, the run stops, because records are files named by node ID.

## Reflection

*Your index says a piece of work is assigned to you. What in your local copy would let a reviewer decide
whether that statement is still true today, without opening GitHub?*

Nothing in the local copy can make it true today. What it can do is say how old the statement is and how it was
established, so a reviewer can decide how far to trust it. Each row carries the time that issue was last
actually synchronized, each repository carries its own last successful sync, and the index names the identity
the data was read as. A reviewer who sees "last synced three weeks ago" knows the claim is three weeks old.
A repository marked "could not be read" tells them the claim was not even refreshed at the last run.

The copy also separates "assigned at the last sync" from "no longer returned", and for the second it says why:
transferred, reassigned, deleted or not found, with the state the issue was last in. So absence is stated, not
left to be noticed. And the run that produced the index proved its own completeness against GitHub's declared
total, so "assigned" does not rest on a list that might have lost a page.

What surprised me is how little of this is about the issue. The fields were the easy part. The reviewer's
question is answered by the times, the identity and the reasons around them.

## Sensitive values

- The token was typed by the participant into their own terminal and was never shown to the assistant. It is
  in no file. It is limited to one private sandbox repository, read-only, and expires in 7 days.
- The real runs wrote to a scratch folder outside the repository. Nothing from it is committed.
  `logs/live-runs.txt` holds only what the sync printed, with the login, user id and repository id masked.
  That output never includes a title, body or comment.
- No raw answer from GitHub is stored anywhere. The sync keeps named fields only, which a test checks.
- Everything else in this attempt comes from the made-up GitHub. The logins in it, such as `robin-fixture`, are
  invented.
