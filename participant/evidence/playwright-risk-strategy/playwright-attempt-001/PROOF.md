# Proof · playwright-risk-strategy

Attempt: `playwright-attempt-001`

Decisions by Tom Carter; wording, the check script and its tests drafted with Claude (Claude Code),
10-30-2026. Tixly and everything about it are invented; no application was touched.

## What was built

- **Twelve testable requirements** for the Tixly checkout: the quest 4 requirements, each vague or
  contradictory one rewritten with assumed answers to the quest 5 questions, one answer per
  question (the three answers used for the quest 6 stories are kept the same). One answer, for CHK-03, was added during this
  quest and is marked as such. Each requirement has an importance (7 High, 4 Medium, 1 Low).
- **A layered test strategy** with stated likelihood and impact scales, 28 risks, each with its
  scores, one layer and the reason for it, a ranking table, and two risks accepted as untested.
  Totals: 5 unit, 10 API, 10 UI, 1 manual, 2 untested.
- **A TypeScript check** that reads both files and checks the strategy is complete and consistent,
  including rebuilding the ranking from the stated rules and comparing it with the table.

## Where the important artifacts are

| What | Path |
|---|---|
| Requirements | `participant/context/playwright/requirements.md` |
| Strategy | `participant/context/playwright/strategy.md` |
| Check script | `participant/tests/playwright/tools/risk-strategy-check.ts` |
| Check output | `participant/evidence/playwright-risk-strategy/playwright-attempt-001/logs/strategy-check.txt` |

## How to reproduce the behavior

From the repository root, with Node 22.18 or later (it runs TypeScript directly; nothing to
install, and the script uses only Node's built-in modules):

```
node participant/tests/playwright/tools/risk-strategy-check.ts
```

It prints the same output as `logs/strategy-check.txt` (recorded with Node v22.23.3), which was
compared with a fresh run and is identical. It reads the two files and writes nothing. Exit status:
0 passed, 1 failed, 2 a file couldn't be read. Nothing in the output needed redacting: it shows only
repository-relative paths, the Node version, invented ids and counts, and the name I gave as the
person who accepted the untested risks.

## How the work meets the criteria

1. **Every requirement is covered or listed as untested.** All 12 appear in the strategy, and
   every one has at least one tested risk; the check lists which risks and layers cover each
   requirement, and verifies the sentence under the totals that says so. CHK-06 and CHK-12 also
   have one untested risk each.
2. **Likelihood and impact on a stated scale.** "How risks are scored" defines both scales from 1
   to 3, each level in words, and each risk gives both scores with the level it meets in brackets.
3. **One layer per risk.** Each risk has exactly one of unit, API, UI, manual or untested. Where a
   requirement needed checks at two layers, it became two risks (for example R-01, the 8-seat rule
   in a unit test, and R-27, the server applying it, in an API test).
4. **A reason for each layer, not only a label.** Every reason says why this is the cheapest
   layer that would fail, usually by naming what the cheaper layer can't see (for example R-05:
   availability is decided by the server, and the map only draws what the server reports).
5. **Browser risks separated from the rest.** The 10 UI risks are in "Risks that need a browser";
   the 16 unit, API and manual risks are in "Risks that don't need a browser". The check refuses
   a UI risk outside the browser section, or a unit or API risk inside it.
6. **Untested risks with the reason and who accepted them.** R-12 and R-21 are in "Accepted as
   untested", each with its reason and "accepted by Tom Carter, acting as the Tixly product owner
   for this exercise, 10-30-2026". No real product owner was involved.
7. **Another person could rebuild the ranking.** Likelihood is scored from the kind of logic a
   risk's own step involves (arithmetic, a time limit, more than one person or another system is
   3; a rule with a few cases is 2; a fixed value or message is 1), impact from what happens to
   the buyer, and the score, order and tie rules are stated. The check rebuilds the ranking from
   those stated rules and compares it with the table row by row. This was tested for real: in the
   first Copilot review, a reader applying the scales got different scores than I had given three
   risks (R-09, R-13 and R-22), because I had scored them by feel. The scales were right and my
   scores were wrong, so the scores were corrected, and a sentence was added to say a risk is
   scored for what its own step does.

## One risk moved to a lower layer

**R-15, the service fee worked out wrongly** (criteria 3 and 4). The team in the scenario would
test the fee by clicking through checkout in a browser: one seat count per run, slowly, reading
the amount off a page that changes, and still missing most counts. The fee is arithmetic in one
function, so R-15 is a **unit** test that checks every count from 1 to 8 in milliseconds. The
browser keeps only what lives in the page: R-16 checks the fee is shown as its own line with the
right amount, as one extra check in the single end-to-end checkout test (R-22). The same move put
the most serious risk, a seat sold to two buyers (R-20), at the **API** layer: two browsers can't
time their clicks closely enough to find it, while an API test can send both requests at once,
many times over.

