---
id: ba-gwt-examples
version: 1
title: "Add Useful Given/When/Then Examples Without Obscuring Business Criteria"
summary: "Write concrete Given/When/Then examples that illustrate each business criterion and expose edge cases, while the criteria themselves stay readable."
region: ba-ruins
level: explorer
xp: 20
estimated_minutes: 60
order: 100
tags:
  - business-analysis
  - gherkin
  - acceptance-criteria
tools:
  - Markdown
  - YAML
bookend: validation
risk:
  external_write: false
  sensitive_data: false
  notes: "Examples use synthetic data."
prerequisites:
  - ba-write-story
outcomes:
  - "Illustrate each criterion with at least one concrete example."
  - "Add examples for edge cases the criteria imply."
  - "Keep the examples subordinate to the criteria."
proof:
  required:
    - id: story-with-examples
      type: file
      description: "Provide a story whose numbered criteria each link to Given/When/Then examples using concrete values."
      path: participant/context/examples/story-with-examples.md
    - id: example-rules
      type: file
      description: "State when an example is worth adding and when it only repeats the criterion."
      path: participant/context/examples/example-rules.md
    - id: example-check
      type: command-record
      description: "Save the redacted output of a check that every criterion has an example, every example links to a criterion, and no example contains a vague value such as some or a few."
      path: participant/evidence/ba-gwt-examples/attempt-001/logs/example-check.txt
    - id: proof-narrative
      type: file
      description: "Explain your approach, your choices and anything you could not do, citing the acceptance criteria by number."
      path: participant/evidence/ba-gwt-examples/attempt-001/PROOF.md
author: Golden Thread maintainers
last_reviewed: "2026-10-20"
---

# Add Useful Given/When/Then Examples Without Obscuring Business Criteria

## Mission

Add Given/When/Then examples that make each criterion concrete without burying it. An example earns its place by showing a value, a boundary or a failure the criterion alone does not make clear.

## Scenario

A story carries forty scenarios in a table. The business owner cannot find the rule any more, and the tests pass for reasons nobody can name.

## Acceptance criteria

1. Each business criterion remains stated in plain words and is numbered.
2. Each criterion has at least one example linked to it.
3. Examples use concrete values, not placeholders like some or a few.
4. At least one example covers a boundary or a failure.
5. An example that only repeats the criterion is removed.
6. Each example has one When and one clear outcome.
7. A business reader can find the rule without reading the examples.

## Required evidence

Provide the story, the rules and the check. In your `PROOF.md`, show one example you removed and one you added after finding an edge case, citing the acceptance criteria by number.

## Safety constraints

- Use synthetic data.
- Do not copy real customer values into an example.

## Hints

Pick the example you would be embarrassed to find missing, not the easy one.

## Reflection

At what point do examples start to replace the criteria rather than explain them?

## Stretch goals

- Convert one example into a table of cases.
- Mark examples that cover the same rule and keep only the sharpest.
