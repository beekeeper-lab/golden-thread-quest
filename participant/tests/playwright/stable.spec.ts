import { expect, test } from "@playwright/test";

// The STABLE version of brittle.spec.ts, for the stable-locators quest: the same business check,
// with every locator replaced by one based on what a user sees (role, label or visible text).
// Beside each one is the reason it survives a redesign that keeps what users see. Like
// brittle.spec.ts, it writes its locators here on purpose, so the two can be compared line by
// line; the other tests find things through the page models in pages/.
//
// Test data (local demo page, made-up data): Spring Concert, ticket $25.00, fee $2.50 per ticket;
// 2 tickets -> $55.00 (quantity x (price + fee)).
test(
  "a buyer choosing 2 Spring Concert tickets sees a total of $55.00 (stable locators)",
  { tag: ["@events", "@risk-high", "@read-only", "@layer-ui", "@fast", "@locator-comparison"] },
  async ({ page }) => {
    await page.goto("/");

    // 1. Was: POSITION AMONG SIBLINGS ("the 1st card").
    //    Now: ROLE + NAME. Users pick the concert by its name, not by where it sits on the page;
    //    a new event above it doesn't change its name.
    const card = page.getByRole("article", { name: "Spring Concert", exact: true });

    // 2. Was: GENERATED ID ("#r-7f3k2").
    //    Now: LABEL. Users find the box by the words "Number of tickets" next to it; a new build
    //    can rename hidden IDs, but the words users read stay the same.
    const quantity = card.getByLabel("Number of tickets", { exact: true });

    // 3. Was: INDEX IN A LIST ("the 2nd paragraph").
    //    Now: VISIBLE TEXT. Users read "Tickets from..."; a new line above it moves it down the
    //    page but doesn't change its words. Relies on that wording staying the same.
    const ticketPrice = card.getByText(/^Tickets from /);

    // 4. Was: GENERATED CLASS NAME (".css-q81zk").
    //    Now: VISIBLE TEXT. Users read "Service fee:"; restyling can change the hidden class name,
    //    not the words. Relies on that wording staying the same.
    const serviceFee = card.getByText(/^Service fee: /);

    // 5. Was: LONG DOM PATH ("main > article > form > p").
    //    Now: ROLE + HIDDEN LABEL. Found by its role (a status message) and its hidden label "Order
    //    total", wherever it sits in the page. Nothing on screen says "Order total": a developer
    //    added both the "status" role and that label. Without them, only the visible wording
    //    "Total:" would be left to find it by.
    const orderTotal = card.getByRole("status", { name: "Order total", exact: true });

    // The business check, the same as in brittle.spec.ts: the price and fee are shown and as
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
