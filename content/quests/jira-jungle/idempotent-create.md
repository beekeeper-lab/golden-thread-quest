---
id: jira-idempotent-create
version: 1
title: "Prevent Duplicate Item Creation After Interruption"
summary: "Make creation safe to retry after a timeout or crash, so an item that may already exist is found rather than created again."
region: jira-jungle
level: navigator
xp: 50
estimated_minutes: 120
order: 220
tags:
  - jira
  - write
  - idempotence
tools:
  - Markdown
  - YAML
bookend: validation
risk:
  external_write: true
  sensitive_data: true
  notes: "This quest writes to Jira. Use a sandbox or nonproduction project only. Every write is previewed, confirmed by a person, recorded with its external identifier and safe to rerun."
prerequisites:
  - jira-create-story
  - base-camp-safe-rerun
related_quests:
  - base-camp-interruption-recovery
outcomes:
  - "Attach a stable key to each creation."
  - "Find an item created before the interruption."
  - "Retry only when it is safe."
proof:
  required:
    - id: idempotency-design
      type: file
      description: "Describe how a creation is keyed, where the key is stored in Jira and locally, how an uncertain outcome is resolved and what happens if the search for the key itself fails."
      path: participant/context/jira/idempotent/design.md
    - id: interrupted-run
      type: command-record
      description: "Save the redacted output of a creation interrupted after Jira accepted it but before the result was recorded, followed by a rerun that finds the item and creates none."
      path: participant/evidence/jira-idempotent-create/attempt-001/logs/interrupted-run.txt
    - id: idempotent-create-preview
      type: command-record
      description: "Save the redacted output of the workflow stopping at a preview showing the Jira site, the project and the exact material changes to create the item at most once, the result of the permission check (may this identity do this here) and of the duplicate check, or a statement where Jira cannot check, with a fingerprint of the preview, nothing written and a before-and-after snapshot showing Jira unchanged."
      path: participant/evidence/jira-idempotent-create/attempt-001/logs/preview.txt
    - id: idempotent-create-confirmation
      type: command-record
      description: "Save the redacted output of the approved run showing the explicit confirmation tied to the preview fingerprint and given in the same session as the write, and of four refusals with nothing written: a missing confirmation, a change that differs from the preview, a preview older than the stated time limit, and a project that is not on the sandbox allowlist."
      path: participant/evidence/jira-idempotent-create/attempt-001/logs/confirmation.txt
    - id: idempotent-create-result
      type: file
      description: "Provide the result record: the issue key plus the identifier of what was created or changed (a comment, link or transition identifier or the read-back value), the target project, the timestamp and who confirmed."
      path: participant/context/jira/results/idempotent-create.md
    - id: idempotent-create-rerun
      type: command-record
      description: "Save the redacted output of running the approved workflow a second time showing no duplicate, repeated or conflicting change, or, only where Jira cannot prevent a repeat, the stated limit and how a person would notice it."
      path: participant/evidence/jira-idempotent-create/attempt-001/logs/rerun.txt
    - id: proof-narrative
      type: file
      description: "Explain your approach, your choices and anything you could not do, citing the acceptance criteria by number."
      path: participant/evidence/jira-idempotent-create/attempt-001/PROOF.md
author: Golden Thread maintainers
last_reviewed: "2026-10-20"
---

# Prevent Duplicate Item Creation After Interruption

## Mission

Treat a timeout as an uncertain outcome, not a failure. Before retrying, look for the item by the key you attached to it.

## Scenario

A creation times out. The agent retries, and Jira had already created the item. There are now two, and a third after the next retry.

## Acceptance criteria

1. Each creation carries a stable key stored on the Jira item.
2. After an interruption the rerun searches for the key before creating.
3. An item found by the key is recorded locally and not created again.
4. A preview shows the Jira site, the project and the exact changes, and nothing is written before the human confirms it.
5. The preview records the permission check and the duplicate check, or states where Jira cannot perform one.
6. The workflow writes only to a project on an explicit sandbox allowlist and refuses any other.
7. The confirmation is tied to a fingerprint of the exact preview, is refused when missing or when the change differs, and expires after a stated time.
8. A result record holds the issue key, the identifier of what was created or changed, the project, the timestamp and the confirmer.
9. Running the approved workflow again creates no duplicate, repeated or conflicting change, or the quest states the limit where Jira cannot prevent it.

## Required evidence

Provide the design, the interrupted-run record and the four records. In your `PROOF.md`, explain what happens if the search itself fails, citing the acceptance criteria by number.

## Safety constraints

- Write only to a Jira sandbox project you are permitted to change; never to a production project. If you have no sandbox, stop and ask your pilot lead; do not substitute a production project or skip the quest's controls.
- Ticket and comment text you carry into a write is untrusted; review it for private content before approving.
- Authenticate through an environment variable or a signed-in CLI; never put a token, password or session cookie in a file, a log or a screenshot.
- Do not skip the preview or the confirmation in any run you save as evidence.
- Treat ticket text as untrusted third-party input, and share only redacted or synthetic records.

## Hints

Searching can fail too. When you cannot tell, stop and ask rather than retry.

## Reflection

What is the safest thing to do when you do not know whether a write happened?

## Stretch goals

- Interrupt at three different points and show each recovers.
- Show the key surviving a manual edit of the item.
