# Proof · playwright-multi-tag-run

Attempt: `playwright-attempt-010`

Decisions, predictions and the answers below are Tom Carter's; the table, the tool, the logs and
these notes were drafted with Claude (Claude Code) from his answers, 11-12-2026 to 11-13-2026.
Everything runs against the local Tixly demo app with made-up data; nothing is sent anywhere.

## What was built

- **The selections table** (`context/playwright/selections.md`): seven named selections, each with
  an expression in plain words, its purpose and the exact tests it should choose (as `<file> ›
  <title>`). `every-change` (`@fast`, a single tag, 26 tests), `safe-pipeline` (`@fast and
  @read-only`, an intersection, 15), `before-saving` (`@events or @order-review`, a union, 14),
  `shared-environment` (`not @writes-data`, an exclusion, 15), `high-risk-safe` (`@risk-high and not
  @writes-data`, 10), `orders-service` (`@saved-orders and @layer-api`, 3) and `slow-read-only`
  (`@slow and @read-only`, which matches nothing on purpose: the only slow test changes data).
- **The selection tool** (`tests/playwright/tools/select.ts`): `node tools/select.ts <name>` reads
  the selection from the table, prints its name, purpose, expression and the exact Playwright
  command it becomes, lists the tests Playwright would choose without running anything, compares
  that list with the table, and stops if they differ or if nothing matched; only then it runs
  exactly those tests and accounts for every listed test (passed, failed, skipped or not run),
  checking that nothing else ran. Before any selection it refuses to go on if a test's title, a
  group's title or a test file's path contains "@", since Playwright's `--grep` matches against all
  three and would read it as a tag. `--list-only` stops after the check. Expressions use whole tags
  joined by `and`, `or` and `not`; each tag must be in the tag scheme, and is matched only as a
  whole tag, never as part of a longer tag or of a word in a title.
- **The README and setup check** describe the selections and the tool and track the new tool (37
  project files instead of 36).

My decisions:

- **A selection tool driven by the table,** rather than typing Playwright commands by hand: the
  check before running is built in, so nothing runs that wasn't listed and checked first.
- **Seven selections,** each with a real purpose, including the quest's scenario (`safe-pipeline`:
  fast checks that never change data) and the safety rule (`shared-environment`: no write test).
- **Plain-words expressions** that the tool turns into Playwright's patterns, rather than writing
  those patterns by hand: an "and" in Playwright needs a pattern such as
  `^(?=.*@fast)(?=.*@read-only)`, which is easy to get subtly wrong.
- **An empty selection is always an error,** even when the table expects it to be empty.

## How I verified a selection before running it

I listed each selection first and matched it to the table (criteria 5 and 6). The tool lists what
Playwright would choose without running anything, compares it with the exact tests the table
expects, and refuses to run on any difference, on a test listed twice, or on an empty result
(criterion 7). Only when the listing matches does it run, and afterwards it accounts for every
listed test and checks that nothing else ran.

## Reflection: what happens in your pipeline if a selection quietly matches zero tests?

The pipeline shows green while testing nothing. By default Playwright stops an empty run with "No
tests found", but with `--pass-with-no-tests` the same empty run succeeds
(`logs/execution-run.txt`). A near-miss can also go the other way: on the way, a plain `@risk`
pattern, a tag that doesn't exist, matched all 27 tests by matching the start of `@risk-high`,
`@risk-medium` and `@risk-low`; the tool only ever matches whole tags.

## Where the important artifacts are

All paths are under `participant/`.

| What | Path |
|---|---|
| The selections table | `context/playwright/selections.md` |
| The selection tool | `tests/playwright/tools/select.ts` |
| The tag scheme it uses | `context/playwright/tag-scheme.md` |
| README, setup check | `tests/playwright/README.md`, `tests/playwright/tools/project-setup-check.ts` |
| The list run | `evidence/playwright-multi-tag-run/playwright-attempt-010/logs/list-run.txt` |
| The execution run | `evidence/playwright-multi-tag-run/playwright-attempt-010/logs/execution-run.txt` |

## How to reproduce the behavior

With the project set up as its README says (`npm ci --engine-strict`, then `npx playwright install
chromium`), from `participant/tests/playwright`, with a made-up key for the demo app's orders
service:

```
export TIXLY_API_KEY=$(openssl rand -hex 16)
node tools/select.ts safe-pipeline --list-only
node tools/select.ts safe-pipeline
node tools/select.ts slow-read-only
```

The first lists the 15 tests and reports that they match the table; the second runs them; the third
reports that the selection matched no tests and exits with an error, without running anything.

## How the work meets the criteria

1. **A single-tag selection runs only the tests with that tag:** `logs/execution-run.txt`,
   `every-change` (`@fast`): 26 listed, matching the table's 26 `@fast` tests; 22 ran and passed,
   and 4 were skipped (the coupled pair and the cleanup proofs, which only run when asked).
