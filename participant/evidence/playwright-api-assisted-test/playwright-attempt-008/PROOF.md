# Proof · playwright-api-assisted-test

Attempt: `playwright-attempt-008`

Decisions, predictions and the answers below are Tom Carter's; the tests, the tool, the demo app's
API key and delay, the log and these notes were drafted with Claude (Claude Code) from his answers,
11-12-2026. Everything runs against the local Tixly demo app with made-up data; nothing is sent
anywhere.

## What was built

The same buyer story, "a buyer cancels an order on Your orders", tested two ways, with the evidence
of what each one can and can't see.

- **The API-assisted test** (`tests/playwright/api-assisted.spec.ts`):
  1. Arrange, through the orders service (the API): one order of its own, with a unique name.
  2. Act, through the screen: on "Your orders", click "Cancel order for <name>", see "Order for
     <name> cancelled." and see the order gone from the list.
  3. Assert, through the API: the order is gone from the orders service, and every order that
     existed before the run is still there, unchanged (checked once before the test saves anything,
     and again at the end).
- **The UI-only test** (`tests/playwright/ui-only.spec.ts`): the buyer's whole walk through the
  screen (events page, 2 Spring Concert tickets, review page, a unique name, Save order, See your
  orders, Cancel), checked only by what the screen shows: the "cancelled" message, and the row gone.
  Behind the scenes, the orders helper notes the saved order so it is cleaned up even if the test
  fails partway; that is housekeeping, not part of what is tested.
- **A made-up API key for the orders service.** The demo app's orders service now answers its own
  pages, and anything else (the tests, the tools, a script) only with a key from the environment
  (`TIXLY_API_KEY`), sent in a request header. A missing or wrong key gets a 401 that never repeats
  the key. The tests send it only from Node (`support/global-setup.ts`), never from the browser, so
  it can't reach a page, a screenshot or a trace; the helper from the data-isolation quest, its
  safety net and its run-order tool now use it too.
- **The broken copy** (`tests/playwright/tools/break-cancel.ts`): copies the demo app to a folder
  and changes three lines in the copy's "Your orders" page, so Cancel only pretends: it says
  "cancelled" and hides the row, but nothing is cancelled. It prints each change.
- **An optional simulated network** (`TIXLY_DEMO_DELAY_MS`, off unless set): the demo app waits that
  many milliseconds before every answer, for timing the two tests.
- **The boundary note** (`context/playwright/api-boundary.md`): what the API-assisted test trusts
  the API for, and what it refuses to trust it for.
- **The README and setup check** describe the key, the two tests, the broken copy and the delay, and
  check the 3 new project files (34 instead of 31).

My decisions:

- **The behavior: a buyer cancels an order on "Your orders",** the quest's scenario almost word for
  word: in the UI-only version, a long walk through other screens just to reach the one step that
  matters.
- **The credential: a made-up API key for the tests' own calls,** read from the environment, so the
  app's own pages keep working without it and it never reaches the browser.
- **The break: Cancel only pretends.** The screen looks right and only a check through the API can
  tell, which is what the API check is for.
- **The UI-only version: the full buyer walk, checked only on screen,** and also run against the
  broken copy, to show what it can't see.
- **Timing: 5 runs of each, taking turns, compared by the median.**
- **When the timing came out close:** report it honestly on this computer, add a labelled simulated
  network as a second measurement, and tidy the API-assisted test (one listing of the orders after
  the cancel serves both of its checks), rather than pick a simulation that makes the numbers pass.

## The bug the API-assisted approach could miss

If the review page stopped saving orders, or saved them with the wrong number of tickets, the
API-assisted test would still pass: it creates its order through the API and never visits that page
(criteria 1 and 2: setup through the API, only the cancel on the screen). The UI-only version walks
through that page, so it would catch a save that stopped working, but it doesn't check the number of
tickets; the data-isolation quest's save test checks the saved order's tickets and total, so it
would catch that.

## Reflection: where does the shortcut stop being a faithful test of the user's experience?

It skips the events and review pages a real buyer walks through. Two smaller gaps follow from that:
the test opens "Your orders" by its address, while a real buyer gets there by following "See your
orders" after saving, so a broken link wouldn't be noticed; and its order was made by the API, not
typed in by a buyer, so anything the save form does (such as limiting the name to 60 characters)
never applies to it.

## What surprised me

The UI-only test passing against the broken page. Cancel there did nothing at all, but the screen
said "cancelled" and the row went away, so a test that only trusts the screen had nothing to fail
on. Only the check through the API showed the order was still saved.

## Where the important artifacts are

All paths are under `participant/`.

