# Proof · playwright-failure-evidence

Attempt: `playwright-attempt-011`

Decisions, predictions and the answers below are Tom Carter's; the configuration, the tools, the
logs and these notes were drafted with Claude (Claude Code) from his answers, 11-13-2026 (setup) and
11-16-2026. Everything runs against the local Tixly demo app, or a broken copy of it in a temporary
folder, with made-up data; nothing is sent anywhere.

## What was built

- **The evidence configuration** (`tests/playwright/evidence.config.ts`): the normal configuration
  with only what is kept, where and for how long changed. A failing test keeps a trace, a
  screenshot, the console, the failed requests and the error text; a passing test keeps nothing
  (its folder is removed). No video, and no HTML report (which would keep a second copy of every
  trace and screenshot). Evidence lasts until the next run, which empties `test-results/`; a bundle
  that should outlive that is copied out on purpose. All of this is written at the top of the file.
- **The recorder** (`tests/playwright/support/evidence-fixture.ts`): while a test runs, it notes the
  page's console messages and uncaught errors, and every answer of 400 or more (with the first 300
  characters of its body, if it arrives within 2 seconds) and every request that got no answer. A pass drops the notes; a failure
  writes `console.txt`, `failed-requests.txt` and `error.txt`. It never notes headers or what the
  page sent, drops the `?…` part of addresses, and shortens file paths so the computer's user name
  doesn't show.
- **The failing test** (`tests/playwright/evidence-tests/orders-list.evidence.ts`): creates an order
  through the orders service, opens Your orders and waits for its row. It is named `*.evidence.ts`
  so only the evidence configuration runs it: the normal configuration runs every `*.spec.ts` in any
  folder, and with that name it would have changed the main suite from 27 tests to 28 and broken
  quest 18's selections.
- **The broken copy** (`tests/playwright/tools/break-orders-list.ts`): copies the demo app to a new
  folder and changes one line in each of two files, so the orders service answers the Your orders
  page's request for the list with a 500, and the page writes the failure to the console. Only the
  page's own request breaks; setup and cleanup ask from Node with the API key and keep working, so
  the run still cancels its order.
- **The copy step** (`tests/playwright/tools/copy-failure-bundle.ts`): copies one failing test's
  folder out of `test-results/` and replaces the home-folder address with `~` in every text file and
  in every text file inside `trace.zip`. The trace keeps a copy of each test file under `src/`,
  named by the sha1 of its full address, and the trace viewer finds the source by that name; the
  copy step renames those files to the sha1 of the shortened address, so the viewer's Source tab
  still works.
- **The check** (`tests/playwright/tools/failure-evidence-check.ts`): scans every file of a bundle,
  every file inside `trace.zip` and the zip's comments and extra fields, for the run's actual API
  key (as it is, URL-encoded, base64 or escaped as in JSON), the shapes of tokens, cookies and
  credentials, and the home-folder address; JSON strings are also checked as their real values,
  after escapes. It reports the file, line and kind, never the value. `--self-test` first requires
  the untouched bundle to be clean, then plants three fresh fake values in a temporary copy and
  passes only if each is found at the exact file and line. Pictures can't be read, so they are
  listed to be checked by eye.
- **A small zip reader and writer** (`tests/playwright/tools/zip-lite.ts`) and **a JSON reader that
  keeps where each string is** (`tests/playwright/tools/json-places.ts`), for the two tools above,
  with no extra package. A zip it can't fully read stops the check with an error instead of being
  skipped.
- **The diagnosis** (`context/playwright/diagnosis.md`), from the bundle alone.
- **The README and setup check** describe the evidence configuration and the tools, and track the
  eight new files (45 project files instead of 37).

My decisions:

- **The failure:** the orders service breaks for the Your orders list (a 500), so the test
  fails with only a timeout and the cause is only in the evidence, as in the quest's scenario.
- **Passing tests keep nothing heavy:** a trace and a screenshot only on failure; the console and
  failed requests collected during every test but written only on failure.
- **Kept until the next run,** stated in the configuration; the hand-in bundle is copied out on
  purpose.
- **A check script that looks everywhere,** including inside `trace.zip`, for token, cookie and
  credential shapes and the run's actual API key; file and line only; proven with a planted fake.
- **No video:** the trace's snapshots of each step are enough, and a video means more frames to
  check for personal data.
- **Hide the home-folder address:** it isn't a secret, but it shows the computer's user name and the
  repository is public. The trace holds it in 13 lines (18 places, as some lines have it more than
  once), so the copy step replaces it in the copy, and the trace is shown to still open.
- **No stretch goal:** the server log is listed below as what I'd do next.

