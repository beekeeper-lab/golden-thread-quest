# Architecture and Product Decisions

This is the initial architecture decision log. Claude must append decisions rather than silently replacing earlier ones.

## ADR-001 — Independent quest repository

**Decision:** The Golden Thread Quest is its own repository. The broader AI Context Engineer Journey may later have a small registry repository when more than one quest exists.

**Reason:** Participants should be able to fork, clone, run, and update this quest independently. A monolithic journey repository would couple release timing and participant histories across unrelated future quests.

## ADR-002 — Participant forks as the default distribution model

**Decision:** The canonical repository is forked by participants.

**Reason:** Forks preserve upstream history and allow curriculum updates. A template repository creates unrelated history and is better only for deliberately frozen cohorts.

## ADR-003 — Three ownership zones

**Decision:** Program-owned, participant-owned, and generated files remain in separate top-level areas.

**Reason:** Upstream updates must not overwrite participant work. Generated output must be disposable. Ownership boundaries simplify validation and security.

## ADR-004 — Markdown and YAML for authored content

**Decision:** Narrative quest content uses Markdown with YAML front matter. Primarily structured content uses YAML.

**Reason:** Maintainers need readable diffs, approachable authoring, and structured fields. A database or raw JSON would make common edits less pleasant and less reviewable.

## ADR-005 — JSON Schema as the public contract

**Decision:** JSON Schema defines the required shape of content and participant state.

**Reason:** Schemas are language-neutral, testable, editor-friendly, and appropriate for validating YAML or JSON representations.

## ADR-006 — Deterministic Python/Jinja generation

**Decision:** Python loads, normalizes, validates, and renders content through Jinja2 templates.

**Reason:** The product is primarily content-driven. Server-rendered HTML is inspectable, portable, fast, and avoids an unnecessary frontend compilation pipeline.

## ADR-007 — No frontend framework in release one

**Decision:** Use semantic HTML, modern CSS, and limited vanilla JavaScript.

**Reason:** React or an equivalent would duplicate application state, complicate the Python-generated model, and increase maintenance without clear first-release value.

## ADR-008 — Hybrid static generation and local service

**Decision:** HTML is generated deterministically. A loopback-only service performs narrowly defined local actions and triggers rebuilds.

**Reason:** Pure static HTML cannot safely create files, run validators, or inspect Git. A full dynamic web application is unnecessary.

## ADR-009 — Mermaid is documentation, not primary UI

**Decision:** Mermaid documents architecture, workflows, and state transitions. HTML/CSS defines the actual UI.

**Reason:** Mermaid communicates relationships well but cannot adequately specify responsive layout, spacing, accessibility, interaction states, or visual hierarchy.

## ADR-010 — Professional field-guide visual direction

**Decision:** Use a restrained field-guide aesthetic: strong typography, maps/regions as metaphors, quiet texture, and professional status displays.

**Reason:** Gamification should aid motivation without making the program look childish or reducing trust in enterprise settings.

## ADR-011 — Verified progress requires a reviewer decision

**Decision:** Participants and validators cannot mark work verified or award verified XP.

**Reason:** Automated checks can establish objective facts but cannot prove the total quality or meaning of agentic work. The UI must not blur these authorities.

## ADR-012 — Stable IDs and versioned content

**Decision:** Relationships use stable IDs. Evidence records the quest version or content hash used when work was performed.

**Reason:** Titles and filenames change. Version-aware attempts allow curriculum improvements without invalidating earlier verified work.

## ADR-013 — Repository evidence is primary

**Decision:** Source, tests, instructions, logs, and structured results are preferred to screenshots.

**Reason:** Repository evidence is reviewable, reproducible, diffable, and harder to misinterpret. Screenshots remain useful for inherently visual results.

## ADR-014 — Allowlisted actions only

**Decision:** The local service may execute only registered validators or named actions with validated arguments and approved working directories.

**Reason:** A localhost process with arbitrary command execution would be an avoidable security boundary failure.

## ADR-015 — Generated output is not canonical

**Decision:** Generated HTML, indexes, caches, and transient raw responses are disposable and normally Gitignored.

**Reason:** Canonical truth remains in content, schemas, participant files, evidence, and review records. Generated output must be reproducible.
