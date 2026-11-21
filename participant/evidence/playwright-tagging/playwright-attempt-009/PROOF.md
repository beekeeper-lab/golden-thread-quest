# Proof · playwright-tagging

Attempt: `playwright-attempt-009`

Decisions, predictions and the answers below are Tom Carter's; the scheme, the tests, the check, the
log and these notes were drafted with Claude (Claude Code) from his answers, 11-12-2026. Everything
runs against the local Tixly demo app with made-up data; nothing is sent anywhere.

## What was built

- **The tag scheme** (`context/playwright/tag-scheme.md`, one page): five dimensions, each tag with
  its meaning. Feature: `@events`, `@order-review`, `@saved-orders`. Risk: `@risk-high`,
  `@risk-medium`, `@risk-low`, by what a buyer would lose if what the test checks broke. Read or
  write: `@writes-data` (any write, in the steps, the setup or the cleanup, or one that would happen
  if the app were broken) and `@read-only`. Layer: `@layer-ui`, `@layer-api`, `@layer-mixed`.
  Duration: `@fast` (at most 2 seconds) and `@slow` (at most 30). Plus an optional suite group, at
  most one per test, keeping the earlier quests' experiment tags (`@locator-comparison`,
  `@data-isolated`, `@data-coupled`, `@api-assisted`, `@ui-only`) so their README commands still
  work.
- **Eight new tests** (`tests/playwright/tagged.spec.ts`), chosen so every tag in the scheme is used
  at least once: the Tixly name on the events page (`@risk-low`), the events-page total for 3
  tickets, the review-page total for 4, a review link for an event not on sale, the orders service
  refusing a 7-ticket order (`@layer-api`, `@writes-data`), the orders service listing every saved
  order that isn't test data exactly as it is in the orders file (`@layer-api`, `@read-only`), an
  API-made order's total on "Your orders" (`@layer-mixed`), and cancelling on a slow connection
  (`@slow`: the test slows the orders service's answers in the browser to about 1.5 seconds each).
- **Every existing test re-tagged** to the scheme: all 19, so all 27 tests in the project follow it.
  The smoke test and the two cleanup proofs had no tags at all; every test gained a layer tag; the
  save and cancel tests went from `@risk-medium` to `@risk-high`; and `@ticket-total` became
  `@events`.
- **The check** (`tests/playwright/tools/tagging-check.ts`): reads the vocabulary and the duration
  limits from the scheme page itself, so the two can't disagree, and the tests and their tags from
  Playwright (`npx playwright test --list`), so every test counts, including those normally skipped.
  It reports by name and file a dimension with no tag or more than one, more than one suite tag, and
  any tag not in the scheme. Given a Playwright JSON report of a real run, it also names every test
  that took longer than its duration tag allows: each test's longest attempt (repeats and retries
  alike), matched by Playwright's own id for the test, and a PASS says how many tests were timed and
  how many were skipped or missing from the report. A report that isn't a Playwright run report
  stops the check. It ends with PASS or FAIL.
- **The README and setup check** describe the tags, the new tests and the check, and track the 2 new
  project files (36 instead of 34).

My decisions:

- **Every test in the project follows the scheme,** not only the eight new ones: a scheme only means
  something if the whole suite uses it.
- **Feature means the part of the app,** with the experiment tags kept as a separate, optional suite
  group, so nobody has to guess whether a "feature" tag is a feature or a technique.
- **Risk comes from my impact scale** from the risk-strategy quest: money wrong or an order lost,
  wrongly kept or the wrong buyer's is high; blocked or misled is medium; cosmetic is low.
- **Three layers,** classifying a test's own setup and checks: whether it works through the screen,
  the orders service or both. Cleanup behind the scenes doesn't count, and every run still uses the
  orders service (and its API key) in its run-wide setup and safety net, so a layer tag doesn't mean
  a test can run without it.
- **Read or write by what could change,** including setup, cleanup and a broken app: the 7-ticket
  test expects nothing to be saved, but a broken app would save it, so it is `@writes-data`.
- **Two duration levels, checked against a real run** rather than only written down.
- **The cleanup proofs are `@risk-low`:** they check the test helper's cleanup, not anything a buyer
  uses; the scheme's low-risk definition says so.

## How I chose the duration limits

