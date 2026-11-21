# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: orders-list.evidence.ts >> a saved order shows on Your orders
- Location: evidence-tests/orders-list.evidence.ts:12:1

# Error details

```
Error: expect(locator).toBeVisible() failed

Locator: getByRole('cell', { name: 'Test User qa-a155b3a3-c782824f', exact: true })
Expected: visible
Timeout: 5000ms
Error: element(s) not found

Call log:
  - Expect "toBeVisible" getByRole('cell', { name: 'Test User qa-a155b3a3-c782824f', exact: true }) with timeout 5000ms
  - waiting for getByRole('cell', { name: 'Test User qa-a155b3a3-c782824f', exact: true })

```

```yaml
- banner:
  - heading "Tixly" [level=1]
- main:
  - heading "Your orders" [level=2]
  - table "Saved orders":
    - rowgroup:
      - row "Name Event Tickets Total Actions":
        - columnheader "Name"
        - columnheader "Event"
        - columnheader "Tickets"
        - columnheader "Total"
        - columnheader "Actions"
    - rowgroup
  - status: Something went wrong on our side. Please try again later.
  - paragraph:
    - link "Back to events":
      - /url: /
```

# Test source

```ts
  1  | import { expect, test } from "../support/evidence-fixture.ts";
  2  | 
  3  | // The failure-evidence quest's test: a buyer's saved order shows on "Your orders". The order is made
  4  | // through the orders service (quick setup, cancelled again afterwards by the orders helper), then the
  5  | // page must show its row.
  6  | // Against the real demo app it passes and leaves nothing behind. Against the broken copy
  7  | // (tools/break-orders-list.ts) the page's request for the list fails with a 500, no row appears and
  8  | // the test fails with only a timeout; the bundle (evidence.config.ts) has to explain why.
  9  | // It is named *.evidence.ts, not *.spec.ts, so only evidence.config.ts runs it. The main suite and its
  10 | // selections (context/playwright/selections.md) stay as they were.
  11 | 
  12 | test(
  13 |   "a saved order shows on Your orders",
  14 |   { tag: ["@saved-orders", "@risk-medium", "@writes-data", "@layer-mixed", "@fast"] },
  15 |   async ({ page, orders }) => {
  16 |     const order = await orders.create({ quantity: 2 });
  17 |     await page.goto("/orders");
> 18 |     await expect(page.getByRole("cell", { name: order.name, exact: true })).toBeVisible();
     |                                                                             ^ Error: expect(locator).toBeVisible() failed
  19 |   },
  20 | );
  21 | 
```