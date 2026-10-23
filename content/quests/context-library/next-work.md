---
id: context-next-work
version: 1
title: "Rank Next Work from Local Markdown with Cited Reasons"
summary: "Recommend what to work on next from local context only, with every ranking reason citing a recorded field and stale context flagged instead of trusted."
region: context-library
level: navigator
xp: 50
estimated_minutes: 120
order: 90
tags:
  - context
  - prioritization
  - explainability
tools:
  - Markdown
  - YAML
bookend: cross-bookend
risk:
  external_write: false
  sensitive_data: false
  notes: "The context is synthetic. The recommendation is advice, not an action."
prerequisites:
  - context-dependency-map
  - context-staleness
related_quests:
  - scrum-refinement-agenda
outcomes:
  - "Rank work using stated, recorded criteria."
  - "Cite the field behind each reason."
  - "Exclude or flag work whose context is stale or blocked."
proof:
  required:
    - id: inputs
      type: file
      description: "Provide the synthetic local records ranked, including at least one blocked item, one item with stale context and one item with missing data."
      path: participant/context/next-work/inputs.md
    - id: ranking-rules
      type: file
      description: "State the ranking criteria, their order and how ties and missing data are handled."
      path: participant/context/next-work/rules.md
    - id: recommendation
      type: file
      description: "Provide the ranked recommendation, each item with its reasons, the fields cited, any blocker named and any warnings."
      path: participant/context/next-work/recommendation.md
    - id: ranking-run
      type: command-record
      description: "Save the redacted output of the ranking run twice with identical results, and of a run after a dependency was completed showing the ranking change and why."
      path: participant/evidence/context-next-work/attempt-001/logs/ranking-run.txt
    - id: proof-narrative
      type: file
      description: "Explain your approach, your choices and anything you could not do, citing the acceptance criteria by number."
      path: participant/evidence/context-next-work/attempt-001/PROOF.md
author: Golden Thread maintainers
last_reviewed: "2026-10-20"
---

# Rank Next Work from Local Markdown with Cited Reasons

## Mission

Build a recommendation you can argue with. Each item comes with reasons that point to fields in your local records, and anything blocked or stale is flagged instead of ranked as if it were fine.

## Scenario

Asked what to do next, an agent names the item with the most upvotes. It is blocked, its context is a week old and a higher-priority item is waiting on nobody.

## Acceptance criteria

1. Every ranking reason cites a recorded field of the item.
2. Blocked work is excluded or ranked last with the blocker named.
3. Items with stale context carry a warning.
4. Ties are broken by a stated rule.
5. Missing data lowers confidence and is reported, not filled in.
6. The same input gives the same ranking.
7. A person can disagree with a reason and see which field to change.

## Required evidence

Provide the rules, the recommendation and the run output. In your `PROOF.md`, explain how you weighed criteria that conflicted and one recommendation you would not trust, citing the acceptance criteria by number.

## Safety constraints

- Use synthetic work items with invented identifiers; do not use a real project.
- This quest is read-only with respect to every external system, and no live connection is needed.
- The recommendation never starts, assigns or changes work.

## Hints

If you cannot say which field a reason came from, it is a guess.

## Reflection

What would you want the ranking to refuse to do?

## Stretch goals

- Show how the ranking changes under a different priority rule.
- Explain why an item was not ranked first.
