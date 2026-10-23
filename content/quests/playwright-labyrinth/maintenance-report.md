---
id: playwright-maintenance-report
version: 1
title: "Recommend Changes Before Modifying a Failed Test"
summary: "Write the maintenance recommendation for a failing test first, saying what to change and what must not change, before touching the test."
region: playwright-labyrinth
level: builder
xp: 30
estimated_minutes: 90
order: 180
tags:
  - playwright
  - maintenance
  - judgment
tools:
  - Markdown
  - YAML
bookend: validation
risk:
  external_write: false
  sensitive_data: false
  notes: "The failing test is deliberate and local."
prerequisites:
  - playwright-failure-triage
outcomes:
  - "Diagnose the cause of a failing test."
  - "State what to change and what must stay."
  - "Record the recommendation before any edit."
proof:
  required:
    - id: failing-test
      type: file
      description: "Provide a test that fails because the application legitimately changed, and the application change itself, as a separate file or diff beside the spec."
      path: participant/tests/playwright/needs-maintenance.spec.ts
    - id: maintenance-report
      type: file
      description: "Provide the report: cause, evidence, the proposed change, the proposed change listed line by line, the business assertion that must be preserved, what would show the change weakened the test, and whether the failure is a test change or a possible product bug."
      path: participant/context/playwright/maintenance-report.md
    - id: unchanged-check
      type: command-record
      description: "Save the output showing the test file is unchanged when the report is written, using a Git status or checksum taken before and after."
      path: participant/evidence/playwright-maintenance-report/attempt-001/logs/unchanged-check.txt
    - id: check-script
      type: file
      description: "Provide the script that produced the check output, so a reviewer can read what it tests."
      path: participant/tests/playwright/tools/maintenance-report-check.ts
    - id: proof-narrative
      type: file
      description: "Explain your approach, your choices and anything you could not do, citing the acceptance criteria by number."
      path: participant/evidence/playwright-maintenance-report/attempt-001/PROOF.md
author: Golden Thread maintainers
last_reviewed: "2026-10-20"
---

# Recommend Changes Before Modifying a Failed Test

## Mission

Think before editing. Decide what the failure is, what the smallest honest change is and which assertion must survive it, and write that down before the test is touched.

## Scenario

A test fails after a redesign. Someone edits it until it passes, and in doing so deletes the assertion that checked the tax calculation.

## Acceptance criteria

1. The report states the cause of the failure and cites the evidence.
2. The proposed change touches only the lines the evidence shows are affected, and the report lists each line.
3. The business assertion to preserve is named.
4. The report says what would show that the change weakened the test.
5. The test file is unchanged when the report is written.
6. The report distinguishes a test change from a possible product bug.
7. Another person could carry out the change from the report.

## Required evidence

Provide the test, the report and the unchanged check. In your `PROOF.md`, explain how you judged that the change did not weaken the test, citing the acceptance criteria by number.

## Safety constraints

- Test only an application you run yourself, such as a local demo app in your own folder or container that you may change and reset; never a public site, a production system or one holding real customer data.
- Do not put a real login, token or session cookie in a test, a log, a trace or a screenshot.
- Do not edit the failing test until the report is written.

## Hints

Name the assertion that must survive before you decide how to fix the locator.

## Reflection

What change would be tempting here and wrong?

## Stretch goals

- Estimate the effort of each option.
- Link the report to the triage that preceded it.
