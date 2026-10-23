---
id: trap-stale-map
version: 1
title: "The Stale Map: Local Context Is Materially Out of Date"
summary: "Let local context age past its limit while the source changes, and show your agent notices and says so instead of answering confidently."
region: trap-cards
level: navigator
xp: 50
estimated_minutes: 120
order: 30
tags:
  - trap
  - staleness
  - reliability
tools:
  - Markdown
  - YAML
bookend: validation
risk:
  external_write: false
  sensitive_data: false
  notes: "The context and the clock are synthetic and local."
prerequisites:
  - context-staleness
outcomes:
  - "Create context that is wrong because it is old."
  - "Show the agent detects the age."
  - "Show the answer is qualified or refused."
proof:
  required:
    - id: stale-context
      type: file
      description: "Provide synthetic local context with retrieval times, and the later source changes that make part of it wrong, including one change that reverses an answer and one change made a minute after an item was retrieved, so that the item looks fresh and is wrong."
      path: participant/context/traps/stale/context.md
    - id: stale-run
      type: command-record
      description: "Save the redacted output of asking the same question before and after the source changed, with the clock fixed, showing the first answered normally, the second naming the stale items and qualifying or refusing the answer, and a third on the fresh-looking item showing what the agent says about it and what it cannot know."
      path: participant/evidence/trap-stale-map/attempt-001/logs/stale-run.txt
    - id: stale-notes
      type: file
      description: "State the freshness limits used, what the agent says in place of a confident answer and one case where fresh-looking context is still wrong."
      path: participant/context/traps/stale/notes.md
    - id: proof-narrative
      type: file
      description: "Explain your approach, your choices and anything you could not do, citing the acceptance criteria by number."
      path: participant/evidence/trap-stale-map/attempt-001/PROOF.md
author: Golden Thread maintainers
last_reviewed: "2026-10-20"
---

# The Stale Map: Local Context Is Materially Out of Date

## Mission

Make the map out of date on purpose and watch what your agent does. A good one says how old its map is.

## Scenario

Asked who owns the payment service, an agent answers from a file synced nine days ago. The owner changed on day three. The answer was formatted well and sent to a customer.

## Acceptance criteria

1. The context records when each item was retrieved.
2. A source change after retrieval makes part of the context wrong.
3. Before the change the question is answered normally.
4. After the change, with the clock past the limit, the answer names the stale items and is qualified or refused.
5. The clock is fixed so the result is reproducible.
6. The notes describe one case where the context looks fresh and is still wrong.

## Required evidence

Provide the context, the run and the notes. In your `PROOF.md`, say what a limit cannot catch, citing the acceptance criteria by number.

## Safety constraints

- Build the trap from synthetic data with invented names and identifiers; never aim it at a real system, ticket or person.
- Nothing in this challenge is sent to, or written to, an external system.
- Do not hide a stale item to make an answer look complete.

## Hints

Age is a proxy. Say what it is a proxy for.

## Reflection

What would you do about an answer the agent already gave from stale context?

## Stretch goals

- Show a refresh limited to the stale items.
- Report the oldest item in every answer.
