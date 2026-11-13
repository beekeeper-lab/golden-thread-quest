// Runs once, after every test has finished: the safety net. Each test already cancels the orders it
// noted (orders-fixture.ts), so normally this finds nothing. If a test was cut short before it
// could note an order (a crash, a timeout at the wrong moment), its order still carries this run's
// marker in its name, and is cancelled here.
//
// Only an order that carries THIS run's marker AND did not exist when the run began
// (TIXLY_PREEXISTING_IDS, noted by global-setup.ts) is touched: never an order from before the run,
// whatever its name says, and never another run's. Each cancellation is checked; one that fails
// (anything but done or already gone) fails the run, so a cleanup failure is never silent.
//
// It does nothing when:
//   - TIXLY_SAFETY_NET_LATER=1: tools/run-in-order.ts runs each test separately and calls this once
//     itself, after the last one;
//   - the app has no orders service at all (answers 404), such as demo-app-redesigned/, used by
//     tests that never save an order.

import { ask, baseUrl } from "./global-setup.ts";
import { runMarker, type SavedOrder } from "./orders-fixture.ts";

export default async function globalTeardown(): Promise<void> {
  if (process.env.TIXLY_SAFETY_NET_LATER === "1") return;
  const marker = runMarker();
  const preexisting = process.env.TIXLY_PREEXISTING_IDS;
  if (preexisting === undefined) {
    throw new Error("Safety net: no record of the orders that existed before the run, so nothing is swept.");
  }
  const before = new Set(JSON.parse(preexisting) as string[]);
  // new URL keeps the path right whether or not the base address ends in "/".
  const base = baseUrl();
  const listing = await ask(new URL("/api/orders", base));
  if (listing.status === 404) return;
  if (!listing.ok) throw new Error(`Safety net: the orders service answered ${listing.status}.`);
  const all = (await listing.json()) as SavedOrder[];
  // Only the exact name the orders helper makes ("Test User <marker>-<8 hex digits>"), not any name
  // that merely contains the marker.
  const generated = new RegExp(`^Test User ${marker}-[0-9a-f]{8}$`);
  const leftovers = all.filter((order) => generated.test(order.name) && !before.has(order.id));
  const problems: string[] = [];
  // Every leftover is tried, even if an earlier one fails; all failures are reported together.
  for (const order of leftovers) {
    try {
      const answer = await ask(new URL(`/api/orders/${encodeURIComponent(order.id)}`, base), { method: "DELETE" });
      if (answer.status !== 200 && answer.status !== 404) problems.push(`${order.id}: ${answer.status}`);
    } catch (problem) {
      problems.push(`${order.id}: ${problem instanceof Error ? problem.message : problem}`);
    }
  }
  if (problems.length > 0) throw new Error(`Safety net couldn't cancel: ${problems.join(", ")}`);
  if (leftovers.length > 0) {
    console.log(`Safety net: cancelled ${leftovers.length} order(s) left with run marker ${marker}.`);
  }
}
