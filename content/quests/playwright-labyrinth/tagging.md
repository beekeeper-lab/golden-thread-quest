---
id: playwright-tagging
version: 1
title: "Tag Tests by Feature, Risk, Read/Write, Layer, and Duration"
summary: "Define a tagging scheme and apply it so a run can be selected by what it covers and how risky or slow it is."
region: playwright-labyrinth
level: explorer
xp: 20
estimated_minutes: 60
order: 80
tags:
  - playwright
  - tags
  - organization
tools:
  - Markdown
  - YAML
bookend: validation
risk:
  external_write: false
  sensitive_data: false
  notes: "Tests run against a practice or local application."
prerequisites:
  - playwright-first-independent-test
outcomes:
  - "Define a small, consistent tag vocabulary."
  - "Tag every test with all five dimensions."
  - "Reject tags outside the vocabulary."
proof:
  required:
    - id: tag-scheme
      type: file
      description: "Define the tag vocabulary for feature, risk, read or write, layer and duration, with the meaning of each tag and the time limit of each duration tag, on no more than one page."
      path: participant/context/playwright/tag-scheme.md
    - id: tagged-tests
      type: file
      description: "Provide at least eight tests, each carrying one tag from every dimension."
      path: participant/tests/playwright/tagged.spec.ts
    - id: tag-check
      type: command-record
      description: "Save the redacted output of a check that every test has a tag in each dimension, that no unknown tag is used, and that a test missing a dimension is reported."
      path: participant/evidence/playwright-tagging/attempt-001/logs/tag-check.txt
    - id: check-script
      type: file
      description: "Provide the script that produced the check output, so a reviewer can read what it tests."
      path: participant/tests/playwright/tools/tagging-check.ts
    - id: proof-narrative
      type: file
      description: "Explain your approach, your choices and anything you could not do, citing the acceptance criteria by number."
      path: participant/evidence/playwright-tagging/attempt-001/PROOF.md
author: Golden Thread maintainers
last_reviewed: "2026-10-20"
---

# Tag Tests by Feature, Risk, Read/Write, Layer, and Duration

## Mission

Make tags mean something. A small fixed vocabulary, applied to every test, lets a person run exactly the right set and trust what the set promises.

## Scenario

Someone adds @smoke to forty tests because it sounds important. Smoke now takes twenty minutes and nobody can say what a failure means.

## Acceptance criteria

1. The scheme defines each tag in all five dimensions.
2. Every test carries one tag from each dimension.
3. A tag outside the vocabulary is rejected by a check.
4. A test missing a dimension is reported by name.
5. Write tests are distinguishable from read-only tests by tag.
6. Duration tags have stated limits.
7. The vocabulary fits on one page.

## Required evidence

Provide the scheme, the tests and the check. In your `PROOF.md`, explain how you chose the duration limits and one tag you removed, citing the acceptance criteria by number.

## Safety constraints

- Test only an application you run yourself, such as a local demo app in your own folder or container that you may change and reset; never a public site, a production system or one holding real customer data.
- Do not put a real login, token or session cookie in a test, a log, a trace or a screenshot.
- Tag tests that write data as write, so they are not run against a shared environment by accident.

## Hints

A tag that nobody could be wrong about is better than a clever one.

## Reflection

Which dimension was hardest to keep consistent across testers?

## Stretch goals

- Generate the scheme document from the check.
- Add a tag for the requirement a test covers.
