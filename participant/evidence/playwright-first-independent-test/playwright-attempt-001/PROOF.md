# Proof · playwright-first-independent-test

Attempt: `playwright-attempt-001`

## How this was made

Claude (an AI coding assistant) wrote the test, the page model, the fixture server and this
document at Beau's direction, ran the test and the quest checker, and saved the records
below. Beau chose what to test (the passport's verified-versus-claimed rule) and chose how
to handle the checker problem described under "What was tested or validated".

## What was built

One Playwright test for a business rule of this application: **only a reviewer's approval
earns verified XP; work the participant finished but no reviewer approved counts as claimed
and stays separate.**

- `participant/tests/playwright/first-independent-test.spec.ts`: the test. Its title says
  the behavior and the expected outcome. It carries the tags `@feature-passport`,
  `@risk-high`, `@read-only` and `@duration-fast`.
- `participant/tests/playwright/pages/example-page.ts`: the page model (`PassportPage`).
  Locators live here and use roles, headings and visible text. The assertions stay in the
  test so the rule is readable there.
- `participant/tests/playwright/serve-fixture.mjs`: copies the repository's fixture
  participant (`fixtures/participant`, the fictional Alex Rivera) to a fixed folder in the
  system temporary directory, builds the site from it with `gtq build`, and serves it on
  `127.0.0.1:4791`. The folder is emptied at the start of each run.
- `participant/tests/playwright/playwright.config.ts`: starts that server, keeps a trace and
  screenshot only on failure, and writes run output to `local-data/playwright-results/`
  (ignored by Git).
- `participant/package.json`: pins `@playwright/test` 1.63.0.

**Test data.** The fixture has two attempts: Base Camp's repository-safety quest (20 XP),
verified by a reviewer; and Jira's read-assigned-stories quest (30 XP), evidence ready and
never reviewed. So the expected passport is 50 claimed XP, 20 verified XP, 1 verified quest,
and a Jira Jungle card showing "Claimed: 1 · Verified quests: 0" and "1 evidence ready".

## Business risk, and why the assertion proves it

The risk is that a participant's own claims show up as verified, so a reviewer or manager
trusts work no one has checked. A test that only opened the passport, or checked that a
number appeared, would pass with that bug. This test asserts the exact verified total (20,
the reviewed quest alone) and the exact claimed total (50, both quests), and that the
unreviewed quest's region shows it as claimed and evidence-ready with no verified quest. If
unreviewed XP leaked into the verified total, the first assertion fails.

## Where the important artifacts are

All under `participant/evidence/playwright-first-independent-test/playwright-attempt-001/`:

| File | What it is |
|---|---|
| `logs/test-run.txt` | Two tagged runs in a row (`--grep @feature-passport`), both passing, with a fingerprint of `fixtures/participant` and `participant/progress.yaml` taken before and after (unchanged). The fingerprint is the SHA-256 of the `shasum -a 256` lines (hash and path) for those files, sorted by path, cut to 16 characters |
| `screenshots/validated-state.png` | The Progress panel, captured once, after the last assertion passed |
| `logs/failure-run.txt` | The deliberately failing run: a two-line reproduction summary, then the full output |
| `logs/failure-trace.zip` | The Playwright trace of that failing run |
| `screenshots/failure-state.png` | The page when the failing run failed |
| `validation/` | The quest checker's records (see below) |

## How to reproduce the behavior

From the repository root, with `gtq` and Node installed:

```
cd participant && npm ci && npx playwright install chromium
cd tests/playwright && npx playwright test --grep @feature-passport
```

`npm ci` installs the exact versions in `package-lock.json`. `npx playwright install
chromium` downloads the browser this Playwright version uses, if it is not already there.

The deliberate failure:

```
GTQ_PLANTED_FAULT=claimed-counted-as-verified npx playwright test --grep @feature-passport
```

That switch makes the fixture server show the claimed total as Verified XP in the passport's
Progress panel. It changes only the served copy of that page. It does not change the
application. The run fails at the first assertion: expected "20", received "50". A
misspelled fault name stops the run with an error naming the known faults, rather than
running the test with no fault.

**What the failing run tells a reviewer who has not seen the test:** the error names the
Progress panel's Verified XP value and the expected and received numbers, so it says that
verified XP included unreviewed work. The screenshot shows the Progress panel reading 50
while the sidebar still reads 20. The trace shows the page at each step.

## What was tested or validated

- The test passed twice in a row against the fixture, and the fingerprint of the fixture and
  of `participant/progress.yaml` was the same before and after (`logs/test-run.txt`).
- The test failed on the planted fault, at the Verified XP assertion, which is the one
  meant to catch that bug (`logs/failure-run.txt`).
- **Quest checker (`validate-playwright-quality`), latest run: `warning`, which counts as a
  pass.** Assertions: pass. Waits: pass. Failure evidence: pass. Selectors: a low warning,
  "No role, label or text query was found". The checker reads only files with "test" in
  their name, and in this test the role and text queries are in the page model, which the
  quest asks for. They were not moved into the test to clear the warning.
- **An earlier checker run in `validation/` failed.** At that point Playwright was installed
  in `participant/tests/playwright/node_modules/`, and the checker read Playwright's own
  library files there as if they were tests. The failures named only files under
  `node_modules`. Moving the install up to `participant/` fixed it, and the failing run's
  record is kept as history. A fix to the checker has been proposed to Beau as a separate
  task. It has not been made, and no issue or pull request records it yet.

## Remaining limitations

- The sidebar's Verified XP is not checked. The failure screenshot shows the gap: the
  planted fault changed only the Progress panel, and the sidebar still read 20.
- There is one test, so "runs in any suite order" was not tested beyond running it alone
  with `--grep`.
- The planted fault edits the served HTML. It simulates the bug on the page; it is not a
  defect in the application's XP calculation.
- The site is built from this repository's curriculum. The assertions avoid totals that
  depend on how many quests exist, but a change to the passport's wording, such as the
  "Claimed: N · Verified quests: N" line or the "Progress" heading, would break the test.
- The page shows each total as a label (role "term") and a number (role "definition") with
  no named group around them. `PassportPage.total()` finds the pair by its visible text, the
  label followed by a number, then reads the number by role. If a total ever showed
  something other than a number, the test would fail with "element not found" rather than
  showing the wrong value. That is inferred from the locator, not run.
- The Jira Jungle state check is a substring match (`toContainText("1 evidence ready")`).
  The independent review served "11 evidence ready" and the test still passed.
- `serve-fixture.mjs` empties one fixed temporary folder at start-up, so two runs at the same
  time would overwrite each other's fixture copy. This was inferred from the code, not run.
- `screenshots/validated-state.png` shows the Progress panel only, not the Jira Jungle card
  the last two assertions check.
- The test needs `gtq` on the PATH (or `GTQ_CLI` set to another command) and Node.

## Independent review

One independent review (a separate AI agent, given the quest and the files, not this
document's conclusions) ran on 2026-10-30. It reran both commands above with the same
results, planted six faults of its own in the served page, and found that four of them fail
the test (Verified quests, Claimed XP, the Jira card's verified count, and its evidence-ready
state) and two pass it (the sidebar's Verified XP, and "11 evidence ready"). Those two are
listed under "Remaining limitations". It also ran the test four times at once
(`--repeat-each=4 --workers=4`): four passed, and the repository's `git status` was the same
before and after. Its one required correction was the earlier wording about the checker fix,
corrected above.

The review ran before one change: `PassportPage.total()` used an XPath step
(`following-sibling::dd[1]`), which was replaced with the text-and-role locator described
under "Remaining limitations". After the change, the two passing runs, the planted-fault
run and the quest checker were run again, and those are the records saved here. The
review's own planted faults were not rerun against the new locator.

## Code sweep

A second independent agent swept the test code on 2026-10-31, with a time limit. It found
no way for the test to pass with the business rule broken beyond the gaps listed above, and
five smaller defects in the fixture server and docs. All five were fixed, each fix was shown
working, and the passing, failing and checker runs were then repeated; the records here are
from after the fixes.

| Defect | Fix, and how it was shown |
|---|---|
| A malformed URL (`/%E0%A4%A`) crashed the fixture server | Now answers 400 and keeps serving: the bad request got 400, the next one 200 |
| A misspelled `GTQ_PLANTED_FAULT` ran the test with no fault, and it passed | An unknown fault name now stops the server with an error naming the known faults; the misspelled run stopped before the test |
| If the passport's markup changed, the fault failed on every request and the run waited out its start-up timeout | The server checks the markup once before serving and stops with a message naming the file; shown with a build whose "Claimed XP" label was changed |
| The reproduce steps had no browser install and used `npm install` | Now `npm ci` and `npx playwright install chromium` (above); both ran and exited without error on this machine, where the browser was already installed |
| `PORT=abc` was not checked; the label in `total()` went into a regular expression unescaped; the fault matched any path ending in `passport/index.html` | `PORT` is checked in both the server and the config; the label is escaped (a label with parentheses matched itself and not a near miss); the fault matches the passport page's exact path |

## Reflection

If this test failed tomorrow, the team could decide not to trust the passport's verified
numbers until the cause was found, because the failure says verified XP disagrees with the
reviewer-approved record. A failure on the Jira Jungle card instead would point at how
unreviewed work is shown, which matters less for trust but still misleads.

## Sensitive values

The test data is the repository's fictional fixture participant. No credential, token,
customer name or private ticket is used. The text logs replace the home folder path with
`~`. The trace file (`logs/failure-trace.zip`) still holds absolute file paths that include
the computer's login name. It holds no credentials. Trace files are binary and are not
covered by the application's secret scan.
