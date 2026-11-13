# Proof · playwright-stable-locators

Attempt: `playwright-attempt-006`

Decisions, predictions and the answers below are Tom Carter's; the tests, the redesigned copy, the
count tool, the log and these notes were drafted with Claude (Claude Code) from his answers,
11-10-2026. Everything runs against the local Tixly demo app with made-up data; nothing is saved
or sent anywhere.

## What was built

Two versions of the same test, one with brittle locators and one with stable ones, and a
redesign that proves the difference.

- **The brittle test** (`brittle.spec.ts`): chooses 2 Spring Concert tickets and checks the
  total is $55.00, finding everything by how the page is built. Five locators, one of each kind,
  each labeled in a comment with its kind and how it breaks:
  1. **Position among siblings:** the card is "the 1st card on the page" (`article:nth-child(1)`).
  2. **Generated ID:** the ticket dropdown is `#r-7f3k2`.
  3. **Index in a list:** the price line is "the 2nd paragraph in the card" (`.nth(1)`).
  4. **Generated class name:** the fee line is `.css-q81zk`.
  5. **Long DOM path:** the total is `main > article > form > p`.
- **The stable test** (`stable.spec.ts`): the same check lines, word for word, with each locator
  replaced by one based on what a user sees, and a note beside each saying what it was and why
  the new one is stable. The stable test's locators also tie each item to the Spring Concert's
  card, which the brittle ones can't (see "What surprised me"):
  1. The card by its **role and name**, "Spring Concert".
  2. The dropdown by its **label**, "Number of tickets".
  3. The price line by its **visible text**, "Tickets from".
  4. The fee line by its **visible text**, "Service fee:".
  5. The total by its **role and hidden label**, a status named "Order total".
- **Two generated-looking names on the demo page** (`demo-app/index.html`): the dropdown's ID is
  now `r-7f3k2` (its label was relinked to match) and the fee line has the class `css-q81zk`, the
  kind of names a build tool makes up. Nothing a user sees changed, and the 8 earlier tests still
  passed afterwards, because they find the dropdown by its label and the fee line by its text.
- **The redesigned copy** (`demo-app-redesigned/`): a copy of the demo app with the same product
  built differently. A new event card, Summer Jazz Night, sits above the Spring Concert, priced
  differently ($40.00 tickets, $3.00 fee); a "Doors open 6:30 PM" line is added to the Spring
  Concert card; its form is wrapped in a new box; and a "new build" renamed the generated names
  (`r-9wq4d`, `css-2mv8p`). The Spring Concert still costs $25.00 plus $2.50 per ticket, and 2
  tickets still cost $55.00. The copy's review page also lists Summer Jazz Night, so the new event
  can be reviewed too. The original demo app was not changed by the redesign.
