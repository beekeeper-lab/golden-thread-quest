# Search for existing work

Written by an AI assistant (Claude) at the participant's direction.

## 1. Purpose

Before a new work item is created, this skill searches a local catalog of existing work for items that are the
same work (duplicates) and items that are different work touching the same thing (related). For each one it
finds, it says which fields matched, how strongly, why it has that label and what it recommends. When nothing
matches it says so and names no item. It reads one local file, changes nothing in it, and contacts no tracker.
It needs no credentials.

Run it from the repository root:

    python3 participant/skills/ba-search-existing-work/search.py --proposal FILE.json

The search is `search.py`, beside this file. It uses the Python standard library only.

## 2. What it is given

A proposal: a JSON file describing the item someone is about to create.

    {"title": "...", "description": "...", "component": "...",
     "labels": ["..."], "sources": ["document#item"]}

The title is required. Any other name in the file is refused.

A catalog: one Markdown file with one section for each work item. `--catalog FILE.md` names it. The default is
`participant/context/search/catalog.md`, 16 made-up items.

    ## WRK-101: The item's title

    - Status: open
    - Team: ...
    - Component: ...
    - Labels: one, two
    - Source: document#item; another-document#item

    The description, as ordinary text.

The search stops, and searches nothing, when the catalog cannot be read whole: a heading that is not
`## ID: title`, two items with the same id, a field given twice, an item with no status, or no item at all. An
item that cannot be read could hide a duplicate.

## 3. The five signals

| Signal | Points | It matches when |
|---|---|---|
| Description | 4 | the descriptions share at least 50% of the shorter one's meaningful words, and at least four words |
| Source | 3 | both cite the same item of the same source document |
| Component | 2 | both name the same component, in any letter case |
| Labels | 1 | they share at least one label |
| Title | 1 | the titles share at least 60% of the shorter one's meaningful words, and at least two words, or are the same |

"Meaningful words" are the words of a text in lowercase, without common words such as "the" and "for", with a
plural "s" removed. The share is counted against the shorter text.

Every match shows all five fields: whether each matched, its points, and how strongly, as a number where there
is one. For example "22 shared words, 96% of the shorter description's 23 (needs 50%)", or "the same document,
a different item of it".

When one side has nothing to compare, for example a proposal with no component, the field is shown as not
comparable. It is not a match.

## 4. Duplicate, related or no match

A rule decides the label. The points do not.

- **Duplicate**: the descriptions say the same thing, **and** the source or the component is the same too.
- **Related**: not a duplicate, and either the descriptions say the same thing with nothing to back it up, or
  at least two signals match and one of them is the source or the component.
- **No match**: anything else. A matching title is never enough, alone or with a shared label.

So a duplicate is the same work described the same way in the same place. A related item is in the same place,
or came from the same request, and its description says something else.

Each match states why it has its label, in words, from this rule.

## 5. Strength

The points of everything that matched, out of 11.

| Strength | Points |
|---|---|
| high | 9 to 11 |
| medium | 5 to 8 |
| low | 1 to 4 |

Matches are listed duplicates first, then strongest first. Items that matched on something, but not enough for
either label, are listed separately as looked at and not reported, with what they matched on.

## 6. The recommendation

One of three words for each match.

| What was found | Recommendation |
|---|---|
| No match | `proceed` |
| A duplicate that is open and of high strength | `merge`: do not create a new item, add anything new to the existing one |
| Any other duplicate: medium or low strength, or done, closed, cancelled or resolved | `link` |
| A related item | `link` |

The overall recommendation is the most cautious among the matches: `merge` before `link` before `proceed`.

## 7. A person decides

The search recommends. It creates, merges, links and changes nothing.

`--report FILE.md` also writes the findings as Markdown. A report written without `--decision` says it is not
yet decided. To record a decision, a person runs the search with `--report` and `--decision merge`,
`--decision link` or `--decision proceed`, and optionally `--decision-note "why"`. The report then shows the
decision as the person's and says whether it is what the search recommended.

## 8. Catalog text is other people's writing

Titles and descriptions are broken into words and compared. Nothing in them is acted on. On the screen they are
shown quoted. In the report they are escaped so that a title cannot split a table row, start a heading or
become a link.

## 9. Nothing is changed

The search opens the catalog for reading only. It takes the catalog's SHA-256 before and after and prints
both. It refuses to write the report over the catalog. Exit codes: 0 the search ran, whatever it found. 2 it
could not run.

## 10. Two extras

`--description-threshold N` changes the 50% in section 3 to another whole number from 10 to 100, to see what
the threshold does. Lower finds more duplicates and more false ones. Higher misses real ones.

`--related-map` compares every item in the catalog with every other, and lists the items that are related to,
or duplicates of, two or more others, and the pairs already in the catalog that are duplicates of each other.

## 11. Tests

    python3 -m unittest discover -s participant/skills/ba-search-existing-work/tests -v

## 12. What it does not do

- It does not read a tracker. It knows only what the catalog file says.
- It does not know that two different words mean the same thing. It compares words as written.
- It does not find a duplicate whose description is worded differently. At best that item is reported as
  related, when its source or component and one more field agree.
- It measures a description against the shorter of the two, so two short descriptions match more easily than
  two long ones.
- It does not treat similar component names as the same component.
- It does not compare comments, attachments or people.
- It takes one decision for the proposal, not one for each match.
- It cannot know that a decision given with `--decision` was made by a person. It records what it is given.