## Reflection: what is the most useful thing your bundle leaves out?

The server's log for that moment, to see why it failed. Everything in the bundle is what the browser
saw: it proves the orders service answered 500 at once while the order existed, but not why. The
person fixing the orders service would start there (criterion 7: the diagnosis is complete up to
that point, `context/playwright/diagnosis.md`, "What the bundle can't tell").

## Where the important artifacts are

All paths are under `participant/`; the attempt folder is
`evidence/playwright-failure-evidence/playwright-attempt-011/`.

| What | Path |
|---|---|
| The evidence configuration | `tests/playwright/evidence.config.ts` |
| The recorder | `tests/playwright/support/evidence-fixture.ts` |
| The failing test | `tests/playwright/evidence-tests/orders-list.evidence.ts` |
| The broken copy | `tests/playwright/tools/break-orders-list.ts` |
| The copy step, the check, the zip and JSON readers | `tests/playwright/tools/copy-failure-bundle.ts`, `failure-evidence-check.ts`, `zip-lite.ts`, `json-places.ts` |
| The bundle | `<attempt>/failure-bundle/` |
| The passing and failing runs | `<attempt>/logs/passing-run.txt`, `<attempt>/logs/failing-run.txt` |
| Copying the bundle out | `<attempt>/logs/copy-bundle.txt` |
| The scan and the self-test | `<attempt>/logs/redaction-check.txt` |
| The diagnosis | `context/playwright/diagnosis.md` |

## How to reproduce the behavior

With the project set up as its README says (`npm ci --engine-strict`, then `npx playwright install
chromium`), from `participant/tests/playwright`, with a made-up key for the demo app's orders
service:

```
export TIXLY_API_KEY=$(openssl rand -hex 16)
npx playwright test --config evidence.config.ts                   # passes; keeps nothing
node tools/break-orders-list.ts /tmp/broken-tixly                 # a new or empty folder
TIXLY_DEMO_PORT=4192 node /tmp/broken-tixly/server.js &
TIXLY_BASE_URL=http://127.0.0.1:4192 npx playwright test --config evidence.config.ts   # fails
kill %1
node tools/copy-failure-bundle.ts test-results/orders-list.evidence.ts-a-saved-order-shows-on-Your-orders-chromium /tmp/bundle
node tools/failure-evidence-check.ts /tmp/bundle
node tools/failure-evidence-check.ts --self-test /tmp/bundle
npx playwright show-trace /tmp/bundle/trace.zip
```

## How the work meets the criteria

1. **A failing test produces a trace, a screenshot, the console log, failed requests and the error
   text:** `failure-bundle/` holds `trace.zip`, `test-failed-1.png`, `console.txt`,
   `failed-requests.txt` and `error.txt`, plus Playwright's own `error-context.md`
   (`logs/failing-run.txt`: 1 failed after 5.1 s, the six files listed).
2. **A passing test does not keep heavy evidence by default:** `logs/passing-run.txt`: 1 passed,
   and `test-results/` afterwards holds only Playwright's one-line `.last-run.json`.
3. **The bundle contains no token, cookie or credential, shown by a scan:**
   `logs/redaction-check.txt`, part 1: 6 files and 17 files inside `trace.zip` scanned, nothing
   found, PASS. The run's API key appears nowhere: the tests send it from Node, so the browser and
   the trace never see it.
4. **The scan finds a planted fake value:** `logs/redaction-check.txt`, part 2: a fake bearer token
   in `console.txt`, a fake session cookie inside `trace.zip` and the run's API key in `error.txt`,
   each found at its exact file and line, and no value shown, PASS. Part 3 is the original in
   `test-results/`: FAIL, the home-folder address on 13 lines inside the trace and nothing else,
   which is why the copy step exists.
5. **The diagnosis cites a bundle file for each claim:** `context/playwright/diagnosis.md`.
6. **The configuration states how long evidence is kept:** `evidence.config.ts`, "HOW LONG": until
   the next run.
7. **Another person can diagnose the failure without rerunning the test:** I diagnosed it from the
   bundle alone, one file at a time (`context/playwright/diagnosis.md`): the error only says the row
   never appeared; the screenshot shows the page loaded with "Something went wrong on our side"; the
   failed requests and the console show `GET /api/orders` answered 500 at +0.03 s, so waiting
   longer could never help; the trace shows the order was saved before the page opened. Verdict:
   the orders service failed, and the test did its job. It matches what the broken copy changed.

## What was tested or validated

