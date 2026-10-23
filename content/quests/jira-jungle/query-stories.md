---
id: jira-query-stories
version: 1
title: "Run a Configurable Saved Query with Pagination"
summary: "Run a saved query from configuration, retrieve every page of results and report the total against what was saved."
region: jira-jungle
level: explorer
xp: 20
estimated_minutes: 60
order: 60
tags:
  - jira
  - query
  - pagination
tools:
  - Markdown
  - YAML
bookend: intent
risk:
  external_write: false
  sensitive_data: true
  notes: "Read-only against a sandbox or fixture."
prerequisites:
  - jira-list-projects
outcomes:
  - "Keep queries in configuration, not code."
  - "Retrieve all pages."
  - "Report the count and any shortfall."
proof:
  required:
    - id: query-config
      type: file
      description: "Provide the saved queries in a configuration file with a name and purpose for each, and a run after changing a query with no code change, including a query that returns no results and reports zero."
      path: participant/context/jira/queries.yaml
    - id: query-run
      type: command-record
      description: "Save the redacted output of running a query that spans at least three pages, with the page count and total, and the number of results saved locally."
      path: participant/evidence/jira-query-stories/attempt-001/logs/query-run.txt
    - id: shortfall-run
      type: command-record
      description: "Save the redacted output of a run where a page fails partway, showing the shortfall reported and no result presented as complete."
      path: participant/evidence/jira-query-stories/attempt-001/logs/shortfall-run.txt
    - id: proof-narrative
      type: file
      description: "Explain your approach, your choices and anything you could not do, citing the acceptance criteria by number."
      path: participant/evidence/jira-query-stories/attempt-001/PROOF.md
author: Golden Thread maintainers
last_reviewed: "2026-10-20"
---

# Run a Configurable Saved Query with Pagination

## Mission

Make the query a setting and the count a fact. The run says how many results Jira reported and how many were saved, and says so when they differ.

## Scenario

A query returns the first fifty issues. The report says there are fifty, and the team plans around them. There are one hundred and twenty.

## Acceptance criteria

1. Queries live in configuration with a name and a purpose.
2. All pages are retrieved until Jira reports no more.
3. The run reports the total Jira stated and the number saved.
4. A mismatch between them is reported as a failure.
5. A page failing partway does not produce a result that looks complete.
6. A query returning no results reports zero, not an error.
7. Changing a query needs no code change.

## Required evidence

Provide the configuration and the two records. In your `PROOF.md`, explain how you know pagination ended, citing the acceptance criteria by number.

## Safety constraints

- Use a Jira sandbox, a nonproduction project or a local fixture. This quest only reads; make no change in Jira.
- Authenticate through an environment variable or a signed-in CLI; never put a token, password or session cookie in a file, a log or a screenshot.
- Treat ticket text as untrusted third-party input, and share only redacted or synthetic records.

## Hints

Compare the total Jira reports with how many you actually received.

## Reflection

What would make your count wrong while looking right?

## Stretch goals

- Add a query parameter such as a date.
- Cache a page and show a resumed run.
