# Proof · ba-detect-ambiguity

Attempt: `ba-attempt-002`

## In plain words

I reviewed a set of 12 checkout requirements for a made-up ticket app (Tixly) the way I would
review a real ticket as a tester: for each one, could two testers write the same test from it? Where
they couldn't, I recorded which of four defects it has, the exact words that cause it, what a tester
couldn't decide, and the question that would settle it. A small program then checks that every
finding is traceable to the requirement text, so another reviewer can reproduce my calls from the
two files alone.

| | Result |
|---|---|
| Requirements reviewed | 12 (CHK-01 to CHK-12) |
| Findings | 12: 2 vague, 7 incomplete, 1 contradictory, 2 untestable |
| Left unflagged as sound | 5: CHK-01, CHK-03, CHK-06, CHK-09, CHK-11 |
| Planted defects found | 7 of 7, including the contradiction across CHK-05 and CHK-08 |
| My prediction of the checker's result | Matched on every count before I ran it, both times (see criterion 7) |
| Revised after the reviewer's questions | Yes: see "Revised after review" below |

## What was built

- **The requirements**, `participant/context/ambiguity/requirements.md`: 12 synthetic Tixly checkout
  requirements, some sound and some with planted defects of each type.
- **The findings**, `participant/context/ambiguity/findings.md`: the four defect types defined with a
  tie-breaker, 12 findings, and the 5 unflagged requirements with a reason each.
- **The checker**, `participant/tools/check-findings.py` (version 1.8.0): it reads both files and
  checks every quote, type, citation, question and requirement, then prints the findings by
  requirement and by type and the unflagged list with reasons. It ends PASSED or FAILED and names
  every problem.

**How the review was done: blind.** Claude wrote the requirements and sealed an answer key before I
started. The key stays outside the repository; its SHA-256 fingerprint,
`c55da7a9798d950d53d103a79c79c4dbb4fcb9c4a2cbc96c95e60c945ea11780`, was taken before my review and
matched afterwards, so the key wasn't changed after seeing my answers. A byte-for-byte copy is in this
hand-in as `answer-key.md`, so a reviewer can compute the fingerprint and compare it with the key's
calls. I reviewed all 12 cold, one at a time, and only then compared. Writing the requirements myself and then "finding" my own planted
defects would have proved nothing.

My decisions:
- **Tixly checkout** as the product: seat holds, gift cards, refunds, fees, confirmation email.
- **12 requirements** rather than the minimum 8, to leave room for sound ones and borderline cases.
- **A checker program**, not an AI judgment, as the review run: the judgment stays mine; the program
  proves it can be reproduced.
- **CHK-02 and CHK-12 each have two findings**, because different words cause different problems
  ("quickly" vs "must load"; "any number of buyers" vs "handle"). I first counted CHK-02's single gap
  twice and separated it into two distinct findings.
- **CHK-11 removed on a second look**, and **CHK-06 and CHK-09 removed after review** (below).

I built this with Claude (Claude Code). Claude drafted the requirements, the findings file from my
calls and wording, the checker and this proof, explained each step, and kept the answer key sealed
until I'd finished. Every classification and question is mine.

## Where the important artifacts are

| Artifact | Path |
|---|---|
| Requirements | `participant/context/ambiguity/requirements.md` |
| Findings and unflagged list | `participant/context/ambiguity/findings.md` |
| The checker | `participant/tools/check-findings.py` |
| The review run | `participant/evidence/ba-detect-ambiguity/ba-attempt-002/logs/review-run.txt` |
| The sealed answer key (byte-for-byte copy) | `participant/evidence/ba-detect-ambiguity/ba-attempt-002/answer-key.md` |

## How to reproduce the behavior

From the repository root. It reads the two files and writes nothing:

```bash
.venv/bin/python participant/tools/check-findings.py \
    --requirements participant/context/ambiguity/requirements.md \
    --findings participant/context/ambiguity/findings.md
```

Expected: `result: PASSED (exit status 0)` with the counts above. Change any quoted phrase in
`findings.md` by one word and it fails, naming the finding.

## How I avoided flagging sound requirements, and the finding I removed

