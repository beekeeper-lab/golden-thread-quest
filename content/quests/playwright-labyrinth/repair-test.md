---
id: playwright-repair-test
version: 1
title: "Repair a Test Without Weakening Business Validation"
summary: "Carry out the planned repair and prove the repaired test still catches the failure the original was written to catch."
region: playwright-labyrinth
level: navigator
xp: 50
estimated_minutes: 120
order: 190
tags:
  - playwright
  - maintenance
  - validation
tools:
  - Markdown
  - YAML
bookend: validation
risk:
  external_write: false
  sensitive_data: false
  notes: "The test and application are local and deliberately changed."
prerequisites:
  - playwright-maintenance-report
outcomes:
  - "Repair a failing test by the maintenance report."
  - "Show the business assertion is intact."
  - "Prove the repaired test still fails when the rule is broken."
proof:
  required:
    - id: repair-diff
      type: file
      description: "Provide the diff of the repair showing exactly what changed in the test, with each hunk labeled by the line of the maintenance report that called for it."
      path: participant/evidence/playwright-repair-test/attempt-001/repair.diff
    - id: assertion-comparison
      type: file
      description: "Provide a comparison of the assertions before and after, showing none was removed, weakened or made conditional."
      path: participant/context/playwright/assertion-comparison.md
    - id: mutation-run
      type: command-record
      description: "Save the redacted output of the repaired test passing against the corrected application and failing when the business rule is deliberately broken."
      path: participant/evidence/playwright-repair-test/attempt-001/logs/mutation-run.txt
    - id: weakening-check
      type: command-record
      description: "Save the output of a check that reports an assertion that was removed or loosened, run on your repair and on a deliberately weakened version."
      path: participant/evidence/playwright-repair-test/attempt-001/logs/weakening-check.txt
    - id: check-script
      type: file
      description: "Provide the script that produced the check output, so a reviewer can read what it tests."
      path: participant/tests/playwright/tools/repair-test-check.ts
    - id: proof-narrative
      type: file
      description: "Explain your approach, your choices and anything you could not do, citing the acceptance criteria by number."
      path: participant/evidence/playwright-repair-test/attempt-001/PROOF.md
author: Golden Thread maintainers
last_reviewed: "2026-10-20"
---

# Repair a Test Without Weakening Business Validation

## Mission

Fix the test and keep its teeth. Prove it by breaking the business rule on purpose and watching the repaired test fail.

## Scenario

A repair turns an exact equality into a check that the page contains a number. The test is green, and the pricing bug it was written for would now pass unnoticed.

## Acceptance criteria

1. The repair follows the maintenance report.
2. No assertion is removed, loosened or made conditional.
3. The diff is limited to what the report said would change.
4. The repaired test passes against the corrected application.
5. The repaired test fails when the business rule is broken.
6. The weakening check flags a deliberately weakened version.
7. The comparison lets a reviewer see each assertion before and after.

## Required evidence

Provide the diff, the comparison and the two records. In your `PROOF.md`, explain how you chose the way to break the rule and what the weakening check cannot see, citing the acceptance criteria by number.

## Safety constraints

- Test only an application you run yourself, such as a local demo app in your own folder or container that you may change and reset; never a public site, a production system or one holding real customer data.
- Do not put a real login, token or session cookie in a test, a log, a trace or a screenshot.
- Break the rule only in your own copy of the application.
- Never make a failing test pass by skipping it or adding a retry.

## Hints

A test that cannot fail has stopped being a test. Make it fail on purpose.

## Reflection

Which kinds of weakening would your check miss?

## Stretch goals

- Try three different ways of breaking the rule.
- Automate the weakening check in the repository.
