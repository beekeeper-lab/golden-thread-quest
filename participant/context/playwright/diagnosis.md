# Diagnosis: "a saved order shows on Your orders" timed out

Diagnosed from the failure bundle alone, without rerunning the test (criteria 5 and 7). Every claim
names the bundle file that supports it. The bundle is
`participant/evidence/playwright-failure-evidence/playwright-attempt-011/failure-bundle/`, and the
file names below are relative to it. Diagnosis by Tom Carter, from his answers to one question per
file; written up with Claude (Claude Code), 11-16-2026.

We knew the failure had been planted (that's how the quest makes one on purpose). The diagnosis
deliberately reads only the bundle; the last section compares it with what was actually broken.

## What failed

The test waited 5 seconds for the row of its own order ("Test User qa-a155b3a3-…") on Your orders,
found no row and failed after 5.1 s with "element(s) not found" (`error.txt`).

On its own this is the scenario's "timeout": it says what was missing and how long the test waited,
but not why. It rules out none of the three suspects: the page, the network or the data
(`error.txt`).

## The page: loaded, and said the server side failed

- The page loaded: the screenshot shows the Your orders heading and the table's column headings
  (`test-failed-1.png`), and Playwright's outline of the page has the same heading and an empty
  table (`error-context.md`).
- Under the table the page says "Something went wrong on our side. Please try again later."
  (`test-failed-1.png`; also `error-context.md`, the "status" line).
- So it isn't "the app was down" or "a broken page". The message points at the server side, but a
  screenshot can't say which request failed or how.

## The network and the orders service: one request, answered 500, at once

- The page's request for the list, `GET /api/orders`, came back **500 Internal Server Error** at
  **+0.03 s**, with the body "Something went wrong on our side. Please try again later."
  (`failed-requests.txt`).
- At the same moment the browser console has two errors: the browser's own "the server responded
  with a status of 500" for `/api/orders`, and the page's "Loading orders failed: GET /api/orders
  answered 500" (`console.txt`).
- The request reached the server and got an answer, so the network itself worked: the failure is the
  orders service's answer (`failed-requests.txt`).
- The trace shows the same: the Navigate step to `/orders` is marked with one failed request, and its
  Network tab lists the page's two requests: the page itself, `GET /orders`, answered 200, and the
  list, `GET /api/orders`, answered 500 (`trace.zip`, opened with `npx playwright show-trace trace.zip`).

## The timing: not slow, failed

The answer came back within 0.03 s, as a failure, and the page never asked again (no later request
in `failed-requests.txt`, `console.txt` or the trace's Network tab), while the test waited the whole
5 seconds (`error.txt`). A longer timeout, or retrying the wait, could never have made the row
appear. "Timeout" here is a symptom, not the cause.

## The data: the order existed

The trace's list of steps shows the passed check "the orders service saved the order" before
"Navigate /orders" (`trace.zip`, Actions list). The order was saved before the page opened; the page just never
received the list that would have shown it. The data is not at fault.

## Verdict

**The orders service failed.** `GET /api/orders` answered 500 to the Your orders page, at +0.03 s,
while the test's order existed. The page and the network behaved; the test did its job and should
not be changed (no retry, no longer timeout). The bug report goes to the orders service, with this
bundle attached.

## What the bundle can't tell

Why the orders service answered 500. Everything in the bundle is what the browser saw; nothing
comes from the server's side. What Tom would most want added: the server's log for that moment, to
see why it failed (the attempt's PROOF.md, "Reflection").

## Checked afterwards (not used above)

The broken copy (`participant/tests/playwright/tools/break-orders-list.ts`, recorded in the
attempt's `logs/failing-run.txt`) made the orders service answer the page's request for the list
with a 500 and made the page write the failure to the console. The diagnosis matches what was
broken.
