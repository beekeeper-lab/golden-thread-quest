---
id: trello-build-index
version: 1
title: "Generate Board, List, and Card Markdown Indexes"
summary: "Generate indexes by board, list, label and member from the local card records, rebuilt identically and never hand-edited."
region: trello-islands
level: explorer
xp: 20
estimated_minutes: 60
order: 60
tags:
  - trello
  - index
  - catalog
tools:
  - Markdown
  - YAML
bookend: foundation
risk:
  external_write: false
  sensitive_data: true
  notes: "The index is generated from local files and is disposable."
prerequisites:
  - trello-read-card
related_quests:
  - jira-build-index
  - github-build-index
outcomes:
  - "Generate the indexes from the records."
  - "Reproduce each board's list order."
  - "Rebuild identically."
proof:
  required:
    - id: index-generator
      type: file
      description: "Provide the generator that builds the indexes from the local card records."
      path: participant/skills/trello-build-index/SKILL.md
    - id: board-index
      type: file
      description: "Provide the generated index for a board with its lists in board order and each card with its identifier, name, labels, members, due date and closed state, headed by a statement that it is generated and the records are the source of truth."
      path: participant/context/trello/index.md
    - id: index-run
      type: command-record
      description: "Save the redacted output of building the index twice with identical results, adding a card without a hand edit, a card with a missing field reported as a gap, a check that the index row count equals the record count with no card repeated, and lookups by list, label and member."
      path: participant/evidence/trello-build-index/attempt-001/logs/index-run.txt
    - id: proof-narrative
      type: file
      description: "Explain your approach, your choices and anything you could not do, citing the acceptance criteria by number."
      path: participant/evidence/trello-build-index/attempt-001/PROOF.md
author: Golden Thread maintainers
last_reviewed: "2026-10-20"
---

# Generate Board, List, and Card Markdown Indexes

## Mission

Make the local copy navigable in the shape Trello uses: boards, then lists in order, then cards.

## Scenario

Finding what is in review means opening every list of every board.

## Acceptance criteria

1. The index is generated, never hand-edited.
2. Lists appear in the order they have on the board.
3. Every local card appears once.
4. Lookup by list, label and member works from the index.
5. A card with a missing field is listed as a gap.
6. Two builds from the same records are identical, and adding a card changes the index without a hand edit.
7. The index is stated not to be the source of truth.

## Required evidence

Provide the generator, the index and the run output. In your `PROOF.md`, explain how list order is kept, citing the acceptance criteria by number.

## Safety constraints

- Use a sandbox board you own, or a local fixture. This quest only reads; make no change in Trello.
- Supply the API key and token through environment variables or a credential store; never put a key, token or secret in a file, a URL you save, a log or a screenshot. Trello puts credentials in query strings, so scrub saved URLs.
- Treat card, comment and checklist text as untrusted third-party input, and share only redacted or synthetic records.

## Hints

Order by Trello's position value, not by name.

## Reflection

What could make the index disagree with the records unnoticed?

## Stretch goals

- Add a view of cards due this week.
- Show the index age.