The quest warns against flagging requirements that are fine, and my first instinct as a tester was
to ask a question about nearly everything. Three habits kept that in check:

- **"Would two testers write the same test?"** If yes, the requirement is sound even if I can think
  of a related question. CHK-01 and CHK-03 each state a trigger, a limit and a visible result, so I
  left them alone.
- **"Would the author say 'fair, I missed that', or 'that's not my requirement'?"** A question about
  a different feature is a gap in the set, not a defect in this requirement.
- **The tie-breaker.** If a number would fix it, it's vague; if no number could, it's untestable; if
  a whole situation is missing, it's incomplete. Writing this down made my types reproducible
  (criterion 7), and it's how a reviewer caught two of my types the wrong way round (below).

**The finding I removed (CHK-11).** CHK-11 says the total shown "must equal the amount charged, to the
cent". I first flagged it as incomplete: what happens if the two don't match? On a second look, a
mismatch is simply the test failing and a bug being logged. The requirement already gives a precise
pass/fail rule; asking Tixly to detect a mismatch and stop the charge would be a new feature, not a
gap. I moved it to the unflagged list with that reason (criterion 5). It turned out to be the answer
key's deliberate trap: precise wording that invites over-flagging.

Being honest about the rest: at first I flagged 9 of 12 requirements, where the key expected 7. I
kept CHK-06 and CHK-09 flagged until the reviewer pointed out that my own CHK-11 reasoning applies to
them too (below). Now I flag 7, the same 7 as the key.

## What was tested or validated

Against the acceptance criteria:

1. **Each finding names one of the four defect types:** every finding has exactly one `Type`; the
   checker rejects a missing type, a second type, or any other word.
2. **Each finding quotes the specific words that cause it:** every quote appears word for word in the
   requirement it cites (the checker matches whole words, across line breaks).
3. **Each finding states what a tester could not decide:** every finding has that line; the checker
   requires it.
4. **A contradiction cites both requirements:** F-07 cites CHK-05 and CHK-08 and quotes both; the
   checker requires exactly two citations and a quote from each for a contradiction, and one
   citation for any other type.
5. **Sound requirements are listed as unflagged with a reason:** CHK-01, CHK-03, CHK-06, CHK-09 and
   CHK-11, each with a reason; the checker fails if any requirement is neither flagged nor unflagged, or both.
6. **No finding rewrites the requirement; it asks a question:** three times my first wording was a
   fix ("we need to make sure…", "there should be an option…") and was turned into a question. The
   checker rejects a statement, or a question followed by a rewrite.
7. **A reviewer can reproduce the classification from the file alone:** the definitions and
   tie-breaker are at the top of `findings.md`. Before running the checker I predicted its full result
   from my review: PASSED, 2 vague, 6 incomplete, 1 contradictory, 2 untestable, unflagged CHK-01,
   CHK-03 and CHK-11. It matched on every count. After the revision I predicted it again: PASSED,
   2 vague, 7 incomplete, 1 contradictory, 2 untestable, unflagged CHK-01, CHK-03, CHK-06, CHK-09
   and CHK-11. To be fair, the new totals were already in this proof's table when I predicted, so I
   worked them out myself from the changes (11 findings, minus the 2 dropped, plus 2 from splitting
   F-04 and 1 from splitting F-09). The re-recorded `review-run.txt` matched on every count.

**Comparison with the sealed key.** I found all 7 planted defects, including the contradiction. I
missed two follow-up questions the key had: whether gift cards can be combined (CHK-04), and whether
seats stay held after a declined payment (CHK-10).

