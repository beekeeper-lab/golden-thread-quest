// Builds the Golden Thread Quest site from a copy of the repository's fixture participant
// (Alex Rivera) and serves it on loopback for the Playwright test.
//
// The fixture is copied to one fixed folder in the system temporary directory, outside the
// repository (the application refuses a participant folder inside its own folders), so the
// test never reads or changes the participant's own progress. The folder is emptied at the
// start of every run, so each run starts from the same data even when the previous server
// was killed.
//
// GTQ_PLANTED_FAULT=claimed-counted-as-verified serves a passport whose Verified XP shows the
// claimed total, to produce the deliberately failing run the quest asks for. It changes only
// the served copy of one page. Any other non-empty value stops the server with an error, so a
// misspelled fault cannot quietly run the test with no fault.

import { execFileSync } from "node:child_process";
import { cpSync, mkdirSync, readFileSync, rmSync, statSync } from "node:fs";
import { createServer } from "node:http";
import { tmpdir } from "node:os";
import { dirname, extname, join, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";

const KNOWN_FAULTS = ["claimed-counted-as-verified"];
const CLAIMED_XP = /<dt>Claimed XP<\/dt><dd>(\d+)<\/dd>/;
const VERIFIED_XP = /<dt>Verified XP<\/dt><dd>\d+<\/dd>/;

function fail(message) {
  console.error(`serve-fixture: ${message}`);
  process.exit(1);
}

const here = dirname(fileURLToPath(import.meta.url));
const repoRoot = resolve(here, "../../..");

const port = Number(process.env.PORT ?? 4791);
if (!Number.isInteger(port) || port < 1 || port > 65535) {
  fail(`PORT must be a whole number from 1 to 65535, not ${JSON.stringify(process.env.PORT)}.`);
}

const fault = process.env.GTQ_PLANTED_FAULT ?? "";
if (fault && !KNOWN_FAULTS.includes(fault)) {
  fail(`unknown GTQ_PLANTED_FAULT ${JSON.stringify(fault)}. Known: ${KNOWN_FAULTS.join(", ")}.`);
}

const work = join(tmpdir(), "gtq-playwright-fixture");
rmSync(work, { recursive: true, force: true });
mkdirSync(work, { recursive: true });
const participantRoot = join(work, "participant");
const generatedRoot = join(work, "generated");
cpSync(join(repoRoot, "fixtures", "participant"), participantRoot, { recursive: true });

execFileSync(process.env.GTQ_CLI ?? "gtq", ["build", "--repo-root", repoRoot], {
  env: {
    ...process.env,
    GTQ_PARTICIPANT_ROOT: participantRoot,
    GTQ_GENERATED_ROOT: generatedRoot,
  },
  stdio: ["ignore", "inherit", "inherit"],
});

const passportPage = join(generatedRoot, "passport", "index.html");

// Check once, before serving, that the planted fault can find what it changes. Otherwise a
// change to the passport's markup would make every request for it fail, and the test run
// would wait out its start-up timeout with no clear reason.
if (fault) {
  const html = readFileSync(passportPage, "utf8");
  if (!CLAIMED_XP.test(html) || !VERIFIED_XP.test(html)) {
    fail(`the planted fault ${fault} cannot find the Claimed XP and Verified XP totals in ${passportPage}.`);
  }
}

const types = {
  ".html": "text/html; charset=utf-8",
  ".css": "text/css",
  ".js": "text/javascript",
  ".json": "application/json",
  ".svg": "image/svg+xml",
  ".png": "image/png",
  ".woff2": "font/woff2",
};

function plant(path, body) {
  if (fault !== "claimed-counted-as-verified" || path !== passportPage) {
    return body;
  }
  const html = body.toString();
  const claimed = html.match(CLAIMED_XP)[1];
  return html.replace(VERIFIED_XP, `<dt>Verified XP</dt><dd>${claimed}</dd>`);
}

const server = createServer((request, response) => {
  let path;
  try {
    const url = new URL(request.url, `http://127.0.0.1:${port}`);
    path = resolve(generatedRoot, "." + decodeURIComponent(url.pathname));
  } catch {
    response.writeHead(400).end();
    return;
  }
  if (path !== generatedRoot && !path.startsWith(generatedRoot + sep)) {
    response.writeHead(403).end();
    return;
  }
  try {
    if (statSync(path).isDirectory()) path = join(path, "index.html");
    const body = plant(path, readFileSync(path));
    response.writeHead(200, { "content-type": types[extname(path)] ?? "application/octet-stream" });
    response.end(body);
  } catch {
    response.writeHead(404).end();
  }
});

function stop() {
  server.close();
  process.exit(0);
}
process.on("SIGTERM", stop);
process.on("SIGINT", stop);

server.listen(port, "127.0.0.1", () => {
  console.log(`Fixture site on http://127.0.0.1:${port}/${fault ? ` (planted fault: ${fault})` : ""}`);
});
