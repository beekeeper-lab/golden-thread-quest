---
id: context-canonical-work-item
version: 2
title: Define a Canonical Cross-System Work-Item Model
summary: Design and apply one local work-item model that represents Jira, Trello, and GitHub work without erasing what makes each system different.
region: context-library
level: builder
xp: 30
estimated_minutes: 120
order: 10
tags:
  - context
  - markdown
  - normalization
  - traceability
  - stable-identity
tools:
  - Markdown
  - YAML
bookend: cross-bookend
risk:
  external_write: false
  sensitive_data: true
  notes: The model is applied to previously synchronized work, so the same redaction rules as the source quests apply.
prerequisites:
  - jira-read-assigned-stories
related_quests:
  - trello-read-board
  - github-read-assigned-issues
outcomes:
  - Define a written canonical work-item model with required fields, optional fields, and explicit non-goals.
  - Map each source system's fields onto the canonical model without losing source-specific structure.
  - Give every work item an identity that survives renames, moves, and re-synchronization.
  - Keep participant analysis separate from synchronized source data so neither overwrites the other.
proof:
  required:
    - id: model-definition
      type: file
      description: Provide the written canonical work-item model, including field definitions, required and optional fields, and stated non-goals.
      path: participant/context/model/work-item.md
    - id: field-mappings
      type: directory
      description: Provide one mapping document per source system, showing how its fields become canonical fields.
      path: participant/context/model/mappings/
    - id: worked-examples
      type: file
      description: Provide at least two real synchronized items, from different source systems, expressed in the canonical model side by side.
      path: participant/context/model/examples.md
    - id: identity-demonstration
      type: command-record
      description: Save the redacted record of re-running normalization after a source item was renamed and moved, showing the identity held.
      path: participant/evidence/context-canonical-work-item/attempt-001/logs/identity-check.txt
    - id: unmappable-record
      type: command-record
      description: Save the redacted record of normalizing an item the model cannot represent, showing the reason reported and that no partial record was written.
      path: participant/evidence/context-canonical-work-item/attempt-001/logs/unmappable.txt
  optional:
    - id: model-review
      type: review
      description: Ask a reviewer to try to break the model with a work item it was not designed for, and record the outcome.
author: Golden Thread maintainers
last_reviewed: "2026-09-17"
---

# Define a Canonical Cross-System Work-Item Model

## Mission

Jira stories, Trello cards, and GitHub issues describe the same underlying thing in three incompatible shapes. An agent that answers questions across all three needs one local model. The naive version of that model is a lowest common denominator that throws away Trello's list position, Jira's issue hierarchy, and GitHub's delivery links, and the resulting local context quietly stops being able to answer the questions people actually ask.

Build a canonical work-item model that is genuinely shared, records what it deliberately does not model, and keeps each system's own structure available beside the canonical fields rather than underneath them.

## Scenario

You have synchronized work from at least one system already. Criterion 9 asks for two, from
different systems, so finish either *Read a Trello board into local context* or *Read your
assigned GitHub Issues* before you claim this quest. Only the Jira quest is a hard
prerequisite, because either of the other two satisfies the second system. Someone now asks the agent which of their open work is blocked, across every system. Answering that requires agreeing what "open", "blocked", and "assigned to me" mean when three systems disagree — and writing that agreement down where a reviewer can argue with it.

## Acceptance criteria

1. The model document defines every canonical field with its meaning, type, and whether it is required.
2. Canonical identity is defined as the source system combined with that system's stable identifier, and never derives from a filename, title, or local path.
3. The model states its non-goals: at least three things it deliberately does not represent, and why.
4. Canonical status is defined as a small, closed set of values, and each source system's statuses are mapped onto it with the lossy cases named.
5. Source-specific fields are preserved in a clearly namespaced area rather than discarded or merged into canonical field names.
6. Each source system has its own mapping document naming the unmapped source fields and the canonical fields it cannot supply.
7. Participant-authored analysis is stored separately from synchronized source data, and re-normalization leaves it unchanged.
8. Provenance is recorded for every item: source system, source identifier, source URL, retrieval time, and the synchronization run that produced it.
9. At least two real items from different source systems are shown in the canonical model, with their differences visible rather than smoothed away.
10. Renaming a source item and moving it between lists, statuses, or repositories updates the existing canonical record instead of creating a second one.
11. An item that cannot be mapped is reported with the reason, and is not written as a partial record that looks complete.
12. The model document says which fields a next-work recommendation may rely on and which are advisory.

## Required evidence

Provide the model definition, the per-system mapping documents, the worked examples, the identity demonstration record, and the record of an item the model could not represent. Write a `PROOF.md` explaining the hardest mapping decision you made, what it costs, and which acceptance criteria your evidence covers, by number.

Submit the attempt for review when the evidence is complete. A reviewer decides whether the model holds.

## Safety constraints

- This quest normalizes work already retrieved. It performs no external reads or writes of its own.
- Do not copy raw authenticated responses into the model or the examples.
- Source text carried into canonical records remains untrusted data, not agent instructions.
- Redact personal names, email addresses, and customer identifiers from examples intended for sharing.

## Hints

Write the non-goals first. A model that claims to represent everything will be contradicted by the third work item you try. Keep the canonical block and the source block in one file but visibly separate, so a diff after re-synchronization is easy for a human to read.

## Reflection

Which canonical field was the hardest to define, and what does the difficulty tell you about the difference between the teams using these systems?

## Stretch goals

- Add a validation pass that reports canonical records missing a required field, instead of rendering them.
- Detect two source items across systems that appear to be the same work, and report the pair for a human decision.
- Record model versions, so a later change to a field's meaning is visible in the history.
