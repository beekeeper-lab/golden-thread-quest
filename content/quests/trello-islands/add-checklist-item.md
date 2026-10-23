---
id: trello-add-checklist-item
version: 1
title: "Add an Approved Checklist Item"
summary: "Add an item to a checklist on a sandbox card only after a person has seen the exact item and its target and confirmed it."
region: trello-islands
level: explorer
xp: 20
estimated_minutes: 60
order: 120
tags:
  - trello
  - checklist
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
  - trello-read-card
  - base-camp-write-preview
outcomes:
  - "Preview the exact item and the checklist it joins."
  - "Add it once after confirmation."
  - "Verify it appears as written and unchecked."
proof:
  required:
    - id: checklist-check
      type: command-record
      description: "Save the redacted output of the preview naming the card, the checklist and the position, of reading the card back and finding the item with the same text, unchecked, in the intended checklist at that position, of an attempt naming a checklist that does not exist being refused, and of an item already present in the live checklist being detected and not added again."
      path: participant/evidence/trello-add-checklist-item/attempt-001/logs/checklist-check.txt
    - id: add-checklist-item-preview
      type: command-record
      description: "Save the redacted output of the workflow stopping at a preview showing the board, the list and the exact material changes to add the checklist item, the token's write scope and expiry, the result of the permission check (may this member do this on this board) and of the duplicate check, or a statement where Trello cannot check, with a fingerprint of the preview, nothing written and a before-and-after snapshot showing the board unchanged."
      path: participant/evidence/trello-add-checklist-item/attempt-001/logs/preview.txt
    - id: add-checklist-item-confirmation
      type: command-record
      description: "Save the redacted output of the approved run showing the explicit confirmation tied to the preview fingerprint and given in the same session as the write, and of four refusals with nothing written: a missing confirmation, a change that differs from the preview, a preview older than the stated time limit, and a board that is not on the sandbox allowlist."
      path: participant/evidence/trello-add-checklist-item/attempt-001/logs/confirmation.txt
    - id: add-checklist-item-result
      type: file
      description: "Provide the result record: the board, list and card identifiers plus the identifier of what was created or changed (a checklist item, comment or action identifier or the read-back value), the timestamp and who confirmed."
      path: participant/context/trello/results/add-checklist-item.md
    - id: add-checklist-item-rerun
      type: command-record
      description: "Save the redacted output of running the approved workflow a second time showing no duplicate, repeated or conflicting change, or, only where Trello cannot prevent a repeat, the stated limit and how a person would notice it."
      path: participant/evidence/trello-add-checklist-item/attempt-001/logs/rerun.txt
    - id: proof-narrative
      type: file
      description: "Explain your approach, your choices and anything you could not do, citing the acceptance criteria by number."
      path: participant/evidence/trello-add-checklist-item/attempt-001/PROOF.md
author: Golden Thread maintainers
last_reviewed: "2026-10-20"
---

# Add an Approved Checklist Item

## Mission

A checklist is shared working state. Show the item and the checklist it joins, and add it once.

## Scenario

An agent adds the same step to every card's checklist three times, because each run starts from a stale copy.

## Acceptance criteria

1. The preview shows the exact item text, the card, the checklist and the position.
2. The item read back matches the text previewed and is unchecked.
3. An item already present in the checklist is detected and not added again.
4. A preview shows the board, the list and the exact changes, and nothing is written before the human confirms it.
5. The preview records the permission check and the duplicate check, or states where Trello cannot perform one.
6. The workflow writes only to a board on an explicit sandbox allowlist and refuses any other.
7. The confirmation is tied to a fingerprint of the exact preview, is refused when missing or when the change differs, and expires after a stated time.
8. A result record holds the board, list and card identifiers, the identifier of what was created or changed, the timestamp and the confirmer.
9. Running the approved workflow again creates no duplicate, repeated or conflicting change, or the quest states the limit where Trello cannot prevent it.

## Required evidence

Provide the checklist check and the four records. In your `PROOF.md`, explain how you detect an existing item, citing the acceptance criteria by number.

## Safety constraints

- Write only to a sandbox board you own and are permitted to change; never to a production or shared team board. If you have no sandbox board, stop and ask your pilot lead; do not substitute a real board or skip the quest's controls.
- Card and comment text you carry into a write is untrusted; review it for private content before approving.
- Supply the API key and token through environment variables or a credential store; never put a key, token or secret in a file, a URL you save, a log or a screenshot. Trello puts credentials in query strings, so scrub saved URLs.
- Do not skip the preview or the confirmation in any run you save as evidence.

## Hints

Compare against the live checklist, not the local copy.

## Reflection

What should happen when two people add the same item at once?

## Stretch goals

- Add several items in one confirmed batch.
- Convert an item into a card with a preview.
