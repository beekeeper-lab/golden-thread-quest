---
id: trap-mimic-ticket
version: 1
title: "The Mimic Ticket: A Duplicate Request Resembles New Work"
summary: "Build a request that looks like new work but duplicates existing work in different words, and show your workflow links it instead of creating it."
region: trap-cards
level: navigator
xp: 50
estimated_minutes: 120
order: 20
tags:
  - trap
  - duplicates
  - judgment
tools:
  - Markdown
  - YAML
bookend: validation
risk:
  external_write: false
  sensitive_data: false
  notes: "The trap and the catalog are synthetic and local."
prerequisites:
  - ba-search-existing-work
outcomes:
  - "Construct a duplicate that survives a title match."
  - "Show the workflow catches it."
  - "Show it does not over-catch genuinely new work."
proof:
  required:
    - id: trap-catalog
      type: file
      description: "Provide a synthetic catalog of at least twelve items and a mimic request: a duplicate of one item that shares no title words and differs in wording, ownership and format, plus a near-miss that is related to it but distinct."
      path: participant/context/traps/mimic/catalog.md
    - id: mimic-run
      type: command-record
      description: "Save the redacted output of the workflow on the mimic request showing it linked to the existing item with the signals that matched and no new item created, on the near-miss, labeled related and not duplicate, and on a genuinely new request, showing it proceeded."
      path: participant/evidence/trap-mimic-ticket/attempt-001/logs/mimic-run.txt
    - id: mimic-notes
      type: file
      description: "Explain why a title-only search would have missed the mimic, which signals caught it and the false match you tried to avoid."
      path: participant/context/traps/mimic/notes.md
    - id: proof-narrative
      type: file
      description: "Explain your approach, your choices and anything you could not do, citing the acceptance criteria by number."
      path: participant/evidence/trap-mimic-ticket/attempt-001/PROOF.md
author: Golden Thread maintainers
last_reviewed: "2026-10-20"
---

# The Mimic Ticket: A Duplicate Request Resembles New Work

## Mission

Build the mimic yourself and make your own process catch it. The point is to find which signals still agree when the words do not.

## Scenario

A stakeholder emails a request for a CSV export of attendee lists. Eight months ago someone filed spreadsheet download for guest data, and it is half built. The new ticket sails through because nothing in the title matches.

## Acceptance criteria

1. The mimic shares no significant title words with the item it duplicates.
2. The workflow links the mimic to the existing item and creates nothing.
3. The output lists the signals that matched.
4. A genuinely new request in the same catalog is not linked.
5. A near-miss that is related but distinct is labeled related, not duplicate.
6. The notes explain what a title-only search would have done.

## Required evidence

Provide the catalog, the run and the notes. In your `PROOF.md`, say which signal did most of the work and what would defeat it, citing the acceptance criteria by number.

## Safety constraints

- Build the trap from synthetic data with invented names and identifiers; never aim it at a real system, ticket or person.
- Nothing in this challenge is sent to, or written to, an external system.

## Hints

Look for the shared noun, the shared requester, the shared acceptance criterion.

## Reflection

What would a determined requester do to make a duplicate undetectable?

## Stretch goals

- Add a second mimic that defeats your first approach.
- Score how close the mimic came to being missed.
