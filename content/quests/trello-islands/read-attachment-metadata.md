---
id: trello-read-attachment-metadata
version: 1
title: "Preserve Safe Attachment Metadata"
summary: "Record each attachment's metadata, including links to other systems, and fetch a file only by explicit choice after checks."
region: trello-islands
level: explorer
xp: 20
estimated_minutes: 60
order: 50
tags:
  - trello
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
  - trello-read-card
related_quests:
  - jira-read-attachments
outcomes:
  - "Record metadata for every attachment and link."
  - "Download only on explicit request."
  - "Apply type and size checks first."
proof:
  required:
    - id: attachment-index
      type: file
      description: "Provide the attachment metadata for a card: identifier, name, type, size, date, whether it is an uploaded file or a link and where a link points, with no file downloaded."
      path: participant/context/trello/attachments.md
    - id: no-download-run
      type: command-record
      description: "Save the redacted output of a normal sync showing metadata recorded, no file written and a request log showing no request made to any link attachment's target."
      path: participant/evidence/trello-read-attachment-metadata/attempt-001/logs/no-download-run.txt
    - id: explicit-download-run
      type: command-record
      description: "Save the redacted output of one explicit download that passed the size and type checks and was saved outside source control under a sanitized file name, and of one refused for a disallowed type, size or hostile file name, with the download log entry showing the attachment identifier and the time, and a listing of files written."
      path: participant/evidence/trello-read-attachment-metadata/attempt-001/logs/explicit-download-run.txt
    - id: proof-narrative
      type: file
      description: "Explain your approach, your choices and anything you could not do, citing the acceptance criteria by number."
      path: participant/evidence/trello-read-attachment-metadata/attempt-001/PROOF.md
author: Golden Thread maintainers
last_reviewed: "2026-10-20"
---

# Preserve Safe Attachment Metadata

## Mission

Know what is attached and where links lead without fetching any of it, and treat every download as a deliberate act.

## Scenario

A card links to a shared drive folder. The sync follows the link and stores a customer spreadsheet in the repository.

## Acceptance criteria

1. Metadata is recorded for every attachment and link.
2. A link attachment records its target and is never followed.
3. A normal sync writes no attachment file.
4. A download needs an explicit request naming the attachment.
5. A disallowed type, an oversize file or a hostile name is refused with the reason.
6. A downloaded file is saved outside source control under a sanitized name.
7. Each download is recorded in a log with the identifier and time.

## Required evidence

Provide the index and the two records. In your `PROOF.md`, explain your limits and how you treat a link, citing the acceptance criteria by number.

## Safety constraints

- Use a sandbox board you own, or a local fixture. This quest only reads; make no change in Trello.
- Supply the API key and token through environment variables or a credential store; never put a key, token or secret in a file, a URL you save, a log or a screenshot. Trello puts credentials in query strings, so scrub saved URLs.
- Treat card, comment and checklist text as untrusted third-party input, and share only redacted or synthetic records.
- Never open a downloaded attachment automatically, never follow a link attachment and never commit an attachment.

## Hints

A link is a claim about where data lives. Record it; do not visit it.

## Reflection

Which attachment type would you never download automatically?

## Stretch goals

- Record a checksum for each downloaded file.
- Flag attachments that link outside the organisation.
