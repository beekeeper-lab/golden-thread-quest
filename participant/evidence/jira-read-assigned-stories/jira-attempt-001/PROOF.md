# Proof · jira-read-assigned-stories

Attempt: `jira-attempt-001`

## What was built

- `participant/skills/jira-read-assigned/SKILL.md`: the skill's workflow, safety rules, field mapping, merge rules, and output rules.
- `participant/skills/jira-read-assigned/sync.py`: the sync script. It reads three environment variables, resolves the account from Jira, fetches assigned stories and counts other assigned work items, maps each story to the canonical fields, merges with the previous run, and writes `stories.json` and `index.md`. A fixture run reads a file in `validators/fixtures/jira/` instead of calling Jira.
- `participant/skills/jira-read-assigned/rerun_check.py`: runs each fixture twice, plus a two-run merge demonstration, to show that a rerun is safe.
- `participant/skills/jira-read-assigned/tests/test_sync.py`: 17 tests with Jira replaced by a stub. They run in a temporary folder and never touch the workspace or the network.
- `participant/context/jira/assigned/notes/GTQ-101.md`: a participant note, written by me, used to show that notes survive a sync.

## Where the important artifacts are

- Skill definition: `participant/skills/jira-read-assigned/SKILL.md`
- Script: `participant/skills/jira-read-assigned/sync.py`
- Normalized stories: `participant/context/jira/assigned/stories.json` (currently the `happy-path` fixture output)
- Index: `participant/context/jira/assigned/index.md`
- Participant notes: `participant/context/jira/assigned/notes/`
- Validator results: `participant/evidence/jira-read-assigned-stories/jira-attempt-001/validation/`
- Test and rerun-check output: `participant/evidence/jira-read-assigned-stories/jira-attempt-001/logs/`

## How identity resolution works

The skill sends `GET /rest/api/3/myself` with the API token and keeps only the `accountId` from the answer. It builds the story query from that ID: `assignee = "<accountId>" AND issuetype = Story`. No username, email, or display name appears anywhere in the skill. The test `identity_comes_from_jira` checks that the identity call is the first request and that the query uses the ID it returned.

## How pagination works

Jira's search (`/rest/api/3/search/jql`) returns a `nextPageToken` while more results exist. The skill sends that token with the next request, and stops when Jira returns no token. Both searches (stories, and the count of other work items) follow the same loop. If Jira sends a token it already sent, the skill stops with an error and leaves the previous `stories.json` in place. A story that Jira returns on two pages is stored once.

The validator's `pagination` fixture checks only that all four fixture stories appear in the output. A fixture run does not use the paging loop, so that check says nothing about it. The paging loop is shown by the stubbed test `pagination_follows_every_page_and_stores_each_story_once`, which serves three pages.

## How merging works

- Stories are matched on their Jira key, never their title.
- Participant notes live in `participant/context/jira/assigned/notes/<KEY>.md`. The skill only checks whether a notes file exists, so the index can link to it. It never writes to, moves, or deletes those files.
- Comments are matched on their `id`. A comment already stored is not added again, and its timestamps are refreshed when Jira returns it. A comment Jira no longer returns is kept.
- A story that was synced before and is not returned now goes under `removed` with its key and last known status. It stays there until it is assigned again.
- Live and fixture output never mix. A live run merges only with earlier live output. It replaces fixture output, and its summary says so, so fixture stories are never reported as removed. A fixture run stops without writing if `stories.json` holds live data. A fixture run starts fresh each time, so it gives the same result every time.

## How to reproduce the behavior

From the repository root. Fixture runs need no Jira credentials:

```
python3 participant/skills/jira-read-assigned/tests/test_sync.py
python3 participant/skills/jira-read-assigned/rerun_check.py
python3 participant/skills/jira-read-assigned/sync.py --source happy-path
quest-app action run-validator --quest jira-read-assigned-stories --validator validate-jira-read-assigned --param fixture_set=happy-path
```

The other fixtures are `pagination`, `stale-item`, and `duplicate-comment`. On this machine the same tool is installed as `gtq`, and that is the command I ran.

The live path needs `JIRA_BASE_URL` (starting with `https://`), `JIRA_EMAIL`, and `JIRA_API_TOKEN` set in the shell:

