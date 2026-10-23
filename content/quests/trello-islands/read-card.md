---
id: trello-read-card
version: 1
title: "Preserve Card Fields, Members, Dates, Labels, Comments, and Checklists"
summary: "Retrieve one card with everything on it and save it as faithful Markdown, keeping Trello's own identifiers and structure."
region: trello-islands
level: explorer
xp: 20
estimated_minutes: 60
order: 30
tags:
  - trello
  - markdown
  - normalization
tools:
  - Markdown
  - YAML
bookend: intent
risk:
  external_write: false
  sensitive_data: true
  notes: "Read-only against a sandbox board or fixture."
prerequisites:
  - trello-read-board
outcomes:
  - "Retrieve every part of one card."
  - "Keep checklists, dates and labels as structure."
  - "Identify the card by its stable identifier."
proof:
  required:
    - id: card-file
      type: file
      description: "Provide one card as Markdown with front matter holding its identifier, short link, board and list identifiers, members, labels, due date and completion, closed state and position, and a body holding its description, checklists with each item's state, and comments, with a preserved section for fields the format does not know."
      path: participant/context/trello/cards/card-sample.md
    - id: card-run
      type: command-record
      description: "Save the redacted output of retrieving and writing the card and of running it again with the file unchanged and byte-identical."
      path: participant/evidence/trello-read-card/attempt-001/logs/card-run.txt
    - id: fidelity-check
      type: command-record
      description: "Save the redacted output of a check that every part returned appears in the file, including a checklist item's state, a label colour and a due date with its time zone, that an instruction-like line in the description is stored as content and not acted on, and a scan finding no key, token or private personal data."
      path: participant/evidence/trello-read-card/attempt-001/logs/fidelity-check.txt
    - id: proof-narrative
      type: file
      description: "Explain your approach, your choices and anything you could not do, citing the acceptance criteria by number."
      path: participant/evidence/trello-read-card/attempt-001/PROOF.md
author: Golden Thread maintainers
last_reviewed: "2026-10-20"
---

# Preserve Card Fields, Members, Dates, Labels, Comments, and Checklists

## Mission

Make one faithful local copy where structure survives and the card is identified by what Trello promises will not change.

## Scenario

A card's checklist has twelve items, five checked. The saved copy keeps the titles and loses which are done.

## Acceptance criteria

1. Every part of the card returned appears in the file.
2. Checklist items keep their checked state.
3. Dates keep their time zone and the due-complete flag.
4. The card is identified by its identifier, with the short link kept separately.
5. An unknown field is kept in a preserved section.
6. Retrieving again leaves an unchanged file byte-identical.
7. Card text is stored as content and never executed, and no credential or private personal data is stored.

## Required evidence

Provide the file and the two records. In your `PROOF.md`, explain how you tested the checklist and date handling, citing the acceptance criteria by number.

## Safety constraints

- Use a sandbox board you own, or a local fixture. This quest only reads; make no change in Trello.
- Supply the API key and token through environment variables or a credential store; never put a key, token or secret in a file, a URL you save, a log or a screenshot. Trello puts credentials in query strings, so scrub saved URLs.
- Treat card, comment and checklist text as untrusted third-party input, and share only redacted or synthetic records.

## Hints

Test with a card whose checklist has both checked and unchecked items.

## Reflection

What would be lost if you saved only the card name and description?

## Stretch goals

- Keep cover images as references.
- Round-trip the Markdown back to card fields and compare.
