// A tiny local web server for the Tixly demo pages, on this computer only (127.0.0.1), so the tests
// never reach a real site. Playwright starts and stops it for each run; the port comes from
// TIXLY_DEMO_PORT (default 4173).
//
// Pages (GET only): the events page (/), the order review page (/review, which reads the event and
// quantity from its address) and the saved orders page (/orders).
//
// Orders service, for saved orders kept in data/orders.json (a stand-in for a real database: what
// is saved stays saved between runs, until it is cancelled):
//   GET    /api/orders       every saved order
//   POST   /api/orders       save one: {"name": ..., "event": ..., "quantity": ...}; answers with the
//                            saved order, including its new id
//   DELETE /api/orders/<id>  cancel the order with that id
// Each request reads, changes and writes the whole file in one uninterrupted step (no waiting in
// between, so no other request can run in the middle), so two tests saving at once through this
// server can't overwrite each other's orders.
//
// Who may use the orders service: the app's own pages, and anything else (tests, tools, scripts)
// only with the API key. The key is made up for this demo and comes from the environment
// (TIXLY_API_KEY, read when the server starts); a caller sends it in the X-Tixly-Api-Key header.
// The server never prints it or sends it back.

import { createServer } from "node:http";
import { createHash, randomBytes, timingSafeEqual } from "node:crypto";
import { readFileSync, renameSync, rmSync, writeFileSync } from "node:fs";

const portSetting = process.env.TIXLY_DEMO_PORT ?? "4173";
if (!/^[1-9][0-9]{0,4}$/.test(portSetting) || Number(portSetting) > 65535) {
  console.error(`TIXLY_DEMO_PORT must be a whole number from 1 to 65535, not "${portSetting}"`);
  process.exit(1);
}
const port = Number(portSetting);

// A stand-in for a network, off unless asked for: TIXLY_DEMO_DELAY_MS (0 to 1000) holds every answer,
// pages and orders service alike, for that many milliseconds. On this computer everything answers
// at once, so timings here would understate what a slow page costs on a real site; the delay is
// only ever a labelled simulation, used to compare tests (the API-assisted test quest).
const delaySetting = process.env.TIXLY_DEMO_DELAY_MS ?? "0";
// At most 1000 ms: a test waits for about ten answers in a row and each check gives a page 5 seconds,
// so longer delays would make a working app fail the tests' time limits.
if (!/^[0-9]{1,4}$/.test(delaySetting) || Number(delaySetting) > 1000) {
  console.error(`TIXLY_DEMO_DELAY_MS must be a whole number from 0 to 1000, not "${delaySetting}"`);
  process.exit(1);
}
const delay = Number(delaySetting);
const eventsPage = readFileSync(new URL("./index.html", import.meta.url));
const reviewPage = readFileSync(new URL("./review.html", import.meta.url));
const ordersPage = readFileSync(new URL("./orders.html", import.meta.url));
const ordersFile = new URL("./data/orders.json", import.meta.url);