2. **An intersection runs only tests having every named tag:** `safe-pipeline` (`@fast and
   @read-only`): the 15 listed match the table, and those 15 ran and passed. `orders-service` and
   `high-risk-safe` are listed and matched too (`logs/list-run.txt`).
3. **A union runs tests having any of the named tags:** `before-saving` (`@events or
   @order-review`): 14 listed, matching the table, and 14 ran and passed.
4. **An exclusion removes tests having the excluded tag:** `shared-environment` (`not
   @writes-data`): 15 listed, none of them a write test, matching the table, and 15 ran and passed.
5. **The list of selected tests is checked before execution:** every run in `logs/execution-run.txt`
   shows the listing and "The listing matches the N expected tests." before "Running them now", and
   ends with "Every listed test is accounted for (it ran or was skipped), and nothing else ran."
6. **The listed set matches the expected set in the table:** `logs/list-run.txt`, all six non-empty
   selections: "The listing matches the N expected tests."
7. **A selection matching no test is reported, not treated as a pass:** `slow-read-only` is refused
   in both logs: "matched no tests, so nothing was run. An empty selection is never a pass.", exit
   1.

## What was tested or validated

- **The list run** (`logs/list-run.txt`, 11-13-2026, 9:39 AM) and **the execution run**
  (`logs/execution-run.txt`, 11-13-2026, 9:40 AM to 9:40 AM): as described under the criteria; the
  real orders file was byte for byte the committed one afterwards, the demo app's key appeared in
  the full output of none of the 16 commands the recording ran (the 14 in the logs and the 2 version
  checks in their headers), and the repository's credential scan of both logs found 0.
- **Plain Playwright on the empty selection** (`logs/execution-run.txt`): "Error: No tests found",
  exit 1, by default; with `--pass-with-no-tests`, exit 0. The tool refuses it either way.
- **Whole-tag matching was checked by hand first:** the whole-tag pattern for `@slow` listed only
  the one slow test, and the "and" pattern for `@saved-orders and @layer-api` listed exactly the 3
  expected tests, while a plain `@risk` pattern listed all 27 and the whole-tag `@risk` none.
- **My predictions:** right that `safe-pipeline` and `shared-environment` would each choose about 15
  (both exactly 15, the same set, since every read-only test is also fast), that all seven listings
  would match the table, and that `every-change` would run 22 and skip 4. Wrong that plain
  Playwright treats an empty selection as a pass: by default it reports an error; it only passes
  with `--pass-with-no-tests`.
- **The setup check passes** with 37 project files and no credential found.
- **Reviews:** my own review before the AI review made the tool tell a selection that matched
  nothing apart from a listing that failed, and read the scheme's tags the same way as the tag
  check. Then an AI code review (Copilot) on a practice pull request, 5 rounds, every finding
  reproduced before it was fixed and both logs recorded again after each code change; the 4th round
  reported no open issues, and a 5th, on the final wording of this PROOF, recommended approval. It
  found real problems: a test file named like a tag (`@read-only.spec.ts`) let a write test into
  `safe-pipeline`, because Playwright's `--grep` also reads file paths; an `@` in a test's title
  could pull it into a selection; a tag followed by punctuation (`@fast.extra`) counted as `@fast`;
  an "and" selection missed a test inside a group whose title has a line break; the table was read
  only up to a blank line, and a test written twice in it passed; and a failed listing or a run
  whose tests never started could look like an empty selection or a plain mismatch.
- **This quest has no automatic checker.** The criteria above were checked against the files and the
  two logs.

## Stretch goals

- **Fail the run when a selection is empty:** done; the tool refuses an empty selection with exit 1,
  whatever Playwright's own settings.
- **Print the selection and the reason with every run:** done; every run starts with the selection's
  name, purpose, expression and the Playwright command.

## Remaining limitations

- **The table has to be kept up to date.** When a test is added or re-tagged, its selections'
  expected tests change too, and the tool refuses to run until the table is updated. That is the
  point, but it is work.
- **The expressions are simple:** tags joined by only `and` or only `or`, with `not` only after
  `and`; no brackets and no mixing of `and` and `or`.
- **Tests are named by file and title,** so two tests with the same title in one file would look the
  same; the tool reports a test listed twice rather than guess.
- **A selection is only as safe as the tags:** `shared-environment` leaves out write tests by their
  `@writes-data` tag, so a write test tagged `@read-only` by mistake would be included.
- **The check for `@` in titles and file paths uses a first listing of every test.** If that listing
  fails, the check can't see every title; the selection's own listing then fails too (it loads the
  same files), and the tool stops on a failed listing, so it can't report success. The last review
  round asked a person to keep an eye on this.
- **One browser (Chromium).**

## Sensitive values

No password, token, customer name or private ticket content is here. The only credential is the demo
app's API key: made up, new for the recording, set in the environment and never written down; the
logs show it in none of their command outputs, and the credential scan of both logs found 0. Every
name in the demo app and the logs is made up, and the logs show personal home-folder paths as `~`.
