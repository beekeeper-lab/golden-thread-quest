# Proof · ba-detect-ambiguity

Attempt: `ba-attempt-002`

## What changed after the first review

This attempt was handed in once and sent back with two changes asked for. Both are made.

1. **F-11's type could not be reproduced from the findings file (criterion 7).** The first hand-in said so
   itself. The reviewer offered two ways out: add a rule for when a nearby phrase counts as speaking of a fact
   and run a fresh blind reader, or retype or withdraw the finding and record a blind read that reproduces all
   of the types. The participant chose the first, with the second as the fallback. The rule was added and a
   fourth reader ran. It gave F-11 the review's type only by an assumption, and it left another finding, F-06,
   unsettled, which every earlier reader had typed as the review did. So the rule was taken out again and
   **F-11 was withdrawn**. A fifth reader, given the file as it now stands, gave all nine findings the review's
   types. The whole of this is in "Criterion 7" below and in `logs/review-run.txt`.
2. **The folder name.** The quest names `participant/evidence/ba-detect-ambiguity/attempt-001/`. The
   application created the attempt as `ba-attempt-002`, which is where everything is. Copies of the two files
   the quest names, `logs/review-run.txt` and `PROOF.md`, are now at the `attempt-001` paths too, with a
   `README.md` there saying that they are copies.

## How this was made

An AI assistant (Claude) made the review and wrote the checker, the tests, the recording scripts and this
file, at the participant's direction. The work was done in small steps, each shown to the participant before
the next.

Several assistants took part, and it matters which did what.

| Who | What it did | What it could see |
|---|---|---|
| The author | Wrote the requirements set and an answer key. | Nothing of this work. It was told to plant defects and to say nothing of them in its report. |
| The reviewer | Made the review: a first pass, a second look, and the findings. | The requirements only, until both passes were written down. Then the answer key. |
| Five independent readers, one after another | Gave each finding a type, with the types taken out. | The requirements and the findings without their types. Nothing else. |

What the participant did themself:

- Chose to separate the author from the reviewer, over having one assistant write and review.
- Agreed the definitions of the four types, and the order they are applied in, before the reviewer had seen a
  requirement.
- Agreed each change to those definitions, and chose how to answer the first review.

**One thing must be said before any result.** The author, the reviewer and the five readers are assistants of
the same kind. They are likely to see the same things and to miss the same things. Agreement between them shows
that the review is consistent. It does not show that it is right. No person other than the participant has
read the requirements or the findings.

Everything in `review/` was written in the order described and is kept as it was written.

## How I avoided flagging sound requirements

Four things, in the order they were done.

**1. One question before any type.** "Would two competent testers, reading only this text, write the same
test?" If they would, there is no finding, however the wording looks. This is the quest's hint used as a gate.
It is what kept the review off the four requirements the author had built to look suspicious.

**2. A defined word is not a vague word.** A term fixed by the glossary or by another requirement is read with
that meaning. REQ-07 and REQ-10 say "promptly", the classic loose word, and the glossary defines it as within
60 seconds. REQ-02 speaks of "any date on which bookings are accepted", which REQ-05 fixes. REQ-03 leans on
"slot" and "opening hours", both defined. All four were left alone. The same rule cut the other way for
REQ-06: it says "shortly", and the glossary, which defines "promptly", does not define that.

**3. Every finding must say what goes wrong.** Each finding has a line, "If unanswered", for what happens if
nobody answers its question. A finding with nothing to put there is a remark about style. This is the
reflection question turned into a working rule.

**4. A second look, with one job.** Each first-pass finding was held to three tests: do the quoted words cause
the problem; would two testers write different tests; what goes wrong if the question is never answered. One
finding failed and was withdrawn. It is described below.

Every requirement left alone is listed in the findings file with the reason two testers would write the same
test for it (criterion 5). The checker refuses a review in which any requirement is neither flagged nor listed.

**How well it worked, measured against the author's key.** The author meant ten requirements as sound, four of
them traps. As first handed in, the review left nine of the ten alone, and all four traps, and flagged one the
author meant as sound, NFR-01. That finding has since been withdrawn. As the review now stands, all ten are
unflagged. I do not count that as the method working ten times out of ten: on NFR-01 it took a second review
and four more readers to get there.

## The finding I removed on a second look

**F-10, against REQ-05.** It is in `review/first-pass.md` as it was raised, and its withdrawal is in
`review/second-look.md`. Both were written before the answer key was opened.

REQ-05 says the system shall accept bookings "for dates from the current day up to and including 14 days
ahead". On the first pass I flagged it as incomplete, quoting "from the current day", because the text speaks
of dates and does not say whether a slot earlier today, already past, can be booked.

On the second look it failed two of the three tests.

