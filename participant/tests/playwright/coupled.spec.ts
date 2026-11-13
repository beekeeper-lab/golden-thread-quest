import { expect, test } from "@playwright/test";

// A deliberately COUPLED pair of tests, for the data-isolation quest: the second test only works
// if the first one has already run, because it cancels the order the first one saved instead of
// making its own. In this order both pass. Reversed, the second test finds nothing to cancel and
// fails; and if the first runs without the second, its order is left behind in the saved orders.
// Compare isolated.spec.ts, where each test makes, uses and removes its own data.
//
// Both use a fixed buyer name, "Test User", so two people running these at once would also trip
// over each other's orders.
//
// Because they can leave a real "Test User" order behind, they are skipped in normal runs and only
// run when asked, with TIXLY_COUPLED=1 (for example when recording the evidence):
//   TIXLY_COUPLED=1 node tools/run-in-order.ts reversed coupled.spec.ts

test.skip(process.env.TIXLY_COUPLED !== "1", "Coupled on purpose and can leave data behind; run with TIXLY_COUPLED=1");

test(
  "a buyer saves an order for Test User and sees it in Your orders (coupled)",
  { tag: ["@saved-orders", "@risk-high", "@writes-data", "@layer-ui", "@fast", "@data-coupled"] },
  async ({ page }) => {
    await page.goto("/review?event=spring-concert&quantity=2");
    await page.getByLabel("Your name", { exact: true }).fill("Test User");
    await page.getByRole("button", { name: "Save order", exact: true }).click();
    await page.getByRole("link", { name: "See your orders", exact: true }).click();

    await expect(page.getByRole("button", { name: "Cancel order for Test User", exact: true })).toBeVisible();
    // No cleanup: the next test relies on this order still being here.
  },
);

test(
  "a buyer cancels Test User's order (coupled: relies on the order the test above saved)",
  { tag: ["@saved-orders", "@risk-high", "@writes-data", "@layer-ui", "@fast", "@data-coupled"] },
  async ({ page }) => {
    await page.goto("/orders");

    await page.getByRole("button", { name: "Cancel order for Test User", exact: true }).click();

    await expect(page.getByText("Order for Test User cancelled.", { exact: true })).toBeVisible();
    await expect(page.getByRole("button", { name: "Cancel order for Test User", exact: true })).toHaveCount(0);
  },
);
