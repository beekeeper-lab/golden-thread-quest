# Proof · playwright-project-setup

Attempt: `playwright-attempt-003`

Decisions by Tom Carter; the project, the check script and its tests drafted with Claude (Claude
Code), 11-05-2026. Tixly is an invented ticket app; the tests run only against a small demo copy of
it on this computer.

## What was built

A Playwright project in `participant/tests/playwright` that someone else can set up and run from
the README alone:

- **Playwright Test 1.63.0, pinned exactly,** with its lockfile. It is the version my Seatwise test
  suite already uses, so one Playwright version covers my projects.
- **A demo app to test:** one read-only "Tixly" event page and a few lines of Node that serve it
  on this computer only (127.0.0.1). Playwright starts it before a run and stops it after, so a
  stranger needs nothing else. I chose this over my Seatwise app, which a reviewer couldn't run
  from this repository.
- **One smoke test,** which opens the page in Chromium and checks the event and its prices.
- **A configuration** that takes the app's address from the environment and refuses any address
  that isn't this computer, and keeps the browser itself on this computer: every request to
  anywhere else goes to a proxy that doesn't exist, so a redirect, script or image from a public
  site fails instead of loading.
- **A README** with the prerequisites and their versions, the setup steps, where the address is
  set, how credentials would be supplied, what is kept out of Git, and what to do when the first
  run fails.
- **A `.gitignore`** for everything a run produces and for environment files.
- **A TypeScript check** (`tools/project-setup-check.ts`) that confirms Git ignores generated
  output and environment files, keeps the project's own files, keeps downloaded browsers out, finds
  no environment file, installed package or downloaded browser anywhere in the repository and no
  output from this project's runs among the files Git would commit, and that the
  repository's own secret scanner finds no credential in them, including in the staged copy of
  every tracked file, which is what a commit takes, and in the text of every link (within the
  scanner's skip rules, listed under Remaining limitations).

## Where the important artifacts are

| What | Path |
|---|---|
| Setup document | `participant/tests/playwright/README.md` |
| Package manifest and lockfile | `participant/tests/playwright/package.json`, `participant/tests/playwright/package-lock.json` |
| Configuration | `participant/tests/playwright/playwright.config.ts` |
| Smoke test | `participant/tests/playwright/tests/smoke.spec.ts` |
| Demo app | `participant/tests/playwright/demo-app/` |
| Ignore rules | `participant/tests/playwright/.gitignore` |
| Check script | `participant/tests/playwright/tools/project-setup-check.ts` |
| Clean-checkout run | `participant/evidence/playwright-project-setup/playwright-attempt-003/logs/clean-run.txt` |
| Ignore and credential check | `participant/evidence/playwright-project-setup/playwright-attempt-003/logs/ignore-check.txt` |

## How to reproduce the behavior

Follow `participant/tests/playwright/README.md` from a fresh copy of the repository: `npm ci
--engine-strict`, `npx playwright install chromium`, `npm test`. Then, from the same folder, `npm
run check-setup` prints the same checks as `logs/ignore-check.txt`. It needs Git and the
repository's Python environment (`.venv`) for the secret scanner, and changes nothing.

## How the work meets the criteria

1. **The setup document lists every prerequisite with versions:** the README's first table gives
   the operating system, Git, Node.js and npm, each with the version it was written and run with,
   and says Playwright Test and its browser come from the lockfile at fixed versions.
2. **Following the document on a clean checkout reaches a passing smoke test:**
   I cloned the final reviewed version from GitHub into a new folder, opened the README and ran
   its steps as written (`logs/clean-run.txt`, 11-05-2026 4:55 PM). Git 2.39.2, Node.js 22.23.3 and
   npm 10.9.9 matched the README's table; `npm ci --engine-strict` installed 3 packages with 0
   vulnerabilities; `npm test` ended `1 passed`; and `npm run check-setup` stopped with "the
   repository's secret scanner ... isn't set up" (exit code 2), as the README says it does in a copy
   without the repository's Python environment. The only change to the log is that the terminal's
   colour codes were removed.
3. **The target URL comes from configuration, not from test code:** the test only opens `/`; the
   address comes from `TIXLY_BASE_URL` in `playwright.config.ts`, or the demo app's address when it
   is unset. Running with another port and against an already-running copy both pass.
4. **Credentials come from the environment and appear nowhere in the repository:** the demo app
   needs none, so none are used; the README says how one would be supplied (an environment
   variable read in the test), `.env` files are ignored, and the repository's secret scanner finds
   none in any of the files Git would commit, including the staged copy of every tracked file,
   since that is what a commit would take, within the scanner's skip rules (see Remaining
   limitations; `logs/ignore-check.txt`).
