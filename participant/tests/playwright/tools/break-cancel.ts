// Makes a BROKEN copy of the demo app, for the API-assisted test quest (criterion 5: "breaking the
// UI behavior makes the API-assisted test fail"). In the copy, Cancel on "Your orders" only
// pretends: it says "Order for <name> cancelled." and takes the row off the page, but never asks the
// orders service to cancel anything, so the order is still saved. The screen looks right; only a
// check through the orders service can tell.
//
// Run it from participant/tests/playwright with an empty or new folder:
//   node tools/break-cancel.ts <folder>
// It copies demo-app/ there (the pages, the server and the saved orders, but not a lock or a
// half-written file), changes three lines in the copy's orders.html, and prints each change. The
// real demo app is only read. Start the copy with its own port and the same API key, for example:
//   TIXLY_DEMO_PORT=4191 node <folder>/server.js
// then point the tests at it with TIXLY_BASE_URL=http://127.0.0.1:4191.

import { cpSync, existsSync, readdirSync, readFileSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";

const target = process.argv[2];
if (!target) {
  console.error("Usage: node tools/break-cancel.ts <folder>   (an empty or new folder for the broken copy)");
  process.exit(2);
}
const folder = resolve(target);
const source = fileURLToPath(new URL("../demo-app", import.meta.url));
if (folder === resolve(source) || folder.startsWith(`${resolve(source)}/`)) {
  console.error("The broken copy can't go inside the real demo-app folder.");
  process.exit(2);
}
if (existsSync(folder) && readdirSync(folder).length > 0) {
  console.error(`${folder} isn't empty; give a new or empty folder, so nothing there is overwritten.`);
  process.exit(2);
}

cpSync(source, folder, {
  recursive: true,
  // Not a lock (the real app's, if it is running) or a half-written orders file.
  filter: (path) => !path.endsWith(".lock") && !path.endsWith(".tmp"),
});

// The three changes, each found exactly once (so a later edit to the page can't make this silently
// break something else).
const changes: [string, string, string][] = [
  [
    "remember which orders were 'cancelled'",
    `      const list = document.getElementById("orders");`,
    `      const list = document.getElementById("orders");\n      const pretendCancelled = new Set(); // BROKEN COPY`,
  ],
  [
    "Cancel sends nothing and reports success",
    "          const answer = await fetch(`/api/orders/${encodeURIComponent(order.id)}`, { method: \"DELETE\" });",
    "          const answer = { ok: true, status: 200 }; pretendCancelled.add(order.id); // BROKEN COPY: nothing is sent",
  ],
  [
    "the list hides the 'cancelled' orders",
    "        const orders = await loadOrders();",
    "        const orders = (await loadOrders())?.filter((saved) => !pretendCancelled.has(saved.id)) ?? null; // BROKEN COPY",
  ],
];
const page = `${folder}/orders.html`;
let text = readFileSync(page, "utf8");
for (const [why, before, after] of changes) {
  const count = text.split(before).length - 1;
  if (count !== 1) {
    console.error(`Couldn't make the change "${why}": the line was found ${count} times in orders.html, not once.`);
    process.exit(1);
  }
  text = text.replace(before, after);
}
writeFileSync(page, text);

console.log(`Broken copy of the demo app in ${folder}. Changes to its orders.html:`);
for (const [why, before, after] of changes) {
  console.log(`  ${why}:`);
  console.log(`    - ${before.trim()}`);
  for (const line of after.split("\n")) console.log(`    + ${line.trim()}`);
}