// One server per orders file: two servers writing the same file could lose each other's changes. A
// lock file holding this server's process id is created at startup (in one step, failing if it
// already exists) and removed when the server stops. If a lock is already there, this server
// refuses to start, even when the server that made it has gone (a crash, or being killed outright):
// taking over a lock automatically can't be made safe when two servers start at once, so a lock
// left behind is cleared by hand, as the message says. A server only ever removes a lock holding
// its own id.
const lockFile = new URL("./data/orders.json.lock", import.meta.url);
function takeLock() {
    try {
    writeFileSync(lockFile, String(process.pid), { flag: "wx" });
    return;
  } catch (problem) {
    // EEXIST: someone has the lock, or had it (looked at below). Anything else (a data folder that
    // can't be written, say) is the real problem, so it is reported as it is.
    if (problem?.code !== "EEXIST") {
      console.error(`Couldn't create the lock demo-app/data/orders.json.lock: ${problem?.message ?? problem}`);
      process.exit(1);
    }
  }
  const holder = Number(readFileSync(lockFile, "utf8"));
  let running = false;
  try {
    process.kill(holder, 0);
    running = Number.isInteger(holder) && holder > 0;
  } catch {
    running = false;
  }
  if (running) {
    // A running process with that number may be another demo app, or (after a crash and a restart
    // of the computer's process numbering) something unrelated; the lock is refused either way.
    console.error(
      `The lock on data/orders.json names process ${holder}, which is still running. If that is another ` +
        "demo app, stop it first. If it isn't a demo app (the number can be reused after a crash), make sure " +
        "no demo app is running, delete demo-app/data/orders.json.lock, and start again.",
    );
  } else {
    console.error(
      `A lock on data/orders.json was left by a demo app that stopped without removing it (process ${holder}). ` +
        "Make sure no demo app is running, delete demo-app/data/orders.json.lock, and start again.",
    );
  }
  process.exit(1);
}
let haveLock = false;
takeLock();
haveLock = true;
process.on("exit", () => {
  if (!haveLock) return;
  try {
    if (Number(readFileSync(lockFile, "utf8")) === process.pid) rmSync(lockFile, { force: true });
  } catch {
    // Already gone.
  }
});
for (const signal of ["SIGINT", "SIGTERM", "SIGHUP"]) process.on(signal, () => process.exit(0));
// Named after this server process, so two servers sharing the file never write the same
// temporary file (they can still lose each other's changes: run one server per orders file).
const ordersTemporary = new URL(`./data/orders.json.${process.pid}.tmp`, import.meta.url);

// The events that can be ordered, and the longest buyer name.
const EVENTS = new Set(["spring-concert"]);
const MAX_NAME = 60;

// Which page a path asks for, or null. Only the path counts: a query string
// (?event=...&quantity=... on the review page, or anything a link adds) is left for the page.
function pageFor(path) {
  if (path === "/" || path === "/index.html") return eventsPage;
  if (path === "/review") return reviewPage;
  if (path === "/orders") return ordersPage;
  return null;
}

// What an order id looks like: the same rule the cancel route uses, so every listed order can be
// cancelled.
const ORDER_ID = /^o-[a-z0-9-]{1,40}$/;

// A problem reading the saved orders (as opposed to saving them).
class Unreadable extends Error {}

// The saved orders. Anything that isn't a list of complete orders (an id, a name, an event and a
// whole number of tickets from 1 to 6, the same limits a save has) counts as unreadable (the caller answers "can't be read"), so it is never
// listed, and never written over.
function readOrders() {
  let orders;
  try {
    orders = JSON.parse(readFileSync(ordersFile, "utf8"));
  } catch (problem) {
    throw new Unreadable(problem instanceof Error ? problem.message : String(problem));
  }
  const complete = (order) =>
    typeof order?.id === "string" &&
    ORDER_ID.test(order.id) &&
    typeof order.name === "string" &&
    order.name !== "" &&
    typeof order.event === "string" &&
    Number.isInteger(order.quantity) &&
    order.quantity >= 1 &&
    order.quantity <= 6;
  if (!Array.isArray(orders) || !orders.every(complete)) {
    throw new Unreadable("the orders file isn't a list of complete orders");
  }
  // Each id once: cancelling by id must only ever reach one order.
  if (new Set(orders.map((order) => order.id)).size !== orders.length) {
    throw new Unreadable("the orders file has the same order id more than once");
  }
  return orders;
}

// Written to a temporary file first and then moved into place, so the file is never left
// half-written. Two-space indentation and a final new line, the same as the file in Git, so once
// the tests have cleaned up, the committed file is byte for byte what it was. If the write or the
// move fails, the temporary file (which may hold the order that wasn't saved) is removed; only a
// hard kill in between can leave one behind.
function writeOrders(orders) {
  try {
    writeFileSync(ordersTemporary, `${JSON.stringify(orders, null, 2)}\n`);
    renameSync(ordersTemporary, ordersFile);
  } catch (problem) {
    rmSync(ordersTemporary, { force: true });
    throw problem;
  }
}

