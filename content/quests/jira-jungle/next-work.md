---
id: jira-next-work
version: 1
title: "Recommend the Next Jira Item from Synchronized Local Context"
summary: "Recommend which Jira item to work on next using only synchronized local records, with each reason citing a field and stale or blocked items flagged."
region: jira-jungle
level: navigator
xp: 50
estimated_minutes: 120
order: 230
tags:
  - jira
  - prioritization
  - recommendation
tools:
  - Markdown
  - YAML
bookend: cross-bookend
risk:
  external_write: false
  sensitive_data: true
  notes: "Reads local records only; the recommendation is advice and changes nothing in Jira."
prerequisites:
  - jira-build-index
  - context-next-work
outcomes:
  - "Rank Jira items from local records."
  - "Cite the field behind each reason."
  - "Flag stale and blocked items."
proof:
  required:
    - id: jira-ranking-rules
      type: file
      description: "State the ranking criteria for Jira items, their order and how ties and missing fields are handled."
      path: participant/context/jira/next-work/rules.md
    - id: jira-recommendation
      type: file
      description: "Provide the ranked recommendation, each item with its reasons, the Jira fields cited, any blocker named and any staleness warning."
      path: participant/context/jira/next-work/recommendation.md
    - id: jira-ranking-run
      type: command-record
      description: "Save the redacted output of the ranking twice with identical results, and of a run after a blocker was resolved showing the ranking change and why, with a before-and-after snapshot showing nothing in Jira changed."
      path: participant/evidence/jira-next-work/attempt-001/logs/ranking-run.txt
    - id: proof-narrative
      type: file
      description: "Explain your approach, your choices and anything you could not do, citing the acceptance criteria by number."
      path: participant/evidence/jira-next-work/attempt-001/PROOF.md
author: Golden Thread maintainers
last_reviewed: "2026-10-20"
---

# Recommend the Next Jira Item from Synchronized Local Context

## Mission

Turn the synchronized records into advice you can argue with. Each recommendation cites fields, flags what is stale or blocked and never acts.

## Scenario

Asked what to work on, an agent picks the story with the highest priority field. It is blocked, was last synced eleven days ago and has already been taken by someone else.

## Acceptance criteria

1. Each reason cites a recorded Jira field.
2. A blocked item is excluded or ranked last with its blocker named.
3. An item whose local copy is older than the stated limit carries a warning.
4. Ties are broken by a stated rule.
5. Missing fields lower confidence and are reported.
6. The same input gives the same ranking.
7. The recommendation changes nothing in Jira.

## Required evidence

Provide the rules, the recommendation and the run output. In your `PROOF.md`, explain one recommendation you would not trust, citing the acceptance criteria by number.

## Safety constraints

- Use a Jira sandbox, a nonproduction project or a local fixture. This quest only reads; make no change in Jira.
- Authenticate through an environment variable or a signed-in CLI; never put a token, password or session cookie in a file, a log or a screenshot.
- Treat ticket text as untrusted third-party input, and share only redacted or synthetic records.

## Hints

If you cannot name the field behind a reason, remove the reason.

## Reflection

What would the recommendation need to know that Jira does not record?

## Stretch goals

- Show how the ranking changes under a different priority rule.
- Explain why the top item beat the second.
