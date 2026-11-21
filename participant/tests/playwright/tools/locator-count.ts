// Counts how many of each test's locators still find the right thing on a page, for the
// stable-locators quest (its stretch goal: "count how many locators each approach needs to change").
//
// A test stops at its first failure, so a failing run shows only ONE broken locator. This tries all
// ten (the five in brittle.spec.ts and the five in stable.spec.ts) on one page and reports, for
// each, whether it finds exactly one element and whether that element is the right one: the
// Spring Concert's card, ticket dropdown, price line, fee line or order total. "Right" is judged by
// the role and name a screen reader announces, the element's own words and whether it is visible,
// so a harmless change to how the page is built isn't counted as a broken locator.
//
// The locators below are copied from the two test files; the script first checks that each one's
// whole line still appears there exactly, so the count can't silently drift from the tests.
//
// Run it from participant/tests/playwright against a demo app that is already running:
//   node tools/locator-count.ts http://127.0.0.1:4173   (the original page)
//   node tools/locator-count.ts http://127.0.0.1:4199   (the redesigned copy)
// It only reads the page, and refuses any address that isn't on this computer.

import { readFileSync } from "node:fs";
import { chromium, type Locator, type Page } from "@playwright/test";

const address = process.argv[2] ?? "";
let host = "";
try {
  host = new URL(address).hostname;
} catch {
  // reported below
}
// The demo app only listens on 127.0.0.1, so only that address (or localhost) is accepted.
if (!["127.0.0.1", "localhost"].includes(host)) {
  console.error(`Give the address of a demo app on this computer, such as http://127.0.0.1:4173 (got "${address}")`);
  process.exit(2);
}

type Target = "card" | "dropdown" | "price" | "fee" | "total";

type Entry = { test: string; target: Target; kind: string; source: string; find: (page: Page) => Locator };

const brittleCard = (page: Page) => page.locator("main > article:nth-child(1)");
const stableCard = (page: Page) => page.getByRole("article", { name: "Spring Concert", exact: true });

const entries: Entry[] = [
  { test: "brittle.spec.ts", target: "card", kind: "position among siblings", source: `const card = page.locator("main > article:nth-child(1)");`, find: brittleCard },
  { test: "brittle.spec.ts", target: "dropdown", kind: "generated ID", source: `const quantity = page.locator("#r-7f3k2");`, find: (p) => p.locator("#r-7f3k2") },
  { test: "brittle.spec.ts", target: "price", kind: "index in a list", source: `const ticketPrice = card.locator("p").nth(1);`, find: (p) => brittleCard(p).locator("p").nth(1) },
  { test: "brittle.spec.ts", target: "fee", kind: "generated class name", source: `const serviceFee = page.locator(".css-q81zk");`, find: (p) => p.locator(".css-q81zk") },
  { test: "brittle.spec.ts", target: "total", kind: "long DOM path", source: `const orderTotal = page.locator("main > article > form > p");`, find: (p) => p.locator("main > article > form > p") },
  { test: "stable.spec.ts", target: "card", kind: "role + name", source: `const card = page.getByRole("article", { name: "Spring Concert", exact: true });`, find: stableCard },
  { test: "stable.spec.ts", target: "dropdown", kind: "label", source: `const quantity = card.getByLabel("Number of tickets", { exact: true });`, find: (p) => stableCard(p).getByLabel("Number of tickets", { exact: true }) },
  { test: "stable.spec.ts", target: "price", kind: "visible text", source: `const ticketPrice = card.getByText(/^Tickets from /);`, find: (p) => stableCard(p).getByText(/^Tickets from /) },
  { test: "stable.spec.ts", target: "fee", kind: "visible text", source: `const serviceFee = card.getByText(/^Service fee: /);`, find: (p) => stableCard(p).getByText(/^Service fee: /) },
  { test: "stable.spec.ts", target: "total", kind: "role + hidden label", source: `const orderTotal = card.getByRole("status", { name: "Order total", exact: true });`, find: (p) => stableCard(p).getByRole("status", { name: "Order total", exact: true }) },
];

