---
id: playwright-failure-evidence
version: 1
title: "Capture Trace, Screenshot, Log, Request, and Error Context on Failure"
summary: "Configure a test so that every failure leaves enough evidence for someone else to diagnose it without rerunning it."
region: playwright-labyrinth
level: builder
xp: 30
estimated_minutes: 90
order: 110
tags:
  - playwright
  - evidence
  - debugging
tools:
  - Markdown
  - YAML
bookend: validation
risk:
  external_write: false
  sensitive_data: true
  notes: "Evidence must be checked for secrets before it is shared."
prerequisites:
  - playwright-first-independent-test
outcomes:
  - "Capture a trace, screenshot, console log, network failures and error text on failure."
  - "Keep evidence from passing runs out of the way."
  - "Strip secrets before evidence is saved."
proof:
  required:
    - id: evidence-config
      type: file
      description: "Provide the configuration that captures evidence on failure, keeps little or none for a passing test, and states what is kept and for how long, with the output of a passing run showing what it kept."
      path: participant/tests/playwright/evidence.config.ts
    - id: failure-bundle
      type: directory
      description: "Provide the evidence folder from one deliberately failing test containing a trace, a screenshot, the console log, failed requests and the error message."
      path: participant/evidence/playwright-failure-evidence/attempt-001/failure-bundle/
    - id: redaction-check
      type: command-record
      description: "Save the output of a scan of the bundle for tokens, cookies and credentials, showing none, and of a deliberately planted fake value being found, reporting only the file and line and never the value itself."
      path: participant/evidence/playwright-failure-evidence/attempt-001/logs/redaction-check.txt
    - id: diagnosis-note
      type: file
      description: "Write a diagnosis of the failure using only the bundle, with each claim pointing to the file that supports it."
      path: participant/context/playwright/diagnosis.md
    - id: check-script
      type: file
      description: "Provide the script that produced the check output, so a reviewer can read what it tests."
      path: participant/tests/playwright/tools/failure-evidence-check.ts
    - id: proof-narrative
      type: file
      description: "Explain your approach, your choices and anything you could not do, citing the acceptance criteria by number."
      path: participant/evidence/playwright-failure-evidence/attempt-001/PROOF.md
author: Golden Thread maintainers
last_reviewed: "2026-10-20"
---

# Capture Trace, Screenshot, Log, Request, and Error Context on Failure

## Mission

Make the failure explain itself. Collect the evidence a stranger would need, keep secrets out of it, and prove it was enough by diagnosing from the bundle alone.

## Scenario

A test fails once in the pipeline and passes on retry. The log says only timeout, and nobody can tell whether the page, the network or the data was at fault.

## Acceptance criteria

1. A failing test produces a trace, a screenshot, the console log, failed requests and the error text.
2. A passing test does not keep heavy evidence by default.
3. The bundle contains no token, cookie or credential, shown by a scan.
4. The scan finds a planted fake value.
5. The diagnosis cites a bundle file for each claim.
6. The configuration states how long evidence is kept.
7. Another person can diagnose the failure without rerunning the test.

## Required evidence

Provide the configuration, the bundle, the scan and the diagnosis. In your `PROOF.md`, say what the bundle did not contain that you wished it had, citing the acceptance criteria by number.

## Safety constraints

- Test only an application you run yourself, such as a local demo app in your own folder or container that you may change and reset; never a public site, a production system or one holding real customer data.
- Do not put a real login, token or session cookie in a test, a log, a trace or a screenshot.
- Check every screenshot and trace for visible personal data before handing it in.

## Hints

Test your evidence by trying to diagnose from it alone. If you need to rerun, it was not enough.

## Reflection

What is the most useful thing your bundle leaves out?

## Stretch goals

- Add the application's server log for the same time window.
- Link each bundle to the commit under test.
