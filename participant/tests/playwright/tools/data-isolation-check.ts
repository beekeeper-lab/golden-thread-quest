// The data-isolation check, for the data-isolation quest: proves that test runs leave no data behind
// and never change or remove data that was there before. It reads the saved orders file directly
// (demo-app/data/orders.json), so it works whether or not the demo app is running.
//
//   node tools/data-isolation-check.ts before   takes a fingerprint of every order there now (the
//                                              "real" orders) and keeps it in the computer's
//                                              temporary folder (not test-results/, which Playwright
//                                              empties at the start of every run), under a name
//                                              made from this orders file's location, so another
//                                              copy of the project keeps its own
//   ...run the tests...
//   node tools/data-isolation-check.ts after    compares with that fingerprint and reports:
//     1. leftovers: any order that wasn't there before, any second copy of an order (the same id
//        twice), or any name carrying a test-run marker ("qa-" and eight hex digits, as the isolated
//        tests use)
//     2. real orders: each order from before still there with exactly the same content (each
//        order's fields are compared, not the file's layout, which the app rewrites in its own way)
//   and ends with PASS (exit 0) or FAIL (exit 1).
//
// Both take --orders-file <path> to check another orders file instead (for example a scratch copy
// of the demo app), and the fingerprint is kept per file. One check session at a time: "before" won't
// replace a fingerprint whose session hasn't passed yet (add --replace if that session was
// abandoned); an "after" that passes ends the session, one that fails keeps it open so the leftovers
// can be cleaned up and "after" run again.

import { createHash } from "node:crypto";
import { existsSync, readFileSync, realpathSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { pathToFileURL } from "node:url";

type Order = { id: string; name: string; event: string; quantity: number };

const fileFlag = process.argv.indexOf("--orders-file");
if (fileFlag !== -1 && !process.argv[fileFlag + 1]) {
  console.error("--orders-file needs the path of an orders file.");
  process.exit(2);
}
const ordersFile =
  fileFlag === -1 ? new URL("../demo-app/data/orders.json", import.meta.url) : pathToFileURL(resolve(process.argv[fileFlag + 1] ?? ""));
// The session is named after the file's real location (links followed), so two spellings of the
// same file, such as a symbolic link to it, share one session.
const sessionKey = existsSync(ordersFile) ? realpathSync(ordersFile) : ordersFile.pathname;
const fingerprintFile = join(
  tmpdir(),
  `tixly-data-isolation-before-${createHash("sha256").update(sessionKey).digest("hex").slice(0, 12)}.json`,
);
const runMarker = /\bqa-[0-9a-f]{8}-/;

// Each order's fields, in name order, so a file whose keys were only reordered (by a formatter,
// say) still matches; every field is kept, so any changed value doesn't.
const fingerprint = (order: Order) =>
  createHash("sha256")
    .update(JSON.stringify(Object.entries(order).sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0))))
    .digest("hex");
const readOrders = () => JSON.parse(readFileSync(ordersFile, "utf8")) as Order[];
const describe = (order: Order) =>
  `${order.id} "${order.name}" (${order.event}, ${order.quantity} ticket${order.quantity === 1 ? "" : "s"})`;

const step = process.argv[2];
if (step === "before") {
  if (existsSync(fingerprintFile) && !process.argv.includes("--replace")) {
    console.error('A check session is already active for this orders file (its "after" hasn\'t passed yet). Run "after" first, or add --replace to start again.');
    process.exit(2);
  }
  const orders = readOrders();
  if (new Set(orders.map((order) => order.id)).size !== orders.length) {
    console.error("Before: some order ids appear more than once; sort the orders file out first.");
    process.exit(2);
  }
  const marked = orders.filter((order) => runMarker.test(order.name));
  if (marked.length > 0) {
    // Test data left by an earlier run would otherwise be fingerprinted as data to keep.
    console.error(`Before: ${marked.length} order(s) left by an earlier test run; clear them first (Your orders page):`);
    for (const order of marked) console.error(`  ${describe(order)}`);
    process.exit(2);
  }
  // Created in one step that fails if a fingerprint already exists (unless --replace), so two
  // "before" commands at the same moment can't both start a session.
  try {
    writeFileSync(fingerprintFile, JSON.stringify(orders.map((order) => ({ id: order.id, sha256: fingerprint(order) })), null, 2),
      { flag: process.argv.includes("--replace") ? "w" : "wx" });
  } catch (problem) {
    if ((problem as NodeJS.ErrnoException).code === "EEXIST") {
      console.error('A check session is already active for this orders file (its "after" hasn\'t passed yet). Run "after" first, or add --replace to start again.');
    } else {
      console.error(`Couldn't write the fingerprint to ${fingerprintFile}: ${problem instanceof Error ? problem.message : String(problem)}`);
    }
    process.exit(2);
  }
  console.log(`Before: ${orders.length} order(s) fingerprinted:`);
  for (const order of orders) console.log(`  ${describe(order)}  sha256 ${fingerprint(order).slice(0, 12)}`);

} else if (step === "after") {
  if (!existsSync(fingerprintFile)) {
    console.error('No fingerprint to compare with: run "node tools/data-isolation-check.ts before" first.');
    process.exit(2);
  }
  const before = JSON.parse(readFileSync(fingerprintFile, "utf8")) as { id: string; sha256: string }[];
  const beforeIds = new Set(before.map((entry) => entry.id));
  const now = readOrders();
  const byId = new Map(now.map((order) => [order.id, order]));

  // Every order is counted, not just looked up by id: a second copy of an order (even an exact
  // copy of one from before) is a leftover too.
  const seen = new Set<string>();
  const leftovers = now.filter((order) => {
    const repeat = seen.has(order.id);
    seen.add(order.id);
    return repeat || !beforeIds.has(order.id) || runMarker.test(order.name);
  });
  console.log(`1. Leftover test data: ${leftovers.length}`);
  for (const order of leftovers) console.log(`   LEFTOVER ${describe(order)}`);

  let changed = 0;
  console.log(`2. Orders from before: ${before.length}`);
  for (const entry of before) {
    const order = byId.get(entry.id);
    if (!order) {
      changed++;
      console.log(`   REMOVED  ${entry.id}`);
    } else if (fingerprint(order) !== entry.sha256) {
      changed++;
      console.log(`   CHANGED  ${describe(order)}`);
    } else {
      console.log(`   unchanged ${describe(order)}`);
    }
  }

  const passed = leftovers.length === 0 && changed === 0;
  // A PASS ends the session. After a FAIL it stays open, so the leftovers can be cleaned up and
  // "after" run again against the same fingerprint.
  if (passed) rmSync(fingerprintFile, { force: true });
  console.log(
    passed
      ? `PASS: no test data left, and all ${before.length} order(s) from before are unchanged.`
      : `FAIL: ${leftovers.length} leftover(s), ${changed} order(s) from before removed or changed.`,
  );
  process.exit(passed ? 0 : 1);
} else {
  console.error("Usage: node tools/data-isolation-check.ts before|after [--orders-file <path>] [--replace]");
  process.exit(2);
}
