// A tiny local web server for the Tixly demo page. It serves one read-only page on this computer
// only (127.0.0.1), so the tests never reach a real site. Playwright starts and stops it for each
// run; the port comes from TIXLY_DEMO_PORT (default 4173).

import { createServer } from "node:http";
import { readFileSync } from "node:fs";

const portSetting = process.env.TIXLY_DEMO_PORT ?? "4173";
if (!/^[1-9][0-9]{0,4}$/.test(portSetting) || Number(portSetting) > 65535) {
  console.error(`TIXLY_DEMO_PORT must be a whole number from 1 to 65535, not "${portSetting}"`);
  process.exit(1);
}
const port = Number(portSetting);
const page = readFileSync(new URL("./index.html", import.meta.url));

createServer((request, response) => {
  if (request.method !== "GET" || (request.url !== "/" && request.url !== "/index.html")) {
    response.writeHead(404, { "content-type": "text/plain; charset=utf-8" });
    response.end("Not found");
    return;
  }
  response.writeHead(200, { "content-type": "text/html; charset=utf-8" });
  response.end(page);
}).listen(port, "127.0.0.1", () => {
  console.log(`Tixly demo app on http://127.0.0.1:${port}`);
});
