# Jira duplicate-search

Written by an AI assistant (Claude) at the participant's direction.

## 1. Purpose

Before a new Jira story is created, this skill searches the local catalog for stories that are probably the
same work. For each one it finds, it says which signals matched, how confident it is and what it recommends.
When nothing matches it says none. It reads local files only, changes none of them, and never contacts Jira.

Run it from the repository root:

    python3 participant/skills/jira-duplicate-search/search.py --proposal FILE.json

The search is `search.py`, beside this file. It uses the Python standard library and the `jira-build-index`
skill, which it imports.

## 2. What it is given

A proposal: a JSON file describing the work someone is about to create.

    {"title": "...", "description": "...", "labels": ["..."], "components": ["..."], "parent": "RPT-1"}

Only the title is required. `parent` is the key or the issue id of the parent story, or null. Any other name
in the file is refused.

`--catalog FOLDER` names the folder to search. It holds `catalog.json` and a `stories/` folder of records, as
the `jira-build-index` skill writes them. The default is `participant/context/jira/`.

`--report FILE.md` also writes the findings as Markdown. `--today YYYY-MM-DD` sets the date that ages are
counted to. The default is today.

## 3. Where it looks

The catalog says which stories exist. What each story holds is read from its record, because the records are
the source of truth and the catalog holds only a few columns.

Before searching, it checks that the catalog is exactly what the index generator would write from the records
now. If it is not, the search stops and says to rebuild. It does not rebuild the catalog itself, because it
changes nothing.

## 4. The signals

Five, each worth a number of points for how far it is trusted. Titles are the weakest.

| Signal | Points | It matches when |
|---|---|---|
| Description | 4 | the two descriptions share at least half of the shorter one's meaningful words, and at least four words |
| Parent | 3 | both sit under the same parent story, by issue id or by key |
| Component | 2 | both name the same component |
| Labels | 1 | they share at least one label |
| Title | 1 | the titles share at least 60% of the shorter one's meaningful words, and at least two words, or are the same |

"Meaningful words" are the words of a text in lowercase, without common words such as "the" and "for", with a
plural "s" removed. The share is counted against the shorter text, so that a short proposal can match a long
story.

When one side has nothing to compare, for example a proposal with no parent, the signal is shown as not
comparable. It is not a match and not a mismatch.

Not used as signals: the reporter and the assignee, because duplicates are usually made by different people,
and the status, which shapes the recommendation instead.

## 5. Candidates and confidence

A story is reported as a candidate only when **at least three signals match**. So a matching title can never
make a candidate by itself, and neither can any two signals.

A candidate's score is the points of its matched signals, out of 11.

| Confidence | Score |
|---|---|
| high | 8 to 11 |
| medium | 5 to 7 |
| low | 4, the least that three signals can add up to |

Candidates are listed strongest first. Each shows all five signals with what was found, its score, when it was
created and last updated, and its record.

Stories that matched on one or two signals are listed separately as looked at and not reported, with the
signals that matched. A story with the same title and nothing else in common appears there.

## 6. The recommendation

One of three words for each candidate.

| Word | When | Meaning |
|---|---|---|
| merge | high, and the existing story is open | Do not create a new story. Add anything new to the existing one. |
| link | high and the existing story is finished, or medium | Look at the story first. If the new one is still needed, create it and link the two. |
| proceed | low, or no candidate | Create the new story. |

The overall recommendation is the strongest of the candidates' recommendations. It is a recommendation. A
person decides, and the search does not create, link or merge anything.

## 7. Story text is untrusted

Descriptions and titles are other people's writing. The search breaks them into words and compares the words.
It acts on nothing they say: a description that tells the tool to report no matches is compared like any
other. A description is never printed. A title is shown quoted on screen and escaped in the report.

## 8. What it does not change

The search writes one file at most, the report it is asked for, and refuses to write that over the catalog.
Before and after searching it takes the SHA-256 of both catalog files and every record, and says whether all
are as they were.

Exit codes: 0 the search ran, whatever it found. 2 it could not run.

## 9. Tests

    cd participant/skills/jira-duplicate-search && python3 -m unittest discover -s tests -v

## 10. What it does not do

- It compares words, not meaning. The same work described in different vocabulary does not match on the
  description. The parent, component and labels may still find it.
- It does not know synonyms: "churn" and "attrition" are different words to it.
- It searches the local catalog only. A story created in Jira since the records were saved is not found.
- It cannot find a duplicate that shares fewer than three signals with the proposal.