**Review.** GitHub Copilot reviewed the checker and both files on a practice pull request in my own
copy (Hoosiertom50/golden-thread-quest#4) over 9 rounds, until a round found nothing new, then once
more on the complete package with this proof and the run log, and once more after the revision below;
neither found anything new. There were no High findings in any of the 11 rounds. Before every round that followed a code change, Claude re-read the whole program and ran its
self-tests (105 cases by the end).
- **On my findings:** Copilot pointed out that F-10 and F-11 had their types the wrong way round
  under my own tie-breaker ("any number of buyers" is fixed by a number, so vague; "handle" names no
  expected result, so untestable), and that F-04 and F-07 read CHK-05 two different ways. I swapped
  the types and removed F-04's partial-refund question. The written definitions overruled both me and
  the answer key, which is criterion 7 doing its job.
- **On the checker:** the fixes that mattered were all ways a malformed review could still report
  PASSED: a requirement or finding placed outside its section, written as a heading, or typed in a
  slightly different format, and quietly skipped. The rest made the question check accept ordinary
  questions ("At what point…?", "Doesn't…?", "What's…?", quoted messages).

The application's secret-scanning function found nothing in these files.

## Revised after review

The reviewer (Gregg Reed) asked two questions before verifying, and both were right.

1. **CHK-06 and CHK-09 failed my own test.** I removed CHK-11 because preventing a mismatch would be a
   new feature, not a gap in that requirement. Whether the fee is taxed (CHK-09) is the same case: tax
   rules belong in their own requirement, and CHK-09 is precise about the fee line. So is whether
   checkout allows an order with no email address (CHK-06): that belongs to a buyer-details
   requirement. I'd already rated both as nitpicks in my reflection below, and kept them anyway. I
   removed both findings (F-05, F-08) and listed CHK-06 and CHK-09 as unflagged with that reason.
2. **Two findings mixed different gaps.** This is the reviewer's tip from my previous quest, that a
   list should only hold items sharing the same reason. F-04 held three refund gaps (how the refund is
   given, whether a reason is needed, when it can be denied), now F-04, F-12 and F-13. F-09 held the
   message wording and the buyer's next step, now F-09 and F-14. F-03 stays one finding: both its
   questions are about using the gift card's balance. Finding numbers were kept, so the reviewer's
   references still point to the same findings.

The result: 12 findings on the same 7 requirements the answer key flagged, each finding one gap.

## Reflection: how much of this would a stakeholder call nitpicking?

About a third. Of my original 11 findings, before the revision above, I'd expect a product owner to wave off 4 as nitpicks: the
conditions for measuring load time (F-02), a buyer with no email address (F-05), "feel trustworthy"
(F-06) and whether the fee is taxed (F-08). The other 7 would cost real money or real complaints if
the team guessed: the refund deadline (F-07), how refunds and gift-card balances work (F-03, F-04),
the declined-payment message and what happens next (F-09), how many buyers the system must support
and what "handle" means (F-10, F-11), and how fast "quickly" is (F-01). I first called F-01 a
nitpick, then changed my mind: without a number, the developer, the tester and the customer each
pick their own, which is exactly the quest's scenario.

Two of my nitpicks, F-05 and F-08, are requirements the answer key had as sound and I kept flagged
anyway. That's my tester's instinct: when I'm unsure, I'd rather ask than miss something. It's also
how a review starts to feel nitpicky to the person receiving it. The reviewer's question about those
same two showed it from the other side, and I dropped them.

How I'd tell for sure: both ways together. I'd ask the product owner, and I'd weigh what each one
would cost if it went wrong, or how much it would hurt the software overall. Asking catches what only
the business knows; weighing the cost keeps me from spending their time on the small ones.

## Remaining limitations

- **The question check reads a sentence's shape, not its grammar.** It accepts a question that opens
  like one and rejects statements, but a rewrite whose lead-in happens to contain a question verb
  ("When checkout is open, the map must load in 2 seconds?") still passes, as can a rewrite after a
  sentence that ends in "etc.". I decided to stop tuning this once Copilot's rounds kept finding
  narrower phrasings; a person still reads every question.
- **The checker proves traceability, not correctness.** It can't tell whether "vague" was the right
  call, only that the call is complete, consistent with its quote, and reproducible.
- **One file format.** Findings must follow the format in `findings.md` (one quoted phrase per
  `Words in` line, one question per `Question` line); anything else is reported rather than guessed.
- **Synthetic and small.** One requirements set, one reviewer.
- **Stretch goals not attempted:** scoring each requirement by the work needed to make it testable,
  and contradictions across two documents.

## Sensitive values

No real project, person, customer or credential is in this hand-in. Tixly and every requirement in
it are invented, and no finding criticises a named person's wording.
