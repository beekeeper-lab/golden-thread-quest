# Freshness policy for local context

This policy says how old a piece of local context may be before an answer stops relying on it. The tool
`participant/skills/context-freshness/answer.py` reads its limits from the table below, so the table and the
tool cannot disagree. If the table cannot be read, the tool stops.

Everything this policy is applied to here is made up: the release, the work items, the team and the decision.

## Limits

| Kind | Limit | Why this limit | When the limit is exceeded, an answer |
|---|---|---|---|
| `work-item-status` | 24 hours | Near a release an item's status and what blocks it change several times a day. Yesterday's blocker is often gone and a new one is missed. | does not state that item's status as current. It shows the old value as "last known", with its age, and counts the item as one it cannot assess. |
| `release-scope` | 3 days | Which items are in a release changes at planning and triage, a few times a week. | does not say what is blocking the release at all. Without knowing what is in the release, no list of blockers can be called complete. |
| `team-ownership` | 30 days | Who owns what changes rarely, and a slightly old copy is still mostly right. | leaves owners out and says so. What is blocking can still be stated. |
| `decision` | 90 days | A recorded decision does not change. It can be superseded, so it is not trusted for ever. | does not apply the decision. An item the decision set aside is reported by its own status, with a note that an old decision once set it aside. |

A limit is a whole number of hours or days. A day is 24 hours.

## The rules

1. **Every item records when it was retrieved**, in a line `retrieved_at`, as a time in UTC written like
   `2026-11-19T07:00:00Z`. That is when the local copy was fetched, not when the work last changed.
2. **Age** is the clock value minus the retrieval time. The clock value is given to the tool with `--now`, so
   that a result can be reproduced. Without `--now` the tool uses the computer's clock and says so.
3. **Stale** means the age is more than the limit for the item's kind. At exactly the limit an item is still
   fresh.
4. **Anything that cannot be shown to be fresh is stale.** That covers an item with no `retrieved_at`, one whose
   `retrieved_at` cannot be read as a time in UTC, one retrieved later than the clock value, one whose kind is
   not in the table, and an item that should be in the library and is missing.
5. **A field can be older than its record.** An item may give a separate retrieval time for one field, in
   `field_retrieved_at`. That field's age is counted from its own time. The limit is still the one for the
   item's kind.

## What an answer does

Every answer, fresh or not:

- states the clock value it used;
- lists every item of context it used, oldest first, with its kind, retrieval time, age, limit and verdict;
- names the oldest item it used and its age.

An answer never leaves a stale item out to look complete, and never uses one without saying so.

When nothing it used is stale, the answer is a plain statement.

When something is stale, the answer is split:

1. **What fresh context supports**, stated plainly.
2. **Last known, not a current claim**: what each stale item said, with its age and limit.
3. **The stale items, named**, and the list of what to refresh.

The first line of the answer changes with what is stale:

| What is stale | First line |
|---|---|
| Nothing | "N work items are blocking release R." |
| One or more work item statuses, scope fresh | "PARTIAL: N work items are blocking release R as far as fresh context shows. M cannot be assessed." |
| The release scope | "CANNOT SAY what is blocking release R." Nothing is stated as blocking or as not blocking. |
| Only team ownership, or only a decision | The count is stated, and the line ends "with qualifications below." |

## How to predict an answer by hand

For each item the answer uses: take the clock value, subtract `retrieved_at`, and compare with the limit for
the item's kind in the table. Then read the first-line table above. The tool's `ages` command prints the same
working for every item in the library.
