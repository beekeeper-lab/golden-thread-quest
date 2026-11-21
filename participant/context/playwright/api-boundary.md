# Where the API-assisted test trusts the API, and where it doesn't

The boundary for `tests/playwright/api-assisted.spec.ts`, the test of "a buyer cancels an order" in
the Tixly demo app (an invented ticket app run on this computer). It uses the app's orders service
(the API) to build the world before the one behavior under test and to confirm the result after
it, and uses the screen only for that behavior. Decisions by Tom Carter; wording drafted with
Claude (Claude Code), 11-12-2026.

## What the test trusts the API for

The API is trusted for setup and for checks:

- **Creating the order.** The order to cancel is saved through the orders service, and the test
  trusts that it is saved the same way a buyer's save would save it.
- **Telling the truth about what is saved.** The list the orders service returns is trusted to be
  the real saved data. That is what makes the final check stronger than the screen: the page can
  say "cancelled" while the order is still saved, and only the list shows it.
- **Not caring about the screens it skips.** The events and review pages are not what this test
  is about, so it doesn't walk through them.

## What the test refuses to trust the API for

- **The behavior under test.** Cancelling is done on the screen, by clicking "Cancel order for
  <name>" on "Your orders". If the API did the cancelling, the test would be testing the API, not
  the page a buyer uses.
- **What the buyer sees.** The API can't tell whether the page shows the right message, total or
  button, so the test still checks the "Order for <name> cancelled." message on the screen.
- **That an order made through the API is just like a buyer's.** An order created through the
  orders service never passes through the events and review pages, so anything those pages do
  differently when they save (the number of tickets, how the name is entered) is never exercised.
- **Anything about the other pages.** If the events page or the review page broke, this test would
  still pass.

## A bug this test could miss

If the review page stopped saving orders, or saved them with the wrong number of tickets, this
test would still pass: it creates its order through the API and never visits that page. The
UI-only version (`tests/playwright/ui-only.spec.ts`) walks through those pages, so it would catch a
save that stopped working, but it doesn't check the number of tickets; the save test in
`tests/playwright/isolated.spec.ts` checks the saved order's tickets and total, so it would catch
that.

## The key

The orders service only answers the tests with a made-up API key from the environment
(`TIXLY_API_KEY`). The test sends it from Node, never from the browser, so it can't appear on a
page, in a screenshot or in a trace, and nothing prints it.
