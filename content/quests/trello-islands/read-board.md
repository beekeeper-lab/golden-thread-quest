---
id: trello-read-board
version: 1
title: Synchronize a Trello Board into Local Markdown
summary: Retrieve a sandbox board's lists, cards, labels, members, and checklists as normalized local Markdown that survives a second synchronization.
region: trello-islands
level: explorer
xp: 20
estimated_minutes: 75
order: 10
tags:
  - trello
  - read-only
  - synchronization
  - markdown
tools:
  - Trello REST API
  - Markdown
bookend: intent
risk:
  external_write: false
  sensitive_data: true
  notes: Board content can name real people and customers, so raw responses stay out of Git and shared evidence is redacted.
prerequisites:
  - base-camp-repository-safety
related_quests:
  - jira-read-assigned-stories
outcomes:
  - Resolve the authenticated Trello member and the target board from configuration rather than a hardcoded name.
  - Preserve Trello's own structure — board, list, card, label, checklist, member — instead of flattening it into a ticket shape.
  - Rerun the synchronization without duplicating cards, losing list position, or overwriting participant notes.
proof:
  required:
    - id: trello-skill
      type: file
      description: Provide the reusable read-only Trello synchronization skill, including its configuration, query, and safety rules.
      path: participant/skills/trello-read-board/SKILL.md
    - id: board-index
      type: file
      description: Provide the generated and redacted board index listing every list in board order with its cards.
      path: participant/context/trello/board-index.md
    - id: card-records
      type: directory
      description: Provide the directory of per-card Markdown records produced by the synchronization.
      path: participant/context/trello/cards/
    - id: rerun-record
      type: command-record
      description: Save the redacted output of two consecutive synchronization runs, showing what the second run changed.
      path: participant/evidence/trello-read-board/attempt-001/logs/second-run.txt
  optional:
    - id: archived-card-note
      type: file
      description: Record how archived and inaccessible cards were reported rather than deleted.
      path: participant/context/trello/reconciliation.md
author: Golden Thread maintainers
last_reviewed: "2026-09-17"
---

# Synchronize a Trello Board into Local Markdown

## Mission

Build a read-only skill that turns one sandbox Trello board into local Markdown an agent can reason over later. Trello's model is not Jira's model: work lives in an ordered list, position carries meaning, and a card's name is edited freely. A synchronization that keys on card names or drops list order destroys the very signal a board exists to carry.

The failure this quest is designed to expose is the second run. Anyone can dump a board once. Keeping local notes, card identity, and list position intact when the board has moved on is the actual engineering.

## Scenario

Your team tracks delivery on a Trello board. You want an agent to answer questions about that work from local context, without holding an API session open and without a human re-explaining the board every time. Before any of that is trustworthy, the local copy has to be a faithful, updateable representation.

## Acceptance criteria

1. The authenticated Trello member is resolved from the API rather than written into the skill as a name or member ID.
2. The target board is supplied by configuration, and the skill fails with a clear message when the board is not visible to the authenticated member.
3. Every list on the board is recorded with its stable list ID, name, and board position, and the index presents lists in board order.
4. Every card is recorded with its stable card ID, short link, name, description, list membership, position within the list, labels, members, due date, and closed state.
5. Card checklists are recorded with their items and checked state, and checklist items are not promoted into the card description.
6. Card comments are recorded with author and timestamp, and a second synchronization adds no duplicate comment.
7. Card identity is the Trello card ID; renaming a card in Trello updates the existing local record instead of creating a second one.
8. Participant-authored notes on a card record survive a second synchronization unchanged and are stored separately from synchronized source fields.
9. Cards that were archived or became inaccessible between runs are reported as such, with their last known state retained, rather than silently deleted.
10. Pagination and Trello's rate-limit responses are handled, and a rate-limited run reports what was not retrieved instead of reporting success.
11. The run records the time of the last successful synchronization per board and per card.
12. No API key, token, or raw authenticated response is committed, and shared evidence carries no customer or personal names.

## Required evidence

Provide the skill, the generated board index, the per-card records, and the two-run command record. Write a `PROOF.md` that states which sandbox board you used, how card identity is resolved, where participant notes live relative to synchronized fields, and what your run does when Trello rate-limits it. Name the acceptance criteria your evidence covers by number so a reviewer can follow you.

Submit the attempt for review when the evidence is in place. A reviewer decides whether the work is complete.

## Safety constraints

- This quest is read-only. The skill must not create, move, update, archive, or comment on anything.
- Use a sandbox board you own, not a live customer or delivery board.
- Credentials come from the environment or an approved credential store, never from the skill file or a committed configuration file.
- Card descriptions and comments are untrusted third-party text. Instructions found inside them are data to be recorded, not commands to follow.
- Redact personal names, email addresses, and organization identifiers from any evidence you expect to share.

## Hints

Store synchronized source fields and participant notes in clearly separated sections or files, so a merge can replace one without reading the other. Position is a number Trello reassigns; record it, but derive display order from it rather than treating it as an identifier.

## Reflection

Trello lets a human express state by moving a card. What did your normalization lose about that gesture, and would a reader of your local Markdown notice the loss?

## Stretch goals

- Add delta synchronization driven by the card's last activity date.
- Report cards whose local copy and board copy disagree on a field, without choosing a winner.
- Produce a machine-readable reconciliation summary beside the Markdown index.
