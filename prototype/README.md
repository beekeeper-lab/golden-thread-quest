# Clickable UI Prototype

Open `index.html` directly in a modern browser. No installation, network request, or local server is required.

## What this prototype defines

- Information hierarchy
- Primary navigation
- Professional field-guide visual direction
- Claimed versus verified progress treatment
- Quest and region card language
- Participant, evidence, environment, and reviewer screens
- Responsive layout intent
- Important empty, warning, failure, and needs-changes states

## What this prototype does not implement

- Python content loading
- Jinja2 page generation
- Filesystem writes
- Git operations
- Validator execution
- Reviewer provenance
- Real progress persistence
- External-system connections

All content comes from `data/prototype-data.js`. The rendering code contains generic UI labels and component behavior, not quest definitions. Production will replace the JavaScript fixture with Python-normalized view models rendered through Jinja2.

## Routes

Use the left navigation or these hash routes:

- `#home`
- `#map`
- `#catalog`
- `#quest/jira-read-assigned-stories`
- `#evidence`
- `#passport`
- `#health`
- `#review`

## Review

Complete `../docs/ui/PROTOTYPE-REVIEW.md` before treating the prototype as an approved production visual baseline.
