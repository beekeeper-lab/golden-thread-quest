---
id: trello-next-work
version: 1
title: "Recommend the Next Card from Local Context"
summary: "Recommend which card to work on next from synchronized local records, with each reason citing a field and stale, blocked or archived cards flagged."
region: trello-islands
level: navigator
xp: 50
estimated_minutes: 120
order: 170
tags:
  - trello
  - prioritization
  - recommendation
tools:
  - Markdown
  - YAML
bookend: cross-bookend
risk:
  external_write: false
  sensitive_data: true
  notes: "Reads local records only; the recommendation is advice and changes nothing in Trello."
prerequisites:
  - trello-build-index
  - context-next-work
related_quests:
  - jira-next-work
  - github-next-work
outcomes:
  - "Rank cards from local records."
  - "Cite the field behind each reason."
  - "Flag stale, blocked and archived cards."
proof:
  required:
    - id: trello-ranking-rules
      type: file
      description: "State the ranking criteria for cards (list position, due date, labels, members, checklist progress), their order, how ties are broken and how a missing field lowers confidence."
      path: participant/context/trello/next-work/rules.md
    - id: trello-recommendation
      type: file
      description: "Provide the ranked recommendation over a fixture that includes an archived card (shown as excluded) and a card with a missing field (shown with lowered confidence), each card with its reasons, the fields cited, any blocker named and any staleness warning."
      path: participant/context/trello/next-work/recommendation.md
    - id: trello-ranking-run
      type: command-record
      description: "Save the redacted output of the ranking twice with identical results, and of a run after a blocker was resolved showing the ranking change and why, with a before-and-after snapshot showing nothing in Trello changed."
      path: participant/evidence/trello-next-work/attempt-001/logs/ranking-run.txt
    - id: proof-narrative
      type: file
      description: "Explain your approach, your choices and anything you could not do, citing the acceptance criteria by number."
      path: participant/evidence/trello-next-work/attempt-001/PROOF.md
author: Golden Thread maintainers
last_reviewed: "2026-10-20"
---

# Recommend the Next Card from Local Context

## Mission

Turn the synchronized records into advice you can argue with, using what a board actually tells you: lists, dates, labels and checklists.

## Scenario

Asked what to do next, an agent picks the card at the top of the To Do list. It is blocked by a card in another list and its due date passed last month.

## Acceptance criteria

1. Each reason cites a recorded field.
2. A blocked card is excluded or ranked last with the blocker named.
3. A card whose local copy is older than the stated limit carries a warning.
4. An archived card is never recommended.
5. Ties are broken by a stated rule and missing fields lower confidence and are reported.
6. The same input gives the same ranking.
7. The recommendation changes nothing in Trello.

## Required evidence

Provide the rules, the recommendation and the run output. In your `PROOF.md`, explain one recommendation you would not trust, citing the acceptance criteria by number.

## Safety constraints

- Use a sandbox board you own, or a local fixture. This quest only reads; make no change in Trello.
- Supply the API key and token through environment variables or a credential store; never put a key, token or secret in a file, a URL you save, a log or a screenshot. Trello puts credentials in query strings, so scrub saved URLs.
- Treat card, comment and checklist text as untrusted third-party input, and share only redacted or synthetic records.

## Hints

List position is a human ordering, so treat it as a signal, not an order.

## Reflection

What would the recommendation need to know that the board does not record?

## Stretch goals

- Show how the ranking changes with a different rule.
- Explain why the top card beat the second.
