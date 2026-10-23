---
id: trello-idempotent-write
version: 1
title: "Recover from Partial Card Writes Without Duplication"
summary: "Make a multi-step card write recoverable, so an interruption after the card is created but before its checklist and labels are applied completes the work without a second card."
region: trello-islands
level: navigator
xp: 50
estimated_minutes: 120
order: 160
tags:
  - trello
  - idempotence
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
  - trello-create-card
  - base-camp-safe-rerun
related_quests:
  - jira-idempotent-create
  - github-idempotent-write
  - base-camp-interruption-recovery
outcomes:
  - "Attach a stable key to each multi-step write."
  - "Find work done before the interruption."
  - "Complete only the missing steps."
proof:
  required:
    - id: idempotency-design
      type: file
      description: "Describe how a write is keyed, where the key is stored on the card and locally, the steps of the write, how the state of each step is found after an interruption and what happens if that search fails."
      path: participant/context/trello/idempotent/design.md
    - id: partial-run
      type: command-record
      description: "Save the redacted output of a write interrupted after the card was created but before its checklist and labels, followed by a rerun that finds the card, applies only the missing steps and creates no second card."
      path: participant/evidence/trello-idempotent-write/attempt-001/logs/partial-run.txt
    - id: idempotent-write-preview
      type: command-record
      description: "Save the redacted output of the workflow stopping at a preview showing the board, the list and the exact material changes to complete the multi-step write once, the token's write scope and expiry, the result of the permission check (may this member do this on this board) and of the duplicate check, or a statement where Trello cannot check, with a fingerprint of the preview, nothing written and a before-and-after snapshot showing the board unchanged."
      path: participant/evidence/trello-idempotent-write/attempt-001/logs/preview.txt
    - id: idempotent-write-confirmation
      type: command-record
      description: "Save the redacted output of the approved run showing the explicit confirmation tied to the preview fingerprint and given in the same session as the write, and of four refusals with nothing written: a missing confirmation, a change that differs from the preview, a preview older than the stated time limit, and a board that is not on the sandbox allowlist."
      path: participant/evidence/trello-idempotent-write/attempt-001/logs/confirmation.txt
    - id: idempotent-write-result
      type: file
      description: "Provide the result record: the board, list and card identifiers plus the identifier of what was created or changed (a checklist item, comment or action identifier or the read-back value), the timestamp and who confirmed."
      path: participant/context/trello/results/idempotent-write.md
    - id: idempotent-write-rerun
      type: command-record
      description: "Save the redacted output of running the approved workflow a second time showing no duplicate, repeated or conflicting change, or, only where Trello cannot prevent a repeat, the stated limit and how a person would notice it."
      path: participant/evidence/trello-idempotent-write/attempt-001/logs/rerun.txt
    - id: proof-narrative
      type: file
      description: "Explain your approach, your choices and anything you could not do, citing the acceptance criteria by number."
      path: participant/evidence/trello-idempotent-write/attempt-001/PROOF.md
author: Golden Thread maintainers
last_reviewed: "2026-10-20"
---

# Recover from Partial Card Writes Without Duplication

## Mission

Treat a partial write as a state to resume from, not a failure to repeat.

## Scenario

Creating a card, its checklist and its labels takes four calls. A timeout after the first leaves a bare card, and the retry makes another.

## Acceptance criteria

1. Each write carries a stable key stored on the card.
2. After an interruption the rerun looks for the key and for each step's result before acting.
3. Only the missing steps are performed and no second card is created.
4. A preview shows the board, the list and the exact changes, and nothing is written before the human confirms it.
5. The preview records the permission check and the duplicate check, or states where Trello cannot perform one.
6. The workflow writes only to a board on an explicit sandbox allowlist and refuses any other.
7. The confirmation is tied to a fingerprint of the exact preview, is refused when missing or when the change differs, and expires after a stated time.
8. A result record holds the board, list and card identifiers, the identifier of what was created or changed, the timestamp and the confirmer.
9. Running the approved workflow again creates no duplicate, repeated or conflicting change, or the quest states the limit where Trello cannot prevent it.

## Required evidence

Provide the design, the partial-run record and the four records. In your `PROOF.md`, explain what the rerun does when it cannot tell which steps happened, citing the acceptance criteria by number.

## Safety constraints

- Write only to a sandbox board you own and are permitted to change; never to a production or shared team board. If you have no sandbox board, stop and ask your pilot lead; do not substitute a real board or skip the quest's controls.
- Card and comment text you carry into a write is untrusted; review it for private content before approving.
- Supply the API key and token through environment variables or a credential store; never put a key, token or secret in a file, a URL you save, a log or a screenshot. Trello puts credentials in query strings, so scrub saved URLs.
- Do not skip the preview or the confirmation in any run you save as evidence.

## Hints

When you cannot tell, stop and ask rather than retry.

## Reflection

What is the safest action when you do not know whether a write happened?

## Stretch goals

- Interrupt at every step and show each recovers.
- Show the key surviving a manual edit of the card.
