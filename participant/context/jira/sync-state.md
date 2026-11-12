# Jira sync state

Written by `participant/skills/jira-read-assigned/sync.py --delta`. Do not edit by hand.

- cursor: 2026-11-10T16:09:14.124-0500
- last_successful_sync: 2026-11-10T21:09:44Z
- safety_margin_minutes: 5
- source: live
- last_run: fetched 4, new 0, changed 0, unchanged 5, removed 0

## What the cursor is

The cursor is the newest `updated` timestamp Jira has sent for a story that was held in `assigned/stories.json`
when a delta run finished. It stays where it is if that story later leaves the list.
It is Jira's own timestamp, copied as Jira sent it. This machine's clock is never used to build a query.
`last_successful_sync` is this machine's clock and is here for people to read; no query uses it.

## How it is updated

1. A delta run reads the cursor and asks Jira for stories updated at or after the cursor minus the safety margin.
2. It lists every story assigned now with its key and updated time only. A story that left the list is
   reported as removed. A listed story whose local copy is missing or has a different updated time is fetched by key.
3. It merges what came back into `stories.json`, matching on the Jira key, and rewrites `index.md`.
4. Last of all, it writes this file with the new cursor.

If any request or write in steps 1 to 3 fails, the run stops before step 4 and this file is left as it was.
The next run asks the same question again. Stories fetched twice are matched on their key, so nothing is duplicated.
The cursor never moves backward.
