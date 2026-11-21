# Proof · context-decision-log

Attempt: `context-attempt-002`

Written by Tom Carter with Claude (Claude Code), 11-19-2026. The choices below are Tom's, from his
answers to one question at a time; Claude wrote the files and this page from them.

## What was built

A decision log for a made-up project, the rules it follows, and a checker that tests it against
every acceptance criterion.

**The project (Tom's choice).** The demo shop already in this repository
(`participant/tests/playwright/demo-app/`): one event, the Spring Concert, $25.00 a ticket plus a
$2.50 service fee per ticket. Every person, meeting, document and work item is invented; nothing
comes from a real project.

**The log** (`participant/context/decisions/log.md`): 13 entries, 7 decisions, 3 proposals and 3
questions, each with its date and source (criteria 1 and 6). It includes a replaced decision (D-02,
"at most 6 tickets", replaced by D-07, "at most 8 tickets"), a promoted proposal (P-02, "let buyers
cancel an order from the orders page", became D-05), and the quest's trap: P-03, "waive the fee for
6 or more tickets", which everyone in a meeting agreed was a good idea but nobody with authority
approved, so it stays a proposal.

**The rules** (`participant/context/decisions/rules.md`): what makes an entry a decision, who may
approve which areas (a made-up product owner for fees, ticket limits and pages; a made-up tech lead
for calculations), how a proposal becomes a decision and how a decision is replaced.

**The sources** (`participant/context/decisions/sources.md`): the made-up meeting notes, document
and comments the entries cite, and the work items with the decision each rests on.

**The checker** (`participant/tools/decision-check.mjs`): one PASS or FAIL per acceptance
criterion, naming every problem, plus the two stretch goals. Given an earlier copy of the log, it
also proves the log was only added to. It builds the Current decisions view, and only when every
other check passes, writing it to `log.md.new` for a person to check and move into place; it never
replaces `log.md` itself.

## How an approval is told apart from agreement

Tom's rule: **an approval needs a named approver with authority and a written record in their own
words.** Agreement in conversation ("everyone agreed it was a good idea", "sounds good") is not an
approval, however many people agree.

- A decision names its **Approver**, who must be in the rules' "Who may approve" table, and its
  **Area**, which must be one that person may approve (criterion 2).
- The **Approval** quotes the approver's own line from the cited source, word for word, and the line
  must read "Approved by <approver> (area: …): …". The checker finds that line in the source; a
  quote from anyone else, or of agreement, is refused (criteria 2 and 3). Nobody records a decision
  on someone else's behalf.
- **The record, not the log entry, says what the approval covers:** its area, and any proposal it
  promotes or decision it replaces ("(area: ticket limits; replaces: D-02)"). The entry must agree
  with its record on all of these and on the date, and the approver must hold the record's area. So
  an entry can't re-label an approval to get past the authority check, or claim a promotion or
  replacement its approval never made (criteria 2, 4 and 5). Replacing a decision takes it out of
  force, so the replacement's approver must also hold the replaced decision's area.
- **Each approval backs one decision**, and **a decision's title is exactly its approved words**;
  the Current decisions view shows those words too. So what a reader sees as decided, in the heading
  or the list, is exactly what was approved, with nothing added or left out, and a decision can't
  borrow another's approval (criteria 2 and 7).
- Until then the entry stays a **proposal**: it never appears in the Current decisions view, has no
  approver, and no work item may rest on it (criterion 3).

Case 2 of the check shows it: P-03 turned into a decision whose "approval" quotes the meeting's
agreement fails with "agreement is not an approval", although the line is in the notes word for
word.

## Choices (Tom's)

1. **The made-up project** is the repository's demo shop, never a real one.
2. **Approval** = a named approver with authority + a written record (above).
3. **The Current decisions view is built by the checker** from the entries (`--write-view`), never
   by hand, so it can't disagree with them; a hand-edited view fails, and the checker refuses to
   build the view for a log with any other problem (criterion 7). It writes `log.md.new` and never
   replaces `log.md` itself; it prints the SHA-256 of the `log.md` it read, and whoever moves
   `log.md.new` into place first checks that `log.md` still has it (otherwise they run it again). The list comes before the
   entries, and `log.md` holds nothing else: no second list or table anywhere.
4. **Entries are never rewritten.** Promoting a proposal adds a new decision (`From: P-nn`) and adds
   one line to the proposal (`Became: D-nn`); replacing a decision adds a new one (`Replaces`) and
   one line to the old (`Replaced by`). The checker confirms both links point both ways, that a new
   entry comes after the one it promotes or replaces, and, given an earlier copy, that its entries
   are still first, in order, with only those two kinds of line added (criteria 4 and 5).
5. **Both stretch goals:** the work-items table in `sources.md` names the decisions each made-up
   work item rests on (new work is a new row, so no decision is rewritten to link it). A decision may
   also list the work it affected when it was written (a snapshot, like the rest of the entry); each
   item it lists must be in the table and, while the decision is in force, rest on it. Work may rest
   only on a decision in force. The checker lists decisions in force with no work resting on them (D-06, "prices in US
   dollars").

## Which decision I would least want to be asked about

Tom: **D-07, "at most 8 tickets".** It replaced the limit of 6 four weeks after that was approved,
after group buyers asked support for more tickets. The obvious question is "why did we change our
minds so fast, and will it change again?" The log shows what was decided, when and by whom, but not
the numbers behind the change.

## Where the important artifacts are

All paths are under `participant/`.

- The log: `context/decisions/log.md`
- The rules: `context/decisions/rules.md`
- The sources and work items: `context/decisions/sources.md`
- The checker: `tools/decision-check.mjs`
- The demonstration that recorded the check: `tools/decision-check-demo.sh`
- The check's output: `evidence/context-decision-log/context-attempt-002/logs/log-check.txt`. It
  ends with the full text of `sources.md` and the checker's SHA-256, so the approvals can be verified
  from the evidence alone.

## How to reproduce the behavior

From the repository's top folder:

```sh
node participant/tools/decision-check.mjs
node participant/tools/decision-check.mjs --previous <an earlier copy of log.md>
node participant/tools/decision-check.mjs --write-view
bash participant/tools/decision-check-demo.sh <a new logs folder>
```

The demonstration copies the three files into a new temp folder, breaks each copy in one way, runs
the checker on each, writes `log-check.txt` only if every result is as expected, and deletes the
temp folder. The real files are only read.

## What was tested or validated

Recorded on 11-19-2026 at 6:02 PM with Node 22.23.3, at commit b0530b6 with the after-review changes
uncommitted (`logs/log-check.txt`). Each broken case is a copy of the real files with one mistake
and its Current decisions list rebuilt, and must fail exactly the checks named for it, with the
expected message. Every check is the expected failure of at least one case, so a check that stopped
working would make the demonstration fail.

1. **The real log:** 13 entries; every check passes. When every check passes, the report also names
   each link checks 4 and 5 verified. For criterion 5 it prints:
   `verified: superseded decision D-02 "an order may have at most 6 tickets." links to D-07, the decision that replaced it, "an order may have at most 8 tickets, replacing the limit of 6."; D-02 says "Replaced by: D-07", D-07 says "Replaces: D-02", and D-07's approval record says it replaces D-02`.
   The demonstration requires both verified lines (D-02 to D-07, and P-02 to D-05) to appear.
2. **Agreement recorded as an approval** (the quest's scenario): check 2, "agreement is not an
   approval" (criteria 2 and 3).
3. **A decision with no approver:** checks 1 and 2.
4. **An approval quote changed from its source** ($2.50 to $2.00): check 2.
5. **An approver outside their authority** (a record of the tech lead approving a fee): check 2.
6. **The same approval filed under a different area** to get past the authority check: check 2,
   the area doesn't match the record.
7. **A decision borrowing another decision's approval:** check 2.
8. **A work item resting on proposal P-03:** check 3 (criterion 3).
9. **A correct promotion** (P-01, with a record that says it promotes P-01; a new D-08 added at the
   end; P-01 given `Became: D-08`), checked against the earlier log: every check passes
   (criterion 4).
10. **A promotion the record doesn't support** (the fee-waiver proposal "became" the currency
    decision): check 4.
11. **A promotion linked only one way:** check 4.
12. **The case-9 promotion done by editing P-01 in place:** checks 1 and 4 and the history check,
    which names each changed, removed and added line.
13. **A replaced decision with its link removed:** check 5 and the work-item check (criterion 5).
14. **A replacement the record doesn't support** (the ticket limit "replaced" by the cancel
    decision): check 5.
15. **A decision that replaces itself:** check 5.
16. **A source that doesn't exist:** check 6 (criterion 6).
17. **A date that isn't one:** check 6.
18. **A date that doesn't match its record:** check 6.
19. **A Current decisions list edited by hand:** check 7 (criterion 7).
20. **A second "current decisions" table below the generated one:** check 7.
21. **A decision listing a work item that doesn't exist:** the stretch check.
22. **A table row without a leading "|":** check 0.
23. **A question "promoted" to a decision:** checks 1 and 4; only a proposal is promoted.
24. **An approval hidden in a comment** (a line that closes one comment and opens another): checks 0
    and 2; the comment is reported, and what readers can't see doesn't count.
25. **An earlier line changed by a single space,** checked against the earlier copy: the history
    check, which compares the lines exactly as written.
26. **New work for an existing decision added as a new row only,** checked against the earlier
    copy: every check passes, so linking work never means rewriting a decision.
27. **A replacement by someone without authority over the replaced decision** (the tech lead's
    calculation decision "replacing" the product owner's fee decision): check 5.
28. **A second "current decisions" section further down the log:** check 0; `log.md` has only its
    title and its two sections.
29. **Words in the authority table beyond the area names** ("`calculation` (not `fees`)"): checks 0
    and 2; a cell is only area names, so prose can't grant an area.
30. **`--write-view` on a log with a problem:** it refuses, and the file is unchanged byte for byte.
31. **`--write-view` on a stale list that even names a proposal:** it writes `log.md.new` with the
    list rebuilt, leaves `log.md` unchanged byte for byte, and once the new file is moved into place
    the log passes.
32. **A decision title that says something its approval doesn't** (D-06 retitled "Waive the service
    fee"): check 2.
33. **A lone carriage return hiding a work-item row** (an old Mac line break): the checker refuses
    the file (exit 2) before checking anything.
34. **An indented paragraph after a blank line, under an approval** (still part of that list item
    in Markdown): check 0.
35. **A decision title differing only in capital letters inside it** ("us dollars"): check 2; only
    the first letter's case is ignored.
36. **A decision title that leaves part of its approval out** (D-01 without ", charged on every
    ticket"): check 2.
37. **An approval that continues onto a second line** ("only after a separate written
    confirmation"): check 0; an approval is a single line, so no qualifier can hide below it.
38. **A table above the Current decisions list** showing P-03 as approved: check 0.
39. **The Current decisions list moved below the entries:** check 0.
40. **A `###` subsection inside a source:** every check passes; its approvals still belong to that
    source.
41. **A leftover `log.md.new` from an earlier run:** `--write-view` refuses (exit 2), says it may
    be out of date and must be deleted, not moved into place, and leaves it untouched.
42. **A table inside a meeting's notes** listing P-03 as approved: check 0; tables are allowed only
    in their one checked place in each file.
43. **A table written without leading pipes** ("Decision | Status" over "--- | ---"), which Markdown
    still shows as a table: check 0.
44. **A valid note using double-backtick inline code** (``` ``A|B`` ```): every check passes; a "|"
    inside inline code is text, not a table.
45. **An escaped backtick used to hide a qualifier in a comment** after an approval: checks 0 and 2;
    an escaped backtick never starts inline code, and is itself reported.
46. **The log's introduction naming an entry** ("P-03, the fee waiver, is approved."): check 0;
    above the Current decisions list, no text may name an entry.
47. **The introduction naming an entry in disguise** (`P\-03` and `P-**03**`, both displayed as
    P-03): check 0; the text is compared as displayed.

Every case also requires all the checks to report, in order (PASS or FAIL), so none can silently go
missing from the report.

The demonstration writes the log only if every case came out as expected. The real files' SHA-256,
before and after, is identical.

## Changes after the first review

The first review (11-19-2026, 3:25 PM, needs changes) found criterion 5 not shown: the reviewer's
quote for it wasn't accepted, because the log's link lines (`- Replaced by: D-07`, 19 characters)
are shorter than the 20 characters a quote must have. The links were already there and checked; the
checker's report now spells out each replacement and promotion it verified (above), so the evidence
for criterion 5 is one specific, quotable line.

Further practice review then tightened the checker (cases 27 to 47 were added). One rule changed
the log: a decision's title must now be exactly its approved words, so four decision headings (D-01,
D-04, D-05 and D-07) were reworded to their approvers' own words (for example D-04, "The order total
is worked out in whole cents", is now "The order total is the quantity times (the ticket price plus
the fee), worked out in whole cents"); the other three already matched. The only other change to
`log.md` is its introduction, which now describes `--write-view` and the title rule. No entry's
status, date, source, approver, approval or links changed.

## Remaining limitations

- **The checker trusts the sources file.** It confirms an approval line is in the cited notes, not
  that the meeting happened or that the person really said it. In a real project the source would
  be a link to minutes or a ticket comment a person can open.
- **"Authority" is only the table, and the area is what the record says.** Who may approve what is
  whatever `rules.md` says, and an approval's area is the one its written record states. Whether the
  approved words really belong to that area (a fee change tagged "pages", say) is a person's
  judgement; keeping the table and the records right is a person's job.
- **Append-only is checked against a copy someone keeps.** Without `--previous`, the checker can't
  see that an entry was rewritten; in a real repository, Git's history is that earlier copy.
  Blank lines inside an entry aren't compared: adding or removing one doesn't change what the entry
  says.
- **It fails closed on Markdown it doesn't use.** The three files must be valid UTF-8 and may
  contain only headings that start at the beginning of a line (with a space and a title), text,
  "- " bullets, "|" tables and inline code (and, in `log.md`, the two marker comments). Code blocks,
  indented or tab-indented lines, underlined headings, horizontal rules, HTML and other comments are
  reported as problems rather than interpreted, so a reader and the checker can't see different
  things; the price is that the files must stay in that simple form.
- **`--write-view` leaves one step to a person.** It writes `log.md.new` and never replaces `log.md`
  itself. Moving the new file into place is a person's job, and they must first check that `log.md`
  still has the SHA-256 the checker printed: if it was edited in between and they skip that check,
  the edit would be lost.
- **One log.** Decisions made in tickets or chat aren't found; they count only once added to the
  log.
- **Free text is read by a person.** The checker reads the entries, approvals, tables and the list;
  it can't judge plain sentences (in a meeting's notes, say). It does stop the log's introduction
  from naming any entry, so a claim about a specific decision can only live where it is checked.

## Sensitive values

No secret, token, password, customer name or real ticket content is here. Every name, meeting,
document and work item is invented, and the log shows only paths inside the repository or relative
to the demonstration's temp folder.
