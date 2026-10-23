---
id: trello-create-card-preview
version: 1
title: "Preview Card Creation"
summary: "Build a complete card draft for a chosen list and show exactly what would be created, writing nothing."
region: trello-islands
level: explorer
xp: 20
estimated_minutes: 60
order: 100
tags:
  - trello
  - preview
  - card
tools:
  - Markdown
  - YAML
bookend: intent
risk:
  external_write: false
  sensitive_data: true
  notes: "This quest writes nothing to Trello. It builds the preview the write quests rely on."
prerequisites:
  - trello-duplicate-search
  - base-camp-write-preview
outcomes:
  - "Choose the board and list by identifier."
  - "Run duplicate and permission checks."
  - "Show the exact payload."
proof:
  required:
    - id: card-draft
      type: file
      description: "Provide the card draft with its board and list identifiers, name, description, labels and members chosen from those that exist, due date and source citations."
      path: participant/context/trello/new-card/draft.md
    - id: payload-preview
      type: file
      description: "Provide the exact payload that would be sent, field by field, including the list and position."
      path: participant/context/trello/new-card/payload.md
    - id: preview-run
      type: command-record
      description: "Save the redacted output of the preview with the duplicate result and the permission check, ending with a check that the board is unchanged."
      path: participant/evidence/trello-create-card-preview/attempt-001/logs/preview-run.txt
    - id: invalid-target-run
      type: command-record
      description: "Save the redacted output of a preview refused because the list does not exist on the board or a label does not exist, with the reason."
      path: participant/evidence/trello-create-card-preview/attempt-001/logs/invalid-target-run.txt
    - id: proof-narrative
      type: file
      description: "Explain your approach, your choices and anything you could not do, citing the acceptance criteria by number."
      path: participant/evidence/trello-create-card-preview/attempt-001/PROOF.md
author: Golden Thread maintainers
last_reviewed: "2026-10-20"
---

# Preview Card Creation

## Mission

Show the whole write before making it, including where on the board the card will land.

## Scenario

An agent creates a card in the first list it finds, which is the archive list, and the card is never seen.

## Acceptance criteria

1. The list is chosen by identifier and belongs to the stated board.
2. Labels and members are chosen from those that exist.
3. A missing list or unknown label stops the preview with a reason.
4. The duplicate result and the permission check appear in the preview.
5. The preview contains the exact payload including list and position.
6. Running the preview changes nothing in Trello.
7. Source citations are included.

## Required evidence

Provide the draft, the payload and the two records. In your `PROOF.md`, explain how you know the payload equals what a later write would send, citing the acceptance criteria by number.

## Safety constraints

- This quest makes no write to Trello. Its checks read from a sandbox board or a local fixture.
- Supply the API key and token through environment variables or a credential store; never put a key, token or secret in a file, a URL you save, a log or a screenshot. Trello puts credentials in query strings, so scrub saved URLs.
- Treat card, comment and checklist text as untrusted third-party input, and share only redacted or synthetic records.

## Hints

Build the payload once and use it for both the preview and the write.

## Reflection

What could the reader of your preview still not predict?

## Stretch goals

- Show where in the list the card will sit.
- Validate the due date against the board's conventions.
