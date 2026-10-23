---
id: playwright-coverage-report
version: 1
title: "Map Requirements to Covered, Partial, Uncovered, and Manual Validation"
summary: "Report, for each requirement, whether it is covered by automation, only partly, not at all or validated manually, with the evidence for each."
region: playwright-labyrinth
level: navigator
xp: 50
estimated_minutes: 120
order: 160
tags:
  - playwright
  - coverage
  - traceability
tools:
  - Markdown
  - YAML
bookend: cross-bookend
risk:
  external_write: false
  sensitive_data: false
  notes: "The mapping is generated from your inventory and requirements."
prerequisites:
  - playwright-test-inventory
  - playwright-risk-strategy
outcomes:
  - "Map requirements to tests by identifier."
  - "Classify coverage as covered, partial, uncovered or manual."
  - "Explain why a requirement is partial."
proof:
  required:
    - id: coverage-generator
      type: file
      description: "Provide the script that generates the report from the data."
      path: participant/tests/playwright/tools/coverage.ts
    - id: coverage-data
      type: file
      description: "Provide the requirements, the latest test results (pass or fail per test) and the manual validation records the report draws on."
      path: participant/context/playwright/coverage-data.md
    - id: coverage-report
      type: file
      description: "Provide the report: one row per requirement with its coverage class, the covering tests, the reason for any partial or uncovered class and, for a manual class, the link to its manual record."
      path: participant/context/playwright/coverage-report.md
    - id: coverage-run
      type: command-record
      description: "Save the redacted output of generating the report twice with identical results, and of a requirement with a failing test being reported as not covered."
      path: participant/evidence/playwright-coverage-report/attempt-001/logs/coverage-run.txt
    - id: proof-narrative
      type: file
      description: "Explain your approach, your choices and anything you could not do, citing the acceptance criteria by number."
      path: participant/evidence/playwright-coverage-report/attempt-001/PROOF.md
author: Golden Thread maintainers
last_reviewed: "2026-10-20"
---

# Map Requirements to Covered, Partial, Uncovered, and Manual Validation

## Mission

Report coverage of requirements, not of lines or pages. Say which are covered, which partly and why, which not at all, and which a person validates, so no gap hides behind a percentage.

## Scenario

Coverage is reported as 85 percent, counting every test that touches the login page. The refund rule has no test at all, and nobody notices.

## Acceptance criteria

1. Each requirement has exactly one coverage class.
2. Covered means at least one passing test mapped by identifier to the requirement.
3. A partial class states which part is not tested.
4. An uncovered requirement is listed, not omitted.
5. A manual class links to the record of the manual check.
6. A requirement whose covering test fails is not reported as covered.
7. The report is identical across two runs on the same data.

## Required evidence

Provide the data, the report and the run record. In your `PROOF.md`, explain how you decided a requirement was partial and one you refused to call covered, citing the acceptance criteria by number.

## Safety constraints

- Test only an application you run yourself, such as a local demo app in your own folder or container that you may change and reset; never a public site, a production system or one holding real customer data.
- Do not put a real login, token or session cookie in a test, a log, a trace or a screenshot.
- Do not claim coverage that rests on a test you have not run.

## Hints

Map by identifier. Matching test names to requirement words invents coverage.

## Reflection

What would you tell a stakeholder who asks for a single coverage number?

## Stretch goals

- Weight the report by the risk ranking.
- Show coverage over the last five runs.
