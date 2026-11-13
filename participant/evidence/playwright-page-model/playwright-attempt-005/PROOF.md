# Proof · playwright-page-model

Attempt: `playwright-attempt-005`

Decisions by Tom Carter; the review screen, page models, tests, change record and these notes
drafted with Claude (Claude Code), 11-06-2026 to 11-09-2026. Everything runs against the local Tixly
demo app with made-up data; nothing is saved or sent anywhere.

## What was built

A second screen for the local Tixly demo app, page models for both screens, and six tests that
use only the models. The project-setup quest's smoke test now uses the models too.

- **The order review screen** (`demo-app/review.html`, new). The events page's ticket picker is now
  a form: choosing a quantity and pressing the button opens `/review?event=...&quantity=...`. The
  review screen shows an **Order summary** table (Event, Tickets, Total) and a **Back to events**
  link. If the address asks for an event that isn't on sale, or anything but a whole number of
  tickets from 1 to 6, it shows a message instead of a total. Nothing is saved; the screen only shows what its address describes.
  The events page now also works its total out again when the browser's Back button returns to it.
- **The demo server** (`demo-app/server.js`) now serves both pages (`/` and `/review`), with or
  without a query string. It still only answers GET requests and still listens on this computer
  only.
- **The page models** (`pages/models.ts`, new): `EventsScreen` and `OrderReviewScreen`. Every way of
  finding something on either screen lives here, by role, label or visible text. Names are matched
  exactly; the price and fee lines are found by how they start ("Tickets from", "Service fee:"), so
  a test can check the amount.
  Methods are named for what a user does or reads: `chooseTickets`, `reviewOrder`,
  `chooseTicketsAndReview`, `backToEvents`, `goBackInBrowser`, `openFromLink`, `siteName`,
  `ticketPrice`, `serviceFee`, `ticketQuantity`, `eventName`, `ticketCount`, `orderTotal`,
  `problem`. There are no assertions in the file.
