import { expect, test } from "../support/evidence-fixture.ts";

// The failure-evidence quest's test: a buyer's saved order shows on "Your orders". The order is made
// through the orders service (quick setup, cancelled again afterwards by the orders helper), then the
// page must show its row.
// Against the real demo app it passes and leaves nothing behind. Against the broken copy
// (tools/break-orders-list.ts) the page's request for the list fails with a 500, no row appears and
// the test fails with only a timeout; the bundle (evidence.config.ts) has to explain why.
// It is named *.evidence.ts, not *.spec.ts, so only evidence.config.ts runs it. The main suite and its
// selections (context/playwright/selections.md) stay as they were.

test(
  "a saved order shows on Your orders",
  {
    tag: ["@saved-orders", "@risk-medium", "@writes-data", "@layer-mixed", "@fast"],
    annotation: [
      { type: "id", description: "T-29" },
      { type: "purpose", description: "A saved order appears on Your orders." },
      { type: "source", description: "none: saving orders isn't in the requirements yet" },
      { type: "value", description: "low: same check as T-08; runs only with the evidence settings, to show failure evidence" },
    ],
  },
  async ({ page, orders }) => {
    const order = await orders.create({ quantity: 2 });
    await page.goto("/orders");
    await expect(page.getByRole("cell", { name: order.name, exact: true })).toBeVisible();
  },
);
