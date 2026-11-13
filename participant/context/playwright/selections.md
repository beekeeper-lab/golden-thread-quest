# Tag selections for the Tixly Playwright tests

Each selection names a set of tests by their tags (`context/playwright/tag-scheme.md`), says why it
exists, and lists exactly the tests it should choose. `tests/playwright/tools/select.ts <name>` reads
a selection from this page, lists what Playwright would choose without running anything, compares
that with the tests below, and runs them only if the two match; a selection that matches no test is
always an error. Expressions use whole tags joined by `and`, `or` and `not`. Tests are named
`<file> › <title>`. Decisions by Tom Carter; wording drafted with Claude (Claude Code), 11-13-2026.

| Name | Expression | Kind | Tests |
|---|---|---|---|
| `every-change` | `@fast` | single tag | 26 |
| `safe-pipeline` | `@fast and @read-only` | intersection | 15 |
| `before-saving` | `@events or @order-review` | union | 14 |
| `shared-environment` | `not @writes-data` | exclusion | 15 |
| `high-risk-safe` | `@risk-high and not @writes-data` | intersection with exclusion | 10 |
| `orders-service` | `@saved-orders and @layer-api` | intersection | 3 |
| `slow-read-only` | `@slow and @read-only` | matches nothing | 0 |

## every-change

- **Expression:** `@fast`
- **Purpose:** Quick feedback on every change: every test that takes at most 2 seconds.
- **Expected tests (26):**
  - api-assisted.spec.ts › a buyer cancels an order (API-assisted: API setup, cancel on screen, API check)
  - brittle.spec.ts › a buyer choosing 2 Spring Concert tickets sees a total of $55.00 (brittle locators)
  - cleanup-proof.spec.ts › proof 1: a test that fails after creating its order still has it cancelled by its cleanup
  - cleanup-proof.spec.ts › proof 2: an order the test never got to note is cancelled by the run-end safety net
  - coupled.spec.ts › a buyer saves an order for Test User and sees it in Your orders (coupled)
  - coupled.spec.ts › a buyer cancels Test User's order (coupled: relies on the order the test above saved)
  - first-independent-test.spec.ts › a buyer choosing 2 Spring Concert tickets sees a total of $55.00, with the $2.50 service fee on each ticket
  - isolated.spec.ts › a buyer saves an order and sees it in Your orders (isolated)
  - isolated.spec.ts › a buyer cancels their own order (isolated: makes the order it cancels)
  - isolated.spec.ts › cancelling one buyer's order leaves another buyer's order in Your orders (isolated)
  - model-usage.spec.ts › a buyer reviewing 2 Spring Concert tickets sees the event, 2 tickets and a total of $55.00
  - model-usage.spec.ts › a buyer who goes back from the review to choose 4 tickets instead sees the new total of $110.00
  - model-usage.spec.ts › a review link asking for 0, a fraction, too many or no whole number of tickets explains the 1 to 6 limit instead of showing a total
  - model-usage.spec.ts › a review link naming an event that isn't on sale says so instead of showing a total
  - model-usage.spec.ts › a buyer who uses the browser's Back button from the review still sees 3 tickets and $82.50
  - model-usage.spec.ts › review links for 1 and for 6 tickets, the smallest and largest orders, show totals of $27.50 and $165.00
  - stable.spec.ts › a buyer choosing 2 Spring Concert tickets sees a total of $55.00 (stable locators)
  - tagged.spec.ts › the events page shows the Tixly name at the top
  - tagged.spec.ts › choosing 3 tickets on the events page shows a total of $82.50
  - tagged.spec.ts › the review page for 4 tickets shows a total of $110.00
  - tagged.spec.ts › a review link for an event not on sale says so instead of showing a total
  - tagged.spec.ts › the orders service refuses an order for 7 tickets
  - tagged.spec.ts › the orders service lists every saved order that isn't test data, exactly as saved
  - tagged.spec.ts › an order created through the API shows the right total on Your orders
  - tests/smoke.spec.ts › a visitor sees the Spring Concert and its ticket price on the Tixly home page
  - ui-only.spec.ts › a buyer cancels an order (UI-only: saved and cancelled through the screen)

## safe-pipeline

- **Expression:** `@fast and @read-only`
- **Purpose:** The quest's scenario: a pipeline step that runs only fast checks that never change saved data.
- **Expected tests (15):**
  - brittle.spec.ts › a buyer choosing 2 Spring Concert tickets sees a total of $55.00 (brittle locators)
  - first-independent-test.spec.ts › a buyer choosing 2 Spring Concert tickets sees a total of $55.00, with the $2.50 service fee on each ticket
  - model-usage.spec.ts › a buyer reviewing 2 Spring Concert tickets sees the event, 2 tickets and a total of $55.00
  - model-usage.spec.ts › a buyer who goes back from the review to choose 4 tickets instead sees the new total of $110.00
  - model-usage.spec.ts › a review link asking for 0, a fraction, too many or no whole number of tickets explains the 1 to 6 limit instead of showing a total
  - model-usage.spec.ts › a review link naming an event that isn't on sale says so instead of showing a total
  - model-usage.spec.ts › a buyer who uses the browser's Back button from the review still sees 3 tickets and $82.50
  - model-usage.spec.ts › review links for 1 and for 6 tickets, the smallest and largest orders, show totals of $27.50 and $165.00
  - stable.spec.ts › a buyer choosing 2 Spring Concert tickets sees a total of $55.00 (stable locators)
  - tagged.spec.ts › the events page shows the Tixly name at the top
  - tagged.spec.ts › choosing 3 tickets on the events page shows a total of $82.50
  - tagged.spec.ts › the review page for 4 tickets shows a total of $110.00
  - tagged.spec.ts › a review link for an event not on sale says so instead of showing a total
  - tagged.spec.ts › the orders service lists every saved order that isn't test data, exactly as saved
  - tests/smoke.spec.ts › a visitor sees the Spring Concert and its ticket price on the Tixly home page

