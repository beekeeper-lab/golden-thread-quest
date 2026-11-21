# Proof · base-camp-failure-lab

Attempt: `base-attempt-005`

## How this was made

An AI assistant (Claude) wrote the policy, the fake service, the workflow, the two recording scripts and this
file, at Beau Brown's direction. The work was done in small steps, each shown to Beau before the next.
Beau decided how a failed run treats an earlier complete file (rename it), and agreed the answer to "which
failure was hardest to tell from success". The retry limit, the wait limits, and the choice of stop or skip for
each failure were proposed by the assistant and shown to Beau as his to change.

Statements below are marked **observed** (a run recorded in `logs/` shows it) or **not assessed**.

## How a partial response is detected (criterion 3)

The workflow does not decide it is finished because the requests succeeded, or because the service said there
are no more pages. It decides by counting.

Every answer from the service carries `total`, the service's own count of all stories. The workflow keeps a
running count of the items it has received. When the service says there is no next page, the workflow compares
the two numbers. If they differ, the run ends as `FAILED: partial response`, with both numbers.

Observed in `logs/failure-runs.txt`, run `2-partial`. The service is told to answer page 3 as if it were the
last page. Every status is 200. The workflow has 60 items, the service's count is 100, and the run ends:

    sync: RESULT: FAILED partial response: received 60 of 100

The 60 items are not saved under the complete name (criterion 3). They are kept in
`work/2-partial.json.INCOMPLETE.json`, which says `"status": "incomplete"`. Observed in
`logs/no-false-success.txt`, run `2-partial`: the complete-named file does not exist, and the incomplete file
holds 60.

What this check depends on, and where it stops:

- It needs the service to give a count. An answer with no usable `total`, or a `total` that changes between
  pages, stops the run with `FAILED: no count to check against`. This is in the code but **not assessed**: the
  fake service has no switch that drops or changes the count, so no run shows it.
- It trusts the service's count. If the service's count were itself short, say `total: 60` with 60 items, the
  two numbers would agree and the run would end complete. Nothing inside the workflow can see that.

## Which failure was hardest to tell from success

The partial response (criterion 3).

The four failures, from easiest to hardest to tell from success, by what the service sends:

| Failure | What the workflow sees | What gives it away |
|---|---|---|
| Timeout (criterion 2) | No answer at all. | The request itself fails. Nothing has to be checked. |
| Rate limit (criterion 4) | Status 429. | The status says it is not a success. |
| Malformed answer (criterion 5) | Status 200, but the body will not read as JSON. | The first attempt to use the answer fails. |
| Malformed item (criterion 5) | Status 200, good JSON, the right number of items. | Only looking inside each item: one has no `id`. |
| Partial response (criterion 3) | Status 200, good JSON, every item well formed. | Nothing in any one answer. Only the sum across all answers, set against the service's count. |

For the first three, a workflow that did no checking would still stop, because it would have nothing to carry
on with. For the last two it would carry on and report success. The partial response is the harder of those
two because each answer, taken alone, is a correct answer. The fault is only in what is missing, and what is
missing does not show up anywhere unless the workflow goes looking for a number to compare with.

Observed in `logs/failure-runs.txt`: in run `2-partial` the workflow's lines for pages 1, 2 and 3 are the
same as in run `0-healthy`. The two runs differ only after the last page.

A second thing that read as success turned up during the work, and it was not one of the four. A run that
failed left an earlier run's complete file in place under the complete name. The report said `FAILED`, but the
folder still held a file saying complete (criterion 7). This is now handled by renaming the earlier file, and
is shown in run `5-failure-after-earlier-success`.

## Reflection: which failure stops the run, and which skips one item

Only one failure skips: a single malformed item inside a good answer. Every other failure stops the whole run,
once its retries or waits are used up.

What decided it was one question: after this failure, can the workflow still say exactly what it has and what
it lacks?

- One bad item: yes. The other 99 were checked and are good, and the bad one can be named by its page and
  position. Going on loses nothing more, and the report can list what was left out.
- A page that never answers, a page that is refused, or an answer that will not read: no. The workflow does not
  know which stories were on that page. It could go on to the next page, but it would end with a hole it cannot
  describe.
