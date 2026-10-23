---
id: playwright-defect-ticket
version: 1
title: "Create a Traceable, Deduplicated Defect After Approval"
summary: "Turn a triaged product bug into a defect report that links its evidence, checks for an existing report and is written to a simulated tracker only after a person approves a preview."
region: playwright-labyrinth
level: navigator
xp: 50
estimated_minutes: 120
order: 200
tags:
  - playwright
  - defects
  - preview
tools:
  - Markdown
  - YAML
bookend: cross-bookend
risk:
  external_write: false
  sensitive_data: false
  notes: "The tracker is simulated and local. The workflow previews the write and requires explicit confirmation, as real integrations will."
prerequisites:
  - playwright-failure-triage
  - base-camp-write-preview
outcomes:
  - "Write a defect another person can reproduce."
  - "Search for an existing report first."
  - "Write only after approving a preview."
proof:
  required:
    - id: defect-draft
      type: file
      description: "Provide the defect draft: summary, steps, expected and actual, environment, the test and commit, and links to the evidence bundle, with the output of a scan of the draft finding no credential or personal data."
      path: participant/context/playwright/defect-draft.md
    - id: duplicate-search
      type: command-record
      description: "Save the redacted output of the search of the simulated tracker, once finding an existing report that is linked instead of recreated and once finding none."
      path: participant/evidence/playwright-defect-ticket/attempt-001/logs/duplicate-search.txt
    - id: preview-run
      type: command-record
      description: "Save the redacted output of the workflow stopping at the preview with nothing written, and of an approval that does not match the preview being refused."
      path: participant/evidence/playwright-defect-ticket/attempt-001/logs/preview.txt
    - id: approved-run
      type: command-record
      description: "Save the redacted output of the approved write to the simulated tracker and of a second run creating no duplicate."
      path: participant/evidence/playwright-defect-ticket/attempt-001/logs/approved-run.txt
    - id: proof-narrative
      type: file
      description: "Explain your approach, your choices and anything you could not do, citing the acceptance criteria by number."
      path: participant/evidence/playwright-defect-ticket/attempt-001/PROOF.md
author: Golden Thread maintainers
last_reviewed: "2026-10-20"
---

# Create a Traceable, Deduplicated Defect After Approval

## Mission

Write the report you would want to receive, check that it is not already filed, and let a person see exactly what will be created before it is.

## Scenario

A failure creates three tickets from three reruns. Each says test failed, none links evidence, and the one that was triaged is the only one nobody opened.

## Acceptance criteria

1. The draft has enough steps and evidence for another tester to reproduce the defect.
2. The draft links the evidence bundle and names the test and commit.
3. An existing report is searched for before writing.
4. An existing report is linked, not recreated.
5. Nothing is written before a person approves the preview.
6. Running the approved workflow again creates no duplicate.
7. No credential or personal data appears in the draft.

## Required evidence

Provide the draft and the three records. In your `PROOF.md`, walk through what a developer would do with your draft and what you could not state, citing the acceptance criteria by number.

## Safety constraints

- The tracker is simulated; make no write to a real tracker.
- Do not put a real login, token or session cookie in a test, a log, a trace or a screenshot.
- Do not skip the approval step in any run you save as evidence.

## Hints

A good defect is one a stranger can reproduce on a bad day.

## Reflection

What detail would a developer ask you for first?

## Stretch goals

- Add severity and priority with stated rules.
- Link the defect back to the requirement it violates.
