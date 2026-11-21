# Proof · ba-search-existing-work

Attempt: `ba-attempt-003`

## How this was made

An AI assistant (Claude) wrote the search, the made-up catalog, the tests, the recording scripts and this
file, at the participant's direction. The work was done in small steps, each shown to the participant before
the next.

What the participant did themself:

- Chose the design from options before anything was written: a rule decides whether an item is a duplicate or
  related, and points only say how strongly it matched.
- Decided the outcome for the proposed item in the report: **merge**. They ran the search in their own
  terminal with `--decision merge`, which wrote `report.md`. The assistant did not choose or record the decision.

Statements below are marked **recorded** (the log `logs/search-run.txt` shows it, against the made-up
catalog), **tested** (a passing test shows it, with the output in `logs/tests.txt`) or **not assessed**. No
tracker was contacted. The quest says to use a synthetic catalog only.

## What was built

A search, `participant/skills/ba-search-existing-work/search.py`, that takes a proposed work item and looks
through a catalog of existing work for duplicates of it and for work related to it.

The catalog, `participant/context/search/catalog.md`, is 16 made-up work items from made-up teams. The planted
ones, for the proposal "Export the customer list as CSV":

| Planted | Item | What it is |
|---|---|---|
| True duplicate, under a different title | `WRK-101`, "Admins can download their contacts as a spreadsheet", open | The same work from the same request. The titles share no word. |
| Near duplicate | `WRK-106`, "CSV export of customers, first attempt", cancelled | An earlier, narrower try at the same work, from another source. |
| Related and distinct | `WRK-102`, "Monthly customer list for finance" | Same component, similar data, a scheduled email instead of a button. |
| Related and distinct | `WRK-103`, "Import customers from a CSV file" | Same component, the opposite direction. |
| Related and distinct | `WRK-104`, "Reply to the tickets asking for a customer export" | Same request, support work instead of a feature. |
| Nearly the proposal's title, unrelated work | `WRK-105`, "Export the customer list" | A nightly copy to a data warehouse. |

One more item, `WRK-116`, has a title and a description worded as orders to the search tool. The other nine
items are unrelated work.

## How a duplicate is told from a related item

Five fields are compared. Each has points for how far it is trusted.

| Signal | Points | It matches when |
|---|---|---|
| Description | 4 | the descriptions share at least 50% of the shorter one's meaningful words, and at least four words |
| Source | 3 | both cite the same item of the same source document |
| Component | 2 | both name the same component |
| Labels | 1 | they share at least one label |
| Title | 1 | the titles share at least 60% of the shorter one's meaningful words, and at least two words |

A rule decides the label. The points do not.

- **Duplicate**: the descriptions say the same thing, **and** the source or the component is the same too.
- **Related**: not a duplicate, and either the descriptions say the same thing with nothing to back it up, or
  at least two signals match and one of them is the source or the component.
- **No match**: anything else. A matching title is never enough, alone or with a shared label.

In plain words: a duplicate says the same thing in the same place. A related item is in the same place, or
came from the same request, and says something else. `WRK-104` shares the proposal's source and a label, which
is 4 points, and its description shares no word with the proposal's, so it is related and can never be a
duplicate however many other fields agree. **tested**:
`test_points_never_make_a_duplicate_without_the_description` and
`test_the_same_source_component_labels_and_title_with_a_different_description_is_only_related`.

The points only say how strongly an item matched, out of 11: **high** 9 to 11, **medium** 5 to 8, **low** 1
to 4.

One part of the rule was added by the assistant after the participant chose the design, and was told to them:
the same description with neither the source nor the component in common is reported as related, not dropped.
That is the case of two teams filing the same work under different components.

## The acceptance criteria, one by one

**1. The search considers more than the title.** It compares the description, the cited source, the component
and the labels as well. **recorded**: part 2, "criterion 1: it was matched on more than the title:
description, source, component and labels". The true duplicate's title line says no, 0 shared words. `WRK-105`,
whose title nearly is the proposal's, is not a match. **tested**: `EachSignal`, 11 tests, and
`test_the_title_alone_is_no_match`, `test_a_title_and_a_label_together_are_no_match`.

