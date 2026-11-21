# Failure policy

What the failure-lab workflow does when the service it reads from fails. Written by an AI assistant (Claude) at
Beau Brown's direction.

The workflow is `participant/evidence/base-camp-failure-lab/base-attempt-005/scripts/sync.py`. The service it
reads from is `fake_service.py` beside it, which runs on this machine only and fails on request. Recorded runs
are in `logs/failure-runs.txt` in the same attempt folder.

## 1. Timeout

| | |
|---|---|
| **Symptom** | The workflow sends a request and no answer comes back within 2 seconds. |
| **Response** | **Retry** the same request. A read is safe to repeat, because reading changes nothing. |
| **Limit** | 3 tries in all: the first one and 2 retries. |
| **Reported** | If a retry gets an answer, the run goes on, and the report says how many tries that request took. If all 3 time out, the run **stops**. The report says `FAILED: timeout`, names the request that timed out, and gives the number of items read before it. Nothing is saved as complete. |

A write that times out is a different case. The workflow cannot tell whether the write landed before the
connection went quiet, so repeating it could do it twice. A write is retried only when it carries a rerun key
(see `rerun-key-rules.md`), which makes the second try a skip. A write with no key is not retried. It is
reported as `UNKNOWN: write may or may not have landed`.

## 2. Partial response

| | |
|---|---|
| **Symptom** | The service answers with a success status, but with fewer items than it said there are. Every answer carries a `total` field, the service's own count. The workflow adds up the items it has received and compares that sum with `total`. |
| **Response** | **Stop.** Not retried. |
| **Limit** | 0 retries. |
| **Reported** | `FAILED: partial response`, with both numbers, for example `received 60 of 100`. The 60 items are kept in a file named as incomplete, and are not saved as the synced result. |

Why no retry: the service said "success", so asking again gives no reason to expect a different answer, and a
second short answer would be no easier to trust than the first.

An answer with no `total` field, or a `total` that is not a whole number, is treated the same way: the run stops
and reports `FAILED: no count to check against`. Without the service's count there is nothing to compare with,
and the workflow does not assume the answer is whole.

## 3. Rate limit

| | |
|---|---|
| **Symptom** | The service answers with status 429 ("too many requests") and a `Retry-After` value: the number of seconds it wants the workflow to wait. |
| **Response** | **Wait** the number of seconds the service gave, then send the same request again. |
| **Limit** | No single wait longer than 10 seconds, and no more than 3 waits for one request. |
| **Reported** | If the request then succeeds, the run goes on, and the report says how many waits there were and how long each was. If the service asks for more than 10 seconds, or a 4th wait would be needed, the run **stops**. The report says `FAILED: rate limit`, gives the wait the service asked for, and gives the number of items read before it. Nothing is saved as complete. |

The wait is the service's number, not the workflow's. The workflow does not wait for less, because that would be
asking again before the service said it could.

A 429 with no `Retry-After`, or one that is not a whole number of seconds from 0 up, stops the run with
`FAILED: rate limit with no usable wait`. The workflow does not make up a wait of its own.

## 4. Malformed data

There are two sizes of this failure, and they get different responses.

**The whole answer is malformed.**

| | |
|---|---|
| **Symptom** | The answer cannot be read as JSON, or it can but is not the expected shape: no `items` list, for example. |
| **Response** | **Stop.** |
| **Limit** | 0 retries. |
| **Reported** | `FAILED: malformed answer`, with the reason (for example `not JSON: ends at character 412`), the request it came from, and the number of items read before it. Nothing is saved as complete. |

**One item inside a good answer is malformed.**

| | |
|---|---|
| **Symptom** | The answer reads as JSON and has the expected shape, but one item breaks a rule: its `id` is missing, or its `title` is not text. |
| **Response** | **Skip** that item and go on with the rest. |
| **Limit** | 0 retries. |
| **Reported** | One `rejected` line per skipped item, with its position and the reason. The run ends as `INCOMPLETE`, never as complete, with the counts: for example `99 of 100 saved, 1 rejected`. The saved file is named as incomplete. |

No repair is tried in either case. A cut-off answer is not patched with a closing bracket. A number where text
should be is not turned into text. A missing `id` is not made up from the title. Any of these would be a guess,
and a wrong guess would be saved looking like real data.

What decides stop or skip: whether the workflow can still tell what it has. When one item is bad, the other 99
are known to be good and the bad one can be named. When the whole answer is bad, the workflow cannot say which
items were in it, so there is nothing sound to carry on from.

## 5. After any failure: what is left on disk

The workflow is given one output name, for example `stories.json`.

- A run that read every story the service counted saves them to `stories.json`, which says `"status": "complete"`.
- Any other run writes nothing to `stories.json`. What it did read goes to `stories.json.INCOMPLETE.json`, which
  says `"status": "incomplete"` and gives the reason.
- If a file from an earlier run is already at `stories.json` when a run fails, it is renamed to
  `stories.json.EARLIER.json`. Its contents are not changed.

The reason for the last rule: an earlier complete file is true about the earlier run, but a person who opens it
after today's failure would read it as today's result. After a failure, no file with the complete name is left.

Shown in run 5 of `logs/failure-runs.txt`, and checked in `logs/no-false-success.txt`.