- **The recording** (`local-data`, not handed in) ran everything in one go on 11-16-2026 at
  10:38 AM, from the same files: the passing run, the failing run, the copy, the scan, the self-test
  and the scan of the original. Each log's header names the commit (`d0d100a`, with the quest's
  files not yet committed). The saved logs show the home folder as `~` and were scanned with the
  same check: nothing found. The real orders file was unchanged afterwards, and the run's order was
  cancelled from the broken copy (0 left).
- **The copied trace still opens:** opened in Playwright's trace viewer with Playwright's own
  Chromium, alongside the original as a control: both list the same 7 steps, the failing step is
  "Expect toBeVisible" after 5.0 s, and the Source tab shows the test's code with line 18
  highlighted. The copy contains the home-folder address 0 times.
- **Reviews and checks:** a self-review of every file, then four rounds of AI code review on a
  practice pull request (12, 9 and 11 findings, then none open), each finding reproduced with
  made-up values before it was fixed or listed; after the fixes, the reproductions of all fixed
  findings no longer reproduce. The project's setup check passes: 45 of 45 project files tracked,
  and its credential scan of the files Git would commit finds 0.
- **Images checked by eye,** by Claude and by me: the screenshot and the trace's 3 page images show
  only the Your orders heading, an empty table and the "Something went wrong" message: no name,
  order or personal data.
- **My predictions:** right that the test would fail with only a timeout; that a passing run keeps
  nothing; that `error.txt` would say nothing about the 500; that the API key would be found
  nowhere, because it goes from Node; and that the copy step's 18 places and the scan's 13 lines
  differ because some lines hold the address more than once (10 lines with one, and 2, 2 and 4).

## Remaining limitations

- **No server log** (the reflection, and the quest's first stretch goal): the bundle shows that the
  orders service failed, not why. Next, I'd have the demo app log each request it answers and copy
  the lines for the test's time window into the bundle.
- **Only tests that use the recorder** (`evidence-tests/`) get `console.txt` and
  `failed-requests.txt`; the main suite's configuration is unchanged (it already keeps a trace and a
  screenshot on failure, and its trace records the console and network too).
- **The check is a safety net, not a guarantee:** it finds the exact key and the shapes of common
  secrets; a secret in an unusual shape could get past it. Pictures are only searched for the key
  and the home-folder address, so they are checked by eye. The self-test proves the scan finds
  planted values (and refuses to plant into a bundle that isn't clean); the plain scan is what
  shows the bundle is clean.
- **Known gaps, listed rather than fixed:** three rounds of AI code review found 32 ways a
  hand-made file could get past the tools (12, 9 and 11); I reproduced each, fixed the 21 from the
  first two rounds and the self-test one from the third, and stopped there, as these got further
  from anything this project produces. Ten remain, each reproduced with made-up values: a
  Set-Cookie header written as a list; the key as big-endian UTF-16 inside a binary file; a
  credential written in a file's name; a zip named in capitals (`TRACE.ZIP`), which isn't opened; a
  readable credential in binary zip metadata; JSON after a prefix on a line (`body: {…}`), whose
  escaped values aren't decoded; bytes in a zip that no record covers; a number over 400 digits,
  which drops its JSON line from the decoded check; the home-folder address with lower-case percent
  escapes (`%2f`); and a destination folder that is a link into the source, which the copy step
  follows and copies into until the path is too long. A fourth round left no open comments, but its summary named one more, which I also
  reproduced and list: a JSON record that repeats a key over several lines (`"name": "x"`, then
  `"name": "Cookie"`), where the check reads the first and JSON itself keeps the last.
- **The original bundle in `test-results/` still holds the home-folder address**; it stays on this
  computer, is ignored by Git and is emptied by the next run. Only the copy is handed in.
- **The failure is planted and happens every time;** the scenario's "fails once, passes on retry"
  isn't reproduced, and retries stay off so a flaky test is noticed.
- **The trace viewer was opened with Playwright's own Chromium:** the in-app browser couldn't start
  the viewer's background helper.
- **The zip reader** handles what Playwright writes (stored or compressed members, under 4 GB) and
  refuses what it can't read (other compression, encryption, a damaged or ambiguous directory, a
  wrong checksum) rather than skipping it; it doesn't check bytes that no record covers (a known
  gap above).
- **The commit under test** (the second stretch goal) is named in each log's header, but the quest's
  own files weren't committed yet when it was recorded.

## Sensitive values

No secret, token, real customer name or private ticket content is here. The demo app's API key was a
made-up value, new for the recording, and appears in no file (`logs/redaction-check.txt`). The
orders are made-up "Test User qa-…" names. The home-folder address was replaced with `~` in the
bundle and the logs, and the scan of both found nothing.