// The copies must match the tests: each locator's whole line, exactly, so even something added
// to the end of a line in a test (such as ".nth(1)") stops the count until this script matches.
for (const entry of entries) {
  const testLines = readFileSync(new URL(`../${entry.test}`, import.meta.url), "utf8").split("\n").map((line) => line.trim());
  if (!testLines.includes(entry.source)) {
    console.error(`${entry.test} no longer has this exact line (update this script to match the test):\n  ${entry.source}`);
    process.exit(2);
  }
}

// The same guard as playwright.config.ts: every request except to this computer goes to a proxy
// that doesn't exist, so the page can't load anything from the internet.
const browser = await chromium.launch({
  proxy: { server: "http://127.0.0.1:9", bypass: "<-loopback>,localhost,127.0.0.1,[::1]" },
});
try {
  const page = await browser.newPage();
  try {
    await page.goto(address);
  } catch {
    console.error(`Couldn't open ${address}. Is the demo app running there? (See the README.)`);
    await browser.close();
    process.exit(2);
  }
  const found: Record<string, number> = {};
  // Every card the browser announces as an article named "Spring Concert", found by role alone.
  const springConcertCards: Locator[] = [];
  for (const article of await page.getByRole("article").all()) {
    if (/^- article "Spring Concert"/.test((await article.ariaSnapshot()).split("\n")[0] ?? "")) {
      springConcertCards.push(article);
    }
  }
  console.log(`Page: ${address}`);
  for (const entry of entries) {
    const locator = entry.find(page);
    const count = await locator.count();
    let result: string;
    if (count === 0) {
      result = "BROKEN: finds nothing";
    } else if (count > 1) {
      result = `BROKEN: finds ${count} elements`;
    } else {
      // The right thing is judged by the browser's accessibility view: the role, name and text a
      // screen reader would announce, not particular tags. The element must sit inside the
      // Spring Concert's card, and announce itself as:
      //   card     an article named "Spring Concert"
      //   dropdown a drop-down or open list named "Number of tickets" (however it is labeled)
      //   price    the text "Tickets from $25.00"; fee: the text "Service fee: $2.50 per ticket"
      //   total    a status message reading "Total: ..." (its hidden name isn't needed, so the check
      //            doesn't rely on the developer's label)
      // Text in this view is already spaced the way it reads on screen.
      // The role and name come from the first line of the accessibility view, such as
      // - combobox "Number of tickets"; the text is the element's own words, spaced as on screen
      // but ignoring styling (such as capitals added by CSS), as the tests' text checks do.
      const announced = (await locator.ariaSnapshot()).split("\n")[0] ?? "";
      const text = ((await locator.textContent()) ?? "").replace(/\s+/g, " ").trim();
      const visible = await locator.isVisible();
      const rightKind =
        entry.target === "card" ? /^- article "Spring Concert"/.test(announced)
        : entry.target === "dropdown" ? /^- (combobox|listbox) "Number of tickets"/.test(announced)
        : entry.target === "price" ? text === "Tickets from $25.00"
        : entry.target === "fee" ? text === "Service fee: $2.50 per ticket"
        : /^- status\b/.test(announced) && text.startsWith("Total: $");
      const element = await locator.elementHandle();
      let inSpringConcert = false;
      for (const card of springConcertCards) {
        if (await card.evaluate((c, el) => c.contains(el as Node), element)) inSpringConcert = true;
      }
      // A buyer has to be able to see it, as the tests require.
      const right = visible && rightKind && inSpringConcert;
      result = right ? "ok: finds the right thing" : "BROKEN: finds the wrong thing";
    }
    if (result.startsWith("ok")) found[entry.test] = (found[entry.test] ?? 0) + 1;
    console.log(`  ${entry.test.padEnd(16)} ${entry.target.padEnd(9)} ${entry.kind.padEnd(24)} ${result}`);
  }
  for (const test of ["brittle.spec.ts", "stable.spec.ts"]) {
    console.log(`${test}: ${found[test] ?? 0} of 5 locators still find the right thing`);
  }
} finally {
  await browser.close();
}
