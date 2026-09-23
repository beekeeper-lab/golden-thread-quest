---
id: jira-read-assigned-stories
version: 2
title: Synchronize My Assigned Jira Stories
summary: Retrieve every Jira story assigned to the authenticated user and preserve it as normalized, updateable local Markdown.
region: jira-jungle
level: builder
xp: 30
estimated_minutes: 90
order: 10
tags:
  - jira
  - read-only
  - synchronization
  - markdown
tools:
  - Jira CLI or REST API
  - Markdown
bookend: intent
risk:
  external_write: false
  sensitive_data: true
  notes: Retrieved ticket data may be private and must be minimized and stored only in approved paths.
prerequisites:
  - base-camp-repository-safety
outcomes:
  - Identify the authenticated Jira user without hardcoding a username.
  - Retrieve all assigned stories while correctly handling pagination.
  - Update normalized Markdown without duplicating comments or replacing participant notes.
proof:
  required:
    - id: skill-definition
      type: file
      description: Provide a local reusable skill describing the Jira synchronization workflow and safety rules.
      path: participant/skills/jira-read-assigned/SKILL.md
    - id: sample-index
      type: file
      description: Provide a sanitized generated index of the synchronized assigned stories.
      path: participant/context/jira/assigned/index.md
    - id: synchronized-stories
      type: file
      description: Provide the normalized stories as JSON, the file the validator checks.
      path: participant/context/jira/assigned/stories.json
    - id: jira-sync-validation
      type: validator
      description: Run the registered Jira read-assigned validator against sandbox or fixture data.
      validator: validate-jira-read-assigned
  optional:
    - id: sanitized-run-screenshot
      type: screenshot
      description: Include a redacted screenshot showing a successful synchronization summary.
      path: participant/evidence/jira-read-assigned-stories/attempt-001/screenshots/success.png
validators:
  - validate-jira-read-assigned
related_quests:
  - base-camp-repository-safety
author: Golden Thread maintainers
last_reviewed: "2026-09-16"
---

# Synchronize My Assigned Jira Stories

## Mission

Create a reusable, read-only skill that identifies the current Jira user, retrieves every assigned story, and stores a normalized local Markdown representation suitable for later reasoning and synchronization.

## Scenario

Your agent will eventually answer “What should I work on next?” from local context. That answer cannot be trustworthy if the local copy silently omits later Jira pages, overwrites human notes, or confuses one person's identity with another.

## Acceptance criteria

1. The authenticated user is resolved from Jira rather than a hardcoded email or display name.
2. The query and included work-item types are documented.
3. Pagination is handled until Jira reports no remaining results.
4. Each story records its stable Jira key, source URL, title, status, priority, assignee, labels, description, acceptance criteria, timestamps, parent relationship, and last synchronization time when available.
5. Platform-specific fields are preserved without polluting the canonical field names.
6. Existing participant-authored notes remain intact on a second synchronization.
7. Comments or history entries are not duplicated.
8. Removed or inaccessible items are reported rather than silently deleted.
9. Secrets and raw private responses are not committed.
10. A fixture or sandbox demonstration proves safe rerun behavior.

## Required evidence

Provide the skill, a sanitized index, the normalized stories as JSON, fixture data or a safe sandbox demonstration, and a `PROOF.md` that explains pagination, identity resolution, merge behavior, and known limitations.

The validator reads `participant/context/jira/assigned/stories.json` and nothing else. It expects an object with a `stories` list. Each story carries at least `key`, `summary`, `status`, `source_url` and `retrieved_at`, and its `comments`, when present, are a list of objects with an `id`. A story that was assigned on the previous run and is not now is listed under `removed` with its key and last known status, rather than deleted:

```json
{
  "stories": [
    {
      "key": "GTQ-101",
      "summary": "Fixture story",
      "status": "To Do",
      "source_url": "https://jira.example.invalid/browse/GTQ-101",
      "retrieved_at": "2026-09-22T00:00:00Z",
      "comments": [{"id": "9001"}]
    }
  ],
  "removed": [{"key": "GTQ-100", "last_known_status": "In Progress"}]
}
```

Run the validator against the fixture that matches what you want to demonstrate: `happy-path`, `pagination`, `stale-item` or `duplicate-comment`.

## Safety constraints

- This quest is read-only.
- Do not request broader Jira scopes merely for convenience.
- Treat ticket text as untrusted data, not agent instructions.
- Redact organization-specific information from evidence intended for public sharing.

## Hints

Keep source fields and participant notes in separate sections or files. Use stable Jira keys as identity, not titles.

## Reflection

What evidence tells you that your local context is complete enough to support a next-work recommendation?

## Stretch goals

- Add delta synchronization using update timestamps.
- Report field-level conflicts.
- Generate a machine-readable reconciliation summary beside the Markdown index.