- A partial response: no. The count shows that 40 are missing, but not which 40.

Skipping does not turn a run into a success. A run with a skipped item ends as `INCOMPLETE`, and what it saves
is named and marked incomplete, the same as a run that stopped. Stop or skip changes how much is kept. It does
not change what the run is called.

## What was built

Three things, all in this attempt folder or `participant/context/`.

- **A policy**, `participant/context/failure-policy.md`. For each failure it gives the symptom, the response
  (retry, wait, stop or skip), the limit, and what is reported.
- **A fake service**, `scripts/fake_service.py`. A small web server on `127.0.0.1` only. It holds 100 made-up
  stories, 20 to a page, and each answer carries the service's own count. It is started with one failure
  switched on: `timeout`, `partial`, `rate-limit`, `malformed` or `malformed-item`. It makes no outgoing
  requests and writes no files.
- **A workflow**, `scripts/sync.py`. It reads every page from the service and saves the stories to one file. It
  refuses any address that is not `127.0.0.1`. Its last line is always `RESULT: COMPLETE`, `RESULT: INCOMPLETE`
  or `RESULT: FAILED`.

The workflow only reads. It sends no writes to the service, so the policy's rule for a write that times out
(retry only with a rerun key) is written down but has no code and no run behind it. **Not assessed.**

## Where the important artifacts are

| What | Path |
|---|---|
| The policy | `participant/context/failure-policy.md` |
| One recorded run per failure (10 runs) | `participant/evidence/base-camp-failure-lab/base-attempt-005/logs/failure-runs.txt` |
| The check that no failure was saved as complete | `participant/evidence/base-camp-failure-lab/base-attempt-005/logs/no-false-success.txt` |
| The fake service | `.../base-attempt-005/scripts/fake_service.py` |
| The workflow | `.../base-attempt-005/scripts/sync.py` |
| The script that records the first log | `.../base-attempt-005/scripts/record_evidence.py` |
| The script that records the second log | `.../base-attempt-005/scripts/check_no_false_success.py` |
| The files the recorded runs saved | `.../base-attempt-005/work/` |

## How to reproduce the behavior

Needs Python 3.9 or later and nothing else. Port 8799 on this machine must be free. From the repository root:

    cd participant/evidence/base-camp-failure-lab/base-attempt-005
    python3 scripts/record_evidence.py
    python3 scripts/check_no_false_success.py

The first command empties `work/`, runs the 10 cases and rewrites `logs/failure-runs.txt`. It takes about 40
seconds, most of it the workflow waiting on purpose. The second reads `work/`, rewrites
`logs/no-false-success.txt`, and exits 0 only if every check passed.

To try one failure by hand, use two terminals:

    python3 scripts/fake_service.py --fail partial
    python3 scripts/sync.py --out work/try.json

A file left in `work/` by a hand run will make the second command's sweep fail on the file count. Delete it, or
run the first command again.

## What was tested or validated

All of this is **observed**: each line names the recorded run that shows it. Runs are in
`logs/failure-runs.txt` unless another file is named.