## before-saving

- **Expression:** `@events or @order-review`
- **Purpose:** Everything a buyer sees before saving an order: the events page and the review page.
- **Expected tests (14):**
  - brittle.spec.ts › a buyer choosing 2 Spring Concert tickets sees a total of $55.00 (brittle locators)
  - first-independent-test.spec.ts › a buyer choosing 2 Spring Concert tickets sees a total of $55.00, with the $2.50 service fee on each ticket
  - model-usage.spec.ts › a buyer reviewing 2 Spring Concert tickets sees the event, 2 tickets and a total of $55.00
  - model-usage.spec.ts › a buyer who goes back from the review to choose 4 tickets instead sees the new total of $110.00
  - model-usage.spec.ts › a review link asking for 0, a fraction, too many or no whole number of tickets explains the 1 to 6 limit instead of showing a total
  - model-usage.spec.ts › a review link naming an event that isn't on sale says so instead of showing a total
  - model-usage.spec.ts › a buyer who uses the browser's Back button from the review still sees 3 tickets and $82.50
  - model-usage.spec.ts › review links for 1 and for 6 tickets, the smallest and largest orders, show totals of $27.50 and $165.00
  - stable.spec.ts › a buyer choosing 2 Spring Concert tickets sees a total of $55.00 (stable locators)
  - tagged.spec.ts › the events page shows the Tixly name at the top
  - tagged.spec.ts › choosing 3 tickets on the events page shows a total of $82.50
  - tagged.spec.ts › the review page for 4 tickets shows a total of $110.00
  - tagged.spec.ts › a review link for an event not on sale says so instead of showing a total
  - tests/smoke.spec.ts › a visitor sees the Spring Concert and its ticket price on the Tixly home page

## shared-environment

- **Expression:** `not @writes-data`
- **Purpose:** Safe to run where other people's data lives: every test that doesn't change saved data.
- **Expected tests (15):**
  - brittle.spec.ts › a buyer choosing 2 Spring Concert tickets sees a total of $55.00 (brittle locators)
  - first-independent-test.spec.ts › a buyer choosing 2 Spring Concert tickets sees a total of $55.00, with the $2.50 service fee on each ticket
  - model-usage.spec.ts › a buyer reviewing 2 Spring Concert tickets sees the event, 2 tickets and a total of $55.00
  - model-usage.spec.ts › a buyer who goes back from the review to choose 4 tickets instead sees the new total of $110.00
  - model-usage.spec.ts › a review link asking for 0, a fraction, too many or no whole number of tickets explains the 1 to 6 limit instead of showing a total
  - model-usage.spec.ts › a review link naming an event that isn't on sale says so instead of showing a total
  - model-usage.spec.ts › a buyer who uses the browser's Back button from the review still sees 3 tickets and $82.50
  - model-usage.spec.ts › review links for 1 and for 6 tickets, the smallest and largest orders, show totals of $27.50 and $165.00
  - stable.spec.ts › a buyer choosing 2 Spring Concert tickets sees a total of $55.00 (stable locators)
  - tagged.spec.ts › the events page shows the Tixly name at the top
  - tagged.spec.ts › choosing 3 tickets on the events page shows a total of $82.50
  - tagged.spec.ts › the review page for 4 tickets shows a total of $110.00
  - tagged.spec.ts › a review link for an event not on sale says so instead of showing a total
  - tagged.spec.ts › the orders service lists every saved order that isn't test data, exactly as saved
  - tests/smoke.spec.ts › a visitor sees the Spring Concert and its ticket price on the Tixly home page

## high-risk-safe

- **Expression:** `@risk-high and not @writes-data`
- **Purpose:** The money checks that can run anywhere: high-risk tests that don't change saved data.
- **Expected tests (10):**
  - brittle.spec.ts › a buyer choosing 2 Spring Concert tickets sees a total of $55.00 (brittle locators)
  - first-independent-test.spec.ts › a buyer choosing 2 Spring Concert tickets sees a total of $55.00, with the $2.50 service fee on each ticket
  - model-usage.spec.ts › a buyer reviewing 2 Spring Concert tickets sees the event, 2 tickets and a total of $55.00
  - model-usage.spec.ts › a buyer who goes back from the review to choose 4 tickets instead sees the new total of $110.00
  - model-usage.spec.ts › a buyer who uses the browser's Back button from the review still sees 3 tickets and $82.50
  - model-usage.spec.ts › review links for 1 and for 6 tickets, the smallest and largest orders, show totals of $27.50 and $165.00
  - stable.spec.ts › a buyer choosing 2 Spring Concert tickets sees a total of $55.00 (stable locators)
  - tagged.spec.ts › choosing 3 tickets on the events page shows a total of $82.50
  - tagged.spec.ts › the review page for 4 tickets shows a total of $110.00
  - tests/smoke.spec.ts › a visitor sees the Spring Concert and its ticket price on the Tixly home page

## orders-service

- **Expression:** `@saved-orders and @layer-api`
- **Purpose:** The orders service alone, without a browser.
- **Expected tests (3):**
  - cleanup-proof.spec.ts › proof 1: a test that fails after creating its order still has it cancelled by its cleanup
  - tagged.spec.ts › the orders service refuses an order for 7 tickets
  - tagged.spec.ts › the orders service lists every saved order that isn't test data, exactly as saved

## slow-read-only

- **Expression:** `@slow and @read-only`
- **Purpose:** Matches nothing on purpose: the only slow test changes data. It must be reported as an error, never as a pass.
- **Expected tests (0):**
  - none