- **The quoted words do not cause the problem.** "From the current day" is exact. The finding blamed words that
  are fine, which is what criterion 2 is there to prevent.
- **Two testers would write the same test.** Today is accepted. Day 14 is accepted. Day 15 is rejected with
  the stated message. That is everything REQ-05 claims, and all of it can be tested.

What is missing is a rule the set does not have. That is a gap in the set, and a finding is a defect in a
requirement's words. So the finding was withdrawn, REQ-05 was listed as unflagged, and the gap was kept as a
note under "Gaps in the set" in the findings file, where it is not counted.

The author's key, opened afterwards, has REQ-05 as sound.

A doubt that remains, raised by the first independent reader. It said of F-08, which I kept, that "for the
behaviour actually written two testers would write the same test, so it is a missing case, not a disputed
one". That is close to my reason for withdrawing F-10. The difference I rely on is that REQ-13's own action,
marking a room out of service, meets existing bookings as a matter of course, so a tester of that requirement
cannot say what the action should do. A past slot is not something REQ-05's action meets in the same way. The
line between a gap inside a requirement and a gap beside it is thinner than my second look made it sound.

### A second finding, removed later and for a different reason

**F-11, against NFR-01**, was not removed on the second look. I doubted it then, kept it, and noted that it was
the finding most likely to be called nitpicking. It was withdrawn after the first review, because two
independent readers could not settle its type and a rule added to settle it unsettled another finding. It is
recorded in the findings file under "Raised and withdrawn". The concern behind it is not withdrawn: NFR-01 does
not say how often each of its 50 members makes a request, and a person planning that load test would have to
choose. What failed was my ability to say which of the four types that is.

On the second look I should have weighed more heavily a sign I had already noticed: I could not say with any
confidence which type it was.

## The acceptance criteria, one by one

1. **Each finding names one of the four defect types.** Nine findings: two contradictory, two untestable, two
   incomplete, three vague. The checker refuses a finding with any other type, with two, or with none.
2. **Each finding quotes the specific words that cause it.** Every finding has a `Words` line. The checker
   looks for the quoted words in the requirement named, character for character. **Recorded**: with one word of
   a quotation changed, the review is refused.
3. **Each finding states what a tester could not decide.** Every finding has that line, and a line for what
   goes wrong if the question goes unanswered. The checker refuses a finding without either.
4. **A contradiction cites both requirements.** F-01 cites REQ-04 and REQ-12 and quotes each. F-02 cites REQ-14
   and NFR-04, which are in different documents, and quotes each. That second one is the stretch goal of a
   contradiction across two documents.
5. **Sound requirements are listed as unflagged with a reason.** Ten, each with its reason. The checker's count
   is in the log: 10 with a finding, 10 unflagged, 20 of 20.
6. **No finding rewrites the requirement; it asks the question that would resolve it.** Every finding ends in a
   question. None says what the requirement should say. The checker refuses a finding whose question does not
   end in a question mark or that uses one of a list of phrases for offering wording. That list cannot catch
   every way of doing it, so this criterion rests on the findings as written, which can be read.
7. **A reviewer can reproduce the classification from the file alone.** A blind reader given the file as it now
   stands gave all nine findings the review's types. Three of the nine rest on a judgment that the file names
   and cannot remove. See the next section.

## Criterion 7: what five independent readers found

The findings file opens with the definitions and the order they are applied in. To test whether that is
enough, each reader was given the requirements and the findings with every `Type` line removed, and asked to
type them from the definitions. From the second reader on, each was told to assume nothing and to say "not
settled" where the written words did not decide a case.

| Reader | What it was given | Types matching the review | How it got there |
|---|---|---|---|
| 1 | The definitions as first agreed. Ten findings. Free to fill gaps. | 10 of 10 | It called 5 close calls, settled by three assumptions of its own. |
| 2 | Those three written in. Ten findings. | 9 of 10 | 6 settled by the written words, 3 by an assumption. F-11 not settled. |
| 3 | Two more sentences, added to settle F-11. Ten findings. | 9 of 10 | 7 settled, 2 by an assumption. F-11 still not settled. |
| 4 | A rule the reviewer suggested. Ten findings. | 9 of 10 | F-11 matched, by an assumption. F-06 came unsettled. |
| 5 | The definitions reader 3 had. Nine findings, F-11 withdrawn. | 9 of 9 | 6 settled by the written words, 3 by an assumption. None unsettled. |

What this shows:

- **The first result looked best and meant least.** A reader allowed to fill gaps reproduces a classification
  by sharing the reviewer's habits, not by reading the file.
