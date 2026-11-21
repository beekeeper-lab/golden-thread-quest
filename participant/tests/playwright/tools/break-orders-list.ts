// Makes a BROKEN copy of the demo app, for the failure-evidence quest (criterion 1: "a failing test
// produces a trace, a screenshot, the console log, failed requests and the error text"). In the copy,
// the orders service answers the "Your orders" page's request for the list with a 500 (a server
// error), and the page writes an error to the browser console. The page then shows no orders, and a
// test waiting for an order's row fails with only a timeout: the cause is in the evidence, not in
// the error message.
//
// Only the page's own request breaks. Setup and cleanup ask for the list from Node with the API key
// (support/global-setup.ts, global-teardown.ts, orders-fixture.ts), and those keep working, so a run
// against the copy still cancels every order it created.
//
// Run it from participant/tests/playwright with an empty or new folder:
//   node tools/break-orders-list.ts <folder>
// It copies demo-app/ there (the pages, the server and the saved orders, but not a lock or a
// half-written file), changes one line in the copy's server.js and one in its orders.html, and
// prints each change. The real demo app is only read. Start the copy with its own port and the same
// API key, for example:
//   TIXLY_DEMO_PORT=4192 node <folder>/server.js
// then point the tests at it with TIXLY_BASE_URL=http://127.0.0.1:4192.

import { cpSync, existsSync, readdirSync, readFileSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";

const target = process.argv[2];
if (!target) {
  console.error("Usage: node tools/break-orders-list.ts <folder>   (an empty or new folder for the broken copy)");
  process.exit(2);
}
const folder = resolve(target);
const source = resolve(fileURLToPath(new URL("../demo-app", import.meta.url)));
if (folder === source || folder.startsWith(`${source}/`)) {
  console.error("The broken copy can't go inside the real demo-app folder.");
  process.exit(2);
}
if (existsSync(folder) && readdirSync(folder).length > 0) {
  console.error(`${folder} isn't empty; give a new or empty folder, so nothing there is overwritten.`);
  process.exit(2);
}

// The changes, per file. Each line must be found exactly once, so a later edit to the app can't
// make this silently change something else. Nothing is written until every change has been found.
const changes: { file: string; why: string; before: string; after: string }[] = [
  {
    file: "server.js",
    why: "the list fails with a 500 when the app's own page asks for it",
    before: `  if (path === "/api/orders" && request.method === "GET") return send(response, 200, readOrders());`,
    after:
      `  if (path === "/api/orders" && request.method === "GET" && fromOwnPage(request)) return send(response, 500, { error: "Something went wrong on our side. Please try again later." }); // BROKEN COPY\n` +
      `  if (path === "/api/orders" && request.method === "GET") return send(response, 200, readOrders());`,
  },
  {
    file: "orders.html",
    why: "the page writes the failure to the browser console",
    before: `          if (answer.ok && Array.isArray(result)) return result;`,
    after:
      `          if (answer.ok && Array.isArray(result)) return result;\n` +
      `          console.error(\`Loading orders failed: GET /api/orders answered \${answer.status}\`); // BROKEN COPY`,
  },
];

const edited = new Map<string, string>();
for (const { file, why, before, after } of changes) {
  const text = edited.get(file) ?? readFileSync(`${source}/${file}`, "utf8");
  const count = text.split(before).length - 1;
  if (count !== 1) {
    console.error(`Couldn't make the change "${why}": the line was found ${count} times in ${file}, not once.`);
    process.exit(1);
  }
  edited.set(file, text.replace(before, after));
}

cpSync(source, folder, {
  recursive: true,
  // Not a lock (the real app's, if it is running) or a half-written orders file.
  filter: (path) => !path.endsWith(".lock") && !path.endsWith(".tmp"),
});
for (const [file, text] of edited) writeFileSync(`${folder}/${file}`, text);

console.log(`Broken copy of the demo app in ${folder}. Changes:`);
for (const { file, why, before, after } of changes) {
  console.log(`  ${file}: ${why}:`);
  console.log(`    - ${before.trim()}`);
  for (const line of after.split("\n")) console.log(`    + ${line.trim()}`);
}
