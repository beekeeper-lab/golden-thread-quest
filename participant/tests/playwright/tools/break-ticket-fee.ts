// Makes a BROKEN copy of the demo app, for the success-evidence quest (criterion 5: "breaking the
// rule changes the evidence or fails the assertion"). In the copy, the review page leaves the $2.50
// fee out of its total, so 6 Spring Concert tickets show $150.00 instead of $165.00. Nothing else
// changes: the page still loads, shows the event and the ticket count, and a total that looks
// normal. Only the business rule is broken.
//
// Run it from participant/tests/playwright with an empty or new folder:
//   node tools/break-ticket-fee.ts <folder>
// It copies demo-app/ there (the pages, the server and the saved orders, but not a lock or a
// half-written file), changes one line in the copy's review.html and prints the change. The real
// demo app is only read. Start the copy with its own port and the same API key, for example:
//   TIXLY_DEMO_PORT=4193 node <folder>/server.js
// then point the tests at it with TIXLY_BASE_URL=http://127.0.0.1:4193.
// Its messages never print a folder's full path (it can show the user name), and a failure is
// reported by its error code only. Exit 0 when the copy is made, 1 when the line to change isn't
// found exactly once, 2 for anything else.

import { cpSync, existsSync, readdirSync, readFileSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";

const target = process.argv[2];
if (!target) {
  console.error("Usage: node tools/break-ticket-fee.ts <folder>   (an empty or new folder for the broken copy)");
  process.exit(2);
}
const folder = resolve(target);
const source = resolve(fileURLToPath(new URL("../demo-app", import.meta.url)));
if (folder === source || folder.startsWith(`${source}/`)) {
  console.error("The broken copy can't go inside the real demo-app folder.");
  process.exit(2);
}

// The change. The line must be found exactly once, so a later edit to the app can't make this
// silently change something else. Nothing is written until it has been found.
const file = "review.html";
const why = "the total leaves out the fee";
const before = `        const cents = quantity * (event.ticketCents + event.feeCents);`;
const after = `        const cents = quantity * event.ticketCents; // BROKEN COPY: the fee is left out`;

try {
  if (existsSync(folder) && readdirSync(folder).length > 0) {
    console.error("The folder given isn't empty; give a new or empty folder, so nothing there is overwritten.");
    process.exit(2);
  }
  const text = readFileSync(`${source}/${file}`, "utf8");
  const count = text.split(before).length - 1;
  if (count !== 1) {
    console.error(`Couldn't make the change "${why}": the line was found ${count} times in ${file}, not once.`);
    process.exit(1);
  }
  cpSync(source, folder, {
    recursive: true,
    // Not a lock (the real app's, if it is running) or a half-written orders file.
    filter: (path) => !path.endsWith(".lock") && !path.endsWith(".tmp"),
  });
  writeFileSync(`${folder}/${file}`, text.replace(before, after));
} catch (error) {
  console.error(`Couldn't make the broken copy in the folder given (${(error as { code?: unknown })?.code ?? "an unexpected error"}).`);
  process.exit(2);
}

console.log("Broken copy of the demo app made in the folder given. Change:");
console.log(`  ${file}: ${why}:`);
console.log(`    - ${before.trim()}`);
console.log(`    + ${after.trim()}`);
