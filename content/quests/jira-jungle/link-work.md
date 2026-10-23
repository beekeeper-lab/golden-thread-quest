---
id: jira-link-work
version: 1
title: "Create Approved Issue Relationships and Verify Them"
summary: "Link two sandbox items with a chosen relationship after confirmation, and verify the link from both sides."
region: jira-jungle
level: builder
xp: 30
estimated_minutes: 90
order: 210
tags:
  - jira
  - write
  - links
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
outcomes:
  - "Choose the right link type and direction."
  - "Create the link once."
  - "Verify it from both items."
proof:
  required:
    - id: link-check
      type: command-record
      description: "Save the redacted output of the preview stating the relationship and its direction in words, of an existing identical link being detected and not created again, and of reading both items back and finding the link with the correct type and direction on each."
      path: participant/evidence/jira-link-work/attempt-001/logs/link-check.txt
    - id: link-work-preview
      type: command-record
      description: "Save the redacted output of the workflow stopping at a preview showing the Jira site, the project and the exact material changes to create the link between the two items, the result of the permission check (may this identity do this here) and of the duplicate check, or a statement where Jira cannot check, with a fingerprint of the preview, nothing written and a before-and-after snapshot showing Jira unchanged."
      path: participant/evidence/jira-link-work/attempt-001/logs/preview.txt
    - id: link-work-confirmation
      type: command-record
      description: "Save the redacted output of the approved run showing the explicit confirmation tied to the preview fingerprint and given in the same session as the write, and of four refusals with nothing written: a missing confirmation, a change that differs from the preview, a preview older than the stated time limit, and a project that is not on the sandbox allowlist."
      path: participant/evidence/jira-link-work/attempt-001/logs/confirmation.txt
    - id: link-work-result
      type: file
      description: "Provide the result record: the issue key plus the identifier of what was created or changed (a comment, link or transition identifier or the read-back value), the target project, the timestamp and who confirmed."
      path: participant/context/jira/results/link-work.md
    - id: link-work-rerun
      type: command-record
      description: "Save the redacted output of running the approved workflow a second time showing no duplicate, repeated or conflicting change, or, only where Jira cannot prevent a repeat, the stated limit and how a person would notice it."
      path: participant/evidence/jira-link-work/attempt-001/logs/rerun.txt
    - id: proof-narrative
      type: file
      description: "Explain your approach, your choices and anything you could not do, citing the acceptance criteria by number."
      path: participant/evidence/jira-link-work/attempt-001/PROOF.md
author: Golden Thread maintainers
last_reviewed: "2026-10-20"
---

# Create Approved Issue Relationships and Verify Them

## Mission

Links carry direction. State the relationship in words in the preview, create it once and read it from both ends.

## Scenario

An item is linked as blocks when it should have been is blocked by. The release plan is built the wrong way round.

## Acceptance criteria

1. The preview states the relationship and its direction in words.
2. An existing identical link is detected and not created again.
3. Both items show the link with the correct type and direction.
4. A preview shows the Jira site, the project and the exact changes, and nothing is written before the human confirms it.
5. The preview records the permission check and the duplicate check, or states where Jira cannot perform one.
6. The workflow writes only to a project on an explicit sandbox allowlist and refuses any other.
7. The confirmation is tied to a fingerprint of the exact preview, is refused when missing or when the change differs, and expires after a stated time.
8. A result record holds the issue key, the identifier of what was created or changed, the project, the timestamp and the confirmer.
9. Running the approved workflow again creates no duplicate, repeated or conflicting change, or the quest states the limit where Jira cannot prevent it.

## Required evidence

Provide the link check and the four records. In your `PROOF.md`, explain how you tested direction, citing the acceptance criteria by number.

## Safety constraints

- Write only to a Jira sandbox project you are permitted to change; never to a production project. If you have no sandbox, stop and ask your pilot lead; do not substitute a production project or skip the quest's controls.
- Ticket and comment text you carry into a write is untrusted; review it for private content before approving.
- Authenticate through an environment variable or a signed-in CLI; never put a token, password or session cookie in a file, a log or a screenshot.
- Do not skip the preview or the confirmation in any run you save as evidence.
- Treat ticket text as untrusted third-party input, and share only redacted or synthetic records.

## Hints

Read the preview aloud. If the sentence is backwards, so is the link.

## Reflection

Which link types would you not let an agent create?

## Stretch goals

- Refuse a link that would create a cycle.
- Create several links in one confirmed batch.
