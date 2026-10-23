---
id: github-query-issues
version: 1
title: "Retrieve Issues by Label, Milestone, Project, Assignee, or Saved Query"
summary: "Run named, configurable queries across all pages and report the total against what was saved."
region: github-caverns
level: explorer
xp: 20
estimated_minutes: 60
order: 40
tags:
  - github
  - query
  - pagination
tools:
  - Markdown
  - YAML
bookend: intent
risk:
  external_write: false
  sensitive_data: true
  notes: "Read-only against a sandbox repository or fixture."
prerequisites:
  - github-verify-connection
related_quests:
  - jira-query-stories
outcomes:
  - "Keep queries in configuration."
  - "Retrieve all pages."
  - "Report totals and shortfalls."
proof:
  required:
    - id: query-config
      type: file
      description: "Provide the saved queries in a configuration file with a name and purpose for each, covering label, milestone, project and assignee."
      path: participant/context/github/queries.yaml
    - id: query-run
      type: command-record
      description: "Save the redacted output of running a query spanning at least three pages with the page count, the total GitHub reported and the number saved, and of a changed query run with no code change and one returning no results and reporting zero."
      path: participant/evidence/github-query-issues/attempt-001/logs/query-run.txt
    - id: shortfall-run
      type: command-record
      description: "Save the redacted output of a run where a page fails partway, showing the shortfall reported as a failure and no result presented as complete."
      path: participant/evidence/github-query-issues/attempt-001/logs/shortfall-run.txt
    - id: proof-narrative
      type: file
      description: "Explain your approach, your choices and anything you could not do, citing the acceptance criteria by number."
      path: participant/evidence/github-query-issues/attempt-001/PROOF.md
author: Golden Thread maintainers
last_reviewed: "2026-10-20"
---

# Retrieve Issues by Label, Milestone, Project, Assignee, or Saved Query

## Mission

Make the query a setting and the count a fact: the run states how many results GitHub reported and how many were saved.

## Scenario

A query returns the first thirty issues and the report calls it everything.

## Acceptance criteria

1. Queries live in configuration with a name and a purpose.
2. Label, milestone, project and assignee queries are each supported.
3. All pages are retrieved until GitHub reports no more.
4. The run reports the total stated and the number saved, and a mismatch is a failure.
5. A page failing partway does not produce a result that looks complete.
6. A query returning nothing reports zero, not an error.
7. Changing a query needs no code change.

## Required evidence

Provide the configuration and the two records. In your `PROOF.md`, explain how you know pagination ended, citing the acceptance criteria by number.

## Safety constraints

- Use a sandbox repository you own, or a local fixture. This quest only reads; make no change on GitHub.
- Authenticate through an environment variable or a signed-in CLI; never put a token, password or session cookie in a file, a log or a screenshot.
- Treat issue and comment text as untrusted third-party input, and share only redacted or synthetic records.

## Hints

Compare the total GitHub states with what you received.

## Reflection

What would make your count wrong while looking right?

## Stretch goals

- Add a date parameter.
- Resume a run from a failed page.