| What | Path |
|---|---|
| The API-assisted test | `tests/playwright/api-assisted.spec.ts` |
| The UI-only test | `tests/playwright/ui-only.spec.ts` |
| The broken copy maker | `tests/playwright/tools/break-cancel.ts` |
| The boundary note | `context/playwright/api-boundary.md` |
| The API key and the delay (demo app) | `tests/playwright/demo-app/server.js` |
| The key, sent from Node | `tests/playwright/support/global-setup.ts` (`ask`), used by `support/orders-fixture.ts` and `support/global-teardown.ts` |
| README, setup check | `tests/playwright/README.md`, `tests/playwright/tools/project-setup-check.ts` |
| The timing run | `evidence/playwright-api-assisted-test/playwright-attempt-008/logs/timing-run.txt` |

## How to reproduce the behavior

With the project set up as its README says (`npm ci --engine-strict`, then `npx playwright install
chromium`), from `participant/tests/playwright`, with a made-up key in the terminal:

```
export TIXLY_API_KEY=$(openssl rand -hex 16)
npx playwright test api-assisted.spec.ts --workers=1
npx playwright test ui-only.spec.ts --workers=1
TIXLY_DEMO_DELAY_MS=300 npx playwright test api-assisted.spec.ts ui-only.spec.ts --workers=1
```

To break Cancel and see which test notices:

```
node tools/break-cancel.ts /tmp/tixly-broken
TIXLY_DEMO_PORT=4191 node /tmp/tixly-broken/server.js
```

then, in a second terminal with the same `TIXLY_API_KEY`, `TIXLY_BASE_URL=http://127.0.0.1:4191 npx
playwright test api-assisted.spec.ts ui-only.spec.ts`: the API-assisted test fails at its API check,
and the UI-only test passes.

## How the work meets the criteria

1. **Setup is performed through the API and creates only the data the test needs:**
   `api-assisted.spec.ts` creates one order through the orders service, with a unique name, and
   nothing else; the orders helper cancels it when the test ends. `logs/timing-run.txt`, part 4:
   after the whole suite, the orders file is byte for byte the committed one.
2. **The behavior under test is performed through the UI:** the cancel is a click on "Cancel order
   for <name>" on the "Your orders" page; the API never cancels anything in this test.
3. **The outcome is verified through the API, not only by what the UI shows:** after the click the
   test asks the orders service until the order is gone, and compares the orders from before the run
   with what the service lists now. `logs/timing-run.txt`, part 3: against a page that only pretends
   to cancel, it is this check that fails ("the cancelled order is gone from the orders service",
   expected false, received true).
4. **The API-assisted test takes less than half the time of the UI-only version:**
   `logs/timing-run.txt`, part 1, on this computer, 5 runs of each taking turns: medians 210 ms and
   420 ms, 50%, not under half. Part 2, with a simulated network delaying every answer by 300 ms:
   3,142 ms and 4,296 ms, 73%, not under half. So on these numbers the API-assisted test is not
   under half. Why the gap is small: most of its time is the part both versions share (loading "Your
   orders", clicking Cancel and waiting for the page to show the result, which includes the row
   disappearing from the list), while the walk the API lets it skip is only two small pages on an
   app running on this computer; and it adds requests of its own (a listing before, the creation, a
   listing after and a cleanup). With the simulated network every answer costs the same 300 ms, page
   or API alike, so those added requests use up most of what skipping the pages saves. On a real
   site, where a page (styles, scripts, images and its own data requests) usually costs more than an
   API call, the saving would grow with each slow page the API lets a test skip; that depends on the
   site (a cached page or a slow API call could reverse it) and isn't measured here. The simulated
   runs of the UI-only test also vary more (3,808 to 4,330 ms), because its screen checks retry
   until each slow answer arrives.
5. **Breaking the UI behavior makes the API-assisted test fail:** `logs/timing-run.txt`, part 3, the
   broken copy's three changed lines, then the API-assisted test failing at its API check while the
   screen check before it passed; the UI-only test passes against the same broken copy.
