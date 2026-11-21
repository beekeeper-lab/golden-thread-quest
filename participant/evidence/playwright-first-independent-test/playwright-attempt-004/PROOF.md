# Proof · playwright-first-independent-test

Attempt: `playwright-attempt-004`

Decisions by Tom Carter; the test, page model, demo page change and these notes drafted with
Claude (Claude Code), 11-06-2026. Everything runs against the local Tixly demo page with made-up
data; nothing is saved or sent anywhere.

## What was built

One Playwright test of a business rule a ticket buyer depends on: **the order total is the ticket
price plus the service fee, on every ticket**. If the math is wrong, a customer is overcharged or
undercharged.

- **The demo page** (`demo-app/index.html`, the local Tixly page from the project-setup quest) now
  has a **Number of tickets** picker and an **Order total** line on the Spring Concert card. The
  total is quantity x (ticket price + service fee), worked out in whole cents from the price and
  fee stored on the card, when the page opens and whenever the quantity changes. Choosing a
  quantity only changes what the page shows; nothing is saved.
- **The page model** (`pages/example-page.ts`) holds every way of finding something on the page,
  by role and label: open the page, find an event's card by its name, choose a ticket quantity,
  read the order total. It finds and does; it never decides whether a result is right.
- **The test** (`first-independent-test.spec.ts`) chooses 2 Spring Concert tickets and checks the
  page shows exactly `Total: $55.00` (2 x ($25.00 + $2.50)).
- **One configuration change** (`playwright.config.ts`): Playwright now also finds tests at the top
  of the project folder, where this quest's test has to be, as well as in `tests/`. The smoke test
  from the project-setup quest still runs.
- **The project-setup quest's files kept true:** its README now says `npm test` runs both tests
  and ends with `2 passed` (it said `1 passed`), and gives the tag command; its setup check now
  also confirms the new test and page model are not ignored by Git, and still passes. The quest
  app notes that these three files have changed since the project-setup quest was approved; these
  are the changes.

My decisions:

- **Test the total, not just the listing.** The page only showed one event with its price, which
  would have made a "the text is there" test. Adding the quantity and total gave a real business
  rule with an exact answer to check.
- **Make the deliberate failure a believable bug in the app, not a broken test:** the fee charged
  once per order instead of once per ticket. The test itself was never changed to fail.
- **Report the quality checker's problems.** Before I'd written the test, the checker failed on
  Playwright's own installed files, and once the selectors were in the page model it warned that it
  found no role queries. I reported both, and planned to work around the first for the run if
  needed; both were fixed upstream the same day, so the recorded run below is from the fixed
  checker, with no workaround.

## Where the important artifacts are

All paths are under `participant/`.

| What | Path |
|---|---|
| The test | `tests/playwright/first-independent-test.spec.ts` |
| The page model | `tests/playwright/pages/example-page.ts` |
| The demo page (with the ticket total) | `tests/playwright/demo-app/index.html` |
| Configuration | `tests/playwright/playwright.config.ts` |
| README and setup check (updated) | `tests/playwright/README.md`, `tests/playwright/tools/project-setup-check.ts` |
| Tagged run, plus the independence run | `evidence/playwright-first-independent-test/playwright-attempt-004/logs/test-run.txt` |
| Deliberately failing run, with the two-line reproduction at the top | `evidence/playwright-first-independent-test/playwright-attempt-004/logs/failure-run.txt` |
| Trace of the failing run | `evidence/playwright-first-independent-test/playwright-attempt-004/logs/failure-trace.zip` |
| The page when the failing run failed | `evidence/playwright-first-independent-test/playwright-attempt-004/screenshots/failure-state.png` |
| The card when the total was proven right | `evidence/playwright-first-independent-test/playwright-attempt-004/screenshots/validated-state.png` |

## How to reproduce the behavior

With the project set up as its README says (`npm ci --engine-strict`, then
`npx playwright install chromium`), from `participant/tests/playwright`:

```
npx playwright test --grep @ticket-total
npx playwright test --repeat-each=3 --fully-parallel --workers=3
```

The first runs this test alone and passes; the second runs the whole suite three times over three
browsers at once and passes. To see it fail, follow the two lines at the top of
`logs/failure-run.txt`: change the total in `demo-app/index.html` to charge the fee once per
order, then run the first command again. It fails with `Expected: "Total: $55.00"` and
`Received: "Total: $52.50"`. Put the line back afterwards. To look at the saved trace:
`npx playwright show-trace <path to failure-trace.zip>`.

## The business risk, and why the assertion proves it

**The risk:** the total a buyer sees before paying is wrong, so they are charged more or less than
the page promised. That is a money and trust problem, so the test is tagged `@risk-high`.

**Why the assertion proves it:** the test checks the exact total text, `Total: $55.00`, for a
quantity where the right answer and the likely wrong answers are all different: charging the fee
once gives $52.50, leaving it out gives $50.00, and not updating the total at all leaves $27.50.
Checking that a total is merely shown, or that the page loaded, would pass in every one of those
cases. Two tickets were chosen on purpose: with one ticket, "fee per ticket" and "fee per order"
give the same $27.50, so that bug would slip through.

## What the failing run's evidence tells a reviewer who hasn't seen the test

- **The log** names the behavior in the test's title, the locator it checked (the Spring Concert
  card's "Order total"), and the numbers: expected $55.00, received $52.50. The gap is exactly
  one $2.50 fee.
- **The screenshot** shows the card at the moment of failure: "Service fee: $2.50 per ticket",
  2 tickets chosen, "Total: $52.50". Anyone can see the fee was applied once, without reading code.