## One risk accepted without testing

**R-21, checkout slowing down or showing errors with a few hundred buyers at once** (criterion 6).
None of the four layers can run hundreds of buyers at once; that needs a separate load-testing
tool and a test environment sized like the real one. A few hundred is a modest load for the
assumed answer to Q-01, and the part of CHK-12 where money or seats go wrong is tested in R-20.
I accepted it, acting as the product owner, with a stated trigger: revisit before any on-sale
expected to draw more buyers. (The other untested risk, R-12, is how the confirmation email looks
in different email apps: annoying if wrong, while its content is checked in R-10.)

## Reflection

**Which risk would I want a human to check even if a test existed?**

I'd want a tester to check three risks, even with their tests in place:

- **R-13:** a test can confirm the refund policy and the full total are on the screen, but not
  whether a first-time buyer would trust the page. A tester needs to look at it and judge how it
  feels.
- **R-03:** a test can measure the 5 seconds, but whether the seat map is really usable on a slow
  phone is a judgment. A tester should try it on a real phone.
- **R-28:** the automated test uses a fake payment provider, which only behaves the way we set it
  up to. A tester should also try it against the payment provider's test environment, where the
  delays and declines come from the real service.

What they have in common: a test confirms facts, and a person judges experience.

## What was tested or validated

- **The check on the real files:** PASSED, as recorded in `logs/strategy-check.txt`.
- **My prediction before recording:** PASSED, 12 requirements, 28 risks, 5 unit, 10 API, 10 UI.
  All matched; I didn't predict the manual and untested counts (1 and 2).
- **Strict type check:** the script was type-checked with TypeScript 6.0.3 in strict mode (with
  `noUncheckedIndexedAccess` and `erasableSyntaxOnly`, so it runs under Node's type stripping).
  The compiler was installed in a temporary folder, not in this repository, so the hand-in stays
  install-free. The first type check found seven places where a value was assumed to exist; all
  were made explicit.
- **Tests of the check itself (kept locally, not handed in):** 91 altered copies of the two files,
  each expected to fail in one named way (or to pass, for the documented limitation and for
  formatting that must stay allowed), with 0 unexpected results; and 43 deliberately broken
  copies of the script, each with one rule switched off, all of which those tests caught.
- **Copilot review in a practice pull request in my own fork, over 9 rounds.** No High findings.
  10 Medium findings, all reproduced before fixing and all fixed: most were ways a badly formed or
  disguised file could still pass (a mistyped heading, rules hidden in an HTML comment, a second
  scale, an empty-looking link). After round 2, I switched the reader to an **allowlist**, so
  every line must be in a form the format allows, the same decision as quest 5. 11 Low findings
  about the strategy itself, which I decided one by one; they added R-23 to R-26, made the
  doors-open boundary exact, corrected three scores and widened R-28. When a review listed nothing
  new, I probed its summary: that found the unchecked totals sentence, the server-side 8-seat
  limit (R-27) and a hold expiring while its payment is processed (R-28, with the CHK-03 answer).
  The final round listed no issues.

## Stretch goals

Not attempted: a run-time estimate for each layer, and how the strategy changes if the release is
next week.

## Remaining limitations

- **The check proves the strategy is complete and consistent, not that its judgments are right.**
  It can't tell whether a score, a layer or a reason is the right one (it requires a reason of at
  least 8 words, which rules out a bare label), or whether other prose contradicts the stated
  rules: a plain sentence such as "ignore that; rank by likelihood alone" passes. Words in prose,
  such as "twelve requirements" in the introductions, aren't checked either.
- **The check reads one exact format.** Anything else is reported rather than interpreted. From
  the fourth Copilot round, I set a stop rule: a further way to disguise text in Markdown is a
  documented limitation, not another fix; plain mistakes are still fixed. The last review's
  summary mentioned further areas without listing an issue; under that rule they weren't
  investigated.
- **This is a strategy, not tests.** The quest asks what to test and where; no unit, API or UI
  test exists yet, and the reasons describe the tests that would be written.
- **Synthetic requirements and decisions.** Every assumed answer is invented, and the risks
  accepted as untested were accepted by me acting as the product owner; with a real team, the
  product owner would accept them.
- **Repeating the type check** needs the TypeScript compiler, which isn't in this repository.

## Sensitive values

No secret, token, customer name or private ticket content is in this hand-in. Tixly, its
requirements and every answer are invented for the exercise, and no real business rules are
included. The app's secret scan found nothing in these files.