6. **Credentials come from the environment and appear in no output:** the key is set in the
   environment (`TIXLY_API_KEY`), a new made-up random value for the recording, and never printed.
   `logs/timing-run.txt`, part 5: its actual value was found in none of the 25 files left by the
   failed run (its trace, searched file by file inside, and 2 screenshots), none of the 50 files
   after a run recorded with tracing on (2 traces), none of the 28 command outputs (including the
   broken copy's server), and not in the log; the repository's credential scan of the log found 0. A
   file search can't read text drawn into a screenshot, so the screenshots rest on a stronger fact:
   the key never reaches the browser (it is sent only from Node), so no page can show it. I also
   looked at a failure screenshot from the broken copy: it shows "Your orders" with the three real
   orders and the "cancelled" message, and nothing like a key.
7. **The note says what the API is not trusted for:** `context/playwright/api-boundary.md`, "What
   the test refuses to trust the API for": the behavior under test, what the buyer sees, that an
   order made through the API is just like a buyer's, and anything about the other pages.

## What was tested or validated

- **The timing run** (`logs/timing-run.txt`, 11-12-2026, 10:35 AM to 10:36 AM): as described under
  criteria 1 and 3 to 6.
- **The key itself** was tried before any test used it, on a scratch copy of the app: listing the
  orders with no key and with a wrong key gave 401, with the right key the 3 orders, and the "Your
  orders" page worked in a browser with no key at all; the server's own output never contained the
  key.
- **The earlier tests still pass with the key:** the whole suite shows 15 passed and 4 skipped
  (`logs/timing-run.txt`, part 4); without a key, the run stops before any test with "TIXLY_API_KEY
  isn't set" and how to set one, and the safety net refuses to sweep.
- **A mistake the key exposed:** the data-isolation quest's test 3 showed the page only its own two
  orders by re-sending the page's request itself; re-sent by Playwright, the request no longer
  counted as the page's own, so the orders service refused it. Test 3 now gets the list through the
  helper (from Node, with the key) and hands that to the page.
- **The setup check passes** with 34 project files; on the way, the repository's credential scanner
  took the line that reads the key from the environment for a secret written into the code, so the
  variable was renamed. The setup check's credential scan finds 0.
- **My predictions:** right for the four key checks, the run without a key (with one surprise: no
  test ran at all, because the run's setup was refused first), both tests against the broken copy,
  and the screen looking fine while the API check failed. Wrong on time: I guessed 2 and 6 seconds,
  then 3; the tests took about 0.2 and 0.4 seconds. I expected the simulated network to make the
  API-assisted test come in under half; it made the gap smaller. For the recorded timing I said
  "about half, not under"; it came out at 50%.
- **Reviews:** my own review before the AI review found one gap (the README's broken-copy example
  would fail on a second try, since the tool refuses a folder that isn't empty). Then an AI code
  review (Copilot) on a practice pull request, 5 rounds, every finding reproduced before it was
  fixed and the log recorded again after each code change; the 5th round reported no open issues. It
  found real problems: a key containing a line break made the header code fail with the key in its
  error message, which reached the test output; a save that wiped every other order, and a page that
  never refreshed after cancelling, both still passed the API-assisted test; a dropped save was
  retried and saved twice; a key with spaces around it could never match; the broken-copy tool
  failed in a folder whose name has a space; the simulated delay accepted values that made a working
  app fail the tests' time limits; and two claims in this PROOF went further than the evidence (the
  real-site saving, and screenshots). The timings also moved between recordings (on this computer,
  the API-assisted median came out between 44% and 52% of the UI-only one), which is why criterion 4
  is written from each recording's own numbers.
- **This quest has no automatic checker.** The criteria above were checked against the files and the
  log.

## Stretch goals

- **Fail the test if setup through the API takes longer than a limit:** not attempted.
- **Verify the same outcome through a second path:** partly. The cancel is confirmed through the
  orders service and through the screen's own message, but there is no second, independent API or
  data path; the orders service is the only one the demo app has.

## Remaining limitations

- **The pages' own way in has no key.** The orders service lets in requests the browser marks as
  coming from the same site, so the key never has to reach the browser. A script on this computer
  could send that mark itself: the demo app has no buyer login, so that way in is open by design.
  The key guards the way tests, tools and scripts use.
- **The simulated network is uniform:** every answer waits the same time, pages and API alike, which
  is not how a real site behaves (criterion 4). The timings come from one computer.
- **The UI-only version still uses the API behind the scenes** to note its order for cleanup; it is
  housekeeping, but the test is not completely free of the API.
- **One browser (Chromium).**
- **Files from earlier quests changed again:** `demo-app/server.js` (the key and the delay),
  `support/global-setup.ts`, `support/orders-fixture.ts` and `support/global-teardown.ts` (sending
  the key from Node), `isolated.spec.ts` (test 3's list, as described above), `README.md` and
  `tools/project-setup-check.ts`. The quest app may note some of them as changed since their quest
  was approved; these are the changes. All earlier tests still pass.

## Sensitive values

No password, token, customer name or private ticket content is here. The only credential is the
orders service's API key: made up, new for each recording, set in the environment and never written
down; the checks above found it in no output, trace or log, and it never reaches the browser, so no
screenshot can show it. Every name in the demo app and the log is made up, and the log shows
personal home-folder paths as `~`.
