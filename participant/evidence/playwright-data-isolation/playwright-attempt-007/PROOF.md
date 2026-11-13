# Proof · playwright-data-isolation

Attempt: `playwright-attempt-007`

Decisions, predictions and the answers below are Tom Carter's; the demo app's saved orders, the
tests, the helper, the tools, the logs and these notes were drafted with Claude (Claude Code) from
his answers, 11-10-2026 to 11-11-2026. Everything runs against the local Tixly demo app with made-up
data; nothing is sent anywhere.

## What was built

Saved orders for the demo app, a deliberately coupled pair of tests, the same stories rewritten so
each test owns its data, and the tools that prove the difference.

- **Saved orders in the demo app.** The order review page now has a "Your name" box and a "Save
  order" button; a new "Your orders" page (`demo-app/orders.html`) lists saved orders, each with a
  "Cancel order for <name>" button. Behind them, the demo server has a small orders service (list,
  save, cancel) that keeps orders in `demo-app/data/orders.json`, a stand-in for a real database:
  what is saved stays saved between runs until it is cancelled. The file starts with three made-up
  "real" orders (Maria Lopez, James Chen, Aisha Patel). Each saved order gets a random id never
  already in use; the file is never left half-written, and if it can't be read (damaged, or not a
  list of orders) the service says so and never writes over it. The service refuses a blank name, an
  event not on sale, a quantity outside 1 to 6, a save that isn't JSON, and any save or cancel sent
  by another website; it only answers requests addressed to this computer (127.0.0.1 or localhost).
  The pages save and cancel one at a time (a double-click can't save twice or cancel the next order
  as it moves up under the pointer, and holding Enter down can't cancel one order after another) and
  say what went wrong instead of going blank. A lock lets only one demo app use the orders file at a
  time.
- **The coupled pair** (`coupled.spec.ts`): test 1 saves an order for "Test User" through the screen
  and checks it is listed; test 2 cancels "Test User's" order without making one, relying on test 1.
  Forward, both pass and nothing is left. Reversed, test 2 fails and test 1's order is left behind.
- **The isolated tests** (`isolated.spec.ts`), the same stories plus one more, each making its own
  data:
  1. A buyer saves an order (through the screen) and sees it in Your orders. On the way it checks
     that a save the service turns down (a name of only spaces) can be corrected and tried again,
     and that a double-click on Save while the save is on its way saves only once.
  2. A buyer cancels their own order: it makes the order first, through the orders service, then
     cancels it through the screen and checks the orders service no longer has it (not just hidden
     from the page).
  3. Cancelling one buyer's order leaves another buyer's order in Your orders: it makes two orders,
     cancels one, clicks the same spot again straight away (as a quick double-click would; the
     page's clock is held still so "straight away" holds on any machine), checks the cancelled one
     is gone from the orders service and the other is still listed and still saved, clicks the same
     spot once more a moment later without moving the pointer (a slower double-click; still not
     cancelled), then moves the pointer away, aims at the other order and cancels it, to show Cancel
     works again.
- **The orders helper** (`support/`): `global-setup.ts` picks a run marker once per run and notes
  the id of every order that already exists; `orders-fixture.ts` gives each test unique names, notes
  every order the test creates and cancels exactly those when the test ends, pass or fail (it only
  accepts a name it gave out itself, and never notes an order that existed before the run);
  `global-teardown.ts` is the run-end safety net, cancelling any order with exactly the name format
  the helper makes, carrying that run's marker, that didn't exist before the run, and failing the
  run if a cancellation fails. The project settings (`playwright.config.ts`) run the setup before
  and the safety net after every run.
- **The run-order tool** (`tools/run-in-order.ts`): Playwright always runs a file's tests top to
  bottom, so this lists the tests, puts them in forward, reversed or random order, and runs them one
  at a time in that order. The whole ordered run behaves like one normal run: one copy of the app,
  one run marker, and the safety net once at the end, even after an error or Ctrl+C. It stops rather
  than borrow an app it didn't start, and keeps each test's failure screenshot and trace in its own
  folder. A test counts as passed only if Playwright recorded it as passed and its run finished
  cleanly; a skipped test is shown as SKIPPED, not counted as a pass. For a random order it prints
  the seed; `--seed` repeats that exact order.
- **The cleanup proofs** (`cleanup-proof.spec.ts`): two tests that fail on purpose after saving an
  order, to show cleanup still happens. They are skipped in normal runs.
- **The check** (`tools/data-isolation-check.ts`): `before` fingerprints every order there now;
  `after` reports any leftover test data (an order that wasn't there before, a second copy of an
  order, or a name with a run marker) and whether each order from before is still there with the
  same content (compared by a fingerprint of each order), then ends with PASS or FAIL. It reads the
  orders file directly, so it works whether or not the app is running. `--orders-file <path>` checks
  another orders file, such as a scratch copy of the app's.
- **The README and setup check** describe the new tests and tools and check the 10 new project files
  (31 instead of 21), and `.gitignore` covers the orders service's temporary and lock files.

My decisions:

- **Saved orders, kept in a file,** so a leaked order really stays and the check proves something;
  in memory only, every run would start clean and "no leftovers" would be true automatically.
- **The coupled pair: one test sets up the other,** the classic "this test assumes that one already
  ran".
- **Names: a run marker plus a random code per test.**
- **Cleanup that always runs, plus a safety net, plus a proof** with a test that fails on purpose.
- **Three ordinary "real" orders** to prove the tests never touch existing data. I decided against a
  "trap" order, a real customer named "Test User": it would make the point that a coupled test can
  damage real data, but only by actually damaging it in the evidence.
- **The screens for what a test is about; the orders service for setup and cleanup,** so cleanup
  still works when a screen is broken.
- **A run-order tool** rather than reordering the test file by hand, so random orders are real and
  repeatable.
- **A third isolated test,** so a random order has six possibilities, not two.
- **The coupled pair and the cleanup proofs are skipped in normal runs** (`TIXLY_COUPLED=1` and
  `TIXLY_CLEANUP_PROOF=1` turn them on), because the coupled pair can leave a real order behind and
  the proofs fail on purpose. The normal suite shows 13 passed and 4 skipped.
- **Five random orders recorded,** not one, so a single random run that happens to repeat forward or
  reversed can't stand in for "random", and five give a better spread of the orders forward and
  reversed don't cover.

## How names are made unique

Every order an isolated test creates is named like `Test User qa-1a2b3c4d-5e6f7a8b`:

- `qa-1a2b3c4d` is the **run marker**, picked once per run (`support/global-setup.ts`) and shared by
  every test in it, in every browser. It is what lets the safety net and the check find all of one
  run's data, and only that run's.
- `5e6f7a8b` is a **random code for that order**, new each time, so two tests in the same run, even
  running at the same moment, are very unlikely to share a name.

Each part has about 4 billion possible values, so a clash (two runs with the same marker, or two
orders with the same name) is very unlikely, though not impossible: nothing reserves them. In the
logs, each one-at-a-time run records its own marker (the parallel runs don't print theirs), and 15
test runs, up to 4 at a time in separate browsers, all passed.

## How cleanup behaves when a test fails halfway

There are two layers, and both are shown working on failing tests in `logs/cleanup-check.txt` (part
1, step 1b):

- **After every test, pass or fail,** the helper cancels exactly the orders the test noted. Proof 1
  creates its order, notes it, then fails on purpose: the run reports the failure, and its order is
  gone afterwards.
- **At the end of the run,** the safety net cancels any order whose name is exactly the helper's
  format with the run's marker, for an order the test never got to note (a crash at the worst
  moment). Proof 2 saves its order through the screen, then fails before noting it: the safety net
  reports "cancelled 1 order(s) left with run marker qa-9c1f0265". The 1 is proof 2's order alone;
  proof 1's had already been cancelled by its own cleanup.

The safety net never touches an order that existed before the run, even one whose name happened to
contain the marker, and a cancellation that fails fails the run, so a cleanup problem is never
silent. The failure is never hidden either: both proofs are reported as failed. The check that
follows reports PASS: nothing left, and the three real orders unchanged.

## Reflection: what data could a test still leak that my cleanup doesn't know about?

Screenshots and traces. When a test fails, Playwright saves a screenshot and a trace of the page,
and they show the test buyer's name; our cleanup only removes orders, not those files. The same goes
for anything else the run writes down: our own logs print the test names too. In a real app the list
would be longer: emails or messages sent for an order, server logs, analytics, or other systems the
order was passed to. Cleanup can only remove what it knows about, so test data should be harmless
(made-up names, no real details), and those other places need their own cleanup or a short retention
period.

## What surprised me

The wrong-order failure. Forwards, the coupled pair looked perfectly healthy: both passed and
nothing was left behind. Just reversing the order made the second test fail, and the failure showed
up in the test that cancels, even though the real cause was the missing order from the other test.
It also left a "Test User" order in the file for the next run to trip over. A suite that only ever
runs in one order can hide this for a long time.

## Where the important artifacts are

All paths are under `participant/`.

| What | Path |
|---|---|
| The coupled pair | `tests/playwright/coupled.spec.ts` |
| The isolated tests | `tests/playwright/isolated.spec.ts` |
| The cleanup proofs | `tests/playwright/cleanup-proof.spec.ts` |
| The orders helper | `tests/playwright/support/` (`orders-fixture.ts`, `global-setup.ts`, `global-teardown.ts`) |
| The check | `tests/playwright/tools/data-isolation-check.ts` |
| The run-order tool | `tests/playwright/tools/run-in-order.ts` |
| Saved orders: service, pages, file | `tests/playwright/demo-app/server.js`, `orders.html`, `review.html`, `data/orders.json` |
| Settings, README, setup check | `tests/playwright/playwright.config.ts`, `README.md`, `tools/project-setup-check.ts`, `.gitignore` |
| The shuffle run | `evidence/playwright-data-isolation/playwright-attempt-007/logs/shuffle-run.txt` |
| The cleanup check | `evidence/playwright-data-isolation/playwright-attempt-007/logs/cleanup-check.txt` |

## How to reproduce the behavior

With the project set up as its README says (`npm ci --engine-strict`, then `npx playwright install
chromium`), from `participant/tests/playwright`:

```
node tools/data-isolation-check.ts before
node tools/run-in-order.ts forward isolated.spec.ts
node tools/run-in-order.ts reversed isolated.spec.ts
node tools/run-in-order.ts random isolated.spec.ts
npx playwright test isolated.spec.ts --fully-parallel --workers=4 --repeat-each=5
TIXLY_CLEANUP_PROOF=1 npx playwright test cleanup-proof.spec.ts --workers=1
node tools/data-isolation-check.ts after
```

Every isolated run passes, the proofs fail on purpose, and the check reports PASS.

To run the isolated tests against an app with no saved orders, copy `demo-app/` to a scratch folder
(`<scratch>` below), put `[]` in its `data/orders.json`, start it with `TIXLY_DEMO_PORT=4184 node
<scratch>/demo-app/server.js`, add `TIXLY_BASE_URL=http://127.0.0.1:4184` in front of the test
commands above, and give both check commands `--orders-file <scratch>/demo-app/data/orders.json`, so
they check that copy's file, not this project's.

To see the coupled pair fail and the check catch its leftover:

```
node tools/data-isolation-check.ts before
TIXLY_COUPLED=1 node tools/run-in-order.ts reversed coupled.spec.ts
node tools/data-isolation-check.ts after
```

The second test fails and the check reports FAIL with the "Test User" order listed; cancel it with
its "Cancel order for Test User" button on the "Your orders" page (`/orders`, with the app started
by `node demo-app/server.js`), and the check reports PASS again.

## How the work meets the criteria

1. **Each test creates the data it needs:** in `isolated.spec.ts`, test 1 saves its own order
   through the screen, test 2 makes the order it cancels, and test 3 makes both orders it uses. None
   reads another test's data or relies on orders already being there: `logs/shuffle-run.txt` also
   runs them, forward, reversed and in parallel, against a copy of the app with no saved orders at
   all, and all pass. (In `coupled.spec.ts`, test 2 makes nothing and relies on test 1: the
   opposite, on purpose.)
2. **Created data has a name that cannot collide with another run:** every order is named with the
   run marker and a random code for that order, about 4 billion possible values each, so a clash is
   very unlikely, though not impossible (see "How names are made unique"); this is met as "very
   unlikely", not guaranteed. Each one-at-a-time run in `logs/shuffle-run.txt` records a different
   marker, which shows the runs were kept apart, not that a clash can't happen.
3. **A test removes only the data it created:** the helper cancels only the ids the test noted, and
   the safety net only orders with that run's marker. Test 3 checks that cancelling one of its
   orders leaves the other, and every check in `logs/cleanup-check.txt` shows the three real orders
   unchanged.
4. **The tests pass in forward, reversed and random order:** `logs/shuffle-run.txt`, 3 of 3 passed
   forward, reversed and in five random orders (seeds 439086005, 413483436, 600201429, 931542100 and
   188421223). Of the random orders, 5 were new (neither forward nor reversed), 2 different orders
   among them.
5. **The tests pass in parallel:** `logs/shuffle-run.txt`, each isolated test 5 times, up to 4 at a
   time in separate browsers (4 workers): 15 runs, all passed.
6. **The coupled version fails under reordering:** `logs/shuffle-run.txt`, the coupled pair passes
   forward (2 of 2) and fails reversed (1 passed, 1 failed: the cancel test waits for a "Cancel
   order for Test User" button that isn't there).
7. **No data present before the run is altered or removed:** `logs/cleanup-check.txt`, every "after"
   check lists the three real orders as unchanged (each compared by fingerprint), and the recording
   script's own comparison shows the orders file ends byte for byte as it began.

## What was tested or validated

- **The shuffle run** (`logs/shuffle-run.txt`, 11-11-2026, 5:10 PM to 5:12 PM): as described under
  criteria 1 and 4 to 6, including the runs against a copy of the app with no saved orders, whose
  orders file was empty again afterwards.
- **The cleanup check** (`logs/cleanup-check.txt`, 11-11-2026, 5:10 PM to 5:12 PM): part 1, around
  the isolated runs and the cleanup proofs, reports PASS; part 2, around the coupled pair, reports
  FAIL with the leaked "Test User" order, which is then cancelled by its id, after which the check
  reports PASS and the orders file is byte for byte what it was.
- **The check itself was checked:** besides catching the coupled pair's leak, it was run before it
  was recorded, and that run exposed a mistake of mine: it first kept its fingerprint in
  `test-results/`, which Playwright empties at the start of every run, so the "after" step had
  nothing to compare. It now keeps it in the computer's temporary folder.
- **The orders service** was tried by hand before any test used it: listing, saving, refusing a
  blank name, an event not on sale, 9 tickets and malformed input, cancelling, and cancelling again
  (not found).
- **The earlier tests still pass:** the whole normal suite shows 13 passed and 4 skipped (the
  coupled pair and the proofs), and the project-setup check passes (`logs/cleanup-check.txt`, part
  3).
- **My predictions before each run** were all right, including that reversing the coupled pair would
  fail the cancel test and leave "Test User" behind, and that a test failing halfway would still be
  reported as failed while its order was removed.
- **My own review before Copilot** found two bugs in the saved orders, both reproduced and fixed: a
  double-click on "Save order" saved the order twice (the button is now disabled while saving, and
  comes back if the save fails), and a damaged orders file crashed the whole demo app, pages
  included (the orders service now answers "The saved orders file can't be read", the pages keep
  working and the file is left as it is).
- **Reviews after mine:** an AI code review (Copilot) on a practice pull request, 20 rounds, every
  finding reproduced before it was fixed and both logs recorded again after each round; the 20th
  round reported no open issues. An independent review in between found nothing High or Medium, and
  its small items were fixed except one noted as theoretical (an order id being reused). Between
  them, these reviews found real problems a buyer or tester would hit, among them: a quick
  double-click on Cancel cancelled the next order as it moved up under the pointer (10 times out of
  10), and later a slower double-click did too; holding Enter down cancelled every order on the
  page; a name made only of invisible characters was accepted; the safety net swept an unrelated
  order whose name merely contained the marker; two runs given the same marker could sweep each
  other's orders; and the helper could be told to note, and so cancel, one of the real orders. Three
  were rated High: one about the orders file's lock, one about the shared marker and one about the
  helper. After the last round I also tried by hand what the logs don't show: stopping the run-order
  tool partway with Ctrl+C or a stop signal (it finishes the running test, cleans up, stops its app
  and doesn't count the run as a pass), cancelling on a touch screen, and holding Enter (one order
  cancelled each time).
- **This quest has no automatic checker.** The criteria above were checked against the files and the
  two logs.

## Stretch goals

- **Add a check that reports leftover data:** done, `tools/data-isolation-check.ts`.
- **Run the suite twice in parallel against the same environment:** not attempted. The parallel run
  above is one run with up to four browsers at a time; two separate runs at the same moment would
  need one shared copy of the app started by hand, since each run otherwise starts its own on the
  same port.

## Remaining limitations

- **The orders file is a simple stand-in for a database.** It works because each request reads,
  changes and writes the whole file in one uninterrupted step; two servers writing the same file
  could lose each other's changes, so the server takes a lock on the file and a second one refuses
  to start. A lock left by a server that was killed outright is never taken over automatically (that
  can't be made safe when two servers start at once); the server says to delete it by hand.
- **A hard kill skips the safety net.** Ctrl+C, a closed terminal or unreadable output still lead to
  the cleanup, but killing the run outright (or a power cut) does not; an order left that way
  carries a marker no later run sweeps, so only the check (or the "Your orders" page) shows it.
- **Screenshots, traces and logs keep test names** after the orders are gone (see the reflection).
  The test names are made up and hold no real details.
- **The orders file is in Git, so a leaked order shows up as a change to it** until it is cancelled;
  the coupled pair is skipped in normal runs for that reason.
- **Random orders are limited with three tests:** there are only six possible orders; the five
  recorded random runs produced 2 of the four that forward and reversed don't cover. A seed can be
  given to repeat any order.
- **Prices are still written in more than one place:** the events, review and orders pages each keep
  the Spring Concert's price and fee.
- **Touch screens: one extra tap after a cancellation.** To stop a slow double-click from cancelling
  the next order as it moves up under the pointer, a click on the same spot as the last cancellation
  counts only after the pointer has moved away. A mouse just moves; on a touch screen the buyer has
  to tap somewhere else first before tapping that spot again. Keyboard and screen-reader users
  aren't affected.
- **One browser (Chromium).**
- **Files from earlier quests changed again:** `demo-app/server.js` (the orders service),
  `demo-app/review.html` (saving an order, and a link to Your orders), `playwright.config.ts` (the
  setup and safety net), `README.md`, `tools/project-setup-check.ts` and `.gitignore`. The quest app
  notes the README, configuration and setup check as changed since the project-setup quest was
  approved; these are the changes. All earlier tests still pass.

## Sensitive values

No password, token, customer name or private ticket content is here. The tests use no credential,
and every name in the demo app and the logs is made up. The logs show personal home-folder paths as
`~`. Every file in this evidence was scanned with the quest app's credential patterns: 0 findings.
