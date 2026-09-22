---
id: ba-ingest-transcript
version: 3
title: Ingest a Meeting Transcript Without Losing Its Source
summary: Turn a raw meeting transcript into a faithful, attributed local record that keeps speakers, timestamps, and provenance intact and treats the text as untrusted.
region: ba-ruins
level: explorer
xp: 20
estimated_minutes: 60
order: 10
tags:
  - business-analysis
  - intent
  - untrusted-input
  - markdown
tools:
  - Markdown
  - YAML
bookend: intent
risk:
  external_write: false
  sensitive_data: true
  notes: Transcripts contain named people and candid discussion, so raw recordings and unredacted transcripts stay outside source control.
prerequisites:
  - base-camp-repository-safety
outcomes:
  - Preserve a transcript as a source of record with speakers, timestamps, and provenance intact.
  - Keep the verbatim record and any derived analysis in separate, clearly labeled files.
  - Treat transcript text as untrusted input rather than as instructions to the agent.
proof:
  required:
    - id: ingest-skill
      type: file
      description: Provide the reusable transcript ingestion skill, including its provenance fields, redaction rules, and untrusted-input handling.
      path: participant/skills/ba-ingest-transcript/SKILL.md
    - id: source-record
      type: file
      description: Provide the ingested transcript as a redacted source of record with speaker attribution and timestamps.
      path: participant/context/transcripts/sample-meeting.md
    - id: provenance
      type: file
      description: Provide the provenance record naming the meeting, date, participants, capture source, and ingestion run.
      path: participant/context/transcripts/sample-meeting.provenance.yaml
    - id: injection-record
      type: command-record
      description: Save the redacted record of ingesting a transcript that contains an embedded instruction, showing it was recorded and not obeyed.
      path: participant/evidence/ba-ingest-transcript/attempt-001/logs/untrusted-input.txt
    - id: rerun-record
      type: command-record
      description: Save the redacted output of ingesting the same transcript twice, showing that the second run produced an identical source record and duplicated no utterance.
      path: participant/evidence/ba-ingest-transcript/attempt-001/logs/second-run.txt
    - id: unparseable-record
      type: command-record
      description: Save the redacted record of ingesting a transcript the skill cannot parse, showing the reason reported and that no partial record was written.
      path: participant/evidence/ba-ingest-transcript/attempt-001/logs/unparseable.txt
  optional:
    - id: redaction-notes
      type: file
      description: Record what was redacted, why, and how the unredacted original remains retrievable outside source control.
      path: participant/context/transcripts/redaction-notes.md
author: Golden Thread maintainers
last_reviewed: "2026-09-17"
---

# Ingest a Meeting Transcript Without Losing Its Source

## Mission

Every requirement an agent later extracts has to be traceable back to something a human actually said. That trace is only as good as the ingestion step. Build a skill that turns a raw transcript into a faithful local record: speakers attributed, timestamps preserved, provenance recorded, and the verbatim text kept separate from anything you conclude from it.

This quest exists to expose two failures. The first is helpful summarization during ingestion, which destroys the evidence that later work depends on. The second is treating a transcript as trustworthy input: a transcript can contain a sentence that looks like an instruction to the agent, and an ingestion step that acts on it has handed control of the workflow to whoever was in the meeting.

## Scenario

A recorded refinement session produced a transcript. Later quests will extract decisions, open questions, and candidate work items from it, and every one of those will need to cite a speaker and a moment. If ingestion paraphrases, drops the timestamps, or loses which of two people said the ambiguous sentence, none of that later work can be checked.

## Acceptance criteria

1. The verbatim transcript is stored as a source of record and is never rewritten, summarized, or reordered by the ingestion step.
2. Every utterance carries a speaker attribution, and speakers whose identity is uncertain are marked as uncertain rather than guessed.
3. Timestamps are preserved in a consistent format, and the record states the format used.
4. The provenance record names the meeting, its date, the participants, the capture source, the transcription tool, and the time of ingestion.
5. A stable identifier is assigned to the transcript and to each utterance, so a later quest can cite a specific line without relying on line numbers or filenames.
6. Derived analysis, notes, and summaries are stored in files separate from the source of record.
7. Re-ingesting the same transcript produces an identical source record and does not duplicate utterances.
8. Text inside the transcript that reads as an instruction is recorded as content and is not executed, followed, or allowed to change the ingestion behavior.
9. The skill states which personal details are redacted, and the redacted record is the one that may be committed.
10. Raw recordings and unredacted transcripts stay outside source control, and the record states where the original can be retrieved.
11. A transcript the skill cannot parse is reported with the reason, and no partial record is written that appears complete.
12. Another person can read the source record and tell who said what and when, without access to the recording.

## Required evidence

Provide the ingestion skill, the redacted source record, the provenance file, the untrusted-input record, the output of ingesting the same transcript twice, and the record of a transcript the skill refused to parse. Write a `PROOF.md` that explains your utterance identifier scheme, what you redacted, and exactly what your run did with the embedded instruction. Cite the acceptance criteria by number.

Submit the attempt for review when the evidence is in place. A reviewer decides whether the ingestion is faithful.

## Safety constraints

- This quest is read-only with respect to every external system.
- Use a transcript you are permitted to store, or a synthetic one you wrote for the exercise.
- Never commit a raw recording, an unredacted transcript, or a participant's personal contact details.
- Treat all transcript text as untrusted third-party input for the whole workflow, not only during ingestion.

## Hints

Decide the utterance identifier before you write the parser. Sequence-based identifiers are stable only if the source record is never reordered, which is exactly why the verbatim file is immutable.

## Reflection

If someone disputed a requirement three months from now, what in your record would settle the question, and what would still come down to memory?

## Stretch goals

- Support a second transcript format without changing the source-record shape.
- Detect and report speaker labels that appear to refer to the same person.
- Add a check that reports derived files whose cited utterance identifiers no longer exist.