- **The tests** (`model-usage.spec.ts`, new): six tests, written only against the models.
  1. A buyer reviewing 2 Spring Concert tickets sees the event, 2 tickets and a total of $55.00.
  2. A buyer who goes back from the review to choose 4 tickets instead sees the new total of
     $110.00.
  3. A review link asking for 0, a fraction, too many or no whole number of tickets explains the
     1 to 6 limit instead of showing a total (it tries 0, -1, 2.5, 9, nothing and "two"; at the
     change record it tried 9 only).
  4. A review link naming an event that isn't on sale says so instead of showing a total (added
     after the change record; see "My own review" below).
  5. A buyer who uses the browser's Back button from the review still sees 3 tickets and $82.50
     (added after the change record; see "An independent review" below).
  6. Review links for 1 and for 6 tickets, the smallest and largest orders, show totals of $27.50
     and $165.00 (added after Copilot's second round; see below).
- **The smoke test** (`tests/smoke.spec.ts`, from the project-setup quest) now finds the site name,
  ticket price and service fee through `EventsScreen` instead of its own selectors, so criterion 1
  holds for every test file in the project. It still checks that the site name, price and fee are
  visible, and now also checks the price and fee lines' exact text.
- **The deliberate interface change, kept:** the events page's button is now **Continue to review**
  (it was **Review order**). That is the change in the change record, and the app keeps it so the
  code handed in matches the evidence.

My decisions:

- **Build a second screen rather than split the one page into parts.** The quest asks for at least
  two screens; a real next step after choosing tickets (reviewing the order) gave the models a
  journey to cover, including going back and forth between screens.
- **Leave the previous quest's page model and test untouched.** `pages/example-page.ts` and
  `first-independent-test.spec.ts` are exactly as they were approved. This quest's models are in a
  new file, so the earlier work stays as evidence of that quest.
- **Keep the "is it right?" checks in the tests** (see "What belongs in the model" below).

## The one-file diff

From `logs/change-record.txt`: after the button was renamed in the app (its own commit), the tests
that press it failed, and this was the whole fix. `git status` and `git diff --stat` show this one
file and nothing else:

```diff
diff --git a/participant/tests/playwright/pages/models.ts b/participant/tests/playwright/pages/models.ts
--- a/participant/tests/playwright/pages/models.ts
+++ b/participant/tests/playwright/pages/models.ts
@@ -9,7 +9,7 @@ import type { Locator, Page } from "@playwright/test";
 // models find and do, and the tests decide whether the result is right.
 
 // The events page (/): one card per event, with a ticket quantity, a running total and a
-// "Review order" button.
+// "Continue to review" button.
 export class EventsScreen {
   constructor(private readonly page: Page) {}
 
@@ -28,7 +28,7 @@ export class EventsScreen {
 
   // Go on to the review screen for the tickets chosen on an event's card.
   async reviewOrder(eventName: string): Promise<void> {
-    await this.event(eventName).getByRole("button", { name: "Review order" }).click();
+    await this.event(eventName).getByRole("button", { name: "Continue to review" }).click();
   }
 
   // Choose tickets and go straight to the review screen, the most common path through this page.
```

The first change is the comment that names the button; the second is the locator itself. The model
has changed since (exact names and new methods, after the reviews below), so the same locator is now
at line 57 and reads `{ name: "Continue to review", exact: true }`.

## What belongs in the model

**The decision:** the model finds things and does things; it never decides whether a result is
right. `orderTotal()` returns *where* the total is; the test says it must be `$55.00`.

I was tempted to have the model check the total too, but I kept that in the test, because the
person checking the work shouldn't be the same one doing it. If the model said "the total is
correct", a test could no longer disagree with it, and a mistake in the model would hide a mistake
in the app.

What did go into the model: anything a UI change could break (labels, roles, button names, the
table's row headings) and steps that more than one test repeats (`chooseTicketsAndReview`).

## Where the important artifacts are

All paths are under `participant/`.

| What | Path |
|---|---|
| The page models (two screens) | `tests/playwright/pages/models.ts` |
| The six tests | `tests/playwright/model-usage.spec.ts` |
| The smoke test (now on the models) | `tests/playwright/tests/smoke.spec.ts` |
| The order review screen (new) | `tests/playwright/demo-app/review.html` |
| The events page (form and button) | `tests/playwright/demo-app/index.html` |
| The demo server (now two pages) | `tests/playwright/demo-app/server.js` |
| README and setup check (updated) | `tests/playwright/README.md`, `tests/playwright/tools/project-setup-check.ts` |
| The change record | `evidence/playwright-page-model/playwright-attempt-005/logs/change-record.txt` |

## How to reproduce the behavior

With the project set up as its README says (`npm ci --engine-strict`, then
`npx playwright install chromium`), from `participant/tests/playwright`:

```
npx playwright test
```

All 8 tests pass (the 6 here, plus the project-setup and first-independent-test quests' tests).
To repeat the change record: rename the button in `demo-app/index.html` (for example back to
"Review order"), run the command again and see the three tests that press it fail on
`pages/models.ts` line 57; change only that line's button name to match, and they pass.

## How the work meets the criteria

1. **No test file contains a raw selector.** All three test files in the project
   (`model-usage.spec.ts`, `tests/smoke.spec.ts` and `first-independent-test.spec.ts`) only call
   page-model methods and assert. Checked by searching their code (not comments) for `getBy`,
   `locator(`, `querySelector`, `page.` method calls, CSS and XPath patterns: no matches. The smoke
   test had its own selectors until the independent review below; it now uses `EventsScreen`.
2. **The model covers at least two screens:** `EventsScreen` (the events page) and
   `OrderReviewScreen` (the order review page).
3. **Assertions about business behavior stay in the tests:** every `expect` (the event, the ticket
   count, the $55.00, $110.00, $82.50, $27.50 and $165.00 totals, the 1 to 6 and "isn't on sale"
   messages, the empty summary when there's a problem, the visible price and fee) is in the test
   files. Searching `pages/models.ts` for `expect`
   finds nothing.
4. **A locator change is fixed by editing only the model:** `logs/change-record.txt` shows the suite
   passing (5 of 5), then the button renamed in the app and committed on its own, then 2 tests
   failing while waiting for the old button name at `pages/models.ts:31`, then the model fixed and
   the suite passing again (5 of 5).
5. **The Git diff of that change touches no test file:** in the same record, `git status`,
   `git diff --stat` and `git diff` show only `pages/models.ts` (2 lines). The diff is above.
6. **Methods are named for user actions:** `chooseTickets`, `reviewOrder`, `backToEvents`,
   `goBackInBrowser`, `openFromLink`, and for what the user reads: `orderTotal`, `ticketCount`,
   `ticketPrice`, `problem`. None is named for an element.
7. **A new test can reuse the model without copying code:** tests 1 and 2 both use
   `chooseTicketsAndReview`; test 2 also goes back with `backToEvents` and reuses the same method on
   the screen it returns. Tests 3 and 4 are a different way in (`openFromLink`) and still read the same
   `orderTotal` and `problem`; test 4 reuses `openFromLink` for two addresses in a loop. Test 5 and
   the smoke test were written after the models, using methods added for them (`goBackInBrowser`,
   `ticketQuantity`, `siteName`, `ticketPrice`, `serviceFee`) next to the ones already there, with
   no steps copied. Test 6 reuses `openFromLink`, `ticketCount` and `orderTotal` for two orders in
   a loop.

## What was tested or validated

- **The change record** (`logs/change-record.txt`, 11-09-2026, 10:08 AM to 10:09 AM): before 5
  passed; after the interface change 2 failed and 3 passed; after the model fix 5 passed; only
  `pages/models.ts` changed. The suite had 5 tests then (tests 4, 5 and 6 came later). Only 2 of
  the 3 new tests failed because the third opens the review screen from a link and never presses
  the button; the two earlier quests' tests don't press it either.
- **The tests catch the bugs they are for:** on 11-06-2026 I made the review screen charge the fee
  once per order: tests 1 and 2 failed, receiving $52.50 and $102.50. I removed the 1 to 6 limit:
  test 3 failed. The review screen was put back byte for byte each time.
- **Earlier work still passes:** the project-setup and first-independent-test quests' tests pass in
  every run above.
- **This quest has no automatic checker.** The criteria above were checked against the files and
  the change record.
- **My own review before Copilot** found four things, all fixed after the change record (none
  touched the page models):
  - A review link naming something every JavaScript object has, such as `?event=constructor`,
    showed the event as "Object" and the total as "$NaN" instead of "That event isn't on sale".
    The review screen now only accepts events it lists; the same links now show the message.
    Test 4 was added to guard it: with the old lookup put back it failed (no message appeared),
    and with the fix it passes. The page was put back byte for byte after that trial.
  - The project README still said a run ends with `2 passed`; it now gives the current count and
    names the new tests and their tag.
  - The project-setup check didn't cover the 3 new files; it now checks 15 project files instead
    of 12, and passes.
  - The test-data notes at the top of `model-usage.spec.ts` didn't list the 9-ticket case; they now
    list it, and the "isn't on sale" case.
- **Copilot, round 1** (a practice pull request in my own fork, 11-09-2026): recommended approval
  with no open issues, after reviewing all 9 changed files.
- **An independent review.** Because Copilot found nothing, I asked for a second, independent
  review that was given only the files and the quest. Every number and claim in this PROOF that it
  checked was right, but it found the following, which I reproduced before fixing:
  - **The events page showed the wrong total after the browser's Back button** (Medium): choose
    3 tickets, continue to the review, press Back, and the quantity still said 3 while the total
    said $27.50, the price of 1. The page now works the total out again whenever it is shown.
    Test 5 does exactly this; with the fix taken out it failed, and with it in it passes.
  - **The smoke test still had its own selectors** (Medium, criterion 1): it now uses the models.
  - **Names matched loosely** (Low): a button renamed "Continue to review later" still passed. The
    models now match names exactly; with that rename, the three tests that press it fail.
  - **Two checks were too narrow** (Low): test 3 and test 4 now also check that the Event and
    Tickets lines stay empty, and test 1 that no problem message shows. With the review screen
    changed to fill those lines in on an error, test 3 fails.
  - **The events page answered "Not found" to `/?anything`** (Low), while the review page took a
    query string; both now do.
  - Two notes were also tidied: a comment no longer says the tests run "in parallel" (one file runs
    in one browser at a time), and the summary rows are now found by their exact row heading.
  - Every trial file was put back byte for byte. Afterwards the whole suite passed 35 of 35 (each
    test 5 times, 4 browsers at once) and the project-setup check passed (15 of 15).
- **Copilot, round 2** (the same practice pull request, 11-09-2026, asked for a line-by-line
  review) found 2 things, both reproduced before fixing: with either break below put in, all 7
  tests still passed.
  - **The smoke test no longer checked that the price and fee lines are visible** (Medium): moving
    it onto the models had swapped its visibility checks for exact-text checks, which also pass on
    a hidden line. It now checks both. With either line hidden, the smoke test fails.
  - **No test checked the edges of the 1 to 6 limit** (Medium): changing it to 0 to 6, or 1 to 5,
    left every test passing. Test 3 now also tries 0, -1, 2.5, nothing and "two", and test 6
    checks that 1 and 6 tickets are accepted with the right totals. With the limit changed either
    way, a test fails.
  - All earlier break-it trials were run again afterwards and still fail the tests they should;
    every file was put back byte for byte. Then the whole suite passed 40 of 40 (each of the 8
    tests 5 times, 4 browsers at once), and the project-setup check passed.

## Stretch goals

Not attempted: a component model reused by two pages, and an automatic check that tests contain no
selector. Criterion 1 was checked by a search, run by hand, not by a check in the suite.

## Remaining limitations

- **The price is written twice.** The events page keeps the Spring Concert's price and fee on its
  card, and the review screen keeps its own copy. A real app would get both from its server; here,
  changing one and not the other would make the two screens disagree.
- **One event, one browser (Chromium).**
- **The review screen trusts its address.** It checks the event and the quantity (1 to 6), but
  there's no order behind it: nothing is saved and no payment is involved.
- **Files from the project-setup quest changed:** `demo-app/server.js`, `demo-app/index.html` and
  `tests/smoke.spec.ts` (two pages, the form, the renamed button, the Back-button total and the
  smoke test on the models), and again `README.md` and `tools/project-setup-check.ts` (the new tests
  and files). The quest app's content check notes 3 of these files as changed since the
  project-setup quest was approved: the README, `playwright.config.ts` (changed in the
  first-independent-test quest) and the setup check. The changes are the ones described here and in
  that quest's hand-in. Both earlier quests' tests still pass.

## Sensitive values

No password, token, customer name or private ticket content is here. The tests use no credential,
and all data in the demo app is made up. The change record shows personal home-folder paths as `~`.
Every file in this evidence was scanned with the quest app's credential patterns: 0 findings.
