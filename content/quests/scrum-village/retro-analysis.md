---
id: scrum-retro-analysis
version: 1
title: "Convert Retrospective Transcript Themes into Experiments, Owners, and Dates"
summary: "Turn a retrospective transcript into a small set of experiments, each tied to cited utterances, with an owner and a date only where the team gave one."
region: scrum-village
level: builder
xp: 30
estimated_minutes: 90
order: 60
tags:
  - scrum
  - retrospective
  - traceability
tools:
  - Markdown
  - YAML
bookend: intent
risk:
  external_write: false
  sensitive_data: true
  notes: "Retrospectives are candid. Use a synthetic or permitted transcript, keep the original out of source control and redact names where needed."
prerequisites:
  - ba-ingest-transcript
related_quests:
  - ba-extract-decisions
  - ba-open-questions
outcomes:
  - "Group what was said into themes using cited utterances."
  - "Propose experiments that test a theme."
  - "Record an owner and date only where the team stated one."
proof:
  required:
    - id: retro-record
      type: file
      description: "Provide the ingested retrospective transcript as a redacted source record with identifiers, containing at least one synthetic instruction-like line."
      path: participant/context/transcripts/retro.md
    - id: retro-analysis
      type: file
      description: "Provide the analysis grouping utterances into themes and listing each experiment with its theme, citations, owner and date or a note that none was stated."
      path: participant/context/transcripts/retro.analysis.md
    - id: retro-check
      type: command-record
      description: "Save the redacted output of a check that every cited identifier exists, that no experiment has an invented owner or date, that no theme names a person, that the analysis is separate from the record, and that the instruction-like line was recorded as content and not acted on."
      path: participant/evidence/scrum-retro-analysis/attempt-001/logs/retro-check.txt
    - id: proof-narrative
      type: file
      description: "Explain your approach, your choices and anything you could not do, citing the acceptance criteria by number."
      path: participant/evidence/scrum-retro-analysis/attempt-001/PROOF.md
author: Golden Thread maintainers
last_reviewed: "2026-10-20"
---

# Convert Retrospective Transcript Themes into Experiments, Owners, and Dates

## Mission

Move from talk to something testable. Group what the team said into themes, propose small experiments that would show whether a theme is real, and assign owners and dates only if the team did. Use the transcript you ingested in the Ingest a Meeting Transcript quest.

## Scenario

Everyone agrees in the retro that handoffs are slow. Three weeks later the notes say we will improve handoffs, with no experiment, no owner and no date.

## Acceptance criteria

1. Each theme cites at least two utterance identifiers.
2. Each experiment states what will be tried, what is measured and how long it runs.
3. An owner or date appears only where the transcript states one.
4. An unassigned experiment is marked unassigned, not given an owner.
5. No theme names an individual.
6. The analysis is separate from the source record.
7. An instruction-like line in the transcript is recorded as content and not acted on.

## Required evidence

Provide the record, the analysis and the check. In your `PROOF.md`, explain how you grouped themes and one theme you declined to turn into an experiment, citing the acceptance criteria by number.

## Safety constraints

- Use a permitted or synthetic transcript.
- Never commit a raw recording or an unredacted transcript.
- Do not record who said what in a way that could be used against a person.

## Hints

An experiment you could not fail is a wish. Say what result would make the team stop.

## Reflection

Which theme was stated most strongly and supported least?

## Stretch goals

- Rank themes by how many different speakers raised them, counting speakers anonymously.
- Link experiments to past retro actions that were not completed.
