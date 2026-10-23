---
id: playwright-success-evidence
version: 1
title: "Capture Evidence at Meaningful Validation Points"
summary: "Record evidence at the moment a business rule is verified, not at every step, so a passing run shows what was actually checked."
region: playwright-labyrinth
level: explorer
xp: 20
estimated_minutes: 60
order: 120
tags:
  - playwright
  - evidence
  - assertions
tools:
  - Markdown
  - YAML
bookend: validation
risk:
  external_write: false
  sensitive_data: true
  notes: "Evidence must be checked for secrets and personal data."
prerequisites:
  - playwright-first-independent-test
outcomes:
  - "Identify the assertion that proves the business rule."
  - "Capture state at that point only."
  - "Show the evidence would differ if the rule failed."
proof:
  required:
    - id: annotated-test
      type: file
      description: "Provide a test with comments marking which assertions prove a business rule and which are only navigation."
      path: participant/tests/playwright/meaningful-evidence.spec.ts
    - id: success-evidence-files
      type: directory
      description: "Provide the evidence captured at the validation points of a passing run, one item per business rule, each showing the value the assertion checked, and the output of the run listing what was and was not captured."
      path: participant/evidence/playwright-success-evidence/attempt-001/validated/
    - id: contrast-run
      type: command-record
      description: "Save the redacted output of the same test with the rule deliberately broken, showing the evidence at the validation point changing or the assertion failing, and of a scan of the validated folder finding no credential or personal data."
      path: participant/evidence/playwright-success-evidence/attempt-001/logs/contrast-run.txt
    - id: proof-narrative
      type: file
      description: "Explain your approach, your choices and anything you could not do, citing the acceptance criteria by number."
      path: participant/evidence/playwright-success-evidence/attempt-001/PROOF.md
author: Golden Thread maintainers
last_reviewed: "2026-10-20"
---

# Capture Evidence at Meaningful Validation Points

## Mission

Capture what matters. Evidence of success should show the business rule holding, so a reader can see the outcome without trusting the word pass.

## Scenario

A passing run saves forty screenshots of pages loading. When asked what the test proved, nobody can point to one that shows the discount was applied.

## Acceptance criteria

1. Each business rule has one captured piece of evidence at its validation point.
2. Navigation steps do not produce evidence by default.
3. The test marks which assertions prove a business rule.
4. Evidence shows the specific value or state the rule is about.
5. Breaking the rule changes the evidence or fails the assertion.
6. No evidence contains personal data or a credential.
7. A reader can tell what was verified from the evidence alone.

## Required evidence

Provide the annotated test, the evidence and the contrast record. In your `PROOF.md`, explain which assertion you considered proof and which only navigation, citing the acceptance criteria by number.

## Safety constraints

- Test only an application you run yourself, such as a local demo app in your own folder or container that you may change and reset; never a public site, a production system or one holding real customer data.
- Do not put a real login, token or session cookie in a test, a log, a trace or a screenshot.
- Blur or avoid personal data in screenshots.

## Hints

Ask what a skeptical reviewer would need to see to believe the rule held.

## Reflection

Which of your captures would still look the same if the rule were broken?

## Stretch goals

- Attach the evidence to the report automatically.
- Record the exact value asserted next to each capture.
