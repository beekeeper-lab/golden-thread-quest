# Proof — Synchronize My Assigned Jira Stories

## What I built

I created a project-local skill that resolves the authenticated Jira user, retrieves assigned stories through all result pages, and writes normalized Markdown without replacing the participant-notes section.

## Important artifacts

- Skill: `participant/skills/jira-read-assigned/SKILL.md`
- Sanitized story index: `participant/context/jira/assigned/index.md`
- Reconciliation report: `participant/context/jira/assigned/reconciliation.md`
- Latest validation: `validation/jira-read-assigned-run-001.json`

## Reproduction

1. Authenticate the Jira CLI against the sandbox tenant.
2. Run the skill in dry-run mode and inspect the target paths.
3. Run the confirmed read-only synchronization.
4. Add a sentence under participant notes in one synchronized story.
5. Run synchronization again and confirm the sentence remains.
6. Compare retrieved item count with the Jira query result count.

## Validation performed

- Pagination fixture containing three result pages
- Existing-notes preservation fixture
- Duplicate comment fixture
- Removed-item reconciliation fixture
- Secret scan over committed evidence

## Limitations

The sample supports Jira Cloud fields used by the sandbox. Custom field interpretation requires explicit mapping rather than guessing from field names.

## Sensitive-data statement

Ticket titles, people, URLs, and comments in this example are fictional. No access token or authenticated raw response is included.
