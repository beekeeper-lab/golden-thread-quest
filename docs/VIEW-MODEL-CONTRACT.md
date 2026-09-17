# View-Model Contract

## Boundary

Content loaders understand YAML and Markdown. Templates understand normalized view models. Templates do not:

- open files;
- parse front matter;
- calculate progress;
- resolve prerequisites;
- inspect Git;
- decide authority;
- execute validators;
- infer routes.

The Python application performs those operations before rendering.

## Shared page model

Every page receives:

- `site`: product title, curriculum title, tagline, navigation;
- `page`: title, description, route, current navigation ID, canonical identifiers;
- `participant`: display-safe participant summary or `null`;
- `service`: availability and safe status summary;
- `build`: application version, content version/hash, build time when displayed;
- `flash`: persistent page messages created by an approved action;

## Quest summary model

A reusable quest card receives:

```json
{
  "id": "jira-read-assigned-stories",
  "title": "Synchronize My Assigned Jira Stories",
  "summary": "Retrieve every assigned Jira story...",
  "route": "/quests/jira-read-assigned-stories/",
  "region": { "id": "jira-jungle", "title": "Jira Jungle", "route": "/regions/jira-jungle/" },
  "state": { "id": "evidence_ready", "label": "Evidence ready", "authority": "participant" },
  "level": { "id": "builder", "label": "Builder" },
  "xp": 30,
  "estimated_minutes": 90,
  "tags": ["jira", "read-only", "synchronization"],
  "prerequisite_summary": { "satisfied": 1, "total": 1 },
  "recommendation_reasons": []
}
```

## Quest detail model

In addition to summary fields:

- version and content hash;
- rendered/sanitized mission, scenario, safety, hints, reflection, and stretch-goal sections;
- outcomes;
- acceptance criteria with stable IDs;
- required and optional proof definitions;
- prerequisites with state and routes;
- related quests;
- validators with availability and latest result;
- allowed primary action;
- version-update notice;
- external-write and sensitive-data risk presentation.

Markdown should be converted and sanitized before the template receives it. A field containing trusted rendered HTML must use a distinct type or name so it cannot be confused with ordinary text.

## Participant authority model

State presentation includes authority:

```json
{
  "id": "locally_validated",
  "label": "Locally validated",
  "authority": "registered_validator",
  "occurred_at": "2026-09-16T14:00:04Z",
  "explanation": "Required automated checks passed. Reviewer approval remains required."
}
```

The template renders the label and explanation. It does not infer that locally validated means verified.

## Error model

Authoring and runtime errors use a shared safe structure:

- code;
- severity;
- public message;
- source filename relative to the repository, when safe;
- field path;
- line and column when known;
- expected rule;
- redacted received-value summary;
- suggested correction;
- documentation route.

Absolute machine paths, stack traces, secrets, and raw request data do not belong in browser view models.
