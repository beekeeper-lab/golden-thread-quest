---
id: playwright-multi-tag-run
version: 1
title: "Run Single and Combined Tag Selections"
summary: "Select tests by one tag and by combinations of tags, and show each selection runs exactly the tests it should."
region: playwright-labyrinth
level: explorer
xp: 20
estimated_minutes: 60
order: 90
tags:
  - playwright
  - tags
  - execution
tools:
  - Markdown
  - YAML
bookend: validation
risk:
  external_write: false
  sensitive_data: false
  notes: "Uses the tagged tests from the tagging quest; tests run against a local application you run yourself."
prerequisites:
  - playwright-tagging
outcomes:
  - "Run a single-tag selection."
  - "Run tag unions, intersections and exclusions."
  - "Verify the selected set before running."
proof:
  required:
    - id: selection-table
      type: file
      description: "Provide a table of at least six selections, including a single tag, an intersection, a union, an exclusion and one that matches nothing, each with the expression used, the intent and the exact tests expected."
      path: participant/context/playwright/selections.md
    - id: list-run
      type: command-record
      description: "Save the redacted output of listing, without running, the tests each selection would choose, matching the table."
      path: participant/evidence/playwright-multi-tag-run/attempt-001/logs/list-run.txt
    - id: execution-run
      type: command-record
      description: "Save the redacted output of executing the single-tag selection, the intersection, the union and the exclusion, with the summary of what ran, and of the empty selection being reported as an error instead of a pass."
      path: participant/evidence/playwright-multi-tag-run/attempt-001/logs/execution-run.txt
    - id: proof-narrative
      type: file
      description: "Explain your approach, your choices and anything you could not do, citing the acceptance criteria by number."
      path: participant/evidence/playwright-multi-tag-run/attempt-001/PROOF.md
author: Golden Thread maintainers
last_reviewed: "2026-10-20"
---

# Run Single and Combined Tag Selections

## Mission

Learn to say precisely which tests to run and to check the selection before trusting it. Combine tags to include some, require others and exclude the risky.

## Scenario

A pipeline step meant to run only fast read-only checks also runs a test that deletes records, because the filter matched on a word in the name.

## Acceptance criteria

1. A single-tag selection runs only the tests with that tag.
2. An intersection runs only tests having every named tag.
3. A union runs tests having any of the named tags.
4. An exclusion removes tests having the excluded tag.
5. The list of selected tests is checked before execution.
6. The listed set matches the expected set in the table.
7. A selection matching no test is reported, not treated as a pass.

## Required evidence

Provide the table and the two records. In your `PROOF.md`, explain how you verified a selection before running it, citing the acceptance criteria by number.

## Safety constraints

- Test only an application you run yourself, such as a local demo app in your own folder or container that you may change and reset; never a public site, a production system or one holding real customer data.
- Do not put a real login, token or session cookie in a test, a log, a trace or a screenshot.
- Check that no selection against a shared environment includes a write test.

## Hints

Listing is free. Run only what you have already seen listed.

## Reflection

What happens in your pipeline if a selection quietly matches zero tests?

## Stretch goals

- Fail the run when a selection is empty.
- Print the selection and the reason with every run.
