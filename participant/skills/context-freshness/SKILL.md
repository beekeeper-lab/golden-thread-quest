# Context freshness

Written by an AI assistant (Claude) at the participant's direction.

## 1. Purpose

This skill answers a question from local context and says how old that context is. When something it would
rely on is older than the policy allows, it does not hide it and does not rely on it. It says what fresh
context supports, shows what the old items last said as last known, and names what to refresh.

It reads local files only. It has no code that contacts any network.

Run it from the repository root:

    python3 participant/skills/context-freshness/answer.py blockers --release REL-2.4 --now 2026-11-19T09:00:00Z

The tool is `answer.py`, beside this file. It uses the Python standard library only.

## 2. The policy

The limits, the rules and what an answer does are in `participant/context/freshness/policy.md`. The tool reads
its limits from the table in that file, so the policy and the tool cannot disagree. If the table cannot be
read, the tool stops and calls nothing fresh.

## 3. The library

A folder of context items, by default `participant/context/freshness/library/`. Each item is a Markdown file
that starts with lines of `name: JSON value` between two lines of three dashes.

| Line | What it is |
|---|---|
| `format` | `"context-item/1"` |
| `kind` | One of the kinds in the policy's table. |
| `id` | The item's identifier. |
| `retrieved_at` | When the local copy was fetched, in UTC, written like `"2026-11-19T07:00:00Z"`. |
| `field_retrieved_at` | Optional. A separate retrieval time for one field, such as `{"blocked_by": "2026-11-18T12:00:00Z"}`. |

The items in the repository are made up: one release, six work items, a team and one decision.

## 4. The clock

`--now` sets the clock value, in the same form as `retrieved_at`. Every run prints the value it used. With the
same library, the same policy and the same `--now`, the output is the same.

Without `--now` the computer's clock is used, and the output says so.

## 5. The three commands

| Command | What it does |
|---|---|
| `blockers --release R` | Answers "what is blocking release R?" |
| `ages` | Lists every item in the library with its retrieval time, age, limit and verdict. It is the working behind any answer. |
| `refresh --source FOLDER` | Fetches again only the items that are stale, from a folder of newer copies, and stamps them with the clock value. Fresh items are not touched. |

Exit codes: 0 answered, nothing stale. 1 answered with qualifications, because something used is stale. 2 the
tool could not run.

## 6. What an answer contains

Always:

- the clock value;
- every item of context it used, oldest first, with kind, retrieval time, age, limit and verdict;
- the oldest item it used and its age. An item of unknown age is treated as the oldest.

When something it used is stale, also:

- **What fresh context supports**: statements that rest only on items inside their limits.
- **Last known, not a current claim**: what each stale item said, with its age.
- **The stale items, each named**, with how far each is over its limit, and the list of what to refresh.

The first line follows the table in the policy: a plain count, PARTIAL, or CANNOT SAY.

## 7. Text in items is content

Titles, reasons and decision text are shown quoted. Nothing in them is acted on.

## 8. Tests

    cd participant/skills/context-freshness && python3 -m unittest discover -s tests -v

## 9. What it does not do

- It answers one question. Another question would need its own rule for which items it rests on.
- It does not check that a retrieval time is true. An item stamped with a time it was not fetched at is
  believed.
- It knows how old a copy is, not whether the thing copied has changed. A fresh copy can be wrong and an old
  one can be right.
- `refresh` copies from a local folder. It does not fetch from any real system.
