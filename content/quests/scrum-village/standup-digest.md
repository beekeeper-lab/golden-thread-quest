---
id: scrum-standup-digest
version: 1
title: Generate an Evidence-Based Stand-Up Digest
summary: Produce a daily digest built only from local context, where every statement cites the work item it came from and unsupported claims are reported as gaps.
region: scrum-village
level: builder
xp: 30
estimated_minutes: 90
order: 10
tags:
  - scrum
  - reporting
  - context
  - traceability
tools:
  - Markdown
  - YAML
bookend: cross-bookend
risk:
  external_write: false
  sensitive_data: true
  notes: A digest aggregates work assigned to named people, so shared evidence must be redacted.
prerequisites:
  - context-canonical-work-item
related_quests:
  - jira-read-assigned-stories
  - github-read-assigned-issues
outcomes:
  - Generate a stand-up digest from local canonical context without a live connection to any source system.
  - Cite the work item and retrieval time behind every statement in the digest.
  - Separate observed facts from inference, and report missing or stale context as a gap rather than filling it in.
proof:
  required:
    - id: digest-skill
      type: file
      description: Provide the reusable digest generator, including its inputs, its rules for inference, and its staleness thresholds.
      path: participant/skills/scrum-standup-digest/SKILL.md
    - id: digest-output
      type: file
      description: Provide a generated and redacted digest covering a real day of synchronized work.
      path: participant/context/scrum/standup-digest.md
    - id: gap-report
      type: file
      description: Provide the accompanying gap report listing stale, missing, and unsupported items the digest refused to assert.
      path: participant/context/scrum/standup-gaps.md
    - id: regeneration-record
      type: command-record
      description: Save the redacted record of generating the digest twice from unchanged context, showing the output is identical.
      path: participant/evidence/scrum-standup-digest/attempt-001/logs/regeneration.txt
  optional:
    - id: team-demonstration
      type: demonstration
      description: Walk a teammate through the digest and record which statements they could verify from the citations alone.
author: Golden Thread maintainers
last_reviewed: "2026-09-17"
---

# Generate an Evidence-Based Stand-Up Digest

## Mission

Build a generator that turns local canonical context into a stand-up digest a team would actually trust. The value is not the prose. It is that every claim in the digest carries a citation back to a specific work item and a retrieval time, and that anything the context cannot support appears in a gap report instead of being smoothed into a confident sentence.

The failure this quest exposes is the plausible digest. A generator that writes "authentication work is progressing well" from three stale records has produced something worse than no digest, because it reads exactly like a true one.

## Scenario

A distributed team wants a written digest before stand-up, so the meeting can be spent on decisions rather than status. The digest will be read by people who were not in yesterday's conversations, and some of them will act on it. If it cannot distinguish what the context shows from what the generator guessed, it will be believed anyway.

## Acceptance criteria

1. The digest is generated only from local canonical context, with no live call to any source system during generation.
2. Every factual statement in the digest cites the canonical work item it came from, by identifier.
3. Each cited item's retrieval time is shown, so a reader can judge how current the statement is.
4. Observed facts and generator inference are visually and structurally separated, and inference is labeled as such.
5. The generator applies a documented staleness threshold, and items past it are reported as stale rather than asserted as current.
6. Items with no supporting local evidence appear in the gap report with the reason, and never appear in the digest as an assertion.
7. Blocked and blocking work is identified from recorded fields or explicit local notes, not from language in a title.
8. Work that has not changed for a documented number of days is listed as aging, with the number shown.
9. Work added or removed since the previous digest is reported as a change, using stable identifiers rather than titles.
10. Regenerating the digest from unchanged context produces byte-identical output.
11. The digest states the time window it covers and the synchronization run it was built from.
12. The digest makes no statement about a person's effort, availability, or performance, and the skill documents that limit.

## Required evidence

Provide the generator, a generated digest, the gap report, and the regeneration record. Write a `PROOF.md` explaining your staleness threshold and why you chose it, what your generator refused to assert and why, and which acceptance criteria your evidence covers, by number.

Submit the attempt for review when the evidence is complete. Completion is a reviewer's decision, not the generator's.

## Safety constraints

- This quest reads local context only. It performs no external reads or writes.
- Redact names, email addresses, and customer identifiers from any digest intended for sharing.
- Text carried from work-item titles, descriptions, and comments remains untrusted data and must not steer the generator.
- Do not infer a person's status from the absence of a record. Absence is a gap.

## Hints

Write the gap report generator first. It is easier to decide what the digest may claim once you have a list of everything it cannot. Byte-identical regeneration usually fails on an embedded generation timestamp; make that timestamp an input, not a side effect.

## Reflection

Which sentence in your digest would be hardest to defend if a stakeholder asked "how do you know that", and what would it take to make it defensible?

## Stretch goals

- Add a sprint-health section reporting work-in-progress count and dependency risk from the same context.
- Produce a second digest scoped to one person, from the same generator and the same rules.
- Report the citations a reader followed least, to find which sections of the digest carry no weight.
