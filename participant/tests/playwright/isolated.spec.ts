import { expect, test } from "./support/orders-fixture.ts";

// The ISOLATED version of coupled.spec.ts, for the data-isolation quest: the same two stories, but
// each test creates the order it needs, with a name no other test, run or tester can share, and
// the orders helper cancels exactly what the test created when it ends, whether it passed or
// failed. Neither test relies on the other, so they pass in any order and in parallel.
//
// Names look like "Test User qa-1a2b3c4d-5e6f7a8b": "qa-1a2b3c4d" marks this run, "5e6f7a8b" this order.

test(
  "a buyer saves an order and sees it in Your orders (isolated)",
  { tag: ["@saved-orders", "@risk-high", "@writes-data", "@layer-ui", "@fast", "@data-isolated"] },
  async ({ page, orders }) => {
    const name = orders.uniqueName();
    await page.goto("/review?event=spring-concert&quantity=2");
    const nameBox = page.getByLabel("Your name", { exact: true });
    const save = page.getByRole("button", { name: "Save order", exact: true });

    // A save the service turns down (a name of only spaces) leaves Save on, to correct and try again.
    await nameBox.fill("   ");
    await save.click();
    await expect(page.getByRole("status")).toHaveText("Give a name of 1 to 60 characters.");
    await expect(save).toBeEnabled();

    // A double-click on Save while the save is on its way sends it only once: the save is held
    // until both clicks are in.
    const saves: string[] = [];
    let letThrough = () => {};
    const held = new Promise<void>((resolve) => (letThrough = resolve));
    await page.route("**/api/orders", async (route) => {
      if (route.request().method() === "POST") {
        saves.push(route.request().postData() ?? "");
        await held;
      }
      await route.fallback();
    });
    await nameBox.fill(name);
    await save.dblclick();
    letThrough();
    // Note the saved order straight away, so it's cleaned up even if a check below fails. (It
    // waits for exactly one order with this name.)
    await orders.trackSavedBy(name);
    expect(saves).toHaveLength(1);
    await page.getByRole("link", { name: "See your orders", exact: true }).click();

    await expect(page.getByRole("button", { name: `Cancel order for ${name}`, exact: true })).toBeVisible();
    // The saved order is the one reviewed: 2 tickets, $55.00.
    const row = page.getByRole("row").filter({ has: page.getByRole("cell", { name, exact: true }) });
    await expect(row.getByRole("cell")).toHaveText([name, "Spring Concert", "2", "$55.00", "Cancel order"]);
  },
);

test(
  "a buyer cancels their own order (isolated: makes the order it cancels)",
  { tag: ["@saved-orders", "@risk-high", "@writes-data", "@layer-mixed", "@fast", "@data-isolated"] },
  async ({ page, orders }) => {
    // Setup through the orders service: this test is about cancelling, not saving.
    const order = await orders.create({ quantity: 1 });
    await page.goto("/orders");

    await page.getByRole("button", { name: `Cancel order for ${order.name}`, exact: true }).click();

    await expect(page.getByText(`Order for ${order.name} cancelled.`, { exact: true })).toBeVisible();
    await expect(page.getByRole("button", { name: `Cancel order for ${order.name}`, exact: true })).toHaveCount(0);
    // Really cancelled, not just hidden: the orders service no longer has it (checked before the
    // helper's own cleanup could remove it and hide the difference).
    await expect.poll(async () => (await orders.list()).some((saved) => saved.id === order.id)).toBe(false);
  },
);

test(
  "cancelling one buyer's order leaves another buyer's order in Your orders (isolated)",
  { tag: ["@saved-orders", "@risk-high", "@writes-data", "@layer-mixed", "@fast", "@data-isolated"] },
  async ({ page, orders }) => {
    // Two orders of its own: one to cancel, one that must survive.
    const toCancel = await orders.create({ quantity: 1 });
    const toKeep = await orders.create({ quantity: 3 });
    // This page sees only this test's two orders (the real list from the server, filtered), so the
    // order to keep sits right below the one to cancel however many other tests save at the same time.
    // The list comes through the orders helper (from Node, with the API key), not by re-sending the
    // page's own request: re-sent by Playwright, it would no longer count as the page's, and the key
    // must never be put on a request that belongs to the browser.
    await page.route("**/api/orders", async (route) => {
      if (route.request().method() !== "GET") return route.fallback();
      const all = await orders.list();
      await route.fulfill({ json: all.filter((order) => order.id === toCancel.id || order.id === toKeep.id) });
    });
    const cancellations: string[] = [];
    page.on("request", (request) => {
      if (request.method() === "DELETE") cancellations.push(request.url());
    });
    // The page's clock is frozen (the network isn't), so however slow this machine is, the second
    // click below always comes "straight after" the first as far as the page can tell.
    await page.clock.install();
    await page.goto("/orders");
    await page.clock.pauseAt(Date.now() + 60_000);

    // Click Cancel; once the list is rebuilt and the kept order's button has moved up into that spot,
    // click the same spot again, as a quick double-click would. It must not cancel the kept order.
    const cancel = page.getByRole("button", { name: `Cancel order for ${toCancel.name}`, exact: true });
    const keep = page.getByRole("button", { name: `Cancel order for ${toKeep.name}`, exact: true });
    const spot = await cancel.boundingBox();
    if (!spot) throw new Error("The Cancel button has no position on the page.");
    const middle = { x: spot.x + spot.width / 2, y: spot.y + spot.height / 2 };
    await page.mouse.click(middle.x, middle.y);
    await expect(cancel).toHaveCount(0);
    await expect.poll(async () => Math.abs(((await keep.boundingBox())?.y ?? -1000) - spot.y)).toBeLessThan(2);
    await page.mouse.click(middle.x, middle.y);
    // No second cancellation, then or after: wait until the page has no requests left in flight.
    await page.waitForLoadState("networkidle");

    expect(cancellations).toHaveLength(1);
    await expect(page.getByText(`Order for ${toCancel.name} cancelled.`, { exact: true })).toBeVisible();
    await expect(keep).toBeVisible();
    expect((await orders.list()).some((order) => order.id === toKeep.id)).toBe(true);
    expect((await orders.list()).some((order) => order.id === toCancel.id)).toBe(false);

    // A slower second click at the same spot, with the pointer never moved, doesn't cancel it either.
    await page.clock.runFor(1000);
    await page.mouse.click(middle.x, middle.y);
    await page.waitForLoadState("networkidle");
    expect(cancellations).toHaveLength(1);
    expect((await orders.list()).some((order) => order.id === toKeep.id)).toBe(true);

    // Once the pointer has moved away and been aimed at the kept order, Cancel works again: the
    // guard doesn't leave the page dead.
    await page.mouse.move(middle.x, middle.y + 100);
    await keep.click();
    await expect(page.getByText(`Order for ${toKeep.name} cancelled.`, { exact: true })).toBeVisible();
    await expect.poll(async () => (await orders.list()).some((order) => order.id === toKeep.id)).toBe(false);
  },
);
