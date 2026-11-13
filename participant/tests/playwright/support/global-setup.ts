// Runs once, before any test (after Playwright has started the demo app):
//   1. picks this run's marker, which goes into the name of every order the isolated tests create
//      (see orders-fixture.ts). Every test in the run, in every browser worker, shares it, because
//      Playwright passes environment variables from here to the workers;
//   2. notes the id of every order that already exists, so the run-end safety net
//      (global-teardown.ts) never touches one of them, whatever its name says.
//
// Each top-level run picks its own marker, even if TIXLY_RUN_MARKER is already set (left in the
// shell, say): two runs sharing a marker could sweep each other's orders. The one exception is
// tools/run-in-order.ts, which runs tests one at a time but as one run: it picks the marker and the
// list itself, passes them to each test it starts together with TIXLY_SAFETY_NET_LATER=1, and runs
// the safety net itself at the end. Only then are TIXLY_RUN_MARKER and TIXLY_PREEXISTING_IDS kept.

import { randomBytes } from "node:crypto";

export const MARKER_PATTERN = /^qa-[0-9a-f]{8}$/;

export default async function globalSetup(): Promise<void> {
    if (process.env.TIXLY_SAFETY_NET_LATER === "1") {
    const given = process.env.TIXLY_RUN_MARKER;
    if (given === undefined || !MARKER_PATTERN.test(given) || process.env.TIXLY_PREEXISTING_IDS === undefined) {
      throw new Error(
        `TIXLY_SAFETY_NET_LATER=1 is for tools/run-in-order.ts, which also sets TIXLY_RUN_MARKER (like qa-1a2b3c4d) and TIXLY_PREEXISTING_IDS; got marker "${given ?? ""}"`,
      );
    }
    return;
  }
  process.env.TIXLY_RUN_MARKER = `qa-${randomBytes(4).toString("hex")}`;
  process.env.TIXLY_PREEXISTING_IDS = JSON.stringify(await existingOrderIds());
}

// Where the demo app is: the same address the tests use (playwright.config.ts).
export function baseUrl(): string {
  return process.env.TIXLY_BASE_URL ?? `http://127.0.0.1:${process.env.TIXLY_DEMO_PORT ?? "4173"}`;
}

// A request to the demo app's orders service, tried once more if the connection drops (the app
// closes a connection that has been idle for a few seconds, and a long test can leave one idle that
// long). Redirects are refused: these requests come from Node, outside the browser's local-only
// proxy, so following a redirect could send them (or a cancellation) to another site.
// Each attempt has 10 seconds, including reading the answer, so a stuck app can't hold up a run or
// its cleanup.
//
// The API key. The orders service only answers tests, tools and scripts that send its made-up API
// key (demo-app/server.js); it comes from the environment (TIXLY_API_KEY) and goes only into this
// header, on these requests from Node. The browser never gets it, so it can't show up in a page,
// a screenshot or a trace, and nothing here ever prints it. A refusal (401) stops with what to do.
//
// The key must be printable characters with no spaces (the same rule as demo-app/server.js), checked
// before it is put in a header: a space at either end would be dropped from the header and no longer
// match, and a line break would make the header code fail with the key in its error message. The
// message here never includes the value.
// Only a request that is safe to send twice (listing, cancelling) is tried again after a dropped
// connection; a save is not, since the first one may have been saved before the answer was lost.
export const KEY_PATTERN = /^[\x21-\x7e]{1,256}$/;
export async function ask(url: URL, init?: RequestInit): Promise<Response> {
  const key = process.env.TIXLY_API_KEY ?? "";
  if (key !== "" && !KEY_PATTERN.test(key)) {
    throw new Error(
      "TIXLY_API_KEY must be 1 to 256 printable characters with no spaces or line breaks (its value isn't shown). " +
        "Set a made-up one, for example: export TIXLY_API_KEY=$(openssl rand -hex 16)",
    );
  }
  const headers = new Headers(init?.headers);
  if (key !== "") headers.set("x-tixly-api-key", key);
  const options = (): RequestInit => ({ ...init, headers, redirect: "error", signal: AbortSignal.timeout(10_000) });
  const method = (init?.method ?? "GET").toUpperCase();
  let answer: Response;
  try {
    answer = await fetch(url, options());
  } catch (problem) {
    if (method !== "GET" && method !== "DELETE") throw problem;
    answer = await fetch(url, options());
  }
  if (answer.status === 401) {
    throw new Error(
      `The orders service refused the request (401): ${key === "" ? "TIXLY_API_KEY isn't set" : "TIXLY_API_KEY isn't the key the app was started with"}. ` +
        "Set the same made-up key for the app and the tests first, for example: export TIXLY_API_KEY=$(openssl rand -hex 16)",
    );
  }
  return answer;
}

// The ids of the orders saved right now, or none if the app has no orders service (such as
// demo-app-redesigned/).
export async function existingOrderIds(): Promise<string[]> {
  const listing = await ask(new URL("/api/orders", baseUrl()));
  if (listing.status === 404) return [];
  if (!listing.ok) throw new Error(`Couldn't list the saved orders before the run: ${listing.status}`);
  return ((await listing.json()) as { id: string }[]).map((order) => order.id);
}
