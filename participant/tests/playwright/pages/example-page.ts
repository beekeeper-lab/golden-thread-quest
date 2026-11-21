import type { Locator, Page } from "@playwright/test";

/** A label used inside a regular expression, with its special characters made literal. */
function escapeRegExp(text: string): string {
  return text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

/**
 * The passport page: what a participant has credibly demonstrated.
 *
 * Interaction mechanics live here. The assertions stay in the test, so the business rule
 * being checked is readable there.
 */
export class PassportPage {
  readonly page: Page;
  /** The "Progress" section, labelled by its heading. */
  readonly progress: Locator;

  constructor(page: Page) {
    this.page = page;
    this.progress = page.getByRole("region", { name: "Progress" });
  }

  async open(): Promise<void> {
    await this.page.goto("/passport/");
  }

  /**
   * The value of one total in the Progress section, such as "Verified XP".
   *
   * Each total is a label (role "term") and a number (role "definition") with no named
   * group around them, so the pair is found by its visible text, the label followed by a
   * number, and the number is read by role inside it.
   */
  total(name: string): Locator {
    return this.progress
      .getByText(new RegExp(`^${escapeRegExp(name)}\\s*\\d+$`))
      .getByRole("definition");
  }

  /** The card for one region under "Capability by region". */
  regionCard(region: string): Locator {
    return this.page
      .getByRole("article")
      .filter({ has: this.page.getByRole("heading", { name: region, exact: true }) });
  }

  /** The line under a region's meter that shows claimed and verified counts side by side. */
  regionCounts(region: string): Locator {
    return this.regionCard(region).getByText(/^Claimed: \d+ · Verified quests: \d+$/);
  }

  /** The list of quest states on a region's card, such as "1 evidence ready". */
  regionStates(region: string): Locator {
    return this.regionCard(region).getByRole("list", { name: "Quest states in this region" });
  }
}
