import { expect, test } from "./support/orders-fixture.ts";

// The UI-ONLY version of "a buyer cancels an order", for comparison with api-assisted.spec.ts in the
// API-assisted test quest. Everything a buyer would do, through the screen alone, and the result
// checked only by what the screen shows:
//   events page -> 2 Spring Concert tickets -> review page -> a unique name -> Save order ->
//   See your orders -> Cancel order for <name> -> the "cancelled" message, and the row is gone.
// Only the screen is trusted here, so a page that says "cancelled" without cancelling would pass
// (the API-assisted version catches that). Behind the scenes, the orders helper notes the saved
// order by its unique name, so it is cleaned up even if the test fails partway; that is
// housekeeping, not part of what is tested.

test(
  "a buyer cancels an order (UI-only: saved and cancelled through the screen)",
  { tag: ["@saved-orders", "@risk-high", "@writes-data", "@layer-ui", "@fast", "@ui-only"] },
  async ({ page, orders }) => {
    const name = orders.uniqueName();

    // Setup, through the screen: the buyer's whole walk to a saved order.
    await page.goto("/");
    const card = page.getByRole("article", { name: "Spring Concert", exact: true });
    await card.getByLabel("Number of tickets", { exact: true }).selectOption("2");
    await card.getByRole("button", { name: "Continue to review", exact: true }).click();
    await page.getByLabel("Your name", { exact: true }).fill(name);
    await page.getByRole("button", { name: "Save order", exact: true }).click();
    // The save message and its "See your orders" link share one line, so the line is checked by its
    // role (the page's status line) rather than as exact text.
    await expect(page.getByRole("status")).toContainText(`Order saved for ${name}.`);
    // Housekeeping: note it for cleanup straight away.
    await orders.trackSavedBy(name);
    await page.getByRole("link", { name: "See your orders", exact: true }).click();

    // The behavior under test, through the screen.
    const cancel = page.getByRole("button", { name: `Cancel order for ${name}`, exact: true });
    await cancel.click();

    // The result, as the screen shows it (and only that).
    await expect(page.getByText(`Order for ${name} cancelled.`, { exact: true })).toBeVisible();
    await expect(cancel).toHaveCount(0);
    await expect(page.getByRole("cell", { name, exact: true })).toHaveCount(0);
  },
);
