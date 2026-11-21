# Proof · playwright-test-inventory

Attempt: `playwright-attempt-013`

Written by Tom Carter with Claude (Claude Code), 11-18-2026. The choices below are Tom's, from his
answers to one question at a time; Claude wrote the code and this page from them.

## What was built

A generated inventory of every test in the project: 29 tests, each with an identifier, a purpose,
its tags, a source requirement, a value score, its file and line, and how it runs. Nobody edits the
inventory; `tools/inventory.ts` writes it from the tests themselves (criterion 1).

**Where purpose and source are written (Tom's choice: Playwright annotations next to the tags).**
Each test carries its own facts, so they change together with the test:

```ts
{
  tag: ["@events", "@risk-high", "@read-only", "@layer-ui", "@fast", "@locator-comparison"],
  annotation: [
    { type: "id", description: "T-02" },
    { type: "purpose", description: "The events page total for 2 Spring Concert tickets is $55.00, the $2.50 fee included on each ticket." },
    { type: "source", description: "CHK-07" },
    { type: "value", description: "low: same check as T-18; kept only to show brittle locators" },
  ],
}
```

- **Identifier (Tom's choice):** a short `T-<number>` written in the test, so it survives a change
  to the title. The generator itself rejects two tests sharing one.
- **Purpose (Tom's choice):** says *what the test proves*, not how it is written. The how is already
  in the title and tags. So tests that guard the same rule get the same purpose, and they show up as
  duplicates.
- **Source (Tom's choice):** a requirement from `participant/context/playwright/requirements.md`
  (CHK-01 to CHK-12), or `none: <reason>` for a **known gap**, listed apart from a test that is
  simply incomplete: a gap chosen on purpose is information, a missing source is a mistake.
- **Value score (Tom's choice):** worked out by the generator, on a three-level scale stated at the
  top of the inventory: **high** = `@risk-high` and a High-importance requirement; **low** =
  `@risk-low` and a Low-importance requirement or none; **medium** = everything else. A test can set
  a different score only with a reason (the `value` annotation), shown next to its score.

Every test now has all of these (criterion 2): 0 incomplete.

**How the generator reads the tests (Tom's choice: Playwright's own list).** It asks Playwright for
its list of tests (`npx playwright test --list`), for the main settings and for the
failure-evidence settings. Listing loads the test files to learn their titles, tags and annotations,
but runs no test, starts no browser and changes nothing. The files are also read as text for one
thing: whether a whole file is skipped unless a setting is switched on. It never writes to a test.

**Which tests (Tom's choice: all 29).** The 24 that run in the main suite, the 4 that are skipped on
purpose unless switched on (`coupled.spec.ts`, `cleanup-proof.spec.ts`), and the 1 that runs only
with the failure-evidence settings (`orders-list.evidence.ts`). A column says how each one runs.

**What it reports.**
- Two tests with the same identifier: **rejected**; nothing is written and the old inventory stays.
- No purpose, no source, a source naming a requirement that doesn't exist (stretch goal 2), or a
  value override without a reason: **incomplete** (criterion 3); the inventory is still written,
  with an Incomplete section.
- Two or more tests whose purposes match once letter case, spaces and punctuation are ignored:
  **possible duplicates** (criterion 4), for a person to decide.
- Tests by requirement, so a new teammate can find the tests for a requirement (criterion 7), and
  the requirements no test serves.
- Tests by value (stretch goal 1, by value only; not by age, below).

## What the inventory found

**4 groups of possible duplicates**, all real, and Tom's decision on each (a `value` override with a
reason; no test was deleted):

1. **$55.00 on the events page:** T-02 (brittle locators), T-07 (the project's first test) and T-18
   (stable locators) prove exactly the same rule. T-18 keeps its score, as the one built to last;
   T-02 and T-07 are set to low, each with its reason. This is the duplicate the quest's scenario
   describes: three tests that check exactly the same thing.
2. **Cancel from Your orders:** T-01 (API-assisted), T-06 (coupled), T-09 (isolated), T-28
   (UI-only). T-01 keeps high: quest 16 showed it is the one that checks the orders service itself,
   while T-28 passed against a Cancel that only pretended. The others are low, with reasons.
3. **A saved order appears on Your orders:** T-08 keeps its score (the one in the everyday suite);
   T-05 (coupled, skipped) and T-29 (evidence settings only) are low.
4. **Event not on sale:** T-15 keeps its score (it also tries a second event and checks every line);
   T-22 is low (it exists so the tag scheme uses every tag).

**10 known gaps**, tests no requirement covers: the 2 cleanup proofs (they test the test setup), 5
tests about saving or listing orders, 2 about events not on sale, and 1 about the site's name. The
requirements say nothing about these.

**8 of the 12 requirements have no test**, 5 of them rated High: CHK-03 (seat hold), CHK-04 (gift
cards), CHK-05 (refunds after doors open), CHK-11 (total equals the amount charged) and CHK-12 (no
seat sold twice), plus CHK-02, CHK-06 and CHK-10. The demo app doesn't have those features (no
payment page or seat map), but this is the picture the inventory exists to show: 10 tests serve a
Low-importance requirement while 5 High ones have none.

**A conflict between a requirement and the app.** CHK-01 says a buyer can hold *up to 8* seats; the
app allows 1 to 6, and two tests check that limit (T-14, T-23). If the requirement is right, both
tests guard a bug. Their purposes say so ("CHK-01 says up to 8, so the limit is unconfirmed"), and
they are linked to CHK-01 rather than hidden as a gap.

**A test that only partly covers its requirement.** T-27 (the smoke test) checks that the $2.50 fee
line is shown on the events page; CHK-09 asks for it on the payment page, which the app doesn't
have yet. Tom chose to keep it linked to CHK-09, with the gap in its purpose and its score set to
medium ("covers CHK-09 only on the events page, not the payment page it names"), so a High
requirement doesn't look fully tested when it isn't. (Found by the practice review, below.)

**Where the scores came out:** 3 high (T-01, T-10, T-26: all cancel tests, CHK-08), 15 medium and 11
low. Seven tests carry `@risk-high` and guard a High-importance requirement (the six CHK-08 cancel
tests and T-27); four of them were set lower by Tom's overrides (T-06, T-09 and T-28 as duplicates
of T-01, T-27 as partial coverage), which leaves 3 high.

**A disagreement between two earlier decisions.** Every total test is tagged `@risk-high` (the tag
scheme calls wrong money high risk), but traces to CHK-07, which `requirements.md` rates Low
importance. So, by the rule, they score medium, not high. Tom chose to keep the rule and note this to
revisit, rather than tune the rule until the scores look right.

## Where the important artifacts are

All paths are under `participant/`.

- The generator: `tests/playwright/tools/inventory.ts`
- The inventory: `context/playwright/inventory.md`
- The annotations: in each test file under `tests/playwright/` (and `tests/playwright/evidence-tests/`)
- The run record: `evidence/playwright-test-inventory/playwright-attempt-013/logs/inventory-run.txt`

## How to reproduce the behavior

From `participant/tests/playwright`:

```sh
node tools/inventory.ts                      # writes participant/context/playwright/inventory.md
node tools/inventory.ts --out <another file> # writes somewhere else
```

Exit 0: written, every test complete; 1: written, some tests incomplete; 2: nothing written (two tests
share an identifier, or it couldn't list the tests or read the requirements).

## What was tested or validated

The run record was made on 11-18-2026 at 10:03 AM, at commit 915123b with the quest-21 files
uncommitted (`logs/inventory-run.txt`). Its temporary test files were only listed by Playwright,
never run, and removed afterwards.

1. **Generated twice: identical** (criteria 1 and 5). Both runs: 29 tests, 0 incomplete, 10 known
   gaps, 4 groups of possible duplicates; the two files are the same 15,916 bytes. Nothing in the
   inventory depends on the date or time.
2. **Incomplete** (criteria 3 and 6). A temporary file with three tests: T-90 with no purpose, T-91
   with no source, T-92 with a source of CHK-99. The generator listed all three as incomplete
   ("no purpose", "no source", "source "CHK-99" isn't a requirement in requirements.md") and exited
   1. The inventory grew from 29 to 32 rows without any hand edit.
3. **Shared identifier: rejected.** A temporary test reusing T-07. The generator named both tests,
   said "Nothing was written" and exited 2; the real inventory's fingerprint and time were the same
   before and after.
4. **Same purpose: possible duplicates** (criterion 4). A temporary test whose purpose is T-20's in
   lower case, with " !" in place of the full stop: reported as a fifth group, T-20 and T-93.
5. **Afterwards:** the inventory generated again is identical to run 1, and the temporary file is
   gone.

Also: after the annotations were added, the full suite still ran with 24 passed and 4 skipped, the
evidence test still lists, and `tools/tagging-check.ts` and the named selections
(`tools/select.ts --list-only`) still pass.

**Reviews.** Claude re-read the whole generator before any outside review and fixed 3 things
(`T-7` and `T-07` accepted as different identifiers, Playwright's raw error text passed on, and the
setup check and README not knowing the new tool). Then a practice Copilot review ran 5 rounds: 13
findings (7, 4, 2, 0 and 0), each reproduced or confirmed first, and all 13 fixed. They included
the inventory being writable over a test file, a second identifier hiding a clash, and T-27 counting
as full coverage of CHK-09 (Tom's decision: keep it, marked partial). After the clean round 4, a check
of the areas its summary pointed to found 2 more (one list left unescaped, and an overstated count
in this page), both fixed and confirmed by the clean round 5.

## Reflection: what stops the purposes from becoming boilerplate?

Tom: **both the writing rule and the duplicate check.** The rule that a purpose says what is proved,
with the specific rule and value ("$55.00, the $2.50 fee included on each ticket"), keeps purposes
specific: a vague one can't name a value, so it stands out. The duplicate check catches it when
someone copies a purpose anyway: every test using the same generic text is flagged together. Each
covers the other's gap: the rule depends on people following it, and the check only catches
boilerplate once two tests share it.

## Remaining limitations

- **What Tom would do next:** ask the product owner whether the order limit is 6 or 8 (CHK-01),
  since two tests may be guarding a bug.
- **"By age" is not shown** (stretch goal 1 asks for value and age). The tests carry no date, and
  working one out from Git history would make the inventory depend on more than the test files.
- **Duplicates are found by identical purposes only**, after tidying. Two tests guarding the same
  rule but described in different words are not flagged; the writing rule (say what is proved, with
  its value) makes that less likely, not impossible.
- **The value score is only as good as its two inputs:** the risk tags and the requirements'
  importance. Where they disagree (the totals, above), the score shows it rather than settles it.
- **A requirement without an Importance line is left out.** The generator reads each requirement's
  importance from `requirements.md`; a requirement written without one would be missing from the
  inventory, and a test pointing at it reported as incomplete. All 12 requirements have one today.
  (Raised by Copilot's last two clean rounds, as an area for a person to look at.)
- **The skip column reads one pattern only:** a whole file skipped unless a setting is switched on.
  A test skipped another way would show as running normally.
- **Earlier quests' line numbers moved.** Adding the annotations made the test files longer, so line
  numbers quoted in earlier quests' evidence now point a few lines above the same code (for example,
  quest 20's proof check, quoted as line 91, is now line 98). What the tests do is unchanged.

## Sensitive values

No secret, token, cookie, customer name or private ticket content is here. The generator reads
test files and the requirements only; the requirements and the demo app are invented. The run used
a made-up API key, never written down, and the log shows the home folder as `~`.
