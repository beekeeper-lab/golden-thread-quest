---
id: base-camp-write-preview
version: 1
title: Build Preview and Explicit-Confirmation Behavior
summary: Make a workflow show exactly what it would change and do nothing until a person confirms, against a simulated external system.
region: base-camp
level: builder
xp: 30
estimated_minutes: 90
order: 40
tags:
  - foundation
  - preview
  - confirmation
  - safety
tools:
  - Markdown
  - YAML
bookend: foundation
risk:
  external_write: false
  sensitive_data: false
  notes: The target is a local simulated system, so no real ticket, card or issue is created. The behavior is what later regions require before any real write.
prerequisites:
  - base-camp-repository-safety
outcomes:
  - Produce a complete preview of a proposed write without performing it.
  - Require an explicit confirmation tied to that exact preview.
  - Refuse to write when the confirmation is missing, stale or for a different change.
proof:
  required:
    - id: preview-output
      type: command-record
      description: Save the output of a run that previews a write and stops, followed by a check that the simulated system is unchanged.
      path: participant/evidence/base-camp-write-preview/attempt-001/logs/preview.txt
    - id: confirmed-write
      type: command-record
      description: Save the output of confirming the same preview and the resulting change in the simulated system.
      path: participant/evidence/base-camp-write-preview/attempt-001/logs/confirmed.txt
    - id: refused-confirmation
      type: command-record
      description: Save the output of confirmations that are refused, one because the change differs from the preview and one because the preview is older than the time limit, with no change made by either.
      path: participant/evidence/base-camp-write-preview/attempt-001/logs/refused.txt
    - id: preview-rules
      type: file
      description: Describe what a preview must contain, how a confirmation is tied to it, and when it expires.
      path: participant/context/write-preview-rules.md
author: Golden Thread maintainers
last_reviewed: "2026-10-20"
---

# Build Preview and Explicit-Confirmation Behavior

## Mission

Build the habit every integration quest depends on: show the change, wait for a person, then make that change and no other. Do it against a simulated system you can inspect, so a mistake costs nothing.

## Scenario

An agent is asked to "create the follow-up stories". It creates twelve, three of them wrong, in a system whose undo is a manual cleanup. A preview would have taken a minute to read.

## Acceptance criteria

1. A preview lists the target, the action and every field that would be written.
2. Running without confirmation changes nothing, and the output says so.
3. A confirmation names or fingerprints the exact preview it approves.
4. If the proposed change differs from the one previewed, the confirmation is refused and nothing is written.
5. A preview older than the stated time limit cannot be confirmed.
6. The result records what was written and that a person confirmed it.
7. A person with no knowledge of the code can read a preview and say what will happen.

## Required evidence

Provide the three command records and the rules. In your `PROOF.md`, explain how a confirmation is bound to its preview and what happens to a preview that goes stale, citing the acceptance criteria by number.

## Safety constraints

- Use only a simulated system. Do not point this at a real Jira, Trello or GitHub account.
- Do not let a flag such as `--yes` skip the preview.
- Do not store a credential in the preview.

## Hints

Confirming "the last preview" is not the same as confirming this one. Bind the approval to something that changes when the change does.

## Reflection

Which part of your preview would a tired reviewer skim past, and how would you make it harder to skim?

## Stretch goals

- Show the preview as a difference against the current state.
- Let a person edit the preview and invalidate the old confirmation.