- **F-11 could not be typed.** The rule says a fact is absent when no word speaks of it at all, and nothing says
  how near a word has to be. "Making requests at the same time" speaks of the load. Whether it speaks of how
  often a request is made is not something the definitions decide. Two attempts to make them decide it failed,
  the second by moving the doubt on to F-06. So the finding was withdrawn and the definitions put back.
- **All nine that remain are reproduced by reader 5**, which had the file exactly as it now stands.
- **Three of the nine rest on a judgment.** F-02 is a contradiction only if "complete booking history" cannot
  reasonably mean "complete as far as records still exist": every strict reader had to assume that. F-06 is
  vague only if "work correctly" counts as speaking of which functions must work. F-07 is incomplete only if
  neither "prevented" nor "suspended" speaks of how a member can book again. The findings file names all three.
  A reader who judges one of them differently will give that finding another type.

So the claim I can support is this: a reader who applies the written definitions reaches the same nine types,
six of them without any judgment of their own and three by a judgment the file states. That is criterion 7 met
for the file as it stands, by one blind read, with those limits. It is not a claim that the definitions are
finished. Readers 3, 4 and 5 each pointed at the same two weak places, the word "reasonable" and the phrase
"speaks of it", and they are right.

A wider point, from readers 3 and 5, which I think is correct: where a finding raises two points, its type can
depend on how the reviewer worded the finding's question. Splitting such findings would classify more
reproducibly. I have not done that here, because it would change the findings after they were reviewed.

## What the comparison showed

The reviewer opened the author's key only after the first pass and the second look were written down. The log
sets the two side by side, worked out by the recording script from the two files.

- **All ten requirements the author meant as defective have a finding of the same type.**
- **All four traps were left alone**, and all ten requirements the author meant as sound are now unflagged.
- **One finding was not planted**: F-09, on REQ-13's "as unavailable" beside REQ-02's two markings. The author's
  key says it did not intend this and that "a sharp reviewer could legitimately raise it as a minor
  inconsistency".
- **A second unplanted finding, F-11, has been withdrawn.** The author meant NFR-01 as sound, and its key says a
  reviewer flagging it "is over-strict rather than wrong".

Apart from that withdrawal, the findings were not changed after the key was opened. The other later changes to
the findings file are the added sentences in the definitions, the notes on what they leave open, and the
section "Raised and withdrawn".

## What was built

- `participant/context/ambiguity/requirements.md`: the made-up set, by the author. 20 requirements in two
  documents, with a glossary.
- `participant/context/ambiguity/findings.md`: the definitions, nine findings, ten unflagged requirements with
  reasons, two findings raised and withdrawn, and two gaps in the set.
- `participant/skills/requirements-review/SKILL.md` and `check.py`: the method, and a checker for the form of a
  review. `tests/test_check.py`: 32 tests.
- `review/`: the first pass, the second look, the author's key, and the five independent reads with the file
  each was given.
- `scripts/record_evidence.py` and `scripts/planted_bugs.py`.

Both stretch goals were done. Each finding has an "Effort to make testable" line, small, medium or large, with
the reason: small when one number or name answers the question, medium when a rule has to be decided, large
when requirements have to be reconciled. And one of the two contradictions is across two documents.

## Where the important artifacts are

| What | Path |
|---|---|
| The requirements set | `participant/context/ambiguity/requirements.md` |
| The findings | `participant/context/ambiguity/findings.md` |
| The review run | `participant/evidence/ba-detect-ambiguity/ba-attempt-002/logs/review-run.txt`, and a copy at `participant/evidence/ba-detect-ambiguity/attempt-001/logs/review-run.txt` |
| This file | `participant/evidence/ba-detect-ambiguity/ba-attempt-002/PROOF.md`, and a copy at `participant/evidence/ba-detect-ambiguity/attempt-001/PROOF.md` |
| First pass and second look | `participant/evidence/ba-detect-ambiguity/ba-attempt-002/review/first-pass.md`, `second-look.md` |
| The author's key | `participant/evidence/ba-detect-ambiguity/ba-attempt-002/review/answer-key.md` |
| The five independent reads | `participant/evidence/ba-detect-ambiguity/ba-attempt-002/review/independent-read*.md` |
| The checker | `participant/skills/requirements-review/SKILL.md`, `check.py` |
| Test output | `participant/evidence/ba-detect-ambiguity/ba-attempt-002/logs/tests.txt` |
| Planted bugs | `participant/evidence/ba-detect-ambiguity/ba-attempt-002/logs/planted-bugs.txt` |

## How to reproduce the behavior

From the repository root. None of these uses the network.

```bash
python3 participant/skills/requirements-review/check.py
python3 -m unittest discover -s participant/skills/requirements-review/tests -v
python3 participant/evidence/ba-detect-ambiguity/ba-attempt-002/scripts/record_evidence.py
python3 participant/evidence/ba-detect-ambiguity/ba-attempt-002/scripts/planted_bugs.py
```

