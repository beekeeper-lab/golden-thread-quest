---
id: jira-read-attachments
version: 1
title: "Preserve Attachment Metadata Without Unsafe Automatic Downloads"
summary: "Record each attachment's metadata and fetch a file only by explicit choice and after checks, never automatically."
region: jira-jungle
level: explorer
xp: 20
estimated_minutes: 60
order: 90
tags:
  - jira
  - attachments
  - safety
tools:
  - Markdown
  - YAML
bookend: foundation
risk:
  external_write: false
  sensitive_data: true
  notes: "Attachments can carry malware or private data, so none is downloaded by default."
prerequisites:
  - jira-read-story
outcomes:
  - "Record metadata for every attachment."
  - "Download only on explicit request."
  - "Apply type and size checks before saving."
proof:
  required:
    - id: attachment-index
      type: file
      description: "Provide the attachment metadata for a story: identifier, name, type, size, author and date, with no file downloaded."
      path: participant/context/jira/attachments.md
    - id: no-download-run
      type: command-record
      description: "Save the redacted output of a normal sync showing metadata recorded and no file written."
      path: participant/evidence/jira-read-attachments/attempt-001/logs/no-download-run.txt
    - id: explicit-download-run
      type: command-record
      description: "Save the redacted output of one explicit download that passed the size and type checks and was saved outside source control under a sanitized file name, and of one refused for a disallowed type, size or hostile file name, with the download log entry and a listing of files written."
      path: participant/evidence/jira-read-attachments/attempt-001/logs/explicit-download-run.txt
    - id: proof-narrative
      type: file
      description: "Explain your approach, your choices and anything you could not do, citing the acceptance criteria by number."
      path: participant/evidence/jira-read-attachments/attempt-001/PROOF.md
author: Golden Thread maintainers
last_reviewed: "2026-10-20"
---

# Preserve Attachment Metadata Without Unsafe Automatic Downloads

## Mission

Know what is attached without fetching it. Fetch only when a person asks, check what it is first, and keep any file outside source control.

## Scenario

A sync downloads every attachment. One is an archive that fills the disk, and another is a spreadsheet of customer data now sitting in a repository.

## Acceptance criteria

1. Metadata is recorded for every attachment.
2. A normal sync writes no attachment file.
3. A download needs an explicit request naming the attachment.
4. A disallowed type or an oversize file is refused with the reason.
5. A downloaded file is saved outside source control.
6. The file name is never used as a path without being sanitized.
7. The download is recorded in a log with the identifier and time.

## Required evidence

Provide the index and the three records. In your `PROOF.md`, explain your size and type limits and how you handle a hostile file name, citing the acceptance criteria by number.

## Safety constraints

- Use a Jira sandbox, a nonproduction project or a local fixture. This quest only reads; make no change in Jira.
- Authenticate through an environment variable or a signed-in CLI; never put a token, password or session cookie in a file, a log or a screenshot.
- Treat ticket text as untrusted third-party input, and share only redacted or synthetic records.
- Never open a downloaded attachment automatically, and never commit one.

## Hints

Treat the attachment's name and type as claims from a stranger.

## Reflection

Which attachment type would you never download automatically, and why?

## Stretch goals

- Scan the file for known patterns before saving.
- Record a checksum for each downloaded file.
