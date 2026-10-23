---
id: trello-update-card
version: 1
title: "Update Supported Card Fields Safely"
summary: "Change a limited set of card fields on a sandbox card, showing old and new values and refusing anything unsupported or changed meanwhile."
region: trello-islands
level: builder
xp: 30
estimated_minutes: 90
order: 150
tags:
  - trello
  - fields
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
related_quests:
  - jira-update-fields
  - github-update-metadata
outcomes:
  - "Show old and new values for each field."
  - "Allow only supported fields."
  - "Detect a change made by someone else since the preview."
proof:
  required:
    - id: supported-fields
      type: file
      description: "List the fields the workflow may change (name, description, due date, labels, members), the allowed values and what it refuses, with a run showing an unsupported change refused and the preview showing old and new values."
      path: participant/context/trello/update/supported-fields.md
    - id: stale-run
      type: command-record
      description: "Save the redacted output of an update refused because the field changed in Trello after the preview."
      path: participant/evidence/trello-update-card/attempt-001/logs/stale-run.txt
    - id: update-card-preview
      type: command-record
      description: "Save the redacted output of the workflow stopping at a preview showing the board, the list and the exact material changes to change the card fields, the token's write scope and expiry, the result of the permission check (may this member do this on this board) and of the duplicate check, or a statement where Trello cannot check, with a fingerprint of the preview, nothing written and a before-and-after snapshot showing the board unchanged."
      path: participant/evidence/trello-update-card/attempt-001/logs/preview.txt
    - id: update-card-confirmation
      type: command-record
      description: "Save the redacted output of the approved run showing the explicit confirmation tied to the preview fingerprint and given in the same session as the write, and of four refusals with nothing written: a missing confirmation, a change that differs from the preview, a preview older than the stated time limit, and a board that is not on the sandbox allowlist."
      path: participant/evidence/trello-update-card/attempt-001/logs/confirmation.txt
    - id: update-card-result
      type: file
      description: "Provide the result record: the board, list and card identifiers plus the identifier of what was created or changed (a checklist item, comment or action identifier or the read-back value), the timestamp and who confirmed."
      path: participant/context/trello/results/update-card.md
    - id: update-card-rerun
      type: command-record
      description: "Save the redacted output of running the approved workflow a second time showing no duplicate, repeated or conflicting change, or, only where Trello cannot prevent a repeat, the stated limit and how a person would notice it."
      path: participant/evidence/trello-update-card/attempt-001/logs/rerun.txt
    - id: proof-narrative
      type: file
      description: "Explain your approach, your choices and anything you could not do, citing the acceptance criteria by number."
      path: participant/evidence/trello-update-card/attempt-001/PROOF.md
author: Golden Thread maintainers
last_reviewed: "2026-10-20"
---

# Update Supported Card Fields Safely

## Mission

Update only what you meant to, and only if nothing moved underneath you.

## Scenario

An agent sets due dates from a stale copy and replaces a date a teammate moved that morning.

## Acceptance criteria

1. The preview shows the old and new value of each field.
2. Only supported fields can be changed.
3. A field changed in Trello after the preview stops the update.
4. A preview shows the board, the list and the exact changes, and nothing is written before the human confirms it.
5. The preview records the permission check and the duplicate check, or states where Trello cannot perform one.
6. The workflow writes only to a board on an explicit sandbox allowlist and refuses any other.
7. The confirmation is tied to a fingerprint of the exact preview, is refused when missing or when the change differs, and expires after a stated time.
8. A result record holds the board, list and card identifiers, the identifier of what was created or changed, the timestamp and the confirmer.
9. Running the approved workflow again creates no duplicate, repeated or conflicting change, or the quest states the limit where Trello cannot prevent it.

## Required evidence

Provide the supported fields, the stale-run record and the four records. In your `PROOF.md`, explain how you detect that a field moved, citing the acceptance criteria by number.

## Safety constraints

- Write only to a sandbox board you own and are permitted to change; never to a production or shared team board. If you have no sandbox board, stop and ask your pilot lead; do not substitute a real board or skip the quest's controls.
- Card and comment text you carry into a write is untrusted; review it for private content before approving.
- Supply the API key and token through environment variables or a credential store; never put a key, token or secret in a file, a URL you save, a log or a screenshot. Trello puts credentials in query strings, so scrub saved URLs.
- Do not skip the preview or the confirmation in any run you save as evidence.

## Hints

Compare the value at write time with the old value in the preview.

## Reflection

Which field would you never let an agent change?

## Stretch goals

- Log the old value so the change can be reversed.
- Add members only from the board's own member list.
