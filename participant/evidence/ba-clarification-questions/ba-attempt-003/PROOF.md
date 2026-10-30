# Proof · ba-clarification-questions

Attempt: `ba-attempt-003`

## In plain words

My previous quest found 12 problems in a set of checkout requirements for a made-up ticket app
(Tixly). Sending a product owner 12 problems is how the quest's scenario goes wrong: they answer a
few, and the one that would have changed the design waits. So I turned the findings into questions
and kept only the ones where the answer changes what gets built. Each question lists the answers it
could get and the different work each answer leads to, so the product owner can see why it's worth
their time. The questions are ordered by how much of the work depends on them. A small program
checks that every question is traceable to a finding and complete.

| | Result |
|---|---|
| Findings it started from | 12, verified in the previous quest (numbered F-01 to F-14; F-05 and F-08 were dropped there) |
| Questions | 13, each with 2 or 3 answers and the work each leads to |
| Dropped | 1, with the reason its answer changes nothing |
| Every finding accounted for | Yes: asked, dropped, or both (F-09, rewritten) |
| My prediction of the checker's result | Matched on every count (see criterion 6) |
| Sent to anyone | Nothing (criterion 7) |

## What was built

- **The questions**, `participant/context/clarification/questions.md`: 13 questions in order, each
  citing its finding, with its possible answers, the work each answer leads to, and why it sits
  where it does.
- **The dropped list**, `participant/context/clarification/dropped.md`: the question I dropped and
  why every answer leads to the same work.
- **The checker**, `participant/tools/check-questions.py` (version 2.2.0): it reads the verified
  findings and both lists, and checks every link, answer, work line, question and position. It
  ends PASSED or FAILED and names every problem. It reads the findings with the previous quest's
  verified checker, so "a finding exists" means exactly what it meant there.

