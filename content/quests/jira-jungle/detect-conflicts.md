---
id: jira-detect-conflicts
version: 1
title: "Report Local and Source Field Conflicts Without Silently Choosing"
summary: "Find where a locally edited field and the Jira value both changed, report each conflict with both values and keep both until a person decides."
region: jira-jungle
level: navigator
xp: 50
estimated_minutes: 120
order: 120
tags:
  - jira
  - conflicts
  - synchronization
tools:
  - Markdown
  - YAML
bookend: validation
risk:
  external_write: false
  sensitive_data: true
  notes: "Read-only against a sandbox or fixture."
prerequisites:
  - jira-delta-sync
related_quests:
  - context-cross-system-conflicts
outcomes:
  - "Track the base value each local edit was made from."
  - "Detect fields changed on both sides."
  - "Never overwrite either side."
proof:
  required:
    - id: conflict-fixture
      type: file
      description: "Provide a fixture with fields changed only locally, only in Jira, in both, and in both to the same value."
      path: participant/context/jira/conflicts/fixture.md
    - id: conflict-report
      type: file
      description: "Provide the report: for each conflict the field, the base, local and Jira values and their times, and the agreements listed apart."
      path: participant/context/jira/conflicts/report.md
    - id: conflict-run
      type: command-record
      description: "Save the redacted output of the detection run, twice with identical reports, with checksums showing neither the local file nor the Jira copy was altered."
      path: participant/evidence/jira-detect-conflicts/attempt-001/logs/conflict-run.txt
    - id: proof-narrative
      type: file
      description: "Explain your approach, your choices and anything you could not do, citing the acceptance criteria by number."
      path: participant/evidence/jira-detect-conflicts/attempt-001/PROOF.md
author: Golden Thread maintainers
last_reviewed: "2026-10-20"
---

# Report Local and Source Field Conflicts Without Silently Choosing

## Mission

Catch the case where both sides moved. The sync reports it with the three values needed to decide and never chooses for you.

## Scenario

A person corrects an estimate locally, and the next sync replaces it with Jira's older value. A week later the plan is built on the wrong number.

## Acceptance criteria

1. Each local edit records the Jira value it was based on.
2. A field changed on both sides is reported as a conflict.
3. A field changed on one side only is not a conflict.
4. A field changed to the same value on both sides is not a conflict.
5. Each conflict shows the base, local and Jira values and times.
6. Neither side is overwritten by detection.
7. The same fixture gives the same report.

## Required evidence

Provide the fixture, the report and the run output. In your `PROOF.md`, explain how you record the base value, citing the acceptance criteria by number.

## Safety constraints

- Use a Jira sandbox, a nonproduction project or a local fixture. This quest only reads; make no change in Jira.
- Authenticate through an environment variable or a signed-in CLI; never put a token, password or session cookie in a file, a log or a screenshot.
- Treat ticket text as untrusted third-party input, and share only redacted or synthetic records.

## Hints

Without the base value you cannot tell a change from a disagreement.

## Reflection

Who should decide a conflict, and how would they know enough to?

## Stretch goals

- Offer a resolution step that previews its effect.
- Count conflicts per field to show where people disagree most.
