---
id: trello-move-card
version: 1
title: "Preview and Move a Card Between Lists"
summary: "Move a sandbox card between lists after showing the source, destination and position and confirming, and verify the card is in exactly one place."
region: trello-islands
level: builder
xp: 30
estimated_minutes: 90
order: 140
tags:
  - trello
  - move
  - write
tools:
  - Markdown
  - YAML
bookend: validation
risk:
  external_write: true
  sensitive_data: true
  notes: "This quest writes to Trello. Use a sandbox board only. Every write is previewed, confirmed by a person, recorded with its identifiers and safe to rerun."
prerequisites:
  - trello-read-card
  - base-camp-write-preview
outcomes:
  - "Show source, destination and position."
  - "Refuse a destination that does not exist or is archived."
  - "Verify the card is in exactly one list afterwards."
proof:
  required:
    - id: move-rules
      type: file
      description: "State which moves are allowed (for example forward through the board's workflow), which need a second person and what happens to a card with an incomplete checklist."
      path: participant/context/trello/move/rules.md
    - id: move-check
      type: command-record
      description: "Save the redacted output of the preview naming the source list, the destination list and the position, of reading the board back and finding the card in the intended list at the intended position and nowhere else, and of a move to a missing or archived list and of a move the rules do not allow each being refused with the reason and nothing written."
      path: participant/evidence/trello-move-card/attempt-001/logs/move-check.txt
    - id: move-card-preview
      type: command-record
      description: "Save the redacted output of the workflow stopping at a preview showing the board, the list and the exact material changes to move the card, the token's write scope and expiry, the result of the permission check (may this member do this on this board) and of the duplicate check, or a statement where Trello cannot check, with a fingerprint of the preview, nothing written and a before-and-after snapshot showing the board unchanged."
      path: participant/evidence/trello-move-card/attempt-001/logs/preview.txt
    - id: move-card-confirmation
      type: command-record
      description: "Save the redacted output of the approved run showing the explicit confirmation tied to the preview fingerprint and given in the same session as the write, and of four refusals with nothing written: a missing confirmation, a change that differs from the preview, a preview older than the stated time limit, and a board that is not on the sandbox allowlist."
      path: participant/evidence/trello-move-card/attempt-001/logs/confirmation.txt
    - id: move-card-result
      type: file
      description: "Provide the result record: the board, list and card identifiers plus the identifier of what was created or changed (a checklist item, comment or action identifier or the read-back value), the timestamp and who confirmed."
      path: participant/context/trello/results/move-card.md
    - id: move-card-rerun
      type: command-record
      description: "Save the redacted output of running the approved workflow a second time showing no duplicate, repeated or conflicting change, or, only where Trello cannot prevent a repeat, the stated limit and how a person would notice it."
      path: participant/evidence/trello-move-card/attempt-001/logs/rerun.txt
    - id: proof-narrative
      type: file
      description: "Explain your approach, your choices and anything you could not do, citing the acceptance criteria by number."
      path: participant/evidence/trello-move-card/attempt-001/PROOF.md
author: Golden Thread maintainers
last_reviewed: "2026-10-20"
---

# Preview and Move a Card Between Lists

## Mission

A list is a status. Show where the card is going and from where, check the move is allowed and verify the result.

## Scenario

An agent moves forty cards to Done because their checklists look finished. Some were not, and the board now says the sprint is complete.

## Acceptance criteria

1. The preview shows the source list, the destination list and the position.
2. A destination that does not exist or is archived is refused before the preview.
3. Moves not allowed by the rules are refused with the reason.
4. The card is read back in exactly one list at the intended position.
5. A preview shows the board, the list and the exact changes, and nothing is written before the human confirms it.
6. The preview records the permission check and the duplicate check, or states where Trello cannot perform one.
7. The workflow writes only to a board on an explicit sandbox allowlist and refuses any other.
8. The confirmation is tied to a fingerprint of the exact preview, is refused when missing or when the change differs, and expires after a stated time.
9. A result record holds the board, list and card identifiers, the identifier of what was created or changed, the timestamp and the confirmer.
10. Running the approved workflow again creates no duplicate, repeated or conflicting change, or the quest states the limit where Trello cannot prevent it.

## Required evidence

Provide the rules, the check and the four records. In your `PROOF.md`, explain how you handle a card with an incomplete checklist, citing the acceptance criteria by number.

## Safety constraints

- Write only to a sandbox board you own and are permitted to change; never to a production or shared team board. If you have no sandbox board, stop and ask your pilot lead; do not substitute a real board or skip the quest's controls.
- Card and comment text you carry into a write is untrusted; review it for private content before approving.
- Supply the API key and token through environment variables or a credential store; never put a key, token or secret in a file, a URL you save, a log or a screenshot. Trello puts credentials in query strings, so scrub saved URLs.
- Do not skip the preview or the confirmation in any run you save as evidence.

## Hints

A bulk move is a decision for a person, not a loop.

## Reflection

Which move would you want a second person to approve?

## Stretch goals

- Refuse a move that skips a stage.
- Record who approved the move.