- **The count tool** (`tools/locator-count.ts`): a test stops at its first failure, so a failing run
  shows only one broken locator. This tries all ten locators on a running page and reports which
  still find the right thing (the Spring Concert's card, dropdown, price, fee or total), which find
  nothing, and which find the wrong thing. "Right" is judged by the role and name a screen reader
  announces, the element's own words and whether it is visible, so a harmless change to how the page
  is built (such as a different heading tag) isn't counted as a broken locator. It first checks that
  each locator's whole line still appears exactly in its test file, so the count can't drift from
  the tests.
- **The README and setup check** now describe the 10 tests and the comparison, and check the 6
  new project files (21 instead of 15).

My decisions:

- **The business check:** the order total for 2 Spring Concert tickets, $55.00, so the focus stays
  on how the test finds things, not on new logic.
- **Five brittle kinds, one each,** rather than the minimum of four.
- **One realistic redesign plus a count,** instead of five separate small changes: one designer's
  update breaks all five brittle locators, and the count proves every one broke, not only the
  first.
- **The new event has a different price,** so the brittle test's first check can't pass by
  accident on the wrong event (with the same price, that check passes on Summer Jazz Night).
- **Role, label and visible text only; no test IDs** in the app, so the stable test finds things
  the way a user would. I propose test IDs below instead.
- **Locators written in the two tests, not in the page models,** so the two files can be compared
  line by line. This is a deliberate teaching comparison; the page models and the tests that use
  them were not changed.
- **The redesign in a separate copy** kept next to the real demo app and handed in, so a reviewer
  can re-run it; the real demo app keeps passing.
- **Both tests stay in the normal suite.** Both pass on the real demo app; the brittle one is
  tagged `@locator-comparison` and its first comment says it is brittle on purpose.

## Which replacement I trust least, and why

**The price line (3) and the fee line (4).** They are found by their wording, "Tickets from" and
"Service fee:". A redesign that keeps the wording leaves them working, but if marketing or product
rewrites the wording, for example "Prices start at", the stable test breaks too. That is why
criterion 2 says visible text "that the user reads **and the team has agreed to keep**": these two
are only as stable as that agreement.

## Reflection: which locator can I not make stable without help from developers?

**The order total, and the price and fee lines.** Every locator on this page can be found somehow,
but without developer help these three can only be found by their wording, which could change. The
total is findable by role and name only because a developer added both: a "status" role and a hidden
label, "Order total". Without them, a test could still find it by its visible text, "Total:", but
that has the same weakness as the price and fee lines. That's why these are the three I'd ask
developers to give test IDs.

**Test IDs I would ask developers to add** (stretch goal): on **the price line, the fee line and the
total.** The price and fee lines depend on wording that could change, and the total's role and name
were added by a developer (otherwise only its wording is left), so a test ID the team agrees not to
change would make all three dependable. The card and the dropdown don't need one: their name and
label are things users read anyway.

## What surprised me

**The wrong-card result: a position-based locator can make a check pass while looking at the
wrong event.** After the redesign, "the 1st card" was Summer Jazz Night, not the Spring Concert.
Here the price check failed because the new event costs more (expected "Tickets from $25.00",
received "Tickets from $40.00"), and that message even reads as if the Spring Concert's price had
changed, which it hadn't. With equal prices, the price check passed on Summer Jazz Night, so it was
checking the wrong concert without knowing it. Here the test still failed: on the renamed fee line
in our redesign, and even with only the new card added, at the total, whose path then matched both
cards. But that was luck, not design: the price check itself never noticed. It goes further: with
the Spring Concert renamed, the brittle test still passed. Nothing in it ever looks for the event
it's named after.
The count shows the two ways the brittle locators broke: three found nothing (loud), and two found
the wrong thing (quiet), and the quiet ones are the dangerous ones.

## Where the important artifacts are

All paths are under `participant/`.

| What | Path |
|---|---|
| The brittle test | `tests/playwright/brittle.spec.ts` |
| The stable test | `tests/playwright/stable.spec.ts` |
| The demo page (two generated names added) | `tests/playwright/demo-app/index.html` |
| The redesigned copy | `tests/playwright/demo-app-redesigned/` |
| The count tool | `tests/playwright/tools/locator-count.ts` |
| README and setup check (updated) | `tests/playwright/README.md`, `tests/playwright/tools/project-setup-check.ts` |
| The run record | `evidence/playwright-stable-locators/playwright-attempt-006/logs/layout-change.txt` |

## How to reproduce the behavior

With the project set up as its README says (`npm ci --engine-strict`, then
`npx playwright install chromium`), from `participant/tests/playwright`:

```
npx playwright test --grep @locator-comparison
```

Both tests pass on the demo app. To see the redesign, start the copy in one terminal and run the
same tests against it in another:

```
TIXLY_DEMO_PORT=4199 node demo-app-redesigned/server.js
TIXLY_BASE_URL=http://127.0.0.1:4199 npx playwright test --grep @locator-comparison
```

The brittle test fails (expected "Tickets from $25.00", received "Tickets from $40.00") and the
stable test passes. With the copy still running, `node tools/locator-count.ts http://127.0.0.1:4199`
reports brittle 0 of 5 and stable 5 of 5; against the original demo app (started with
`node demo-app/server.js`), `node tools/locator-count.ts http://127.0.0.1:4173` reports 5 of 5 for
both.

## How the work meets the criteria

1. **At least four brittle locators, named by kind:** five, each labeled in a comment in
   `brittle.spec.ts`: position among siblings, generated ID, index in a list, generated class name
   and long DOM path.
2. **Each replaced by role, label, visible text or a test ID:** in `stable.spec.ts`, role and name
   (the card), label (the dropdown), visible text (the price and fee lines), role and hidden label
   (the total). No test ID was used (see my decisions).
3. **Each replacement has a stated reason:** the note beside each locator in `stable.spec.ts` says
   what it was and why the new one survives a redesign.
4. **The same business assertion in both tests:** the last seven lines (the check lines) of both
   tests are identical: the price line is shown and says "Tickets from $25.00", the fee line is shown and says
   "Service fee: $2.50 per ticket", choose 2, and the total is shown and says "Total: $55.00".
5. **After a layout change the brittle test fails and the stable one passes:**
   `logs/layout-change.txt`, section 1 (before: 2 passed) and section 3 (after, on the redesigned
   copy: the brittle test failed, the stable test passed). Section 5 adds the count: before 5 of 5
   for both; after, brittle 0 of 5 and stable 5 of 5.
6. **A search of the stable test finds no generated class name, nth-child or index-based
   locator:** section 4 of the log, with three searches using the same pattern. The whole file
   finds 2 matches, both in the notes that name the locator each line replaced ("Was: GENERATED ID
   ("#r-7f3k2")" and "Was: GENERATED CLASS NAME (".css-q81zk")"); a comment is not a locator. The
   code alone finds 0. The same search on the brittle test's code finds all 5 of its locators,
   which shows the search catches them.
7. **Another tester can follow the reason for each replacement:** each note in `stable.spec.ts` is
   written in plain words (what a user reads or sees), and each brittle locator's comment says how
   it breaks. The PROOF repeats the five pairs above.

## What was tested or validated

- **The run record** (`logs/layout-change.txt`, 11-10-2026, 11:07 AM): before the redesign both
  tests passed; on the redesigned copy the brittle test failed and the stable test passed; the
  searches and the count as described under criteria 5 and 6. The script that recorded it also
  checked each of these outcomes, and all were as expected.
- **My predictions before each run** were all right: the 8 earlier tests still passing after the
  generated names were added; the brittle and then the stable test passing on today's page (9,
  then 10 tests); after the redesign, brittle failing and stable passing, with expected $25.00 and
  received $40.00; and the count, brittle 0 of 5 and stable 5 of 5.
- **The whole suite** passes on the real demo app (10 of 10, log section 6), and the project-setup
  check passes (21 of 21 project files, log section 7).
- **Reviews.** My own review before each Copilot round, then 7 Copilot rounds on a practice pull
  request in my own fork (11-10-2026), every finding reproduced before anything was changed: 8
  findings, then 3, 3, 1, 2, then no open issues with one note (fixed), and the seventh recommended
  approval with no open issues. They corrected two of my own answers (the reflection and "What
  surprised me" both overstated), found that a hidden total passed the brittle test (both tests now
  check that the price, fee and total are visible), and hardened the count tool. On one point I
  pushed back in part: a role-only locator for the total still relies on a developer, because the
  "status" role is developer-added too. An independent review, given only the files and the quest,
  found no High or Medium issue; its Low findings and nits were fixed or are listed under "Remaining
  limitations".
- **This quest has no automatic checker.** The criteria above were checked against the files and
  the run record.

## Stretch goals

- **Propose the test IDs a developer should add:** done, above (the price line, the fee line and
  the total).
- **Count how many locators each approach needs to change:** done with `tools/locator-count.ts`.
  After this redesign, the brittle test needs all 5 of its locators changed; the stable test needs
  none.

## Remaining limitations

- **One redesign.** It breaks all five brittle kinds, but other changes would treat the stable
  test differently: reworded price or fee lines break it (see "Which replacement I trust least"),
  and a developer removing the hidden "Order total" label would too.
- **The generated names are imitations.** A real build tool may keep a generated name for a while
  or rename it after any change to the page, its styling or the tools; the risk is that no one has
  promised to keep it. Here the names were renamed by hand in the copy.
- **The count tool's idea of "the right element" has limits.** It recognizes each target by the role
  and name a screen reader announces, its words, and whether it's visible, as this page builds them.
  Copilot's later review rounds found several harmless ways to build the page that the tool didn't
  expect, and all were fixed (a different heading tag, other ways of labeling, a drop-down shown as
  an open list, capitals added by styling, a hidden line). Other unusual markup may need the tool
  updated; the tests themselves are the final judge. For the card itself, the tool recognizes the
  Spring Concert the same way the stable test does, by its name, so it can't catch the stable card
  locator finding the wrong card; it can only show it finding nothing.
- **The copy is a second set of files to keep in step.** If the real demo app changes, the copy
  doesn't follow; it shows one moment in time.
- **One browser (Chromium).**
- **Files from the project-setup quest changed again:** `demo-app/index.html` (the two generated
  names), and `README.md` and `tools/project-setup-check.ts` (the new tests and files). The quest
  app already notes the README and setup check as changed since that quest was approved; these are
  the changes.

## Sensitive values

No password, token, customer name or private ticket content is here. The tests use no credential,
and all data in the demo app is made up. The run record shows personal home-folder paths as `~`.
Every file in this evidence was scanned with the quest app's credential patterns: 0 findings.
