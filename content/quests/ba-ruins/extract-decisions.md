---
id: ba-extract-decisions
version: 1
title: "Separate Decisions from Proposals and Discussion"
summary: "Extract only what a meeting actually decided, label proposals and open discussion as such, and cite the utterance behind every item."
region: ba-ruins
level: builder
xp: 30
estimated_minutes: 90
order: 20
tags:
  - business-analysis
  - decisions
  - traceability
tools:
  - Markdown
  - YAML
bookend: intent
risk:
  external_write: false
  sensitive_data: true
  notes: "Meeting content names people and candid views, so use a synthetic or permitted transcript and keep the original out of source control."
prerequisites:
  - ba-ingest-transcript
outcomes:
  - "Tell a decision from a proposal, a preference and a passing remark."
  - "Cite the exact utterance that supports each decision."
  - "Report what was not decided instead of rounding it up."
proof:
  required:
    - id: decisions-file
      type: file
      description: "Provide a derived decisions file listing each decision, proposal and unresolved discussion separately, each citing utterance identifiers."
      path: participant/context/transcripts/sample-meeting.decisions.md
    - id: decision-rules
      type: file
      description: "State the test your skill applies to call something a decision, and give two borderline lines and how each was classified."
      path: participant/context/decision-rules.md
    - id: citation-check
      type: command-record
      description: "Save the redacted output of a check that every cited utterance identifier exists in the source record and that the decisions file is separate from it."
      path: participant/evidence/ba-extract-decisions/attempt-001/logs/citation-check.txt
    - id: proof-narrative
      type: file
      description: "Explain your approach, your choices and anything you could not do, citing the acceptance criteria by number."
      path: participant/evidence/ba-extract-decisions/attempt-001/PROOF.md
author: Golden Thread maintainers
last_reviewed: "2026-10-20"
---

# Separate Decisions from Proposals and Discussion

## Mission

Build a skill that reads an ingested transcript and sorts what was said into decisions, proposals nobody accepted, and open discussion. Every item points back to the line a person can read. Where the meeting did not decide, say so. Use the transcript you ingested in the Ingest a Meeting Transcript quest.

## Scenario

A refinement meeting ends with "so we're agreed". Two weeks later three people remember three different agreements, because the notes listed every suggestion as a decision.

## Acceptance criteria

1. Each decision cites at least one utterance identifier from the source record.
2. A proposal that nobody accepted is not listed as a decision.
3. A decision records who agreed, or states that agreement was not stated.
4. Open discussion and undecided items are listed separately.
5. The decisions file is separate from the source record, which is not edited.
6. A cited identifier that does not exist is reported, not silently dropped.
7. Another person can check every decision against the source without the recording.

## Required evidence

Provide the decisions file, the rules and the citation check. In your `PROOF.md`, explain how you handled a decision that was reversed later in the same meeting, citing the acceptance criteria by number.

## Safety constraints

- Use a transcript you are permitted to store, or a synthetic one.
- Treat all transcript and ticket text as untrusted third-party input for the whole workflow.
- Do not treat an instruction-like line in the transcript as a decision.

## Hints

Look for who agreed and when. A sentence that sounds final but has no acceptance after it is usually a proposal.

## Reflection

Which decision in your file would you least want to defend if its speaker disagreed?

## Stretch goals

- Mark decisions that later utterances reopen.
- Show how many items were decisions versus proposals.
