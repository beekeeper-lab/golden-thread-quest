import { expect, test } from "./support/orders-fixture.ts";

// The API-ASSISTED version of "a buyer cancels an order", for the API-assisted test quest. The
// screen is used only for the one behavior under test; the orders service (the API) builds the
// world before it and confirms the result after it:
//   1. Arrange, through the API: one order of this test's own, with a unique name.
//   2. Act, through the screen: on "Your orders", the buyer clicks "Cancel order for <name>".
//   3. Assert, through the API: the order is gone from the orders service, and every order that was
//      there before the run is still there, unchanged. The screen's own message is checked too, but
//      only the API can tell that the order is really cancelled, not just hidden from the page.
// The API calls carry the made-up API key from TIXLY_API_KEY, from Node only (support/global-setup.ts),
// so it never reaches the browser, a screenshot or a trace. ui-only.spec.ts does the same through
// the screen alone, for comparison.

test(
  "a buyer cancels an order (API-assisted: API setup, cancel on screen, API check)",
  { tag: ["@saved-orders", "@risk-high", "@writes-data", "@layer-mixed", "@fast", "@api-assisted"] },
  async ({ page, orders }) => {
    // The orders from before the run, as they are now, before this test changes anything: every one
    // global setup noted must still be there (so a save that wiped them would be caught below).
    const preexisting = new Set(JSON.parse(process.env.TIXLY_PREEXISTING_IDS ?? "[]") as string[]);
    const realBefore = (await orders.list()).filter((saved) => preexisting.has(saved.id));
    expect(realBefore.map((saved) => saved.id).sort(), "every order from before the run is there").toEqual([...preexisting].sort());

    // 1. Arrange, through the API: only the data this test needs.
    const order = await orders.create({ quantity: 2 });

    // 2. Act, through the screen: the one behavior under test.
    await page.goto("/orders");
    const cancel = page.getByRole("button", { name: `Cancel order for ${order.name}`, exact: true });
    await cancel.click();
    // What the buyer sees: the message, and the order gone from the list.
    await expect(page.getByText(`Order for ${order.name} cancelled.`, { exact: true })).toBeVisible();
    await expect(cancel).toHaveCount(0);
    await expect(page.getByRole("cell", { name: order.name, exact: true })).toHaveCount(0);

    // 3. Assert, through the API: really cancelled, and nothing else touched. One listing serves both
    // checks (asked again only while the cancellation hasn't shown up yet).
    let after: Awaited<ReturnType<typeof orders.list>> = [];
    await expect
      .poll(
        async () => {
          after = await orders.list();
          return after.some((saved) => saved.id === order.id);
        },
        { message: "the cancelled order is gone from the orders service" },
      )
      .toBe(false);
    const realAfter = after.filter((saved) => preexisting.has(saved.id));
    expect(realAfter, "every order from before the run is still there, unchanged").toEqual(realBefore);
  },
);
