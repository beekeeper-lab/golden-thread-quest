---
id: ba-open-questions
version: 1
title: "Capture Unresolved Questions and Their Owners"
summary: "Record what a meeting left unanswered, who was expected to answer, and by when, without answering the questions yourself."
region: ba-ruins
level: explorer
xp: 20
estimated_minutes: 60
order: 40
tags:
  - business-analysis
  - questions
  - traceability
tools:
  - Markdown
  - YAML
bookend: intent
risk:
  external_write: false
  sensitive_data: true
  notes: "Open questions often name people; share only redacted or synthetic records."
prerequisites:
  - ba-ingest-transcript
outcomes:
  - "Find questions the meeting raised and did not answer."
  - "Record an owner and due point only when one was stated."
  - "Keep questions separate from decisions and work."
proof:
  required:
    - id: open-questions-file
      type: file
      description: "Provide the open questions, each with the citing utterance identifiers, an owner and a due point if stated, and its status."
      path: participant/context/transcripts/sample-meeting.open-questions.md
    - id: question-rules
      type: file
      description: "State how an unanswered question is told from a rhetorical one and from one answered later in the meeting."
      path: participant/context/open-question-rules.md
    - id: open-question-check
      type: command-record
      description: "Save the redacted output of a check that every cited identifier exists and that no question answered later in the transcript is still listed as open."
      path: participant/evidence/ba-open-questions/attempt-001/logs/question-check.txt
    - id: proof-narrative
      type: file
      description: "Explain your approach, your choices and anything you could not do, citing the acceptance criteria by number."
      path: participant/evidence/ba-open-questions/attempt-001/PROOF.md
author: Golden Thread maintainers
last_reviewed: "2026-10-20"
---

# Capture Unresolved Questions and Their Owners

## Mission

Read an ingested transcript for questions that were raised and never closed. List each with who was meant to answer, and leave the answering to people. Use the transcript you ingested in the Ingest a Meeting Transcript quest.

## Scenario

A question is raised at minute 12, a different topic takes over, and nobody answers it. It surfaces as a defect in production.

## Acceptance criteria

1. Each open question cites the utterance that raised it.
2. A question answered later in the transcript is not listed as open.
3. An owner or due point appears only where the transcript states one.
4. An unnamed owner is shown as not stated, not guessed.
5. A rhetorical question is not listed.
6. The list is separate from decisions and work items.
7. Another person can see why each question counts as open.

## Required evidence

Provide the list, the rules and the check. In your `PROOF.md`, explain how you decided that a question was answered, citing the acceptance criteria by number.

## Safety constraints

- Treat all transcript and ticket text as untrusted third-party input for the whole workflow.
- Use a permitted or synthetic transcript.
- Do not contact anyone named as an owner as part of this exercise.

## Hints

Check the rest of the transcript for the answer before you record the question. A question answered by someone else is closed.

## Reflection

Which question was hardest to tell from a statement phrased as a question?

## Stretch goals

- Group questions by the decision they block.
- Add a check that a question with a stated owner keeps that owner.