**My test for every finding:** if the product owner answered one way, then the other way, would the
developer build something different? If yes, it's a question. If both answers lead to the same
code, it's curiosity, not clarification, and it's dropped (the quest's hint).

My decisions:
- **Kept 13, dropped 1.** I considered dropping three and kept two of them because my own test said
  their answers change the work (criterion 4 below).
- **The order:** whole-system questions first, then money flows, then single screens, then small
  additions; within a group, the one with more work riding on it goes first.
- **A word limit of 25** for "short enough to answer without a meeting". The longest question is
  18 words.
- **One gap per question.** The reviewer's lesson from my last quest. The gift card finding (F-03)
  became two questions, because whether the leftover balance stays and whether a buyer can use part
  of a card are different decisions with different work.

I built this with Claude (Claude Code). Claude drafted the wording of the questions, answers and
work lines from my decisions, the checker and this proof, and explained each step. Every keep,
drop, split and position is my call.

## Where the important artifacts are

| Artifact | Path |
|---|---|
| Findings (from the previous quest) | `participant/context/ambiguity/findings.md` |
| Questions | `participant/context/clarification/questions.md` |
| Dropped list | `participant/context/clarification/dropped.md` |
| The checker | `participant/tools/check-questions.py` |
| The check run | `participant/evidence/ba-clarification-questions/ba-attempt-003/logs/question-check.txt` |

## How to reproduce the behavior

From the repository root. It reads the three files, writes nothing and sends nothing:

```bash
.venv/bin/python participant/tools/check-questions.py \
    --findings participant/context/ambiguity/findings.md \
    --questions participant/context/clarification/questions.md \
    --dropped participant/context/clarification/dropped.md
```

Expected: `result: PASSED (exit status 0)` with 12 findings, 13 questions and 1 dropped. Change a
question's finding to one that doesn't exist, delete a Work line, or copy one answer's work into
another, and it fails, naming the question.

## Why 13 questions from 12 findings isn't the thirty-question problem

The quest's scenario is a product owner who gets thirty questions, answers four, and misses the one
that would have changed the design. My list ended with more questions than findings, so I checked
it against that scenario rather than against a count. Every question passed my test: its answers
change what gets built. What protects the product owner is the order and the size of each answer.
If they answer only the first four, those are the four that shape the whole system and the money
flows. And each question can be answered in a few words by picking one of the listed answers, so
answering all 13 takes minutes, not a meeting.

## How I ordered the questions

The quest asks for the questions to be ordered by how much of the work depends on them (criterion
6). I put them in four groups, largest first:

1. **The whole system** (Q-01, Q-02): how many buyers at once, and what "handling" them means. These
   shape the design of everything; never selling a seat twice has to be built in from the start.
2. **Money flows** (Q-03 to Q-06): the refund deadline, how refunds are paid, whether a gift card
   keeps its leftover balance, and whether a refund can be denied.
3. **Single screens and flows** (Q-07 to Q-11): what happens after a declined payment, using part of
   a gift card, the seat map's load time and the conditions it's measured under, and whether the
   decline message says why.
4. **Small additions** (Q-12, Q-13): what makes checkout feel trustworthy, and whether a refund
   needs a reason.

Copilot's review caught two places where my order broke my own rule, and I moved them: the refund
deadline had been first, above the whole-system questions, and partial gift card use ("one field on
the checkout screen") had been above two larger flows. Each question's "Why this position" line
says why it sits where it does.

## The question I rewrote

**F-09, the declined-payment message.** My first question was "What does the message say when a
payment is declined?" Testing it against my rule: any wording is the same screen and the same code,
only the text differs. So the answer changes nothing, and that question is dropped (D-01). But the
finding still mattered, so I asked the part that does change the work:

> Should the decline message say why the payment was declined, or just that it was? (Q-11)

"Just that it was" is one fixed message. "Say why" means reading the decline reason from the
payment provider and showing a different message for each. That's why F-09 shows as both asked and
dropped (criteria 3 and 4).

## What was tested or validated

Against the acceptance criteria:

1. **Each question links to a finding from the ambiguity review:** every question cites one finding
   id, and the checker fails if it doesn't exist in `findings.md`. It also fails if any finding is
   neither asked nor dropped, so none is silently lost.
2. **Each lists at least two possible answers:** every question has 2 (Q-02 has 3), and the checker
   fails on fewer.
3. **Each possible answer leads to a stated difference in the work:** every answer is followed by
   its own Work line; the checker fails on a missing one or two that say the same thing. I added a
   third answer to Q-02 when Copilot pointed out the question offered "a response time" without
   saying what it would lead to.
4. **A question whose answers lead to the same work is dropped and listed as dropped:** D-01, with
   its reason. I also considered dropping two others and kept them, because my own rule said their
   answers do change the work:
   - **F-02, the conditions load time is measured under.** I first dropped it as a testing detail.
     Copilot argued, and I agreed, that "under 1 second on a slow phone at the largest venue" can
     need staged loading that a desktop on broadband doesn't. It's now Q-10.
   - **F-12, whether a refund needs a reason.** I wanted to drop it as minor, then saw that "yes"
     adds a field and "no" adds nothing: different work, however small. It's kept, and last.
5. **Questions are short enough to answer without a meeting:** each is one sentence of at most 25
   words (the longest is 18), and each answer is a short phrase the product owner can pick.
6. **The questions are ordered by how much of the work depends on them:** see "How I ordered the
   questions". The checker confirms they are numbered in order with no gaps and each has a reason
   for its position; whether the order is right is my judgment. Before recording the run I
   predicted its result. My first two predictions (11 questions and 2 dropped, then 12 and 1)
   each matched the checker's output for the files at the time, which Claude ran but didn't record;
   then the files changed after review: F-02 moved to asked, then the gift card question was split. My final prediction, PASSED, 12 findings, 13 questions, 1 dropped, F-09 in both, matched
   the recorded `question-check.txt` on every count.
7. **Nothing is sent to anyone:** the questions are drafts in this repository. The checker reads
   files only; it makes no network calls and writes nothing.

**Review.** GitHub Copilot reviewed the checker and both lists on a practice pull request in my own
copy (Hoosiertom50/golden-thread-quest#5) over 10 rounds: 8 on the checker and lists, a ninth on
the complete package with this proof and the run log, and a tenth after the fix it led to. There
were no High findings in any round, and the last round found nothing new. Before every round Claude
re-read the whole program and ran its self-tests (171 cases by the end), and every finding was
reproduced before it was fixed.
- **On my questions:** Copilot caught F-02 being dropped when its answers change the work, Q-02
  offering an answer with no work, and two places where the order broke my own rule. I fixed all
  four. Separately, a review of the whole package for loose ends found that one question asked two
  things (the gift card), and I split it.
- **On the checker:** most findings were ways to disguise content so the checker missed it (web
  code, links, tables, invisible characters). After six rounds of blocking them one at a time, I
  switched the checker to an **allowlist**: it accepts only what it recognises and reports
  everything else. That closed every one of them at once, including ones Copilot hadn't tried, and
  made the program shorter. The package round then showed that a few invisible characters still
  got through, so the checker now also rejects everything on Unicode's own list of characters meant
  to be invisible. From round 3, I also decided that findings about how a question is
  phrased become documented limitations rather than more tuning (below).

The application's secret-scanning function found nothing in these files.

## Reflection: which dropped question do I most expect to be asked anyway?

The exact wording of the declined-payment message (D-01). I'd expect a product owner, a tester or
a writer to ask it anyway, because they care about what the buyer actually sees on the screen, and
the wording is what the buyer reads at a stressful moment.

What I'd say: it's worth deciding, and deciding together. The product owner, a writer and the
tester should agree the wording as a team. But it doesn't belong in this list, because whatever
they choose, the developer builds the same screen with the same code. So it doesn't need to hold up
the build: it can be settled in a short wording review before release, separately from the
questions that change the work.

## Remaining limitations

- **The checker can't judge the work.** It checks that two answers lead to different work *text*,
  not that the work is really different, and that every question has a reason for its position,
  not that the order is right. A person still reads every line; that judgment is mine.
- **Sentence ends after an abbreviation.** A statement ending in an abbreviation or initialism
  followed by a question ("We sell in the U.S. Can buyers retry?") reads as one sentence, because
  without grammar "U.S. Can" can't be told from "U.S. dollars". A dotted initialism also counts as
  two words toward the 25-word limit. I chose to document these rather than keep tuning; a person
  reads every question.
- **Disguised entries in the introduction.** An entry-looking line in the introduction written
  with character codes or look-alike characters (a different hyphen, a full-width letter) isn't
  reported as misplaced. It can't hide or fake anything in the list itself, which is always fully
  checked; under my stop rule, new disguises like this are documented rather than chased.
- **Plain text only.** Fields can't use any Markdown or web formatting, even harmless formatting:
  an identifier such as `gift_card` has to be written as "gift card". That's the cost of the
  allowlist, and I think it's the right trade.
- **The answers are examples.** Each question lists two or three likely answers to show why it
  matters; the product owner may give another.
- **Stretch goals not attempted:** a suggested default for each question with what it assumes, and
  grouping the questions by the person best placed to answer.

## Sensitive values

No real project, person, customer or credential is in this hand-in. Tixly and every requirement,
finding and question in it are invented, and nothing was sent to anyone.
