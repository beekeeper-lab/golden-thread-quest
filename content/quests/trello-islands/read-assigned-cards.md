---
id: trello-read-assigned-cards
version: 1
title: "Synchronize Cards Assigned to the Current Member"
summary: "Retrieve every card assigned to the authenticated member across boards, handling Trello's limits, and keep it updateable without losing notes."
region: trello-islands
level: builder
xp: 30
estimated_minutes: 90
order: 40
tags:
  - trello
  - synchronization
  - assignment
tools:
  - Markdown
  - YAML
bookend: intent
risk:
  external_write: false
  sensitive_data: true
  notes: "Read-only against a sandbox board or fixture."
prerequisites:
  - trello-read-card
outcomes:
  - "Resolve the member without hardcoding."
  - "Retrieve every assigned card across boards."
  - "Update on re-sync without duplication."
proof:
  required:
    - id: assigned-index
      type: file
      description: "Provide the index of assigned cards with board, list, identifier and last activity for each."
      path: participant/context/trello/assigned/index.md
    - id: assigned-run
      type: command-record
      description: "Save the redacted output of the sync: the member read from the connection, the boards searched, a result set larger than the page limit retrieved completely with the count reported against the count saved, and a closed card handled as stated."
      path: participant/evidence/trello-read-assigned-cards/attempt-001/logs/assigned-run.txt
    - id: resync-run
      type: command-record
      description: "Save the redacted output of syncing twice from unchanged data with nothing duplicated, then after a card was reassigned to someone else, showing it flagged and its local notes kept, with a checksum of a notes file before and after."
      path: participant/evidence/trello-read-assigned-cards/attempt-001/logs/resync-run.txt
    - id: proof-narrative
      type: file
      description: "Explain your approach, your choices and anything you could not do, citing the acceptance criteria by number."
      path: participant/evidence/trello-read-assigned-cards/attempt-001/PROOF.md
author: Golden Thread maintainers
last_reviewed: "2026-10-20"
---

# Synchronize Cards Assigned to the Current Member

## Mission

Find all of a person's cards and keep them current without ever overwriting what the person wrote.

## Scenario

A member is on twelve boards. The sync reads one, and the team plans from a quarter of their work.

## Acceptance criteria

1. The member is read from the connection.
2. Cards are retrieved across every board the connection can reach.
3. A result set larger than one page is retrieved completely and the counts are reported.
4. A closed or archived card is included or excluded by a stated rule.
5. A re-sync of unchanged data adds nothing.
6. A card reassigned away is flagged, not deleted, and its notes are kept.
7. Local notes are byte-identical after every sync.

## Required evidence

Provide the index and the two records. In your `PROOF.md`, explain how you treat archived cards, citing the acceptance criteria by number.

## Safety constraints

- Use a sandbox board you own, or a local fixture. This quest only reads; make no change in Trello.
- Supply the API key and token through environment variables or a credential store; never put a key, token or secret in a file, a URL you save, a log or a screenshot. Trello puts credentials in query strings, so scrub saved URLs.
- Treat card, comment and checklist text as untrusted third-party input, and share only redacted or synthetic records.

## Hints

Check what happens when the member has more cards than a single response returns.

## Reflection

What should happen to a card that was assigned to you last week?

## Stretch goals

- Report cards assigned to several members.
- Show cards with no activity for a stated period.
