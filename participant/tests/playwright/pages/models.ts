import type { Locator, Page } from "@playwright/test";

// Page models for the two Tixly demo screens: the events page and the order review page.
//
// Every way of finding something on a screen lives here, by role, label or visible text (what a
// user or a screen reader would describe), so a change to a screen is fixed in this one file and
// no test has to change. Names are matched exactly, so a renamed control (even "Continue to review
// later") is noticed rather than quietly matched. Methods are named for what a user does or reads
// (chooseTickets, reviewOrder, orderTotal), not for the element they touch. There are no
// assertions here: the models find and do, and the tests decide whether the result is right.

// The events page (/): one card per event, with a ticket quantity, a running total and a
// "Continue to review" button.
export class EventsScreen {
  constructor(private readonly page: Page) {}

  async open(): Promise<void> {
    await this.page.goto("/");
  }

  // The site's name at the top of the page.
  siteName(): Locator {
    return this.page.getByRole("heading", { level: 1, name: "Tixly", exact: true });
  }

  // One event's card, found by the event's name.
  event(name: string): Locator {
    return this.page.getByRole("article", { name, exact: true });
  }

  // The line on an event's card giving the ticket price ("Tickets from ...").
  ticketPrice(eventName: string): Locator {
    return this.event(eventName).getByText(/^Tickets from /);
  }

  // The line on an event's card giving the service fee ("Service fee: ...").
  serviceFee(eventName: string): Locator {
    return this.event(eventName).getByText(/^Service fee: /);
  }

  // The number of tickets chosen on an event's card.
  ticketQuantity(eventName: string): Locator {
    return this.event(eventName).getByLabel("Number of tickets", { exact: true });
  }

  // The running total on an event's card.
  orderTotal(eventName: string): Locator {
    return this.event(eventName).getByRole("status", { name: "Order total", exact: true });
  }

  async chooseTickets(eventName: string, quantity: number): Promise<void> {
    await this.ticketQuantity(eventName).selectOption(String(quantity));
  }

  // Go on to the review screen for the tickets chosen on an event's card.
  async reviewOrder(eventName: string): Promise<void> {
    await this.event(eventName).getByRole("button", { name: "Continue to review", exact: true }).click();
  }

  // Choose tickets and go straight to the review screen, the most common path through this page.
  async chooseTicketsAndReview(eventName: string, quantity: number): Promise<OrderReviewScreen> {
    await this.chooseTickets(eventName, quantity);
    await this.reviewOrder(eventName);
    return new OrderReviewScreen(this.page);
  }
}

// The order review page (/review): what the buyer is about to order, before paying.
export class OrderReviewScreen {
  constructor(private readonly page: Page) {}

  // Open the review screen straight from an address, as a buyer would by following a saved or
  // shared link. The event is given by its id in the address (for example "spring-concert") and
  // the quantity as typed, so a test can try a quantity the events page would never offer.
  async openFromLink(eventId: string, quantity: string): Promise<void> {
    const query = new URLSearchParams({ event: eventId, quantity });
    await this.page.goto(`/review?${query}`);
  }

  heading(): Locator {
    return this.page.getByRole("heading", { name: "Review your order", exact: true });
  }

  // One line of the order summary, found by its row heading ("Event", "Tickets" or "Total").
  private summaryValue(rowHeading: string): Locator {
    return this.page
      .getByRole("table", { name: "Order summary", exact: true })
      .getByRole("row")
      .filter({ has: this.page.getByRole("rowheader", { name: rowHeading, exact: true }) })
      .getByRole("cell");
  }

  eventName(): Locator {
    return this.summaryValue("Event");
  }

  ticketCount(): Locator {
    return this.summaryValue("Tickets");
  }

  orderTotal(): Locator {
    return this.summaryValue("Total");
  }

  // The message shown instead of a total when the order can't be reviewed.
  problem(): Locator {
    return this.page.getByRole("alert");
  }

  // Back to the events page by the page's own link.
  async backToEvents(): Promise<EventsScreen> {
    await this.page.getByRole("link", { name: "Back to events", exact: true }).click();
    return new EventsScreen(this.page);
  }

  // Back to the events page with the browser's Back button, as many buyers do.
  async goBackInBrowser(): Promise<EventsScreen> {
    await this.page.goBack();
    return new EventsScreen(this.page);
  }
}