- **The trace** replays every step (open the page, choose 2, check the total) with the page at each
  step; the failed check is marked in red with the received text highlighted.
- **The two-line reproduction** says how to make it happen again on purpose.

Together they point at the price calculation, not the test, the browser or the data, so the team
can go straight to the fix.

## How the work meets the criteria

1. **The title describes user behavior and the expected outcome:** "a buyer choosing 2 Spring
   Concert tickets sees a total of $55.00, with the $2.50 service fee on each ticket".
2. **It runs alone and in any suite order:** `logs/test-run.txt` shows it alone (`--grep
   @ticket-total`, 1 passed) and in the whole suite, each test three times over three browsers at
   once (6 passed). Each test gets a fresh browser page, and nothing it does is saved.
3. **Selectors and reusable page behavior are centralized:** every locator and action is in
   `pages/example-page.ts`; the test only calls it and asserts.
4. **Stable locators:** the page model finds things by role and label only: the event's card by
   its name (`getByRole("article", { name })`), the quantity by its label ("Number of tickets"),
   the total by its role and name (`getByRole("status", { name: "Order total" })`). No generated IDs,
   classes or DOM paths.
5. **No arbitrary fixed sleep:** `toHaveText` waits for the total to update; there is no
   `waitForTimeout` or sleep anywhere.
6. **The assertion validates the business outcome:** the exact amount the buyer would pay, not a
   URL, visibility or HTTP status (see "The business risk" above).
7. **Test data and preconditions are explicit:** the comment at the top of the test lists the
   event, price, fee, quantity and expected total with its arithmetic, and says the only
   precondition is the demo page itself.
8. **Tags for feature, risk, read-only/write and duration:** `@ticket-total @risk-high @read-only
   @fast`, shown with the test's name in both logs.
9. **Failure evidence includes trace, screenshot and a concise reproduction summary:**
   `logs/failure-trace.zip`, `screenshots/failure-state.png`, and the two lines at the top of
   `logs/failure-run.txt`.
10. **Success evidence is captured at the meaningful validation point:** the test takes one
    screenshot of the event card right after the total is proven right and attaches it to the run
    (saved here as `screenshots/validated-state.png`, showing $55.00), not on every step.
11. **Rerunning does not change application data:** choosing a quantity only changes what the page
    shows; the demo server only answers GET requests for the page itself. The suite ran the test
    three times, with other runs going on at the same time, and every run got the same result.

## Reflection

**If this test failed tomorrow, what decision could the team make from the evidence it produces?**

It depends on what the failure log and the screenshot show, but if this test fails, the math behind
the order total isn't right, and a customer could be overcharged or undercharged. That makes it a
high-priority fix. The log gives the expected and actual totals, and the screenshot shows the fee,
the quantity and the total together, so the team can see which way it's wrong without re-running
the test.

## What was tested or validated

- **The recorded runs:** the tagged run passed; the whole suite passed 6 of 6; the deliberately
  failing run failed exactly as described above. After the failing run, the demo page was put back
  and checked byte for byte against the original, and the test passed again.
- **The test catches the bug it is for:** before recording, a trial run with the fee charged once
  per order failed with the same $55.00 / $52.50 message.
- **The trace opens:** I opened `logs/failure-trace.zip` in Playwright's trace viewer and it shows
  every step, the failed check and the page snapshot with $52.50.
- **The project-setup quest still holds:** its setup check passed after these changes, now
  checking 12 project files instead of 10.
- **My own review before Copilot** found three things, all fixed: the README still promised
  `1 passed`; the setup check didn't cover the new files; and the page's starting total was typed
  in rather than worked out from the price and fee (checked afterwards: with the fee changed to
  $3.00, the starting total follows, $28.00).
- **The quest's quality checker (`validate-playwright-quality`, version 2):** passed all four checks
  on 11-06-2026 at 1:21 PM: every test file asserts something; queries are by role, label or text
  (in the test and the page model); no arbitrary wait; and the evidence includes a record of the
  test failing (the failure log, trace and screenshot). The saved result is in `validation/`. The
  checker was fixed after I reported two problems with it (it read Playwright's installed files,
  and didn't count queries in a page model); this run used the fixed version.
- **Copilot review:** 2 rounds on a practice pull request in my own fork, on 11-06-2026. I
  reproduced each item before changing anything. Round 1 found 2 Low items, both about the practice
  pull request missing what this hand-in has: I had left the trace and screenshots out of it, and
  the checker result was still a placeholder. Both were fixed. Round 2 recommended approval with no
  open issues.

## Stretch goals

- **Tag combinations from the command line:** partly. The tags work with `--grep`
  (`--grep @ticket-total` runs only this test); combinations were not demonstrated separately.
- Not attempted: an API-assisted setup or check, and scoring the test 0-100.

## Remaining limitations

- **One quantity, one event.** The test proves the rule for 2 Spring Concert tickets. Other
  quantities, or an event with a different fee, are not checked; with exact cents the rule is the
  same, but a regression that only hits large quantities would not be caught.
- **The total is worked out on the page.** In a real ticket app the amount charged would come from
  the server; this checks what the buyer is shown, not what a payment system charges.
- **One browser (Chromium),** as the project is set up.
- **The failing run is a simulated bug,** made by changing one line of the demo page and putting it
  back.

## Sensitive values

No password, token, customer name or private ticket content is here. The test uses no credential,
and all data on the demo page is made up. The logs show personal home-folder paths as `~`; the trace
had the same path in its stack and source records, so the saved copy shows `~` there too. Every
file in this evidence, including every file inside the trace zip, was scanned with the quest app's
credential patterns: 0 findings.