`@fast` is at most 2 seconds because that leaves room for timing wobble: in the recorded run the
slowest `@fast` test took 0.78 seconds and most took 0.1 to 0.5, and a test's time shifts with the
tests running beside it. `@slow` is at most 30 seconds because that is Playwright's own limit for
one test. The one `@slow` test takes about 5 seconds (criterion 6).

## The tag I removed

`@ticket-total`, folded into `@events`, for three reasons (criteria 1 and 2). It named one test's
subject rather than a part of the app. Only one test used it, while the brittle and stable tests,
which check the same events-page total, carried `@locator-comparison`, so `--grep @ticket-total`
missed tests it sounds as if it would find. And "ticket total" could also mean the review page's
total, so two testers could disagree about which tests it covers.

## Reflection: which dimension was hardest to keep consistent?

Risk: deciding what a buyer would lose isn't obvious. Even with a written rule, two of the eight new
tests were first tagged wrong: a check of the prices shown was tagged low as if it were wording,
though a wrong price is money that is wrong, and a cancel was tagged medium, though a cancel that
fails keeps an order. The save and cancel tests had all been medium before the scheme, and the
cleanup proofs needed a judgment call. Another tester could reasonably land elsewhere, which is why
the scheme defines each level by what the buyer loses.

## Where the important artifacts are

All paths are under `participant/`.

| What | Path |
|---|---|
| The tag scheme | `context/playwright/tag-scheme.md` |
| The eight new tests | `tests/playwright/tagged.spec.ts` |
| The check | `tests/playwright/tools/tagging-check.ts` |
| The re-tagged tests | `tests/playwright/` (`tests/smoke.spec.ts`, `first-independent-test.spec.ts`, `model-usage.spec.ts`, `brittle.spec.ts`, `stable.spec.ts`, `coupled.spec.ts`, `isolated.spec.ts`, `cleanup-proof.spec.ts`, `api-assisted.spec.ts`, `ui-only.spec.ts`) |
| README, setup check | `tests/playwright/README.md`, `tests/playwright/tools/project-setup-check.ts` |
| The check's output | `evidence/playwright-tagging/playwright-attempt-009/logs/tag-check.txt` |

## How to reproduce the behavior

With the project set up as its README says (`npm ci --engine-strict`, then `npx playwright install
chromium`), from `participant/tests/playwright`, with a made-up key for the demo app's orders
service:

```
export TIXLY_API_KEY=$(openssl rand -hex 16)
PLAYWRIGHT_JSON_OUTPUT_FILE=/tmp/tixly-run.json npx playwright test --reporter=json
node tools/tagging-check.ts --results /tmp/tixly-run.json
```

The check ends with PASS. To see it reject tags, add a test with an unknown tag, a missing dimension
or two tags in one dimension (as in `logs/tag-check.txt`, part 2) and run `node
tools/tagging-check.ts`: it names each one and ends with FAIL.

## How the work meets the criteria

1. **The scheme defines each tag in all five dimensions:** `context/playwright/tag-scheme.md` has a
   table for each of feature, risk, read or write, layer and duration, with each tag's meaning; the
   check reads those tables (`logs/tag-check.txt`, part 1, its first line lists them).
2. **Every test carries one tag from each dimension:** `logs/tag-check.txt`, part 1: all 27 tests
   "ok" and "PASS: all 27 tests carry one tag from each dimension and only tags from the scheme",
   including the 4 normally skipped (they are listed, though not run).
3. **A tag outside the vocabulary is rejected by a check:** part 2, the planted `@smoke` test:
   "unknown tag @smoke (not in the scheme)" and FAIL. Two tags in one dimension are rejected too
   ("more than one risk tag").
4. **A test missing a dimension is reported by name:** part 2, `badly-tagged.spec.ts:5 "planted:
   missing its layer tag"` with "no layer tag".
5. **Write tests are distinguishable from read-only tests by tag:** every test carries
   `@writes-data` or `@read-only` (part 1), so `--grep-invert @writes-data` leaves out every test
   that changes saved data.
