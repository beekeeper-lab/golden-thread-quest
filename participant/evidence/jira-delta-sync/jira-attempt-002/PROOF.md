# Proof · jira-delta-sync

Attempt: `jira-attempt-002`

## Who did what

Claude (an AI assistant) wrote the code, the tests, the evidence scripts and this file, working with Beau step by step. Beau made the design decisions listed below and ran the live Jira commands in his own terminal. Two independent AI reviewers, each started with a fresh context and without the builder's conclusions, reviewed the work. Their findings are summarized under "What was tested or validated".

## What was built

- A delta mode in the existing skill: `participant/skills/jira-read-assigned/sync.py --delta`. The full sync from the earlier quest is still there. One check was added to it: a search answer that holds no list of issues now stops the run instead of counting as an empty result.
- `participant/skills/jira-read-assigned/SKILL.md`, section 12, describes delta mode.
- A note for the reviewer: `SKILL.md` and `sync.py` are also the subject of the approved attempt `jira-attempt-001`, and both have changed since that approval. In `SKILL.md` the change is the added section 12; sections 1 to 11 are untouched. In `sync.py` the changes are delta mode and the one check on the full sync described above. The quest app's validation prints a warning about `SKILL.md` for this reason.
- `participant/context/jira/sync-state.md`: the state file that holds the cursor. Delta mode writes it.
- `participant/skills/jira-read-assigned/tests/test_delta.py`: 34 tests for delta mode.
- `participant/skills/jira-read-assigned/fake_jira.py` and `delta_fixture/timeline.json`: a stand-in for Jira and six synthetic tickets (GTQ-201 to GTQ-206) across four moments in time.
- `participant/skills/jira-read-assigned/delta_check.py`: prints the three fixture evidence records.
- `participant/skills/jira-read-assigned/live_check.py`: runs delta mode against a real sandbox Jira from a throwaway folder outside the repository.
- `participant/skills/jira-read-assigned/live_probe.py`: a read-only probe that asks a live Jira whether it accepts the filter delta mode sends.

## Where the important artifacts are

- State file: `participant/context/jira/sync-state.md`
- Delta run record (fixture): `logs/delta-run.txt`
- Failed sync record (fixture): `logs/failed-sync-run.txt`
- Analysis-intact and full-resync record (fixture): `logs/analysis-intact.txt`
- Live runs against a sandbox Jira: `logs/live-run.txt`
- Both test runs: `logs/tests.txt`

The `logs/` paths are under `participant/evidence/jira-delta-sync/jira-attempt-002/`.

## How delta mode works

Each run does these steps in this order:

1. Read the cursor from `sync-state.md`. With no cursor, fetch every assigned story once.
2. Ask Jira for assigned stories with `updated >=` the cursor minus 5 minutes.
3. List every assigned story with two fields only, `key` and `updated`.
4. Fetch by key any listed story that step 2 did not return and whose local copy is missing or has a different `updated` time.
5. Merge into `stories.json` on the Jira key and rewrite `index.md`.
6. Write `sync-state.md` with the new cursor. This is the last write.

A request or write that fails before step 6 stops the run, so the cursor stays where it was.

## How the acceptance criteria are met

1. **Only changed items are fetched.** Step 2 carries the `updated >=` filter. In the fixture run, 3 of 5 stories were fetched (`delta-run.txt`, run 2). In the live run, the three full-story requests sent to Jira each carried the filter 1794344593217, which is the cursor minus 5 minutes, and 4 stories came back (`live-run.txt`, live run 3). The fourth was a story inside the 5 minute overlap, counted as unchanged. Two things are fetched besides changed stories, and both are stated here so the claim stays narrow: the `key` and `updated` time of each assigned story (step 3), and the key and type of assigned items that are not stories. The first run, with no cursor, fetches everything.
2. **The cursor advances only after the whole sync succeeds.** The cursor file is written once, after `stories.json` and `index.md` (test `c2_cursor_file_is_written_once_and_last`).
3. **A failed sync leaves the cursor where it was.** A test fails each of the 7 requests of a run in turn, and after each failure the state file, `stories.json`, `index.md` and the notes are byte-identical. Another test fails the write of `stories.json` and of `index.md`. In the live fault run, the checksums of `sync-state.md` and `stories.json` were the same before and after (`live-run.txt`, live run 2).
4. **The next sync recovers what the failed one missed.** After each of those failures, the next run reaches the same local state as a run that never failed. Live run 3 picked up the reworded story, the story moved to In Progress, and the new story.
5. **The run reports changed, unchanged and new counts.** It also reports fetched and removed. The fixture expectations were worked out by hand from the timeline before the code existed. "Changed" means the stored content differs, so a story fetched again inside the overlap and found identical counts as unchanged.
6. **Local analysis files are byte-identical after every sync.** `analysis-intact.txt` lists the sha256 of four files under `notes/` before any sync and after each of five delta runs (one of them the run that fails partway), and checks them again after a full resync. The live runs show the same for three files. The claim covers the runs that were made, on the files that were checked.
7. **A full resync reaches the same local state as the deltas.** On the fixture and on live Jira, a full resync over the delta-built folder changed nothing, and a full sync into an empty folder held the same stories. Two exclusions: `retrieved_at` is left out of the comparison because it records when a story was fetched, and a sync into an empty folder cannot know which stories were once held, so its `removed` list is empty.

