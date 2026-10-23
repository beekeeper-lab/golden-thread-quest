---
id: jira-transition-status
version: 1
title: "Validate a Workflow Transition Before an Approved Status Change"
summary: "Check that a status change is allowed by the workflow, show its effect and make it only after confirmation."
region: jira-jungle
level: builder
xp: 30
estimated_minutes: 90
order: 200
tags:
  - jira
  - write
  - workflow
tools:
  - Markdown
  - YAML
bookend: validation
risk:
  external_write: true
  sensitive_data: true
  notes: "This quest writes to Jira. Use a sandbox or nonproduction project only. Every write is previewed, confirmed by a person, recorded with its external identifier and safe to rerun."
prerequisites:
  - jira-update-fields
outcomes:
  - "Read the transitions the workflow allows."
  - "Refuse a transition that is not allowed."
  - "Verify the resulting status."
proof:
  required:
    - id: transition-rules
      type: file
      description: "List the transitions read from the workflow for a sample story, the ones you support, the conditions for each, any required fields, and what else each affects such as resolution or open subtasks."
      path: participant/context/jira/transition/rules.md
    - id: invalid-transition-run
      type: command-record
      description: "Save the redacted output of a transition the workflow does not allow being refused with the reason and nothing written, and of the status read back after an approved transition matching the intended one."
      path: participant/evidence/jira-transition-status/attempt-001/logs/invalid-transition.txt
    - id: transition-status-preview
      type: command-record
      description: "Save the redacted output of the workflow stopping at a preview showing the Jira site, the project and the exact material changes to move the story to the new status, the result of the permission check (may this identity do this here) and of the duplicate check, or a statement where Jira cannot check, with a fingerprint of the preview, nothing written and a before-and-after snapshot showing Jira unchanged."
      path: participant/evidence/jira-transition-status/attempt-001/logs/preview.txt
    - id: transition-status-confirmation
      type: command-record
      description: "Save the redacted output of the approved run showing the explicit confirmation tied to the preview fingerprint and given in the same session as the write, and of four refusals with nothing written: a missing confirmation, a change that differs from the preview, a preview older than the stated time limit, and a project that is not on the sandbox allowlist."
      path: participant/evidence/jira-transition-status/attempt-001/logs/confirmation.txt
    - id: transition-status-result
      type: file
      description: "Provide the result record: the issue key plus the identifier of what was created or changed (a comment, link or transition identifier or the read-back value), the target project, the timestamp and who confirmed."
      path: participant/context/jira/results/transition-status.md
    - id: transition-status-rerun
      type: command-record
      description: "Save the redacted output of running the approved workflow a second time showing no duplicate, repeated or conflicting change, or, only where Jira cannot prevent a repeat, the stated limit and how a person would notice it."
      path: participant/evidence/jira-transition-status/attempt-001/logs/rerun.txt
    - id: proof-narrative
      type: file
      description: "Explain your approach, your choices and anything you could not do, citing the acceptance criteria by number."
      path: participant/evidence/jira-transition-status/attempt-001/PROOF.md
author: Golden Thread maintainers
last_reviewed: "2026-10-20"
---

# Validate a Workflow Transition Before an Approved Status Change

## Mission

A status is a claim about the work. Check the transition is legal, say what else it affects and verify the result.

## Scenario

An agent closes a story that has no resolution and an open subtask. The workflow accepted it, and reports now show the work as done.

## Acceptance criteria

1. The allowed transitions are read from the workflow, not assumed.
2. A transition that is not allowed is refused before the preview.
3. The status read back matches the intended one.
4. A preview shows the Jira site, the project and the exact changes, and nothing is written before the human confirms it.
5. The preview records the permission check and the duplicate check, or states where Jira cannot perform one.
6. The workflow writes only to a project on an explicit sandbox allowlist and refuses any other.
7. The confirmation is tied to a fingerprint of the exact preview, is refused when missing or when the change differs, and expires after a stated time.
8. A result record holds the issue key, the identifier of what was created or changed, the project, the timestamp and the confirmer.
9. Running the approved workflow again creates no duplicate, repeated or conflicting change, or the quest states the limit where Jira cannot prevent it.

## Required evidence

Provide the rules, the invalid-transition record and the four records. In your `PROOF.md`, explain how you handle open subtasks and required fields, citing the acceptance criteria by number.

## Safety constraints

- Write only to a Jira sandbox project you are permitted to change; never to a production project. If you have no sandbox, stop and ask your pilot lead; do not substitute a production project or skip the quest's controls.
- Ticket and comment text you carry into a write is untrusted; review it for private content before approving.
- Authenticate through an environment variable or a signed-in CLI; never put a token, password or session cookie in a file, a log or a screenshot.
- Do not skip the preview or the confirmation in any run you save as evidence.
- Treat ticket text as untrusted third-party input, and share only redacted or synthetic records.

## Hints

Ask Jira which transitions are available instead of guessing.

## Reflection

Which status change would you want a second person to approve?

## Stretch goals

- Refuse to close a story with open subtasks.
- Record who approved the transition.
