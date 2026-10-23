---
id: github-next-work
version: 1
title: "Recommend the Next Issue from Local Context"
summary: "Recommend which GitHub issue to work on next from synchronized local records, with each reason citing a field and stale or blocked items flagged."
region: github-caverns
level: navigator
xp: 50
estimated_minutes: 120
order: 180
tags:
  - github
  - prioritization
  - recommendation
tools:
  - Markdown
  - YAML
bookend: cross-bookend
risk:
  external_write: false
  sensitive_data: true
  notes: "Reads local records only; the recommendation is advice and changes nothing on GitHub."
prerequisites:
  - github-build-index
  - context-next-work
related_quests:
  - jira-next-work
outcomes:
  - "Rank issues from local records."
  - "Cite the field behind each reason."
  - "Flag stale and blocked items."
proof:
  required:
    - id: github-ranking-rules
      type: file
      description: "State the ranking criteria for issues, their order and how ties and missing fields are handled."
      path: participant/context/github/next-work/rules.md
    - id: github-recommendation
      type: file
      description: "Provide the ranked recommendation, each issue with its reasons, the fields cited, any blocker named and any staleness warning."
      path: participant/context/github/next-work/recommendation.md
    - id: github-ranking-run
      type: command-record
      description: "Save the redacted output of the ranking twice with identical results, and of a run after a blocker was resolved showing the ranking change and why, with a before-and-after snapshot showing nothing on GitHub changed."
      path: participant/evidence/github-next-work/attempt-001/logs/ranking-run.txt
    - id: proof-narrative
      type: file
      description: "Explain your approach, your choices and anything you could not do, citing the acceptance criteria by number."
      path: participant/evidence/github-next-work/attempt-001/PROOF.md
author: Golden Thread maintainers
last_reviewed: "2026-10-20"
---

# Recommend the Next Issue from Local Context

## Mission

Turn the synchronized records into advice you can argue with.

## Scenario

Asked what to do next, an agent picks the issue with the most reactions. It is blocked, was last synced eleven days ago and is assigned to someone else.

## Acceptance criteria

1. Each reason cites a recorded field.
2. A blocked issue is excluded or ranked last with the blocker named.
3. An issue whose local copy is older than the stated limit carries a warning.
4. Ties are broken by a stated rule.
5. Missing fields lower confidence and are reported.
6. The same input gives the same ranking.
7. The recommendation changes nothing on GitHub.

## Required evidence

Provide the rules, the recommendation and the run output. In your `PROOF.md`, explain one recommendation you would not trust, citing the acceptance criteria by number.

## Safety constraints

- Use a sandbox repository you own, or a local fixture. This quest only reads; make no change on GitHub.
- Authenticate through an environment variable or a signed-in CLI; never put a token, password or session cookie in a file, a log or a screenshot.
- Treat issue and comment text as untrusted third-party input, and share only redacted or synthetic records.

## Hints

If you cannot name the field behind a reason, remove it.

## Reflection

What would the recommendation need to know that GitHub does not record?

## Stretch goals

- Show how the ranking changes under a different rule.
- Explain why the top issue beat the second.