**2. Each match states which fields matched and how strongly.** Every match shows all five fields, each as
matched with its points or not, and a measure: "22 shared words, 96% of the shorter description's 23 (needs
50%)", "the same item of the same document", "the same document, a different item of it". Then a strength and
the points out of 11. **recorded**: part 2, "criterion 2: every match lists all five fields", and AFTERWARDS
for the report. **tested**: `test_how_strongly_a_description_matched_is_stated`, `Strength` at the boundaries
4, 5, 8 and 9, and `Report`.

**3. The true duplicate is found, and a related item is labelled related, not duplicate.** **recorded**: part
2. `WRK-101` is the first match: DUPLICATE, HIGH, 10 of 11. `WRK-102`, `WRK-103` and `WRK-104` are each RELATED.
**tested**: `test_the_true_duplicate_is_found_though_its_title_shares_nothing`,
`test_related_items_are_labelled_related_not_duplicate`, and `TheRule`, 10 tests.

**4. A proposal with no match reports none instead of the closest guess.** **recorded**: part 3. The proposal
"Keyboard shortcut list in the help menu" gives "RESULT: NO MATCH", and the output names no catalog item at
all. All 16 items were compared. **tested**:
`test_a_proposal_with_no_match_reports_none_and_does_not_offer_the_closest`.

**5. The recommendation is link, merge or proceed, and the human decides.** Merge only for a duplicate that is
open and of high strength. Link for any other duplicate and for every related item. Proceed when nothing
matched. **recorded**: part 2 (`WRK-101` MERGE, the cancelled `WRK-106` LINK, the related items LINK), part 3
(PROCEED), and "the search says a person decides". **tested**: `Strength` and `Recommendation`. A report
written with no `--decision` says none was made, and a decision changes nothing else in the report.
**tested**: `Report`. The participant's decision, merge, is in `report.md`. **recorded**: AFTERWARDS.

**6. The search does not change the catalog.** The recording script took the catalog's SHA-256 before the
first search and after the last. They are the same, and each search printed that same value as its own before
and after. No file was added beside the catalog. **recorded**: part 4. **tested**: `NothingChanges`, 5 tests:
byte for byte the same after a search, a report cannot be written over the catalog, no file is written without
`--report`, and the search holds no code that could contact anything.

**7. A reviewer can see why each result was returned.** Each match has a sentence from the rule, for example
"Duplicate, because the descriptions say the same thing, and the source and component are the same too", and
"Related, because component and labels match, but the descriptions do not say the same thing: it is different
work in the same place". The report states the whole rule and the table of signals above the matches, and
lists the items looked at and not reported, each with why. **recorded**: part 2, "criterion 7". **tested**:
`test_the_report_says_why_each_kind`, `test_the_report_states_the_rule`.

Also **recorded**: `WRK-116`, whose text tells the search to report nothing and recommend proceed, matched on
component only and was not obeyed (part 2). A catalog with two items of one id stops the search with exit code
2 (part 7).

## The stretch goals

**Tune a threshold and show the effect.** `--description-threshold N` sets the share of words two
descriptions must have in common. **recorded**: part 5, the same proposal at six thresholds.

| Threshold | Effect on this catalog |
|---|---|
| 30% and 45% | `WRK-102`, which is different work, becomes a duplicate: a false duplicate |
| 50% (used everywhere else), 60%, 80% | 2 duplicates, 3 related |
| 90% | `WRK-106`, the near duplicate, becomes only related: a missed one |

The true duplicate stays a duplicate at every threshold tried. `WRK-103` and `WRK-104`, related for other
reasons, do not move. **tested**: `TheThreshold`.

`WRK-102` was written as a near duplicate and came out at 48%, just under the line. The catalog was not
adjusted to push it either side. It is disclosed here as the borderline item.

**Report items related to several others.** `--related-map` compares every catalog item with every other.
**recorded**: part 6. Three items match two or more others, and the catalog already holds the same work
twice, `WRK-101` and `WRK-106`. **tested**: `TheRelatedMap`.

The map also calls `WRK-102` and `WRK-106` duplicates of each other, which they are not. See the limitations.

## Where the important artifacts are

| What | Path |
|---|---|
| The catalog | `participant/context/search/catalog.md` |
| The two proposals | `participant/context/search/proposals/` |
| The report, with the decision | `participant/context/search/report.md` |
| The search and how to use it | `participant/skills/ba-search-existing-work/search.py`, `SKILL.md` |
| The tests | `participant/skills/ba-search-existing-work/tests/test_search.py` |
| The run log | `logs/search-run.txt` |
| The test output | `logs/tests.txt` |
| The planted-bugs log | `logs/planted-bugs.txt` |
| The scripts that made the logs | `scripts/` |

