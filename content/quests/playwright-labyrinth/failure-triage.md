---
id: playwright-failure-triage
version: 1
title: "Classify Failures as Bug, Test Defect, Environment, Data, or Inconclusive"
summary: "Classify failing tests from their evidence into five classes with a stated reason for each, and say inconclusive when the evidence cannot tell."
region: playwright-labyrinth
level: navigator
xp: 50
estimated_minutes: 120
order: 170
tags:
  - playwright
  - triage
  - diagnosis
tools:
  - Markdown
  - YAML
bookend: validation
risk:
  external_write: false
  sensitive_data: false
  notes: "Failures are produced deliberately against a practice application you control."
prerequisites:
  - playwright-failure-evidence
outcomes:
  - "Reproduce failures of each class."
  - "Classify each from its evidence."
  - "Use inconclusive honestly."
proof:
  required:
    - id: ground-truth
      type: file
      description: "Write down, before classifying, the real cause you injected for each failure, kept apart from the triage report."
      path: participant/context/playwright/ground-truth.md
    - id: failure-set
      type: directory
      description: "Provide evidence bundles for at least six failures: at least one each of a product bug, a test defect, an environment problem and a data problem, one that the evidence cannot settle, and one product bug that passes on retry."
      path: participant/evidence/playwright-failure-triage/attempt-001/failures/
    - id: triage-rules
      type: file
      description: "State the signs that point to each class and what the evidence must show before you classify."
      path: participant/context/playwright/triage-rules.md
    - id: triage-report
      type: file
      description: "Provide the classification of each failure with the class, the evidence cited, the next action and who takes it, and for an inconclusive failure what would settle it."
      path: participant/context/playwright/triage-report.md
    - id: triage-check
      type: command-record
      description: "Save the redacted output of a check that every classification cites a file in its bundle and that no failure is classified without a cited file."
      path: participant/evidence/playwright-failure-triage/attempt-001/logs/triage-check.txt
    - id: check-script
      type: file
      description: "Provide the script that produced the check output, so a reviewer can read what it tests."
      path: participant/tests/playwright/tools/failure-triage-check.ts
    - id: proof-narrative
      type: file
      description: "Explain your approach, your choices and anything you could not do, citing the acceptance criteria by number."
      path: participant/evidence/playwright-failure-triage/attempt-001/PROOF.md
author: Golden Thread maintainers
last_reviewed: "2026-10-20"
---

# Classify Failures as Bug, Test Defect, Environment, Data, or Inconclusive

## Mission

Decide what each failure is from what the evidence shows. A classification you cannot support is inconclusive, and saying so is a result.

## Scenario

Every red test is called flaky and retried. Three real bugs shipped because their failures looked like the usual noise.

## Acceptance criteria

1. Each failure is assigned exactly one of the five classes.
2. Each classification cites a file in its evidence bundle.
3. A product bug is not classified as flaky because it passed on retry.
4. Inconclusive is used where the evidence cannot settle it, with what would settle it.
5. Each classification states the next action and who takes it.
6. The rules say what evidence is needed for each class.
7. A reviewer can reach the same class for each failure from the bundle.

## Required evidence

Provide the bundles, the rules, the report and the check. In your `PROOF.md`, explain one failure you first classified wrongly, citing the acceptance criteria by number.

## Safety constraints

- Test only an application you run yourself, such as a local demo app in your own folder or container that you may change and reset; never a public site, a production system or one holding real customer data.
- Do not put a real login, token or session cookie in a test, a log, a trace or a screenshot.
- Cause failures only in an application you control.

## Hints

Passing on retry is a symptom to explain, not a reason to close it.

## Reflection

How would you notice that your triage was biased toward test defect?

## Stretch goals

- Measure how often a classification changes after more evidence.
- Track class counts across several runs.