5. **Reports, traces and downloads are ignored by Git:** `logs/ignore-check.txt` asks Git about
   every kind of file a run produces (results, traces, failure screenshots, downloads, the HTML
   report, merged-report files and the build cache) and five kinds of environment file name, and
   names the rule that ignores each one; and it confirms no such file is among the files Git would
   commit, even one added on purpose before an ignore rule existed.
6. **Dependency versions are pinned:** `package.json` names Playwright Test as exactly `1.63.0`,
   and `package-lock.json` fixes every installed package; the README uses `npm ci`, which installs
   exactly what the lockfile says, with `--engine-strict` so an older Node.js is refused.
7. **The document says what to do when the first run fails:** the README's last section is a table
   of the failures I met or expected, each with what to do, and how to get the report, trace and
   screenshot when a check fails. The port and wrong-address messages in it are the real messages,
   copied from runs.

## What broke when I followed my own document

Nothing, on the clean run: every step worked as written and nothing in the README confused me.
The one thing it couldn't show is the first-time browser download, because Chromium was already on
my computer (see Remaining limitations).

What broke while building it, before the clean run:

- **Adding `package.json` to this folder broke my earlier quests' logs.** The checks from my
  layered test strategy and automation quests live in the same folder; with a `package.json` that
  didn't say how its files are written, Node printed a warning before their output, so their logs
  no longer matched. Adding `"type": "module"` fixed it, and both logs are identical to fresh runs
  again.
- **The README's first draft gave the wrong Git version and claimed Linux.** Checking each line
  against the machine found Git 2.39.2, not the version written, and that the setup had only been
  run on macOS. Both are now stated as they are.
- **A test of the "port already in use" advice hung.** The stand-in program on the port accepted
  connections but never answered, so the run waited instead of failing. That is a real way the
  first run can go wrong, so it is now its own row in the README's table.
- **My first fix for an older Node.js would never have reached a clean copy.** I first put the
  setting in an `.npmrc` file in this folder, but the repository's main `.gitignore` ignores every
  `.npmrc` on purpose, because such files often hold login tokens. My check script caught it the
  moment `.npmrc` was added to the files it requires Git to keep. Rather than override a
  deliberate safety rule, the README's install command carries the setting instead:
  `npm ci --engine-strict`.
- **The strict type check found a configuration problem.** The setting that starts the demo app
  was written as "nothing" when another address is used; Playwright's types expect it to be left
  out instead. It is now left out, and all three ways of running pass.

## Reflection

**What is the first thing a new teammate would still get stuck on?**

**Installing Node.js at the right version.** It is the one prerequisite the README can't do for
them, there are several ways to install it, and a teammate who already has an older Node won't
necessarily know it's too old. My own computer has two copies (22 and 24), and which one runs
depends on the order the terminal searches. I tried the project with Node 20: npm installed it
anyway, with a warning that was easy to scroll past; the smoke test even passed, because Playwright
handles TypeScript itself; and then the check script failed with an error about an unknown ".ts"
file extension that never mentions Node's version. A teammate would get stuck late, on a
confusing message, for a reason the README states at the top.

So I acted on it: the README's install step is now `npm ci --engine-strict`, which stops at the
first step with npm's own message, `Required: {"node":"^22.18.0 || >=23.6.0"}` and
`Actual:   {"npm":"10.8.2","node":"v20.20.2"}`, and the README's first-run table has that message
and the `which -a node` check for more than one copy. With Node 22 nothing
changes. What's still left is the install itself: the README can say which version, but not install
it for them.

## What was tested or validated

- **The smoke test:** passes, in three ways: as set up, on another port, and against a copy of
  the demo app already running.
- **The port check:** an empty `TIXLY_DEMO_PORT`, `0`, `abc`, `70000`, `4173.5` and `08080` each stop
  the run within about a second with the README's message; before the check, an empty value or `0`
  made the run wait 60 seconds and then time out. `65535` and the default both pass.
- **The address guard:** setting `TIXLY_BASE_URL` to a public site stops the run with the README's
  message before any test starts.
