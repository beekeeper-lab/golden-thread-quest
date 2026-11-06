# Tixly Playwright tests

Browser tests for Tixly, an invented ticket app, run against a small demo copy of the app on your
own computer. The tests never reach a public or production site. Written by Tom Carter, with
Claude (Claude Code), 11-05-2026.

This folder also holds checks from earlier quests (`tools/`); they need nothing from this setup
beyond Node.

## What you need

| Prerequisite | Version | How to check |
|---|---|---|
| macOS | written and run on macOS 27; Linux should work the same way but hasn't been tried; Windows isn't covered | |
| Git | any recent version (written and run with 2.39.2) | `git --version` |
| Node.js | 22.18 or later in the 22 line, or 23.6 or later (written and run with 22.23.3); 23.0 to 23.5 can't run the TypeScript checks | `node --version` |
| npm | comes with Node.js (written and run with 10.9.9) | `npm --version` |
| Internet access | for the first install only | |

Everything else comes from the steps below, at fixed versions: Playwright Test 1.63.0, installed
into this folder from `package-lock.json`, and the Chromium build made for it, which Playwright
keeps in its own cache folder outside the repository. Nothing else is installed.

## Set up and run

From a fresh copy of the repository:

1. Go to this folder:

   ```
   cd participant/tests/playwright
   ```

2. Install the exact package versions from the lockfile:

   ```
   npm ci --engine-strict
   ```

   `--engine-strict` makes npm stop with a clear message if your Node.js isn't a supported version
   (see the table above), instead of installing anyway and failing later with a confusing error.

3. Download the Chromium browser Playwright uses (a large download the first time; nothing is
   downloaded if the right version is already there):

   ```
   npx playwright install chromium
   ```

4. Run the tests:

   ```
   npm test
   ```

   Playwright starts the demo app on `http://127.0.0.1:4173`, runs both tests in Chromium (the
   smoke test in `tests/` and the ticket-total test, `first-independent-test.spec.ts`) and stops
   the app again. A passing run ends with `2 passed`. To run only the ticket-total test, use its
   tag: `npx playwright test --grep @ticket-total`.

5. Optional: confirm generated files and environment files are ignored by Git, and scan the
   repository for credentials. This step also needs the repository's Python environment
   (`.venv`), which you have once the quest app is set up as the repository's main README
   describes; without it, the step stops and says so rather than passing:

   ```
   npm run check-setup
   ```

## Where the target address is set

The address the tests use is never written in a test. It is set in `playwright.config.ts` from
the environment:

- `TIXLY_BASE_URL`: the app's address. Left unset, the tests use the demo app they start
  themselves. If set, it must be on this computer (`127.0.0.1` or `localhost`); the configuration
  refuses any other address, so the tests can't reach a public or production site by mistake.
- `TIXLY_DEMO_PORT`: the port the demo app uses, `4173` unless set. Change it if that port is
  already in use.

For example, to use another port for one run:

```
TIXLY_DEMO_PORT=5174 npm test
```

## Credentials

The demo app needs no login, so no credentials are used. If a later test needs one, read it from an
environment variable in the test (for example `process.env.TIXLY_TEST_PASSWORD`) and set it in your
terminal before running. Never write a password, token or session cookie into a test, this folder
or a log. Environment files in this folder (`.env`, and names such as `.env.local`, `.env-local`,
`.env_production` or `production.env`) are ignored by Git, so they can't be committed by accident;
only `.env.example` is kept.

## What is kept out of Git

`node_modules/`, `test-results/` (traces, screenshots and downloads from runs),
`playwright-report/`, `blob-report/` and environment files (`.env`, `.env.*`, `.env-*`, `.env_*`
and `*.env`, except `.env.example`) are listed in `.gitignore`. Installing creates `node_modules/`
and running the tests creates `test-results/` and `playwright-report/`; none of them is committed.

## If the first run fails

| What you see | What to do |
|---|---|
| `npm ci` says the lockfile and `package.json` don't match | Make sure you are in `participant/tests/playwright` and haven't edited `package.json`; then run `npm ci --engine-strict` again. |
| `npm error code EBADENGINE` with `Required: {"node":"^22.18.0 \|\| >=23.6.0"}` | Your Node.js isn't a supported version: install 22.18 or later in the 22 line, or 23.6 or later, from nodejs.org, open a new terminal, check `node --version`, then run `npm ci --engine-strict` again. The `--engine-strict` option in step 2 makes npm stop here on purpose, rather than install and fail later with a confusing error. |
| `node: command not found`, or `node --version` shows an older version than you installed | Node isn't installed, or another copy is found first. Run `which -a node` to list every copy; the first one is the one used. Open a new terminal after installing, or put the newer copy first. |
| `Executable doesn't exist` or `browserType.launch` errors | The browser isn't installed yet: run `npx playwright install chromium`. |
| `http://127.0.0.1:4173 is already used` | Another program is using the port: run `TIXLY_DEMO_PORT=5174 npm test`. |
| The run seems to hang before any test starts | A program on the port is accepting connections but not answering. Press Ctrl+C, then run `TIXLY_DEMO_PORT=5174 npm test`. |
| `TIXLY_DEMO_PORT must be a whole number from 1 to 65535` | `TIXLY_DEMO_PORT` is set but empty, `0` or not a port number. Unset it (`unset TIXLY_DEMO_PORT`) to use 4173, or set a port such as `5174`. |
| `TIXLY_BASE_URL must point at this computer` | `TIXLY_BASE_URL` is set to another site. Unset it (`unset TIXLY_BASE_URL`) or point it at `http://127.0.0.1:<port>`. |
| The test fails on a check | Open the report with `npx playwright show-report`; the trace and screenshot of the failure are in `test-results/`. |

If none of these fit, run `npx playwright test --reporter=line` and keep the full output for
whoever helps you.
