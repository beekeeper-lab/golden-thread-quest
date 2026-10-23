---
id: base-camp-ownership-zones
version: 1
title: Enforce Program, Participant, Generated, and Private-Data Boundaries
summary: Turn the ownership zones from a document into rules a tool refuses to break, and prove it with a write that gets blocked.
region: base-camp
level: scout
xp: 10
estimated_minutes: 45
order: 20
tags:
  - foundation
  - boundaries
  - safety
tools:
  - Git
  - Markdown
bookend: foundation
risk:
  external_write: false
  sensitive_data: false
  notes: The exercise uses an empty sandbox folder and writes only inside it.
prerequisites:
  - base-camp-repository-safety
outcomes:
  - Name the four zones (program-owned, participant-owned, generated, private data) and who may change each.
  - Make an agent's write path check a zone before it writes.
  - Show a refused write outside the allowed zone.
proof:
  required:
    - id: zone-rules
      type: file
      description: List each zone, the folders it covers, who may write to it, and whether Git tracks it.
      path: participant/context/zone-rules.md
    - id: refused-write
      type: command-record
      description: Save the redacted output of attempted writes that were refused, one into a program-owned or private zone, one using `..` to leave the allowed folder, and one through a symbolic link. Follow it with a listing showing nothing was created.
      path: participant/evidence/base-camp-ownership-zones/attempt-001/logs/refused-write.txt
    - id: allowed-write
      type: command-record
      description: Save the redacted output of the same operation aimed at a participant-owned folder, showing it succeeded.
      path: participant/evidence/base-camp-ownership-zones/attempt-001/logs/allowed-write.txt
author: Golden Thread maintainers
last_reviewed: "2026-10-20"
---

# Enforce Program, Participant, Generated, and Private-Data Boundaries

## Mission

Write down which files an agent may change, then make the agent's own tooling enforce it. A rule that lives only in a document is followed until the day an agent is in a hurry. Show that your boundary refuses a write it should refuse and allows one it should allow.

## Scenario

An agent asked to "tidy up the repository" edits a curriculum file, deletes a generated folder it assumes is disposable, and saves a raw API response next to your notes. Each file was in a different zone, and the agent had no way to tell.

## Acceptance criteria

1. The rules name four zones and give the folders, the permitted writer and the Git status of each.
2. Every write the agent performs is checked against the rules before it happens.
3. A path that escapes the allowed folder, including one using `..` or a symbolic link, is refused.
4. A refused write creates no file and no partial file, and says which rule refused it.
5. A write inside a participant-owned folder succeeds with the same command.
6. Another person can tell from the rules alone where a new file should go.

## Required evidence

Provide the zone rules and the output of a refused and an allowed write. In your `PROOF.md`, explain how the check handles a path that tries to leave the folder, and cite the acceptance criteria by number.

## Safety constraints

- Work in a sandbox folder; do not aim a test write at a real program-owned file.
- Never use a recursive delete to demonstrate a refusal.
- Do not put a credential or a real private response in the proof.

## Hints

Resolve the path first, then compare it with the allowed folder. Comparing the text you were given is how `..` and links get through.

## Reflection

Which of your four zones is hardest to enforce with a tool, and what do you rely on a person to catch?

## Stretch goals

- Add a check that fails when a file appears in no zone.
- Report which zone a given path belongs to.