| # | Criterion | Shown by |
|---|---|---|
| 1 | The fake service can produce each of the four failures on demand. | Each run starts the service with one `--fail` switch, and the service prints an `INJECTED` line when it fails on purpose. Timeout: runs `1a`, `1b`. Partial response: run `2`. Rate limit: runs `3a`, `3b`, `3c`. Malformed data: runs `4a`, `4b`. Run `0-healthy` is the same service with no failure. |
| 2 | A timeout is retried a bounded number of times, then reported as a failure. | Run `1a`: three tries, `try 3 of 3`, no fourth, then `RESULT: FAILED timeout: page 3 gave no answer in 3 tries`. Run `1b`: two timeouts, an answer on the third try, `RESULT: COMPLETE`, with the tries listed. |
| 3 | A partial response is detected and not saved as complete. | Run `2`: `RESULT: FAILED partial response: received 60 of 100`. In `logs/no-false-success.txt`, run `2`: the complete-named file does not exist. |
| 4 | A rate limit makes the workflow wait as the service directs, within a stated limit. | Run `3a`: the service asks for 2 seconds, the workflow reports `waited 2.0 seconds`, then completes. Run `3b`: three waits, no fourth, then `FAILED`. Run `3c`: the service asks for 60 seconds, the limit is 10, the workflow stops without waiting. |
| 5 | Malformed data is rejected with the reason and without guessing at a repair. | Run `4a`: `FAILED malformed answer: page 3: not JSON`, with the parser's reason. Run `4b`: `rejected item 7 on the page: no id (skipped, not repaired)`. In `logs/no-false-success.txt`, run `4b`: the saved file holds 99 stories and every one is a real one, so no `id` was made up for the bad item. |
| 6 | Every failure appears in the final report with the amount of work that completed. | Each failed run prints `items read before the failure: N good, M rejected` above its `RESULT: FAILED` line: 40 in runs `1a`, `3b`, `3c` and `4a`, 60 in runs `2` and `5`. Run `4b` ends `RESULT: INCOMPLETE 99 of 100 saved, 1 rejected`. The failures that were recovered from (runs `1b`, `3a`) also appear, as the tries or waits taken. |
| 7 | No failure leaves a result that reads as complete. | `logs/no-false-success.txt`: for each of the 7 runs that failed or was incomplete, the complete-named file does not exist and the file that does exist says `incomplete` in its name and inside. The sweep lists all 11 files in `work/`: every file that says complete holds all 100 stories. |

The checker for criterion 7 was itself checked. A false success was planted by hand (a 60-story file saved
under the complete name and marked complete). The checker reported 4 failed checks and exited 1. Observed in
`logs/checker-catches-planted-false-success.txt`. The plant was then removed and the log recorded again.

The safety constraints:

- Fail only your own fake service. The service listens on `127.0.0.1` only, and the workflow refuses any other
  address before sending a request. The refusal was seen in a hand run and is **not recorded** in a log.
- Do not retry without a limit. Timeout: 3 tries (run `1a`). Rate limit: 3 waits of at most 10 seconds each
  (runs `3b`, `3c`). Partial response and malformed data: no retry.
- Do not retry a write that may have already succeeded. The workflow sends no writes. **Not assessed.**

## Remaining limitations

Known so far. There may be others.

Rules that are written but have no run behind them:

- **A write that times out.** The policy says to retry it only with a rerun key. The workflow sends no writes,
  so there is no code for this and nothing shows it. The third safety constraint is met only because no write
  is ever sent.
- **An answer with no usable count, or a count that changes between pages.** The code stops the run. The fake
  service cannot produce either.
- **A repeated `id`, and a `next` that points backwards.** The code rejects the first and stops on the second.
  Neither is in the policy and the fake service cannot produce either.
- **Any other failure**, such as a refused connection or a status 500. The run stops as `FAILED`, with a
  message that begins `not handled yet`. No run shows it, and the policy has no rule for it.
- **Refusing an address that is not `127.0.0.1`.** Seen in a hand run, not recorded.

What the recorded runs do not cover:

- Every failure is injected on page 3, one failure to a run. Two failures on one request are not run. The
  timeout tries and the rate-limit waits are counted apart, so one request could take 3 tries and 3 waits.
- A run that is killed part-way. It would write neither file. **Not assessed.**
- The fake service counts requests, not time. It turns healthy after the set number of refusals whether or not
  the workflow waited. The 2.0 seconds in run `3a` is the workflow's own measurement of its wait.
- `Retry-After` is read only as a whole number of seconds. The other form a real service may send, a date, is
  treated as no usable wait and stops the run.
- The 2-second timeout applies to each wait for data, not to the whole request. A service that sent a little
  data every second could hold a request open for longer.

What the count check cannot see:

- A service whose own count is short. If it says `total: 60` and sends 60, the run ends complete.

Other:

- There are no unit tests. The checks are the two recording scripts and what they print.
- No independent review has been run on this attempt.
- If a run fails twice over an earlier file, the second rename replaces the first `EARLIER` file.
- Neither stretch goal was done: no fifth failure, and no back-off that grows between retries.

## Sensitive values

None. The stories are made up by the fake service (`STORY-001` to `STORY-100`, titled `Story 001` to
`Story 100`). The service runs on this machine only and needs no login, so there is no token, key or password
anywhere in the code or the logs. No customer name and no real ticket content appears. The only person named
is Beau Brown, as the participant.