6. **Duration tags have stated limits:** the scheme's duration table gives 2 seconds for `@fast` and
   30 for `@slow`, and the check enforces them against a real run: in part 1 all 23 timed tests were
   within their limits (the 4 skipped tests weren't timed); in part 3 a planted `@fast` test that
   took 2.59 seconds was reported as over the 2 second limit, and the check failed.
7. **The vocabulary fits on one page:** the scheme is 55 lines.

## What was tested or validated

- **The tag check** (`logs/tag-check.txt`, 11-12-2026, 12:49 PM): parts 1 to 3 as described under
  the criteria; the whole suite showed 23 passed and 4 skipped, and the real orders file was byte
  for byte the committed one afterwards.
- **The eight new tests** pass; the `@slow` one takes about 5 seconds, the others well under 1.
- **A trap found on the way:** a planted test whose title contained "@smoke," got an extra tag
  "smoke," because Playwright counts any `@word` in a title as a tag. The check caught it, and the
  scheme and README now say not to use `@` in titles.
- **The setup check passes** with 36 project files and no credential found.
- **My predictions:** right that the check would find no problems in the real project, that it would
  report all three planted tests by name and fail, and that none of the existing tests is slow; and
  test 5 is `@writes-data`, as I reasoned, because a broken app would save. Wrong that the UI-only
  test is the slowest of the existing tests: in the recorded run the slowest existing test was
  "cancelling one buyer's order leaves another buyer's order in Your orders (isolated)" (0.78
  seconds) while the UI-only test took 0.42, because timings shift with the tests running beside
  each one.
- **Reviews:** my own review before the AI review made the check refuse a scheme that lists a tag
  twice or a duration tag without a limit. Then an AI code review (Copilot) on a practice pull
  request, 4 rounds, every finding reproduced before it was fixed and the log recorded again after
  each code change; the 4th round reported no open issues. It found real problems: a test meant to
  be refused could, against a broken app, cancel one of the real orders (now it hands any order it
  saved to the helper by its own name, and the helper never touches an order from before the run);
  the listing test compared the listing with a list from the same service, so a listing that lost
  everything still passed, and later it accepted duplicates; and the check could be fooled by a tag
  mentioned in the scheme's prose or examples, a retry that hid a slow attempt, two tests with the
  same title, an empty or malformed report, a mistyped option, or a report location left in the
  shell (which made it overwrite the report). One suggestion I didn't take: raising the listing test
  to `@risk-high`, because by the scheme a wrong listing misleads the buyer but loses no order.
- **This quest has no automatic checker.** The criteria above were checked against the files and the
  log.

## Stretch goals

- **Generate the scheme document from the check:** done the other way round. The check reads the
  scheme page (its tags and its duration limits), so there is one source and the two can't disagree;
  the page isn't generated.
- **Add a tag for the requirement a test covers:** not attempted.

## Remaining limitations

- **Risk is still a judgment.** The levels are defined by what a buyer would lose, but two testers
  can still disagree about a test (see the reflection); the check can only make sure a test has
  exactly one risk tag, not that it is the right one.
- **Durations come from one computer** and shift with the tests running at the same time. A `@slow`
  test that runs quickly isn't flagged; only a test over its limit is.
- **The suite group is optional and small,** and only stays useful while the earlier quests' README
  commands use it.
- **Earlier quests' evidence keeps its old tags.** Their handed-in logs and notes still show the
  tags they were recorded with (such as `@ticket-total`); they describe what was true then and were
  left as they are.
- **Files from earlier quests changed again:** the tags in `tests/smoke.spec.ts`,
  `first-independent-test.spec.ts`, `model-usage.spec.ts`, `brittle.spec.ts`, `stable.spec.ts`,
  `coupled.spec.ts`, `isolated.spec.ts`, `cleanup-proof.spec.ts`, `api-assisted.spec.ts` and
  `ui-only.spec.ts` (and the layout of the smoke test and the cleanup proofs, which had no tags),
  `README.md` and `tools/project-setup-check.ts`. The default run still passes (23 passed, 4
  skipped: the coupled pair and the cleanup proofs, which only run when asked; the proofs fail on
  purpose).
- **One test reads the orders file directly:** the listing test compares the orders service with
  this project's own orders file, so it is skipped when the tests are pointed at another copy of the
  app (`TIXLY_BASE_URL`, which the run-order tool also uses).
- **The check reads a simple form of Markdown:** tag definitions are table rows under the six known
  headings, and fenced examples are skipped. Unusual Markdown it wasn't written for could still be
  misread; the last review round named no such case, but advised a person to keep an eye on it.
- **One browser (Chromium).**

## Sensitive values

No password, token, customer name or private ticket content is here. The only credential is the demo
app's API key: made up, new for the recording, set in the environment and never written down; the
log shows it in none of its command outputs, and the credential scan of the log found 0. Every name
in the demo app and the log is made up, and the log shows personal home-folder paths as `~`.
