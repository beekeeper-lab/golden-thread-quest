import { expect, test } from "./support/orders-fixture.ts";

// Proof, for the data-isolation quest, that cleanup still happens when a test FAILS halfway. Both
// tests here fail on purpose, after they have saved an order, so they are skipped in normal runs;
// they only run with TIXLY_CLEANUP_PROOF=1, when the evidence is recorded:
//   TIXLY_CLEANUP_PROOF=1 npx playwright test cleanup-proof.spec.ts
// Expected: both tests fail; afterwards no order from this run is left, and the run-end safety net
// reports that it cancelled exactly one order (the one from the second test).

test.skip(process.env.TIXLY_CLEANUP_PROOF !== "1", "Fails on purpose; run with TIXLY_CLEANUP_PROOF=1");

test(
  "proof 1: a test that fails after creating its order still has it cancelled by its cleanup",
  { tag: ["@saved-orders", "@risk-low", "@writes-data", "@layer-api", "@fast"] },
  async ({ orders }) => {
    const order = await orders.create();
    console.log(`proof 1 created ${order.id} (${order.name}), then fails on purpose`);

    expect("the check this test was written to make", "deliberate failure").toBe("a different result");
  },
);

test(
  "proof 2: an order the test never got to note is cancelled by the run-end safety net",
  { tag: ["@saved-orders", "@risk-low", "@writes-data", "@layer-ui", "@fast"] },
  async ({ page, orders }) => {
    const name = orders.uniqueName();
    await page.goto("/review?event=spring-concert&quantity=1");
    await page.getByLabel("Your name", { exact: true }).fill(name);
    await page.getByRole("button", { name: "Save order", exact: true }).click();
    await expect(page.getByText(`Order saved for ${name}.`)).toBeVisible();
    console.log(`proof 2 saved an order for ${name} through the screen, then fails before noting it`);

    // As if the test crashed at the worst moment: the order is saved, but the cleanup list never hears
    // of it (orders.trackSavedBy is not called), so only the run marker in its name can find it.
    throw new Error("deliberate failure before the saved order was noted");
  },
);