The quest names `participant/evidence/ba-search-existing-work/attempt-001/`. The application created this
attempt as `ba-attempt-003`. Copies of this file and of `logs/search-run.txt` are in `attempt-001/`, with a
note saying so.

## How to reproduce the behavior

From the repository root. None of these contacts anything.

    python3 participant/skills/ba-search-existing-work/search.py --proposal participant/context/search/proposals/1-duplicate.json
    python3 participant/skills/ba-search-existing-work/search.py --proposal participant/context/search/proposals/2-no-match.json
    python3 participant/skills/ba-search-existing-work/search.py --related-map
    python3 -m unittest discover -s participant/skills/ba-search-existing-work/tests -v
    python3 participant/evidence/ba-search-existing-work/ba-attempt-003/scripts/planted_bugs.py
    python3 participant/evidence/ba-search-existing-work/ba-attempt-003/scripts/record_evidence.py

The report is written by adding `--report participant/context/search/report.md --decision merge` to the first
command.

## What was tested or validated

| Check | Result | Where |
|---|---|---|
| Unit tests | 75 pass | `logs/tests.txt` |
| Planted bugs: 27 faults put into `search.py` one at a time | all 27 caught by at least one test; the file restored byte for byte | `logs/planted-bugs.txt` |
| Recorded run, parts 1 to 7 and AFTERWARDS | 38 checks pass | `logs/search-run.txt` |

The planted bugs include the ones the quest turns on: a description match alone counted as a duplicate, a
title match alone reported, the closest item offered when nothing matched, a related item recommended for
merge, and a finished duplicate recommended for merge.

## Remaining limitations

- **A made-up catalog only.** Not assessed on real work items. Real descriptions are longer, messier and
  often empty.
- **The assistant wrote both the catalog and the search.** The planted items fit the search's rules. A
  duplicate written by someone else, in their own words, is a harder test and has not been run.
- **Words are compared as written.** The search does not know that two different words mean the same thing.
  The true duplicate is found because its description uses the same words and its source and component agree,
  not because "contacts" was understood as "customers". The same work described in different words is reported
  as related at best, and as no match if it also sits under another component with another source.
- **Short descriptions match too easily.** The share is counted against the shorter description. In the
  related map `WRK-102` and `WRK-106` come out as duplicates of each other, because the cancelled item's short
  description is mostly contained in the finance item's. They are different work. This is a false duplicate
  that the search makes on its own catalog.
- **The thresholds are judgement.** 50% of the shorter description, 9 points for high: none was measured
  against real duplicates. Part 5 shows that a different threshold changes which items are called duplicates.
- **Component names must be the same text.** "Customers" and "Customer list" are different components to the
  search.
- **Finished is a list of four words:** done, closed, cancelled, resolved. A status the search does not know
  counts as open.
- **One decision for the proposal,** not one for each match. And the search cannot know that the decision it
  is given was made by a person. It records what it is given and says who is meant to give it.
- **Nothing is carried out.** No item is created, merged or linked. The decision is recorded in the report
  and nowhere else.
- **Comments, attachments and people are not compared.**

## Reflection

*What does a false duplicate cost compared with a missed one?*

A missed duplicate costs effort. Two teams build the same thing, or one item sits unseen while another is
worked on. That is waste, but it is visible waste: sooner or later someone notices two items for one piece of
work, and they can still be merged or linked.

A false duplicate costs work that silently does not happen. If the search calls a new item a duplicate when it
is not, the likely result is that the item is never created, and a real need disappears without anyone
deciding to drop it. Nobody looks for an item that was never made, so the mistake is found late, usually by
the person who asked for the work. There is a second cost: after a few false alarms people stop trusting the
matches, and then the true ones are ignored too.

So a false duplicate is the more expensive mistake when it leads to a merge, and the search is built around
that. It asks for the description and one more field before it says duplicate. It recommends merge only for an
open duplicate of high strength, and link for everything less certain, because a false link costs someone a
minute to look and a false merge costs a piece of work. And it stops at a recommendation, so that a person
reads the fields before anything is dropped.

## Sensitive values

No credential is involved: the search reads one local file and has no code that reads the environment or
contacts a network. Every work item, team, component and source in the catalog, the report and the logs is
made up. The logs show the temporary folder as COPY. No personal name, email address, site address or
home-folder path is in the evidence.