**Stretch goal taken into scope: items removed in Jira.** A stored story that is no longer on the step 3 list is reported under `removed`. There is one `removed` bucket. A deleted story and a reassigned story are not told apart.

## How clock differences between machines are handled

- **This machine's clock is never used in a query.** The cursor is a timestamp Jira sent, copied as Jira sent it (criterion 2). `sync-state.md` also records the local time of the last successful run, and no query reads it. Two machines with different clocks would send the same query for the same cursor.
- **No time zone is involved in the filter.** Jira's documentation says a quoted JQL date is read in the user's configured time zone and to the minute, and that an unquoted number is milliseconds since 1970. Delta mode sends the number. A read-only probe on a live Jira showed the number form accepted and compared to the millisecond.
- **Timestamps with different offsets are compared as instants.** The fixture includes a story stamped `+1100` and the live sandbox returned `-0500`. A test confirms that the same instant written with another offset is not fetched again.
- **The 5 minute margin covers lag and rounding** (criteria 1 and 4). Jira's API documentation says recent updates might not be immediately visible in search results. Each run asks again for the 5 minutes before the cursor. A story fetched twice is matched on its key, so nothing is duplicated.
- **Step 4 covers what the margin misses.** If Jira shows an edit later than 5 minutes, the list in step 3 shows a different `updated` time from the stored one, and the story is fetched by key. A test moves an edit 15 minutes before the cursor and it is still picked up.

## Choices Beau made

- Evidence source: a local fixture, plus live runs.
- Build delta mode into the existing skill instead of a new one. The 17 earlier tests had to pass unchanged, and `logs/tests.txt` shows `test_sync.py` has no diff.
- Take removal detection into scope, with one `removed` bucket.
- A 5 minute safety margin.
- Run live in a throwaway folder outside the repository, so real ticket data never enters it.
- After the first review: list `key` and `updated` for every assigned story (step 3 and step 4), which changed the original keys-only design.
- What could reopen the work was agreed before any result existed: the cursor advancing after a failed sync, any byte of a notes file changing, a full resync disagreeing with the deltas, any of the 17 earlier tests failing or being edited, or a token, email or real ticket text in the evidence.

## How to reproduce the behavior

From the repository root. None of these needs Jira credentials or a network:

```
python3 participant/skills/jira-read-assigned/tests/test_delta.py
python3 participant/skills/jira-read-assigned/tests/test_sync.py
python3 participant/skills/jira-read-assigned/delta_check.py delta
python3 participant/skills/jira-read-assigned/delta_check.py failed
python3 participant/skills/jira-read-assigned/delta_check.py intact
```

The live runs need `JIRA_BASE_URL`, `JIRA_EMAIL` and `JIRA_API_TOKEN` in the shell, pointing at a sandbox site where five test stories are assigned to you, the fifth created more than 5 minutes after the others:

```
python3 participant/skills/jira-read-assigned/live_check.py first <a folder outside the repository that does not exist yet>
```

Then, in Jira: reword one story, move one to In Progress, create and assign a sixth, and unassign one. Then:

```
python3 participant/skills/jira-read-assigned/live_check.py second <the same folder>
```

`live_check.py` expects the summaries to start with "Delta final story" followed by one to six. The name is set at the top of the script.

## What was tested or validated

Observed, on the final code (`sync.py` sha256 beginning `9304a90e`, which is the hash `live-run.txt` prints):

- `test_delta.py`: 34 of 34 passed. `test_sync.py`: 17 of 17 passed, and the file has no diff against the last commit (`logs/tests.txt`).
- The three fixture records: every check held.
- Live, against a sandbox Jira: 29 checks held and none failed, across a first run, a run with a fault injected partway, the recovery run, a quiet run, a full resync comparison, and a run on a deliberately damaged copy (an older `stories.json` and a cursor set to the year 2099). In the damaged copy, 3 stories were fetched by key and it ended in the same state as the healthy folder.
- The expected results of each live run were written down before the run.

Observed, about the tests themselves:

- Planted bugs: the builder planted 6 bugs in copies of `sync.py` before the first review, and each was caught. The first reviewer planted 22, and 11 got through. Tests were added, and the two cursor-order bugs among them were re-planted and caught. The second reviewer planted 18 against the fixes, and 10 got through, 2 of which it judged to change no behavior. Tests were added, and 4 of those were re-planted and caught, along with 2 new planted bugs aimed at the two code fixes. Not every bug that got through was re-planted, so some of the added tests have not been shown to catch the bug they were written for.
- One test passed before any code existed because no run happened in it. It was tightened before the code was written.
- One check in `delta_check.py` was corrected after its first run reported NOT OK. It had assumed one filtered request, and the filtered search took two pages. The first reviewer judged this a correction and not a weakening.

