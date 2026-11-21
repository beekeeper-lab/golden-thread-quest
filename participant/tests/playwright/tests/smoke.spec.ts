import { expect, test } from "@playwright/test";
import { EventsScreen } from "../pages/models.ts";

// The smoke test: the one check that proves the project is set up and can reach the app. It finds
// everything through the events page's model (pages/models.ts), so it holds no selector of its own.
test(
  "a visitor sees the Spring Concert and its ticket price on the Tixly home page",
  {
    tag: ["@events", "@risk-high", "@read-only", "@layer-ui", "@fast"],
    annotation: [
      { type: "id", description: "T-27" },
      { type: "purpose", description: "The events page shows the Spring Concert with its $25.00 ticket price and its $2.50 per-ticket fee; CHK-09 asks for the fee on the payment page, which the app doesn't have yet." },
      { type: "source", description: "CHK-09" },
      { type: "value", description: "medium: covers CHK-09 only on the events page, not the payment page it names" },
    ],
  },
  async ({ page }) => {
    const events = new EventsScreen(page);
    await events.open();
    await expect(events.siteName()).toBeVisible();
    await expect(events.ticketPrice("Spring Concert")).toBeVisible();
    await expect(events.ticketPrice("Spring Concert")).toHaveText("Tickets from $25.00");
    await expect(events.serviceFee("Spring Concert")).toBeVisible();
    await expect(events.serviceFee("Spring Concert")).toHaveText("Service fee: $2.50 per ticket");
  },
);
