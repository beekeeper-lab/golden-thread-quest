import { expect, test } from "@playwright/test";

// A deliberately BRITTLE version of the ticket-total test, for the stable-locators quest.
// It finds everything by how the page is BUILT (positions, generated names, paths), not by what
// a user sees. Each locator is labeled with its kind. It passes on today's page; a redesign that
// changes nothing a user cares about breaks it. Compare stable.spec.ts, which checks the same thing.
//
// Test data (local demo page, made-up data): Spring Concert, ticket $25.00, fee $2.50 per ticket;
// 2 tickets -> $55.00 (quantity x (price + fee)).
test(
  "a buyer choosing 2 Spring Concert tickets sees a total of $55.00 (brittle locators)",
  { tag: ["@events", "@risk-high", "@read-only", "@layer-ui", "@fast", "@locator-comparison"] },
  async ({ page }) => {
    await page.goto("/");

    // 1. POSITION AMONG SIBLINGS: "the 1st card on the page". A new card above it changes which
    //    event this is.
    const card = page.locator("main > article:nth-child(1)");

    // 2. GENERATED ID: a name a build tool made up. No one has promised to keep it; a change to the
    //    page or the build tools can rename it without warning.
    const quantity = page.locator("#r-7f3k2");

    // 3. INDEX IN A LIST: "the 2nd paragraph in the card" (counting from 0). One new line above
    //    it, and this is a different line.
    const ticketPrice = card.locator("p").nth(1);

    // 4. GENERATED CLASS NAME: a styling name a build tool made up. No one has promised to keep it;
    //    a change to the styling or the build tools can rename it without warning.
    const serviceFee = page.locator(".css-q81zk");

    // 5. LONG DOM PATH: "main, then a card, then a form, then a paragraph". Wrapping any of these
    //    in a new box breaks the path.
    const orderTotal = page.locator("main > article > form > p");

    // The business check, the same as in stable.spec.ts: the price and fee are shown and as
    // expected, and 2 tickets show a total of $55.00.
    await expect(ticketPrice).toBeVisible();
    await expect(ticketPrice).toHaveText("Tickets from $25.00");
    await expect(serviceFee).toBeVisible();
    await expect(serviceFee).toHaveText("Service fee: $2.50 per ticket");
    await quantity.selectOption("2");
    await expect(orderTotal).toBeVisible();
    await expect(orderTotal).toHaveText("Total: $55.00");
  },
);