- **The browser stays on this computer:** a local test server that redirects to a public site and
  loads an image and a script from public addresses (one by name, one by raw IP address) showed,
  before the fix, the browser following the redirect and loading the site's script; after it, only
  the local pages loaded and all three outside requests failed. A second probe showed Chromium
  still went straight to link-local addresses (169.254.169.254 and fe80::1), which it treats as
  local by default; with that default turned off, they fail at the proxy too, and 127.0.0.1,
  localhost and [::1] still load.
- **The check script on the real repository:** PASSED, as recorded in `logs/ignore-check.txt`.
- **Strict type check:** the check script, the configuration and the test were type-checked with
  TypeScript 6.0.3 in strict mode, in a temporary folder outside this repository.
- **Tests of the check itself (kept locally, not handed in):** 69 throwaway Git repositories, each
  holding a copy of the project with one thing broken (for example an environment file forced
  into Git, a made-up token in a notes file, the lockfile ignored, or browsers stored inside the
  repository), each giving the expected result; and 39 deliberately broken copies of the script,
  all of which those tests caught. They found one real bug: on macOS a folder can have two names
  (`/var` is a link to `/private/var`), so a browser folder inside the repository could look as if
  it were outside. The script now compares real locations.
- **An older Node.js:** in a throwaway copy, with Node 20.20.2 downloaded only into a temporary
  folder, `npm ci --engine-strict` stops at once with the required and actual versions; with
  Node 22 it installs and the test passes as before.
- **My earlier quests' checks:** their logs still match fresh runs with this project in place.
- **Copilot review:** 13 rounds on a practice pull request in my own fork, before the clean run.
  I reproduced every item before changing anything. The numbered findings were 2 High, 11 Medium
  and 2 Low, all fixed: the High ones were a local page able to send the browser to a public site,
  and a staged token hidden from the scan by a Git setting (assume-unchanged). From round 5 on,
  Copilot mostly listed no open issues but raised items in its summary; each one I tested was real,
  and through round 12 I fixed them or, for the scanner's own skip rules, documented them (for
  example link-local addresses skipping the proxy, environment files under other names, an empty
  port that made the run hang, and a failing Git command read as "nothing found"). After round 13
  I stopped by a rule I set: what's left can't let a credential or a public site through, so it is
  documented under Remaining limitations instead.

## Stretch goals

Not attempted: a command that checks the environment before running, and running the setup on a
second operating system.

## Remaining limitations

- **One operating system.** The setup was written and run on macOS only; the README says so.
- **The browser was already downloaded** on my computer, because my Seatwise suite uses the same
  Playwright version, so the clean run couldn't show the first-time browser download working.
- **One browser.** The project runs Chromium only, to keep the download small.
- **A demo app, not a real one.** The smoke test proves the project is set up and can reach an app;
  it tests one small page, not a real application.
- **The credential scan depends on the repository's scanner,** which needs the repository's Python
  environment; without it, the check stops and says so rather than passing.
- **The credential scan follows the scanner's own skip rules.** The repository's scanner leaves out
  images, PDFs, fonts, audio, video, archives and `.lock` files, anything in a folder named
  `generated`, `local-data`, `node_modules`, `.git`, `.venv` or `__pycache__`, files over 2 MB, and
  files that aren't UTF-8 text, and it skips any line marked `# secret-scan: allow`. A credential in
  one of those files or lines would not be found. I tested this with a made-up token in a link named
  like an archive, a file in a `generated` folder, a `.lock` file and a 2.1 MB text file: the check
  passed each time. The quest app's hand-in check is a separate scan with its own rules (for
  example, it ignores that marker), so passing my check doesn't guarantee passing the hand-in check.
- **The credential scan can over-report for links.** Git commits a link as the text of where it
  points, and the check scans that text. The scanner also reads the file a link points to, which
  isn't committed, so a credential there is reported even though it wouldn't be committed.
- **The check confirms the project's own files aren't ignored, not that they exist.** If
  `package-lock.json` or another of them were deleted, the check would still pass; the README's
  install step would stop with an error instead. Found in the last review round and left as it is,
  since it can't let a credential or a public site through.
- **A finding's label can look odd on macOS.** When the temporary folder is reached through a link
  (for example with `TMPDIR=/tmp`), a finding in a staged copy is labelled "/privatestaged copy of"
  instead of "staged copy of". The check still fails and still names the file and line.

## Sensitive values

No secret, token, password, customer name or private ticket content is in this hand-in. The demo
app and its data are invented, the tests use no login, and the repository's secret scanner finds
no credential in anything Git would commit, within the skip rules listed under Remaining
limitations.
