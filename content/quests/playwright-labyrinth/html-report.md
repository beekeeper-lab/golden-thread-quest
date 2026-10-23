---
id: playwright-html-report
version: 1
title: "Produce a Useful Execution Report"
summary: "Generate a report that a stakeholder and a developer can each use, linking results to evidence and tags and showing what was and was not run."
region: playwright-labyrinth
level: builder
xp: 30
estimated_minutes: 90
order: 130
tags:
  - playwright
  - reporting
  - communication
tools:
  - Markdown
  - YAML
bookend: validation
risk:
  external_write: false
  sensitive_data: true
  notes: "The report is generated and disposable; the generating configuration is what is handed in."
prerequisites:
  - playwright-failure-evidence
  - playwright-success-evidence
outcomes:
  - "Generate a report from a run."
  - "Link each result to its evidence and tags."
  - "State clearly what did not run."
proof:
  required:
    - id: report-config
      type: file
      description: "Provide the configuration that generates the report, including tags, evidence links and run metadata."
      path: participant/tests/playwright/report.config.ts
    - id: report-sample
      type: file
      description: "Provide one generated report, redacted, as a single self-contained file, with a scan showing it holds no credential or personal data."
      path: participant/evidence/playwright-html-report/attempt-001/report/index.html
    - id: report-check
      type: command-record
      description: "Save the redacted output of a check that the report lists passed, failed, skipped and not-run tests, links each failure to its evidence, shows the tag selection used and states the environment and commit."
      path: participant/evidence/playwright-html-report/attempt-001/logs/report-check.txt
    - id: reader-note
      type: file
      description: "Write a short note for each reader (stakeholder and developer) saying what they should look at first in the report and why."
      path: participant/context/playwright/report-readers.md
    - id: check-script
      type: file
      description: "Provide the script that produced the check output, so a reviewer can read what it tests."
      path: participant/tests/playwright/tools/html-report-check.ts
    - id: proof-narrative
      type: file
      description: "Explain your approach, your choices and anything you could not do, citing the acceptance criteria by number."
      path: participant/evidence/playwright-html-report/attempt-001/PROOF.md
author: Golden Thread maintainers
last_reviewed: "2026-10-20"
---

# Produce a Useful Execution Report

## Mission

Build a report that tells the truth about a run: what passed, what failed with evidence, and what was never run. Different readers need different starting points.

## Scenario

A green report is sent to the product owner. It does not say that half the suite was excluded by a tag, and the release goes out untested in that area.

## Acceptance criteria

1. The report counts passed, failed, skipped and not-run tests separately.
2. Each failure links to its evidence.
3. The report shows which tag selection was used.
4. The report states the environment and the commit under test.
5. A skipped or excluded test is listed, not hidden.
6. The report contains no credential or personal data.
7. The reader note says where each reader should start.

## Required evidence

Provide the configuration, the sample, the check and the note. In your `PROOF.md`, explain what the report says about an excluded test and why, citing the acceptance criteria by number.

## Safety constraints

- Test only an application you run yourself, such as a local demo app in your own folder or container that you may change and reset; never a public site, a production system or one holding real customer data.
- Do not put a real login, token or session cookie in a test, a log, a trace or a screenshot.
- Do not commit the generated report folder; hand in the single redacted sample file only.

## Hints

A report that cannot show what was left out is advertising.

## Reflection

What could a reader wrongly conclude from your report?

## Stretch goals

- Compare this run with the previous one.
- Add a one-line verdict that cannot say pass if anything is not-run.
