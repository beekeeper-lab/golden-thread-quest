---
id: trello-create-card
version: 1
title: "Create and Reconcile an Approved Card"
summary: "Create the previewed card on a sandbox board after explicit confirmation and record its identifiers locally."
region: trello-islands
level: builder
xp: 30
estimated_minutes: 90
order: 110
tags:
  - trello
  - card
  - write
tools:
  - Markdown
  - YAML
bookend: intent
risk:
  external_write: true
  sensitive_data: true
  notes: "This quest writes to Trello. Use a sandbox board only. Every write is previewed, confirmed by a person, recorded with its identifiers and safe to rerun."
prerequisites:
  - trello-create-card-preview
outcomes:
  - "Create exactly the card that was previewed."
  - "Record the returned identifiers locally."
  - "Reconcile local files to the new card."
proof:
  required:
    - id: local-link
      type: file
      description: "Provide the local card file updated with the board, list and card identifiers returned, matched to the Trello card by identifier, with a read-back-and-compare record showing the created card equals the preview field for field."
      path: participant/context/trello/new-card/linked.md
    - id: create-card-preview
      type: command-record
      description: "Save the redacted output of the workflow stopping at a preview showing the board, the list and the exact material changes to create the card, the token's write scope and expiry, the result of the permission check (may this member do this on this board) and of the duplicate check, or a statement where Trello cannot check, with a fingerprint of the preview, nothing written and a before-and-after snapshot showing the board unchanged."
      path: participant/evidence/trello-create-card/attempt-001/logs/preview.txt
    - id: create-card-confirmation
      type: command-record
      description: "Save the redacted output of the approved run showing the explicit confirmation tied to the preview fingerprint and given in the same session as the write, and of four refusals with nothing written: a missing confirmation, a change that differs from the preview, a preview older than the stated time limit, and a board that is not on the sandbox allowlist."
      path: participant/evidence/trello-create-card/attempt-001/logs/confirmation.txt
    - id: create-card-result
      type: file
      description: "Provide the result record: the board, list and card identifiers plus the identifier of what was created or changed (a checklist item, comment or action identifier or the read-back value), the timestamp and who confirmed."
      path: participant/context/trello/results/create-card.md
    - id: create-card-rerun
      type: command-record
      description: "Save the redacted output of running the approved workflow a second time showing no duplicate, repeated or conflicting change, or, only where Trello cannot prevent a repeat, the stated limit and how a person would notice it."
      path: participant/evidence/trello-create-card/attempt-001/logs/rerun.txt
    - id: proof-narrative
      type: file
      description: "Explain your approach, your choices and anything you could not do, citing the acceptance criteria by number."
      path: participant/evidence/trello-create-card/attempt-001/PROOF.md
author: Golden Thread maintainers
last_reviewed: "2026-10-20"
---

# Create and Reconcile an Approved Card

## Mission

Make one approved write and tie the local record to it.

## Scenario

An agent creates a card and does not record its identifier. The next run creates it again.

## Acceptance criteria

1. The card created matches the previewed payload field for field.
2. The returned identifiers are written to the local file.
3. The local file is matched to the Trello card by identifier afterwards.
4. A preview shows the board, the list and the exact changes, and nothing is written before the human confirms it.
5. The preview records the permission check and the duplicate check, or states where Trello cannot perform one.
6. The workflow writes only to a board on an explicit sandbox allowlist and refuses any other.
7. The confirmation is tied to a fingerprint of the exact preview, is refused when missing or when the change differs, and expires after a stated time.
8. A result record holds the board, list and card identifiers, the identifier of what was created or changed, the timestamp and the confirmer.
9. Running the approved workflow again creates no duplicate, repeated or conflicting change, or the quest states the limit where Trello cannot prevent it.

## Required evidence

Provide the local link, the four records and the result. In your `PROOF.md`, explain how you verified the card equals the preview, citing the acceptance criteria by number.

## Safety constraints

- Write only to a sandbox board you own and are permitted to change; never to a production or shared team board. If you have no sandbox board, stop and ask your pilot lead; do not substitute a real board or skip the quest's controls.
- Card and comment text you carry into a write is untrusted; review it for private content before approving.
- Supply the API key and token through environment variables or a credential store; never put a key, token or secret in a file, a URL you save, a log or a screenshot. Trello puts credentials in query strings, so scrub saved URLs.
- Do not skip the preview or the confirmation in any run you save as evidence.

## Hints

Read the card back after creating it and compare it with the preview.

## Reflection

What happens locally if the write succeeds but recording the identifier fails?

## Stretch goals

- Create the card with its labels in one approved step.
- Handle a timeout where the creation may have happened.