What the two reviews found, and what was done:

- **First review, one high finding, fixed.** A story assigned in Jira, not held locally, and older than the cursor was dropped from both `stories` and `removed`, with no warning. That broke criterion 7. Two tests reproduced it, then step 4 was added.
- **First review, medium findings, fixed.** Failure tests covered only some request positions; they now cover each one. Some evidence checks could not fail on the value they named; they now compare exact values. A cursor set in the future left held stories stale; step 3 now carries `updated`, and a test and live run 5 cover it.
- **Second review, no blocking or high finding.** It could not make the cursor move past an unsaved item or lose a story from both lists. Fixed from its medium findings: the run could save a cursor it could not read back; an answer with no list of issues was read as "nothing assigned"; three fixes had no test that failed without them.
- Earlier live rounds the same day, on earlier versions of `sync.py`, passed the same runs. Each code change made that proof stale, so the live runs were repeated from the start on the final code. Only the final round is in `live-run.txt`.

A deviation from the safety constraints, disclosed: before the sandbox existed, `live_probe.py` was run once against Beau's employer's Jira site, which is not a sandbox. It only read, it asked Jira for the `updated` field only, and it printed five timestamps and some counts. Its output has been removed from the evidence. The sandbox runs show the same thing through `sync.py` itself.

A reading of the quest, disclosed: the quest says "make no change in Jira". The skill and every script in the repository only read. The test tickets in the sandbox were created and changed by a separate script that is not in the repository. It refused any site but the sandbox and waited for a typed "yes". Its steps are the ones listed under "How to reproduce". Treating sandbox test data as outside "make no change in Jira" is an interpretation, not something the quest states.

Not assessed:

- A real Jira outage partway through a sync. The live fault was injected by cutting a request before it was sent.
- Live paging at the normal page size of 100. The live runs used page size 2 so that a handful of stories spanned pages.
- More than six live tickets, more than one site, or more than one day.
- Jira showing an edit late, on a live site. It was shown on the fixture only. Live run 3 ran within about a minute of the edits and saw them.
- More than 50 stories fetched by key on a live site. The 120-story case was run on the fixture only.
- How live Jira answers a by-key query that names a story deleted a moment earlier.
- Two syncs running at the same time, and a crash or power loss in the middle of a file write.
- The final code has not had a third independent review. The fixes from the second review were checked by tests written first, re-planted bugs, and the last live round.

A passing run is not reviewer approval.

## Remaining limitations

- The workspace `sync-state.md` was copied from the throwaway folder of the live sandbox runs. The workspace `stories.json` still holds the earlier quest's `happy-path` fixture. So the state file does not describe the stories in this repository. The first real `--delta` run here would replace the fixture stories and fetch everything, which is the tested behavior for stories that came from a fixture.
- A story that leaves the list and returns loses comments that were stored only locally, because the stored copy is dropped when the story is removed.
- If one answer to the step 3 list leaves a story out, that story is reported as removed for that run. The next complete answer brings it back as new, subject to the comment loss above.
- A story that changed in Jira without its `updated` time changing would not be noticed by delta mode. A full sync would pick it up.
- A cursor set in the future stays there, because the cursor never moves backward. The filter then returns nothing and changes arrive through step 4. No warning says the cursor is ahead.
- The state file does not record which site or account it belongs to. Pointing the same folder at another site would report the old site's stories as removed.
- The searches carry no sort order. Adding one was considered and not done, because it would change the query the earlier, verified full sync sends.
- `stories.json`, `index.md` and `sync-state.md` are each written safely, but not as one unit. A failure between them leaves newer stories beside an older cursor, which is the safe direction. The run that then recovers reports those stories as unchanged.
- A `stories.json` that is valid JSON but has the wrong shape ends in a Python error message, not a plain one.
- A raw `sync.py` run prints absolute local paths. The evidence scripts shorten them. Redact a raw run before sharing it.
- The `removed` list is never trimmed, and a comment deleted in Jira stays in the local copy. Both carry over from the earlier quest.

## Reflection: a cursor that moves too early compared with too late

A cursor that moves too late costs a few repeated fetches. The same stories come back, are matched on their key, and are counted as unchanged. A cursor that moves too early skips changes, and nothing reports it: the next run asks only for what is newer, so the local copy is wrong and looks fine. That is why the cursor is written last and why each run reaches back 5 minutes. The first review showed a second way to end up with the same damage without the cursor moving early at all (a story older than the cursor that was not held), which is why each run also compares the list of assigned stories with what is stored.

## Sensitive values

- No token, password, email address, account ID or Jira hostname is in this folder, the state file, or the scripts. The records were searched for these after each change.
- The fixture tickets are synthetic. The live tickets (SCRUM-17 to SCRUM-22) were made for this proof in Beau's own sandbox site and hold only the summaries shown in `live-run.txt`.
- The live runs wrote their `stories.json` to a throwaway folder outside the repository. Nothing from it was copied in except `sync-state.md`, which holds a timestamp and counts.
