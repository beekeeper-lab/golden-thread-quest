// A tiny local web server for the Tixly demo pages. It serves two read-only pages on this computer
// only (127.0.0.1), so the tests never reach a real site: the events page (/) and the order review
// page (/review, which reads the event and quantity from its address). Only GET requests are
// answered. This copy, in demo-app-redesigned/, is started by hand (see the README), not by
// Playwright; the port comes from TIXLY_DEMO_PORT (default 4173).

import { createServer } from "node:http";
import { readFileSync } from "node:fs";

const portSetting = process.env.TIXLY_DEMO_PORT ?? "4173";
if (!/^[1-9][0-9]{0,4}$/.test(portSetting) || Number(portSetting) > 65535) {
  console.error(`TIXLY_DEMO_PORT must be a whole number from 1 to 65535, not "${portSetting}"`);
  process.exit(1);
}
const port = Number(portSetting);
const eventsPage = readFileSync(new URL("./index.html", import.meta.url));
const reviewPage = readFileSync(new URL("./review.html", import.meta.url));

// Which page an address asks for, or null. Only the path counts: a query string
// (?event=...&quantity=... on the review page, or anything a link adds) is left for the page.
function pageFor(url) {
  const path = url.split("?")[0];
  if (path === "/" || path === "/index.html") return eventsPage;
  if (path === "/review") return reviewPage;
  return null;
}

createServer((request, response) => {
  const page = pageFor(request.url ?? "");
  if (request.method !== "GET" || page === null) {
    response.writeHead(404, { "content-type": "text/plain; charset=utf-8" });
    response.end("Not found");
    return;
  }
  response.writeHead(200, { "content-type": "text/html; charset=utf-8" });
  response.end(page);
}).listen(port, "127.0.0.1", () => {
  console.log(`Tixly demo app on http://127.0.0.1:${port}`);
});
