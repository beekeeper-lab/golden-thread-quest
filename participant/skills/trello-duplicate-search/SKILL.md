# Trello duplicate-search

Written by an AI assistant (Claude) at the participant's direction.

## 1. Purpose

Before a new Trello card is created, this skill searches the local indexes of every board it is given for
cards that are probably the same work. For each one it finds, it says which signals matched, how confident it
is and what it recommends. When nothing matches it says none. It reads local files only, changes none of them,
and never contacts Trello. It needs no credentials.

Run it from the repository root:

    python3 participant/skills/trello-duplicate-search/search.py --proposal FILE.json

The search is `search.py`, beside this file. It uses the Python standard library and the `trello-build-index`
skill, which it imports.

## 2. What it is given

A proposal: a JSON file describing the card someone is about to create.

    {"name": "...", "board": "<board id>", "desc": "...", "labels": ["..."],
     "members": ["<member id>"], "checklist": ["..."], "due": "2026-12-04"}

The name and the board the card would go on are required. Any other name in the file is refused.

`--boards FOLDER` names the boards folder. It holds one folder for each board, and each of those holds
`board.json`, `cards/` and that board's index, `index.md` and `index.json`, as the `trello-build-index` skill
writes them when the records folder is also the `--out` folder. The default is
`participant/context/trello/duplicates/boards/`, two made-up boards.

`--report FILE.md` also writes the findings as Markdown. `--decision` and `--decision-note` record a person's
decision in that report. See section 7.

## 3. Where it looks

Every board in the boards folder is searched, not only the board the card would go on.

The index of each board says which cards exist and holds each card's name, list, labels, members, due date
and state. The description and the checklist items are read from the card's record, which the index names.

Before searching, it checks that each index is exactly what the index generator would write from the records
now. If one is not, the search stops and says to rebuild. It does not rebuild an index itself, because it
changes nothing. It also stops if a folder in the boards folder is not a board, if two folders hold the same
board, or if the proposal's board is not among those searched. A board left out could hide a duplicate.

## 4. The signals

Five beyond the name, each worth a number of points for how far it is trusted. The name is compared too, and
is the weakest.

| Signal | Points | It matches when |
|---|---|---|
| Description | 4 | the two descriptions share at least half of the shorter one's meaningful words, and at least four words |
| Checklist | 3 | at least two checklist items are alike, and at least half of the shorter checklist's items |
| Labels | 2 | they share a label, by name in any letter case. A label's id is different on each board, so ids are not used |
| Members | 2 | the same Trello member id is on both |
| Due date | 1 | the due dates are at most three days apart |
| Name | 1 | the names share at least 60% of the shorter one's meaningful words, and at least two words, or are the same |

"Meaningful words" are the words of a text in lowercase, without common words such as "the" and "for", with a
plural "s" removed. The share is counted against the shorter text, so that a short proposal can match a long
card. Two checklist items are alike by the same rule as two names.

When one side has nothing to compare, for example a card with no due date, the signal is shown as not
comparable. It is not a match and not a mismatch.

## 5. Candidates and confidence

A card is reported as a candidate only when **at least three of the five signals beyond the name match**. The
name never counts towards the three. So:

- a card with the same name is not a candidate for that reason, even with two other signals;
- a card with a different name is not hidden by it.

A candidate's score is the points of everything that matched, the name included, out of 13.

| Confidence | Score |
|---|---|
| high | 10 to 13 |
| medium | 7 to 9 |
| low | 5 or 6. 5 is the least that three signals can add up to |

Candidates are listed strongest first. Each shows all six signals with what was found, its score, its board
and list, whether it is open, and its record. Cards that matched on something, but on fewer than three signals
beyond the name, are listed separately as looked at and not reported, with what they matched on.

## 6. The recommendation

One of three words for each candidate.

| What was found | Recommendation |
|---|---|
| No candidate | `proceed` |
| The candidate is archived, on an archived list, or its due date is marked complete | `proceed`, and the earlier card is named |
| The candidate is open and on another board | `link` |
| The candidate is open, on the board the new card would go on, and the confidence is high | `archive-as-duplicate` |
| The candidate is open, on the same board, and the confidence is medium or low | `link` |

Another team's card is never recommended for archiving. The overall recommendation is the most cautious one
among the candidates: `archive-as-duplicate` before `link` before `proceed`.

## 7. A person decides

The search recommends. It creates, links and archives nothing.

A report written without `--decision` says "Not yet decided". To record a decision, a person runs the search
again with `--decision link`, `--decision archive-as-duplicate` or `--decision proceed`, and optionally
`--decision-note "why"`. The report then shows the decision as the person's, and says whether it is what the
search recommended. Giving a decision does not change anything else in the report.

## 8. Card text is other people's writing

Card names, descriptions and checklist items are broken into words and compared. Nothing in them is acted on.
On the screen they are shown quoted. In the report they are escaped so that a name cannot split a table row,
start a heading or become a link.

## 9. Nothing is changed

The search opens files for reading only, apart from the report it is asked for, and it refuses to write the
report inside the boards folder. It takes the SHA-256 of every file in the boards folder before and after, and
prints the index files' hashes. Exit codes: 0 the search ran, whatever it found. 2 it could not run.

## 10. Tests

    python3 -m unittest discover -s participant/skills/trello-duplicate-search/tests -v

## 11. What it does not do

- It does not read Trello. If an index's records are out of date with Trello, the search agrees with the records.
- It does not know that two different words mean the same thing. It compares words as written.
- It cannot report a card that has fewer than three of the five fields filled in, however alike the names are.
- It does not compare comments or attachments.
- It does not treat a list called "Done" as finished. It goes by archived cards, archived lists and due dates
  marked complete.
- It does not group duplicates of each other into clusters.
- It cannot know that a decision given with `--decision` was made by a person. It records what it is given.