// A saved order must name a buyer (1 to 60 characters, not only spaces), an event on sale and a
// whole number of tickets from 1 to 6. Returns the order to save, or a message saying what's wrong.
function validOrder(body) {
  if (typeof body !== "object" || body === null || Array.isArray(body)) {
    return "Send the order as a JSON object.";
  }
  const name = typeof body.name === "string" ? body.name.trim() : "";
  // A name has to show something: no control characters, and at least one letter, digit or mark
  // once the characters that draw nothing are set aside (spaces, zero-width and format characters,
  // and blank-looking ones such as the braille blank or the Hangul fillers).
  const visible = name.replace(/[\p{Z}\p{Cf}\u2800\u115F\u1160\u3164\uFFA0]/gu, "");
  const shows = /[\p{L}\p{N}\p{P}\p{S}]/u.test(visible) && !/\p{Cc}/u.test(name);
  if (!shows || name.length > MAX_NAME) return `Give a name of 1 to ${MAX_NAME} characters.`;
  if (typeof body.event !== "string" || !EVENTS.has(body.event)) return "That event isn't on sale.";
  if (!Number.isInteger(body.quantity) || body.quantity < 1 || body.quantity > 6) {
    return "Choose from 1 to 6 tickets.";
  }
  return { name, event: body.event, quantity: body.quantity };
}

function send(response, status, value) {
  response.writeHead(status, { "content-type": "application/json; charset=utf-8" });
  response.end(JSON.stringify(value));
}

// A save or cancel sent by another website (a page open in the browser can send one to this
// computer) is refused: a browser always says which site a request comes from (Origin), and it must
// be this app itself. The tests' own requests come from no website, so they carry no Origin.
function fromAnotherSite(request) {
  const origin = request.headers.origin;
  return origin !== undefined && origin !== `http://${request.headers.host}`;
}

// The app's own pages: the browser itself marks their requests as coming from the same site
// (Sec-Fetch-Site), which a page's code can't change, so the key never has to reach the browser.
// (A script on this computer could send that header too: the demo has no buyer login, so the pages'
// own way in is open by design. The key guards the way in that tests, tools and scripts use.)
function fromOwnPage(request) {
  return request.headers["sec-fetch-site"] === "same-origin";
}

// The key from the environment; without one, only the pages can use the orders service. It must be
// printable characters with no spaces (the same rule as the tests' helper, support/global-setup.ts):
// spaces at either end are dropped from a header, so such a key could never match. The message never
// shows the value.
const expectedKey = process.env.TIXLY_API_KEY ?? "";
if (expectedKey !== "" && !/^[\x21-\x7e]{1,256}$/.test(expectedKey)) {
  console.error("TIXLY_API_KEY must be 1 to 256 printable characters with no spaces or line breaks (its value isn't shown).");
  process.exit(1);
}
const digest = (text) => createHash("sha256").update(text).digest();
// Compared in a way that takes the same time however much of the key is right, so it can't be
// guessed one character at a time.
function hasValidKey(request) {
  const given = request.headers["x-tixly-api-key"];
  return expectedKey !== "" && typeof given === "string" && timingSafeEqual(digest(given), digest(expectedKey));
}

function handleOrders(request, response, path, bodyText) {
  // Listing too: the list holds buyers' names.
  if (!fromOwnPage(request) && !hasValidKey(request)) {
    return send(response, 401, { error: "The orders service needs a valid API key (the X-Tixly-Api-Key header) for requests that don't come from this app's own pages." });
  }
  if (path === "/api/orders" && request.method === "GET") return send(response, 200, readOrders());
  if ((request.method === "POST" || request.method === "DELETE") && fromAnotherSite(request)) {
    return send(response, 403, { error: "Orders can only be changed from this app." });
  }
  if (path === "/api/orders" && request.method === "POST") {
    // Only a JSON save: a plain-text one is what another site can send without asking first.
    // The media type, without parameters such as "; charset=utf-8", in any letter case.
    const mediaType = (request.headers["content-type"] ?? "").split(";")[0].trim().toLowerCase();
    if (mediaType !== "application/json") {
      return send(response, 415, { error: "Send the order as JSON." });
    }
    let body;
    try {
      body = JSON.parse(bodyText);
    } catch {
      return send(response, 400, { error: "Send the order as a JSON object." });
    }
    const order = validOrder(body);
    if (typeof order === "string") return send(response, 400, { error: order });
    const orders = readOrders();
    // A new random id, never one already in use: cancelling by id must only ever reach one order.
    let id;
    do id = `o-${randomBytes(4).toString("hex")}`;
    while (orders.some((existing) => existing.id === id));
    const saved = { id, ...order };
    writeOrders([...orders, saved]);
    return send(response, 201, saved);
  }
  const match = /^\/api\/orders\/(.+)$/.exec(path);
  if (match && !ORDER_ID.test(match[1])) return send(response, 404, { error: "No order with that id." });
  if (match && request.method === "DELETE") {
    const orders = readOrders();
    const remaining = orders.filter((order) => order.id !== match[1]);
    if (remaining.length === orders.length) return send(response, 404, { error: "No order with that id." });
    writeOrders(remaining);
    return send(response, 200, { cancelled: match[1] });
  }
  return send(response, 404, { error: "Not found" });
}