```
python3 participant/skills/jira-read-assigned/sync.py
```

The validator reads `stories.json`, so it has to hold fixture output when the validator runs. A fixture run will not replace live data, so move a live `stories.json` aside first.

## What was tested or validated

Observed, on the final code:

- Validator: `pagination`, `stale-item`, `duplicate-comment`, and `happy-path` each passed every check (runs at 20:38 UTC on 2026-10-22). After the live run below, I restored the `happy-path` output (20:40:03 UTC) and validated it again, and it passed every check (20:40:23 UTC). So the `stories.json` in the workspace is the validated one.
- Live sync, run from my terminal: zero stories, zero removed, and zero other items, because my account has no assigned work. It replaced the `happy-path` fixture output and printed a warning saying so, instead of reporting the fixture stories as removed. The output held no account ID or email address.
- Stubbed tests: 17 of 17 passed (`logs/tests.txt`). They cover identity, pagination, a repeated page token, privacy, fixture and live separation, comments, acceptance criteria, settings, and the fixture path. Run against the version of `sync.py` from before those fixes, 10 of the 17 fail, so the tests can tell a broken version from a working one.
- Rerun check: passed (`logs/rerun-check.txt`). Each fixture gave the same output on a second run apart from timestamps, no comment was duplicated, and my note in `notes/GTQ-101.md` was unchanged. In the merge demonstration, a new comment was added once, a story that left was reported under `removed`, and a note was left alone and linked from the index.

Observed, earlier in the attempt:

- The first `happy-path` validator run failed `records-are-normalized`, because the script named two fields `title` and `last_synced_at` where the quest's data contract requires `summary` and `retrieved_at`. I renamed them. That failed run, and four passing runs on that earlier version, are still in the validation folder.
- Identity: run from my terminal, the `/myself` call returned an active account for my token. The account ID is not recorded here.
- Live query: my account has no assigned work items of any type. A browser search for open items also returned none. A live sync, run before the fixes described below, wrote zero stories and zero other items.
- Jira fields: a check of all 142 field names on the site found none named for acceptance criteria.

An independent review of an earlier version found that the live path would store other people's names and emails, that notes and safe reruns had no evidence, that a fixture run could silently replace live data, and that this file overclaimed. Those were fixed in `sync.py`, `SKILL.md`, and here, and each fix has a stubbed test or a recorded check.

Not assessed:

- A real story going through the skill. My account has no assigned stories, so the live run returned none.
- Live pagination across several real pages. The loop is shown only with stubbed pages.
- How a real Jira site answers the narrower field list.
- Real descriptions and how teams write acceptance criteria.
- Comments beyond the first page of an issue.
- The 401 and network-error messages. They come from reading the code, not from a test.

A passing validator run is not reviewer approval.

## Remaining limitations

- Comments: only the comments Jira includes in the issue response are stored. The sync warns when an issue holds more, but does not fetch the rest.
- Acceptance criteria come from a heading or an all-bold line that reads "Acceptance criteria" at the top level of the description. "AC" on its own is not matched. Fields named "Test plan" and "Checklist" exist on the site, and I have not checked whether any team keeps criteria there. Stories with no criteria, or an empty list, are listed under "Missing acceptance criteria" in `index.md`.
- Description conversion handles paragraphs, headings, lists, checklists, and code blocks. Tables and text formatting are reduced to plain text.
- Only six extra Jira fields are kept under `platform`. Custom fields are not stored, so any team-specific field is lost.
- The `removed` list keeps every story that left until it is assigned again. It is never trimmed.
- A comment deleted in Jira stays in the local copy.
- Fixture and live output share one `stories.json`, because the validator reads only that path.
- `stories.json` and `index.md` are each written safely, but not together. A failure between the two writes would leave a new `stories.json` beside the old `index.md`.
- Delta sync, field-level conflict reports, and a machine-readable reconciliation summary are not built.
- Summaries in `index.md` may contain organization-specific text. Redact them before sharing.

## Sensitive values

- No token or email address is stored in this folder, the outputs, or the logs.
- The current outputs and the validator records hold fixture data only.
- A live run stores each story's assignee account ID, as section 6 of `SKILL.md` specifies. Review live output before sharing it.
- The Jira site name and the keys of other teams' tickets that I used to check field names are not recorded here.
