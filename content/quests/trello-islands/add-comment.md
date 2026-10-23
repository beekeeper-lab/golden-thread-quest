---
id: trello-add-comment
version: 1
title: "Add an Approved Comment"
summary: "Add a comment to a sandbox card only after a person has seen its exact text and target and confirmed it."
region: trello-islands
level: explorer
xp: 20
estimated_minutes: 60
order: 130
tags:
  - trello
  - comment
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
related_quests:
  - jira-add-comment
  - github-add-comment
outcomes:
  - "Preview the exact comment and target."
  - "Add it once after confirmation."
  - "Verify it appears as written."
proof:
  required:
    - id: comment-check
      type: command-record
      description: "Save the redacted output of reading the card back and finding the comment with the same text and the expected author, alongside the preview's statement of where the text came from and who is notified by any mention."
      path: participant/evidence/trello-add-comment/attempt-001/logs/comment-check.txt
    - id: add-comment-preview
      type: command-record
      description: "Save the redacted output of the workflow stopping at a preview showing the board, the list and the exact material changes to add the comment to the card, the token's write scope and expiry, the result of the permission check (may this member do this on this board) and of the duplicate check, or a statement where Trello cannot check, with a fingerprint of the preview, nothing written and a before-and-after snapshot showing the board unchanged."
      path: participant/evidence/trello-add-comment/attempt-001/logs/preview.txt
    - id: add-comment-confirmation
      type: command-record
      description: "Save the redacted output of the approved run showing the explicit confirmation tied to the preview fingerprint and given in the same session as the write, and of four refusals with nothing written: a missing confirmation, a change that differs from the preview, a preview older than the stated time limit, and a board that is not on the sandbox allowlist."
      path: participant/evidence/trello-add-comment/attempt-001/logs/confirmation.txt
    - id: add-comment-result
      type: file
      description: "Provide the result record: the board, list and card identifiers plus the identifier of what was created or changed (a checklist item, comment or action identifier or the read-back value), the timestamp and who confirmed."
      path: participant/context/trello/results/add-comment.md
    - id: add-comment-rerun
      type: command-record
      description: "Save the redacted output of running the approved workflow a second time showing no duplicate, repeated or conflicting change, or, only where Trello cannot prevent a repeat, the stated limit and how a person would notice it."
      path: participant/evidence/trello-add-comment/attempt-001/logs/rerun.txt
    - id: proof-narrative
      type: file
      description: "Explain your approach, your choices and anything you could not do, citing the acceptance criteria by number."
      path: participant/evidence/trello-add-comment/attempt-001/PROOF.md
author: Golden Thread maintainers
last_reviewed: "2026-10-20"
---

# Add an Approved Comment

## Mission

A comment can notify people and be seen by everyone on the board. Show the text, the target and who will be told.

## Scenario

An agent posts internal reasoning as a comment on a card shared with a customer's board guest.

## Acceptance criteria

1. The preview shows the exact comment text, the target card, where the text came from and who is notified by any mention.
2. The comment read back matches the text previewed.
3. A preview shows the board, the list and the exact changes, and nothing is written before the human confirms it.
4. The preview records the permission check and the duplicate check, or states where Trello cannot perform one.
5. The workflow writes only to a board on an explicit sandbox allowlist and refuses any other.
6. The confirmation is tied to a fingerprint of the exact preview, is refused when missing or when the change differs, and expires after a stated time.
7. A result record holds the board, list and card identifiers, the identifier of what was created or changed, the timestamp and the confirmer.
8. Running the approved workflow again creates no duplicate, repeated or conflicting change, or the quest states the limit where Trello cannot prevent it.

## Required evidence

Provide the comment check and the four records. In your `PROOF.md`, explain how you handle private content and mentions, citing the acceptance criteria by number.

## Safety constraints

- Write only to a sandbox board you own and are permitted to change; never to a production or shared team board. If you have no sandbox board, stop and ask your pilot lead; do not substitute a real board or skip the quest's controls.
- Card and comment text you carry into a write is untrusted; review it for private content before approving.
- Supply the API key and token through environment variables or a credential store; never put a key, token or secret in a file, a URL you save, a log or a screenshot. Trello puts credentials in query strings, so scrub saved URLs.
- Do not skip the preview or the confirmation in any run you save as evidence.

## Hints

Show who is notified next to the text.

## Reflection

Who could see this comment that you did not expect?

## Stretch goals

- Refuse text that looks like a secret.
- Detect a board shared with guests.