// Only requests addressed to this computer, by its own address, are answered. A website can make a
// browser send requests to this app under the website's own name (DNS rebinding); refusing every
// other name stops that, and makes the Origin check below compare against a name we trust.
// (On port 80, browsers leave the port out of the name, so the bare names count too.)
const OWN_HOSTS = new Set([`127.0.0.1:${port}`, `localhost:${port}`, ...(port === 80 ? ["127.0.0.1", "localhost"] : [])]);

createServer((request, response) => {
  if (delay > 0) setTimeout(() => answer(request, response), delay);
  else answer(request, response);
}).listen(port, "127.0.0.1", () => {
  console.log(`Tixly demo app on http://127.0.0.1:${port}`);
  if (expectedKey === "") console.log("No TIXLY_API_KEY set: only the app's own pages can use the orders service.");
  if (delay > 0) console.log(`Simulated network delay: ${delay} ms on every answer.`);
});

// One request, answered. (A request's body waits unread until it is read below, so the delay
// above loses nothing.)
function answer(request, response) {
  if (!OWN_HOSTS.has(request.headers.host ?? "")) {
    response.writeHead(403, { "content-type": "text/plain; charset=utf-8" });
    response.end("This app only answers requests addressed to 127.0.0.1 or localhost.");
    return;
  }
  const path = (request.url ?? "").split("?")[0];
  if (path === "/api/orders" || path.startsWith("/api/orders/")) {
    // Orders are small; a request body over 10 KB (counted in bytes, as sent) is refused rather
    // than read.
    const chunks = [];
    let bytes = 0;
    request.on("data", (chunk) => {
      chunks.push(chunk);
      bytes += chunk.length;
      if (bytes > 10_000 && !response.writableEnded) {
        send(response, 413, { error: "Too large: a request can be at most 10,000 bytes." });
        request.destroy();
      }
    });
    request.on("end", () => {
      if (response.writableEnded) return;
      const bodyText = Buffer.concat(chunks).toString("utf8");
      // If the orders file can't be read (damaged, or not valid JSON) or can't be updated (a full
      // disk, no permission), say which instead of crashing: the pages keep working, and the file
      // is left as it is (every change is made only after a successful read and written whole), so
      // it can still be put right by hand.
      try {
        handleOrders(request, response, path, bodyText);
      } catch (problem) {
        console.error(`Orders service: ${problem instanceof Error ? problem.message : problem}`);
        const error = problem instanceof Unreadable ? "The saved orders file can't be read." : "The saved orders file couldn't be updated.";
        if (!response.headersSent) send(response, 500, { error });
      }
    });
    return;
  }
  const page = pageFor(path);
  if (request.method !== "GET" || page === null) {
    response.writeHead(404, { "content-type": "text/plain; charset=utf-8" });
    response.end("Not found");
    return;
  }
  // Never shown inside another site's frame, so no site can trick a click on Save or Cancel
  // (clickjacking).
  response.writeHead(200, {
    "content-type": "text/html; charset=utf-8",
    "content-security-policy": "frame-ancestors 'none'",
    "x-frame-options": "DENY",
  });
  response.end(page);
}
