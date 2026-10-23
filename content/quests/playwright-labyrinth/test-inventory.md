---
id: playwright-test-inventory
version: 1
title: "Document Every Test, Its Purpose, Tags, Source, and Value Score"
summary: "Build a generated inventory of the suite so each test has a stated purpose, a requirement it serves and a value score, and orphans are visible."
region: playwright-labyrinth
level: navigator
xp: 50
estimated_minutes: 120
order: 140
tags:
  - playwright
  - inventory
  - traceability
tools:
  - Markdown
  - YAML
bookend: validation
risk:
  external_write: false
  sensitive_data: false
  notes: "The inventory is generated from the test files and is reproducible."
prerequisites:
  - playwright-tagging
outcomes:
  - "Generate an inventory from the tests rather than maintaining it by hand."
  - "Record purpose, tags, source requirement and value for each test."
  - "Report tests with no purpose or no source."
proof:
  required:
    - id: inventory-generator
      type: file
      description: "Provide the generator that reads the test files and writes the inventory."
      path: participant/tests/playwright/tools/inventory.ts
    - id: inventory
      type: file
      description: "Provide the generated inventory with one row per test: identifier, purpose, tags, source requirement, a value score on a stated three-level scale (high, medium, low) and file location."
      path: participant/context/playwright/inventory.md
    - id: inventory-run
      type: command-record
      description: "Save the redacted output of generating the inventory twice with identical results, of a test added without a purpose or without a source requirement being reported as incomplete, of two tests sharing an identifier being rejected, and of two tests with the same purpose being reported as possible duplicates."
      path: participant/evidence/playwright-test-inventory/attempt-001/logs/inventory-run.txt
    - id: proof-narrative
      type: file
      description: "Explain your approach, your choices and anything you could not do, citing the acceptance criteria by number."
      path: participant/evidence/playwright-test-inventory/attempt-001/PROOF.md
author: Golden Thread maintainers
last_reviewed: "2026-10-20"
---

# Document Every Test, Its Purpose, Tags, Source, and Value Score

## Mission

Make the suite a known quantity. The inventory is generated, never hand-edited, and it names the purpose and source of every test so gaps and duplicates show up.

## Scenario

A suite of 400 tests has no list. Nobody knows which cover the payment rules, and three tests turn out to check exactly the same thing.

## Acceptance criteria

1. The inventory is generated from the test files.
2. Each test has a unique identifier, purpose, tags, source requirement and value score.
3. A test missing a purpose or a source is reported as incomplete.
4. Two tests with the same purpose are reported as possible duplicates.
5. The inventory is identical across two runs on the same tests.
6. Adding a test changes the inventory without any hand edit.
7. A new teammate can find the tests for a requirement from the inventory.

## Required evidence

Provide the generator, the inventory and the run record. In your `PROOF.md`, explain where purpose and source are written and one duplicate you found, citing the acceptance criteria by number.

## Safety constraints

- Test only an application you run yourself, such as a local demo app in your own folder or container that you may change and reset; never a public site, a production system or one holding real customer data.
- Do not put a real login, token or session cookie in a test, a log, a trace or a screenshot.
- The generator reads test files only and does not run them or change them.

## Hints

Put the purpose next to the test, where it is changed together with it.

## Reflection

What stops the purposes from becoming boilerplate?

## Stretch goals

- Show the inventory sorted by value and by age.
- Report tests whose source requirement no longer exists.
