import type { Locator, Page } from "@playwright/test";

// The Tixly "upcoming events" page, as a test sees it. Every way of finding something on the page
// lives here, by role and label (what a user or a screen reader would describe), so a change to
// the page's markup is fixed in one place. Assertions stay in the tests: this model only finds and
// does, it never decides whether the result is right.
export class UpcomingEventsPage {
  constructor(private readonly page: Page) {}

  async open(): Promise<void> {
    await this.page.goto("/");
  }

  // One event's card, found by the event's name.
  event(name: string): Locator {
    return this.page.getByRole("article", { name });
  }

  // Choose how many tickets to buy for an event.
  async chooseTicketQuantity(eventName: string, quantity: number): Promise<void> {
    await this.event(eventName).getByLabel("Number of tickets").selectOption(String(quantity));
  }

  // The order total the page shows for an event.
  orderTotal(eventName: string): Locator {
    return this.event(eventName).getByRole("status", { name: "Order total" });
  }
}
