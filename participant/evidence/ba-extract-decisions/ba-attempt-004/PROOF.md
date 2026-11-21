# Proof · ba-extract-decisions

Attempt: `ba-attempt-004`

Written by Tom Carter with Claude (Claude Code), 11-20-2026. The choices below are Tom's, from his
answers to one question at a time; Claude applied the rules, wrote the files and this page.

## What was built

A skill that sorts a meeting transcript into decisions, proposals, open questions and commitments,
every item pointing back to the lines a person can read, and a checker that proves the result
against the transcript.

**The source** (`participant/context/transcripts/sample-meeting.md`): the synthetic "Seating Chart
Refinement" meeting ingested in the Ingest a Meeting Transcript quest, 41 utterances (U001 to U041).
It is the source of record and is not edited (criterion 5).

**The skill is the written rules** (`participant/context/decision-rules.md`, Tom's choice): the test
for a decision, the other lists, what happens when the meeting changes its mind, and two borderline
lines. Claude applied them to the transcript; a checker proves the mechanical parts.

**The result** (`participant/context/transcripts/sample-meeting.decisions.md`), a separate file
(criterion 5) with:

- **8 decisions**, each citing its lines (criterion 1), naming who agreed and at which line
  (criterion 3), and quoting its key line word for word (criterion 7);
- **2 proposals** nobody accepted, kept out of the decisions (criterion 2);
- **3 open questions**, listed separately (criterion 4);
- **5 commitments** (who will do what, by when; Tom's choice of a fourth list: they are tasks, not
  decisions about the product);
- **the instruction-like line U027**, under "Not classified": never a decision, and not acted on.

**The checker** (`participant/tools/citation-check.mjs`) checks each acceptance criterion and, when
every check passes, prints one "verified" line per criterion naming what it confirmed.

## The test for a decision (Tom's choices)

1. **A decision is something proposed and accepted out loud** by someone in the meeting ("Agreed",
   "Yes", "Fine", "Exactly"), and it records who agreed at which line. A sentence that sounds final
   is not accepted until someone agrees with it. Agreement given only in the meeting's wrap-up is
   recorded as "via the wrap-up". With no stated agreement, it is a proposal (criteria 2 and 3).
2. **The written rules are the skill;** Claude applied them, and a checker proves the citations, the
   quotes, the speakers and the untouched transcript.
3. **When the meeting changes its mind, both versions are kept, linked** (below).
4. **Commitments are a fourth list.**
5. **Both stretch goals:** decisions a later line doubts are marked "Not yet confirmed" and name the
   commitment that settles them (which names them back, "Settles: D7"), and the file counts each
   list.

The two borderline lines, as `decision-rules.md` records them:

- **U016, locked tables:** Dana stated it and nobody replied then. Classified as **decision D6,
  agreed via the wrap-up** (Marcus listed it at U034, Dana said "Yes" at U035).
- **U018 to U019, undo covering drops:** Marcus said it "should cover drops for free"; Priya will
  "test it rather than assume it". Classified as **decision D7, not yet confirmed** until Priya's
  test (commitment C2).

## How a decision changed later in the same meeting was handled

Nothing is overwritten and nothing silently disappears: the final decision cites every line that
led to it (the checker requires the change and every line of the earlier version), and the earlier
version stays, linked both ways (criteria 1, 2 and 4).

- **The full-table message (U010 to U011).** Marcus proposed "I'd block it and shake the table, maybe
  a message" (U010); Dana changed it: "A message, please. Shaking alone isn't clear enough." (U011).
  The file lists **D4**, "A full table refuses the drop, with a message such as 'Table 4 is full.'",
  citing U009 to U011 and the wrap-up, with "Changed in the meeting: from P1 at U011"; and **P1**,
  the shake-the-table version, as a proposal with "Not accepted: changed at U011 into D4". The
  checker confirms the two point at each other.
- **Tablet touch (U021 to U026, U035).** The question was logged as open (U024), then Marcus asked
  to keep touch out of this story and Dana said "Fine. Out of scope for now, separate story later."
  (U026), yet the wrap-up still listed it as an open question (U035). Both are true, so both are
  kept: **D8**, out of scope for this story, and **O1**, the open question for a later story, each
  naming the other ("See also").

## Which decision I would least want to defend if its speaker disagreed

Tom: **D7, "undo covers drops".** It rests on Marcus saying undo "should" cover drops, Priya openly
doubted it, and it was agreed only in the wrap-up. If Marcus said he never promised it, the record
shows a hope rather than a commitment, which is why it is marked "not yet confirmed".

## Where the important artifacts are

All paths are under `participant/`.

- The rules: `context/decision-rules.md`
- The decisions file: `context/transcripts/sample-meeting.decisions.md`
- The transcript (source of record, not edited): `context/transcripts/sample-meeting.md`
- The checker: `tools/citation-check.mjs`
- The demonstration that recorded the check: `tools/citation-check-demo.sh`
- The check's output: `evidence/ba-extract-decisions/ba-attempt-004/logs/citation-check.txt`

## How to reproduce the behavior

From the repository's top folder:

```sh
node participant/tools/citation-check.mjs
bash participant/tools/citation-check-demo.sh <a new logs folder>
```

The demonstration checks the real files, then copies broken in one way each in a new temp folder,
writes `citation-check.txt` only if every case came out as expected, and deletes the temp folder.
The real files are only read.

## What was tested or validated

Recorded on 11-20-2026 at 10:17 AM with Node 22.23.3, at commit ff85888 with the quest's files
uncommitted (`logs/citation-check.txt`). Every broken case must fail exactly the checks named for it,
with the expected message, and every check must report; every check is the expected failure of at
least one case.

1. **The real files:** every check passes. The verified lines include, for criterion 6, "all 53 cited
   utterance identifiers exist in the source record, which has 41 utterances (U001 to U041)", and
   for criterion 5, that the transcript is unchanged since it was committed (its Git object id).
2. **Agreement credited to the wrong person** (D2 "agreed by Marcus Lee at U004", spoken by Dana):
   check 3.
3. **A cited utterance that doesn't exist** (U099): check 6, reported by name.
4. **A decision whose agreement was never stated:** checks 2 and 3; it is a proposal.
5. **A key line not quoted word for word** ("usually" for "always"): check 7.
6. **The instruction-like line U027 cited by a decision:** the safety check.
7. **The transcript itself edited:** check 5.
8. **A commitment credited to the wrong person:** check 4.
9. **An open question said to have an uncertain speaker who is known:** check 4.
10. **A change in the meeting linked only one way:** the stretch check.
11. **A count that doesn't match the lists:** the stretch check.
12. **A doubt that names no commitment to settle it:** the stretch check.
13. **A decision moved into the proposals list:** checks 0 and 2 and the stretch check (its
    numbering, a proposal's missing "Not accepted", and the counts).
14. **A table added to the decisions file:** check 0.
15. **A comment hidden inside an item:** check 0.
16. **An escaped backtick used to hide a comment:** check 0; an escaped backtick never starts inline
    code, and is itself reported.
17. **A short underline ("--") turning a line into a heading** that would split an item: check 0.
18. **A "See also" that points only one way:** the stretch check.
19. **A decision whose citations all point to lines that don't exist:** checks 1 and 6; a decision must
    cite at least one line that exists.
20. **A changed decision that doesn't cite what it changed** (D4 without P1's U010): the stretch
    check; a changed decision cites the change and every line of what it changed.
21. **An item placed above the five lists:** check 0.
22. **A count given twice** (a reader would see both): checks 0 and the stretch check.
23. **A list line in the introduction** ("+ Decision: …"): check 0.
24. **An open question raised at a line it doesn't cite:** check 4.
25. **The instruction-like line U027 used as evidence outside the citations** (in a doubt): the
    safety check, which looks at every field.
26. **A doubt pointing at the wrong commitment:** the stretch check; the doubt and the commitment's
    "Settles" line must name each other.
27. **A link whose syntax changes what counts as code:** check 0, and the stretch check's count,
    since the disguised decision isn't read; brackets aren't used in the decisions file.
28. **A character reference that displays as U027** (`&#85;027`): check 0, and the stretch check,
    since the rejected line was D7's doubt; character references aren't used in the decisions file.
29. **A code block made with mixed spaces and tabs:** check 0; no line may be indented.
30. **An identifier wrapped in underscores** (`_U099_`, shown as emphasis): check 6; identifiers are
    found whatever punctuation surrounds them.
31. **An item title naming the instruction-like line:** the safety check, which reads titles too.
32. **The introduction naming an utterance that doesn't exist** (U099): check 6; the introduction's
    references are checked too.
33. **The introduction naming an item, in disguise** (`*D*9`, displayed as D9): check 6; the
    introduction may never name an item.
34. **The file's title naming an item, a missing line and the instruction-like line:** check 6 and
    the safety check; the title is checked like the introduction.

The real files' SHA-256, before and after, is identical.

## Remaining limitations

- **Sorting is judgement.** The checker proves the mechanical parts (citations, quotes, speakers,
  links, counts, the untouched transcript); whether "Fine." accepts a proposal, or whether an item
  belongs in decisions or proposals, is the reading the rules guide and a person checks.
- **It checks the quotes it is given.** A key line proves the item is grounded in that line; it
  doesn't prove the item's title summarises the line fairly. A person reads the titles.
- **One transcript, one format.** The checker reads this transcript's utterance table; another
  format would need its reader adjusted.
- **Free text is read by a person.** The checker checks the items, their quotes, speakers and
  links, and the title's and introduction's references (any utterance they name must exist, they
  never name U027, and they never name an item); plain sentences beyond that are for a person to
  read.
- **The decisions file stays in plain Markdown.** Headings, text and "- Field: value" lines only;
  tables, code blocks, comments, HTML, links, character references, underlines and indented lines
  are reported rather than interpreted, so a reader and the checker always see the same items.
- **Unchanged means unchanged since the last commit.** The transcript is compared with its committed
  version in Git (or, for a copy, with an original given by `--original`).

## Sensitive values

No secret, token, password, customer name or real ticket content is here. The meeting is synthetic;
its two redacted contact details stay redacted, and no file shows this computer's folders.
