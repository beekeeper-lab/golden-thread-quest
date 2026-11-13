import { expect, test } from "@playwright/test";
import { UpcomingEventsPage } from "./pages/example-page.ts";

// Business rule: a buyer pays the ticket price plus the service fee on every ticket, so the total
// they see before paying must be quantity x (price + fee). Getting it wrong means charging more,
// or less, than the page promised.
//
// Test data, all from the local demo page (made-up data, nothing saved or sent):
//   event:        Spring Concert
//   ticket price: $25.00, service fee: $2.50 per ticket (both shown on the event's card)
//   quantity:     2  ->  expected total 2 x ($25.00 + $2.50) = $55.00
// Precondition: none beyond the demo page itself. Each test gets a fresh browser page, and choosing
// a quantity changes nothing on the server, so the test runs alone, in any order, and again.
const EVENT = "Spring Concert";
const QUANTITY = 2;
const EXPECTED_TOTAL = "Total: $55.00";

test(
  "a buyer choosing 2 Spring Concert tickets sees a total of $55.00, with the $2.50 service fee on each ticket",
  // Tags from the scheme (participant/context/playwright/tag-scheme.md): feature, risk, read or write,
  // layer and duration. It was tagged @ticket-total before the scheme; that tag was folded into @events.
  { tag: ["@events", "@risk-high", "@read-only", "@layer-ui", "@fast"] },
  async ({ page }, testInfo) => {
    const eventsPage = new UpcomingEventsPage(page);
    await eventsPage.open();

    await eventsPage.chooseTicketQuantity(EVENT, QUANTITY);

    // The business outcome: the exact amount the buyer would pay. toHaveText waits for the page to
    // update, so there is no fixed sleep.
    await expect(eventsPage.orderTotal(EVENT)).toHaveText(EXPECTED_TOTAL);

    // Success evidence, taken once, at the point the total has been proven right.
    await testInfo.attach("validated-state", {
      body: await eventsPage.event(EVENT).screenshot(),
      contentType: "image/png",
    });
  },
);
