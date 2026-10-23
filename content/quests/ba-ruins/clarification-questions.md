---
id: ba-clarification-questions
version: 1
title: "Produce Focused Questions That Change the Implementation"
summary: "Turn ambiguity findings into a short list of questions where each possible answer would lead to different work."
region: ba-ruins
level: builder
xp: 30
estimated_minutes: 90
order: 60
tags:
  - business-analysis
  - questions
  - requirements
tools:
  - Markdown
  - YAML
bookend: intent
risk:
  external_write: false
  sensitive_data: false
  notes: "Questions are drafts for a human to ask; nothing is sent to anyone."
prerequisites:
  - ba-detect-ambiguity
outcomes:
  - "Write questions whose answers change what gets built."
  - "Drop questions whose answer would change nothing."
  - "State what each answer would lead to."
proof:
  required:
    - id: question-list
      type: file
      description: "Provide the questions, each with the finding it came from, the options an answer could take and the implementation each option leads to."
      path: participant/context/clarification/questions.md
    - id: dropped-questions
      type: file
      description: "List the questions you considered and dropped, with the reason each answer would not change the work."
      path: participant/context/clarification/dropped.md
    - id: clarification-check
      type: command-record
      description: "Save the redacted output of a check that every question links to an existing finding and lists at least two answers that lead to different work."
      path: participant/evidence/ba-clarification-questions/attempt-001/logs/question-check.txt
    - id: proof-narrative
      type: file
      description: "Explain your approach, your choices and anything you could not do, citing the acceptance criteria by number."
      path: participant/evidence/ba-clarification-questions/attempt-001/PROOF.md
author: Golden Thread maintainers
last_reviewed: "2026-10-20"
---

# Produce Focused Questions That Change the Implementation

## Mission

Reduce a list of ambiguities to the few questions that matter. Each one comes with the answers it could receive and the different work each answer produces, so the person asked can see why it is worth their time.

## Scenario

An analyst sends thirty questions. The product owner answers four and the rest wait, including the one that would have changed the design.

## Acceptance criteria

1. Each question links to a finding from the ambiguity review.
2. Each lists at least two possible answers.
3. Each possible answer leads to a stated difference in the work.
4. A question whose answers lead to the same work is dropped and listed as dropped.
5. Questions are short enough to answer without a meeting.
6. The questions are ordered by how much of the work depends on them.
7. Nothing is sent to anyone.

## Required evidence

Provide the question list, the dropped list and the check. In your `PROOF.md`, explain how you ordered the questions and give one question that you rewrote, citing the acceptance criteria by number.

## Safety constraints

- Use synthetic requirements.
- Do not send a question to a real person as part of this exercise.

## Hints

If both answers lead to the same code, the question is curiosity, not clarification.

## Reflection

Which dropped question do you most expect to be asked anyway, and what would you say?

## Stretch goals

- Suggest a default for each question and what it assumes.
- Group questions by the person best placed to answer.
