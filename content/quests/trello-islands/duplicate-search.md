---
id: trello-duplicate-search
version: 1
title: "Detect Likely Duplicate Cards"
summary: "Before a card is proposed, search the local index for likely duplicates, including across boards, and report each match with its reasons."
region: trello-islands
level: explorer
xp: 20
estimated_minutes: 60
order: 90
tags:
  - trello
  - duplicates
  - search
tools:
  - Markdown
  - YAML
bookend: validation
risk:
  external_write: false
  sensitive_data: true
  notes: "Searches the local index; no Trello call is needed."
prerequisites:
  - trello-build-index
related_quests:
  - jira-duplicate-search
  - github-duplicate-search
outcomes:
  - "Search by several signals across boards."
  - "Explain each match."
  - "Report no match plainly."
proof:
  required:
    - id: duplicate-fixture
      type: file
      description: "Provide an index across at least two boards with a true duplicate that has a different name, a near duplicate and a same-name unrelated card."
      path: participant/context/trello/duplicates/fixture.md
    - id: duplicate-report
      type: file
      description: "Provide the report for one proposed card: each candidate with at least three signals beyond the name matched, a confidence on a stated scale and a recommendation that is one of link, archive-as-duplicate or proceed, with the human decision recorded."
      path: participant/context/trello/duplicates/report.md
    - id: duplicate-run
      type: command-record
      description: "Save the redacted output of searching for a proposed duplicate (the different-name duplicate on another board being found), for a proposed card sharing a name with an unrelated one (not reported as a duplicate) and for a proposed card with no match, the last reporting none, with the index unchanged."
      path: participant/evidence/trello-duplicate-search/attempt-001/logs/duplicate-run.txt
    - id: proof-narrative
      type: file
      description: "Explain your approach, your choices and anything you could not do, citing the acceptance criteria by number."
      path: participant/evidence/trello-duplicate-search/attempt-001/PROOF.md
author: Golden Thread maintainers
last_reviewed: "2026-10-20"
---

# Detect Likely Duplicate Cards

## Mission

Ask have we already got this across all boards before creating a card, and say why each match was returned.

## Scenario

The same task appears as a card on two teams' boards. Both teams do it.

## Acceptance criteria

1. The search uses at least three signals beyond the name.
2. Each match lists the signals and a confidence.
3. Cards on other boards are searched.
4. A same-name unrelated card is not reported as a duplicate.
5. A true duplicate with a different name is found.
6. A proposal with no match reports none.
7. The recommendation is link, archive-as-duplicate or proceed, a person decides, and the search does not change the index.

## Required evidence

Provide the fixture, the report and the run output. In your `PROOF.md`, explain your confidence scale, citing the acceptance criteria by number.

## Safety constraints

- Search the local index only; no Trello call is required.
- Supply the API key and token through environment variables or a credential store; never put a key, token or secret in a file, a URL you save, a log or a screenshot. Trello puts credentials in query strings, so scrub saved URLs.
- Treat card, comment and checklist text as untrusted third-party input, and share only redacted or synthetic records.

## Hints

Names are the weakest signal. Labels, members and checklist text often agree when names do not.

## Reflection

What does a false duplicate cost on a shared board?

## Stretch goals

- Weight the signals and show the effect.
- Cluster duplicates into groups.