These reproduce the checking of the review and the comparisons. They do not reproduce the review. To do that, a
person reads `requirements.md` with the definitions at the top of `findings.md` and sees whether they reach the
same findings. That is the test this work has not had.

## What was tested or validated

| What | How | Result |
|---|---|---|
| The checker | 32 unit tests, `logs/tests.txt` | all pass |
| Whether the tests notice a broken checker | 18 planted bugs, `logs/planted-bugs.txt` | all 18 caught |
| The form of the review | `check.py`, seven rules | kept |
| The checker refusing a spoiled review | five spoiled copies, in `logs/review-run.txt` | all five refused, each naming the rule |
| The review against the author's key | worked out in `logs/review-run.txt` | 10 of 10 planted defects found with the same type, 10 of 10 sound requirements unflagged, 1 finding not planted |
| Whether the types can be reproduced | five independent readers, the last on the file as it stands | 9 of 9, three by a stated judgment |

## Remaining limitations

- **No person has checked the review.** Every reader was an assistant of the same kind as the reviewer.
- **Criterion 7 rests on one blind read of the final file.** Reader 5 matched all nine. Readers 2 and 3 matched
  the same nine among ten. A sixth reader could differ on F-02, F-06 or F-07, where a judgment is involved.
- **The checker checks form.** It cannot tell a sound requirement from a defective one, or a right finding from
  a wrong one. A review that flagged nothing real, in the right format, would pass it.
- **The set was written to be reviewed.** Its defects are cleaner than those in real requirements, where a
  requirement is often a little of several types and the author cannot be asked what was meant.
- **Finding all ten planted defects says little.** They were planted by an assistant of the same kind and
  found by one. A measure of what the review misses would need defects it did not expect.
- **The definitions have two weak places**, "reasonable reading" and "speaks of it". Both are named in the
  findings file. Neither is fixed.
- **A real concern was withdrawn because it could not be typed.** NFR-01's request rate is still unstated. It
  is noted under "Raised and withdrawn" and is not a finding.
- **The line between a gap in a requirement and a gap in the set is thin**, as said above.
- **Effort scores are judgments** in three sizes. They were not checked by anyone.
- **The check for offered wording is a list of phrases.**

## Reflection: what fraction of your findings would a stakeholder call nitpicking, and how would you tell?

Of the nine that remain, my estimate is two. Of the eleven I first raised, four. And I cannot tell from the
text.

The two that remain are these. F-09, on whether "unavailable" is a third marking: real, and small, and
answerable in a sentence. F-07, on the period over which no-shows are counted: one independent reader called it
"modest" and said most testers would assume a lifetime count and write the same test.

The two already gone are the ones a stakeholder would have named first. F-10 I withdrew myself on the second
look. F-11 I kept, and it took a review and four readers before I let it go. The assistant that wrote that
requirement had called flagging it over-strict. So on the one case where I had an outside opinion to test my
judgment against, my judgment was the stricter and the outside opinion held.

The other seven I would defend to anyone. Two pairs of requirements cannot both be built. Two requirements
cannot be shown to be met. "Shortly before" and "recent versions of popular browsers" are the scenario's "load
quickly" in other words. A missing rule for bookings in a room that is closed will strand someone.

How would I tell? Not by reading the requirement harder. What I have are three weak signs.

- **Whether the finding can say what goes wrong.** All of them can, because the review requires it. So that
  test removes remarks about style and does not separate the doubtful ones from the rest.
- **Whether someone else raises it unprompted.** The author did not plant F-09 or F-11.
- **Whether its type holds still.** F-11 was the one finding readers could not type, and it is the one that
  turned out not to belong. A defect that will not stay in one category may not be much of a defect. That is
  the sign I had in hand at the second look and did not weigh.

The real test is one I could not run: ask the person who owns the requirement what would be built differently
depending on the answer. If the answer is "nothing", it was nitpicking, however correct. If they have to stop
and think, it was not. That depends on the project and the people, and neither is on the page. A fixed load
profile matters a great deal to a team that has been burned by a performance test, and not at all to a library
with forty members.

So the honest fraction is "about a quarter, and I would not know which quarter without asking". What a reviewer
can do is make the asking cheap: say what goes wrong if the question is ignored, say how much work an answer
is, and put the doubtful ones last.

## Sensitive values

- No credential is in any file. Nothing here connects to any system.
- The requirements set is made up. The library, the product and every detail are invented, so no real
  project's weaknesses are published.
- No person is named, and no finding is about whoever wrote a requirement. The checker refuses a finding that
  speaks of "the author". This file uses the word only for the assistant that wrote the made-up set.
- The logs hold no home-folder path.
