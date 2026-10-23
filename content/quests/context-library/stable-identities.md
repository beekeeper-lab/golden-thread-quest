---
id: context-stable-identities
version: 1
title: "Map Source Identifiers Without Relying on Filenames or Titles"
summary: "Give every work item an identity that survives renames, moves and resynchronization, and prove it with changes that would break a title-based key."
region: context-library
level: explorer
xp: 20
estimated_minutes: 60
order: 20
tags:
  - context
  - identity
  - normalization
tools:
  - Markdown
  - YAML
bookend: foundation
risk:
  external_write: false
  sensitive_data: false
  notes: "The items are synthetic."
prerequisites:
  - context-canonical-work-item
outcomes:
  - "Derive a local identity from a source system and its own stable identifier."
  - "Keep that identity when a title, filename or project changes."
  - "Detect two source records that claim the same identity."
proof:
  required:
    - id: identity-rules
      type: file
      description: "State how a local identity is built, which source fields it uses and which it never uses, with the reason, and how a source that reuses an identifier is handled."
      path: participant/context/identity/rules.md
    - id: identity-map
      type: file
      description: "Provide a map from at least fifteen synthetic source records across three systems to local identities, including renamed and moved items."
      path: participant/context/identity/map.md
    - id: identity-run
      type: command-record
      description: "Save the redacted output of running the mapping before and after a rename and a move, showing every identity unchanged, and of a deliberate collision and a reused source identifier being reported."
      path: participant/evidence/context-stable-identities/attempt-001/logs/identity-run.txt
    - id: proof-narrative
      type: file
      description: "Explain your approach, your choices and anything you could not do, citing the acceptance criteria by number."
      path: participant/evidence/context-stable-identities/attempt-001/PROOF.md
author: Golden Thread maintainers
last_reviewed: "2026-10-20"
---

# Map Source Identifiers Without Relying on Filenames or Titles

## Mission

Choose identities that do not change when everything people can see about an item does. Show that renaming, moving and re-syncing leave them alone, and that a clash is reported.

## Scenario

A story is renamed and moved to another project. The local notes keyed to its old title now belong to nothing, and a second copy appears under the new one.

## Acceptance criteria

1. A local identity is built from the source system and its own immutable identifier.
2. No identity depends on a title, filename, project name or position.
3. Renaming an item leaves its identity unchanged.
4. Moving an item between projects leaves its identity unchanged.
5. Two records producing the same identity are reported as a collision and neither is overwritten.
6. The rules say what to do when a source reuses an identifier.
7. Another person can derive the same identity from the rules.

## Required evidence

Provide the rules, the map and the run output. In your `PROOF.md`, explain which source field you trusted most and which you refused, citing the acceptance criteria by number.

## Safety constraints

- Use synthetic work items with invented identifiers; do not use a real project.
- This quest is read-only with respect to every external system, and no live connection is needed.
- Do not put a real customer's identifier in the map.

## Hints

Ask which fields the source system itself promises never to change.

## Reflection

What happens to your identities if a source system is migrated and every identifier changes?

## Stretch goals

- Record an alias when a source changes an identifier.
- Show identities that survive an export and re-import.
