import { writeFileSync } from "node:fs";
import { expect, test } from "@playwright/test";
import { OrderReviewScreen } from "./pages/models.ts";

// Evidence at the point a business rule is proved, and nowhere else (the success-evidence quest).
//
// The business rule: the review page's total is (ticket $25.00 + fee $2.50) x the number of tickets.
// For 6 Spring Concert tickets that is $165.00.
//
// Each check below is marked NAVIGATION (it only gets the test to the right place, and keeps no
// evidence) or PROOF (it proves the rule, and keeps one piece of evidence, captured right before the
// check, so a failing check still leaves the evidence of what was shown).
//
// The evidence goes into the test's own folder in test-results/ and is attached to the report:
//   - order-total.png: a picture of the order summary only (event, tickets, total), not the name box;
//   - order-total.txt: the rule, the values the check used, the value shown, and whether the rule held.
// The test never types a name, so no buyer's name can appear in the evidence.
//
// One exception, on purpose: when any check fails, navigation or proof, Playwright also keeps its own
// failure evidence (a screenshot of the whole page, a trace and error-context.md), as
// playwright.config.ts asks for every test. That is evidence for diagnosing a failure, not proof that
// a rule held, and a passing run keeps none of it.

const EVENT_ID = "spring-concert";
const QUANTITY = 6;
const TICKET_CENTS = 2500;
const FEE_CENTS = 250;
const dollars = (cents: number) => `$${(cents / 100).toFixed(2)}`;
// MM-DD-YYYY and a 12-hour time.
const when = (d: Date) =>
  `${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}-${d.getFullYear()} ` +
  d.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit", second: "2-digit" });

test(
  "the review page total for 6 tickets is (ticket + fee) x 6 = $165.00",
  {
    tag: ["@order-review", "@risk-high", "@read-only", "@layer-ui", "@fast"],
    annotation: [
      { type: "id", description: "T-11" },
      { type: "purpose", description: "The review page total for 6 tickets is $165.00: ($25.00 ticket + $2.50 fee) x 6." },
      { type: "source", description: "CHK-07" },
    ],
  },
  async ({ page }, testInfo) => {
    const review = new OrderReviewScreen(page);
    const expected = dollars((TICKET_CENTS + FEE_CENTS) * QUANTITY);
    const notCaptured: string[] = [];

    // NAVIGATION: open the review page from a link. No evidence: a page loading proves no rule.
    await review.openFromLink(EVENT_ID, String(QUANTITY));
    notCaptured.push("opening the review page (navigation)");

    // NAVIGATION: the right page is showing. No evidence.
    await expect(review.heading()).toBeVisible();
    notCaptured.push("the page heading (navigation)");

    // NAVIGATION: the summary is for the order the rule is applied to. No evidence of their own; the
    // values are written into the proof's text file, and they show in the proof's picture.
    await expect(review.eventName()).toHaveText("Spring Concert");
    await expect(review.ticketCount()).toHaveText(String(QUANTITY));
    notCaptured.push("the event name and ticket count (navigation: shown in the proof's picture)");

    // PROOF: the total follows the rule. Wait only until a total is shown (any value), then capture
    // the evidence, then check the value that was captured: the check and the evidence are about the
    // same value, so they can't disagree.
    const total = review.orderTotal();
    await expect(total).not.toBeEmpty();
    // The values as the page shows them, read at the moment of capture.
    const text = async (cell: typeof total) => ((await cell.textContent()) ?? "").trim();
    const shown = await text(total);
    const shownEvent = await text(review.eventName());
    const shownTickets = await text(review.ticketCount());
    const held = shown === expected;
    const picture = testInfo.outputPath("order-total.png");
    const values = testInfo.outputPath("order-total.txt");
    await review.summary().screenshot({ path: picture });
    // Read again after the picture: if the total changed while it was taken, the picture and the
    // values file might not show the same value, so the test stops (after saving them).
    const afterPicture = await text(total);
    writeFileSync(
      values,
      [
        "Rule: the order total is (ticket $25.00 + fee $2.50) x the number of tickets",
        `Event: ${shownEvent}`,
        `Tickets: ${shownTickets}`,
        `Expected total: ${expected}   ((${dollars(TICKET_CENTS)} + ${dollars(FEE_CENTS)}) x ${QUANTITY})`,
        `Shown total: ${shown}${afterPicture === shown ? "" : ` (changed to ${afterPicture} while the picture was taken)`}`,
        `Result: ${held ? "rule held" : "RULE BROKEN"}`,
        `Captured: ${when(new Date())}, right before the check`,
        "",
      ].join("\n"),
    );
    await testInfo.attach("proof: order summary", { path: picture, contentType: "image/png" });
    await testInfo.attach("proof: checked values", { path: values, contentType: "text/plain" });
    console.log(`Captured (proof): order total, shown ${shown}, expected ${expected} -> order-total.png, order-total.txt`);
    for (const step of notCaptured) console.log(`Not captured: ${step}`);
    expect(afterPicture, "the total stayed the same while the evidence was captured").toBe(shown);
    expect(shown, "the total captured in the evidence").toBe(expected);
  },
);
