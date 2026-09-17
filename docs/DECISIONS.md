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

---

## Stage 0 decisions (2026-09-16)

Recorded by the implementation agent during the Stage 0 planning and feasibility audit.
Evidence and reasoning: `docs/audits/stage-00-planning-audit.md`.

## ADR-016 — Acceptance criteria are derived from the quest body with positional IDs

**Decision:** Acceptance criteria are parsed from the ordered list under the quest body's
`## Acceptance criteria` heading. Each criterion gets the positional ID `ac-<n>` (1-based) and a
`text_hash` of its normalized text. Reviewer findings and evidence status reference the positional ID.
A build error is raised when the heading is missing or contains no ordered list.

**Reason:** `COMPONENT-CATALOG.md` C10, `VIEW-MODEL-CONTRACT.md`, and the shipped
`quest-detail.html.j2` all require stable criterion IDs, while `CONTENT-MODEL.md` forbids duplicating
the criteria into front matter. Deriving them keeps one copy. The `text_hash` makes a silent change of
meaning under a stable ID detectable, which is what the quest `version` rule already asks an author to
declare.

## ADR-017 — A validation run never changes attempt state

**Decision:** Running a validator appends a result record and changes nothing else. `locally_validated`
is reached only when the participant requests it and every required validator's latest run returns a
qualifying outcome. A failing run leaves the attempt where it was and surfaces findings. The
`EvidenceReady --> InProgress: Validation fails` edge in the `ARCHITECTURE.md` diagram is not
implemented.

**Reason:** An automatic backward transition would make a registered validator an authority over
participant state, which ADR-011 denies it, and would discard the `evidence_ready` assertion the
participant deliberately made. `SCREEN-SPECS.md` U06 requires that a validator failure never become
"quest failed".

## ADR-018 — Participant paths are contract-fixed, the participant root is configuration

**Decision:** `evidence_path` and `result_path` keep the literal `participant/` prefix the schemas
require. The base directory they resolve against is injected (`participant_root`), defaulting to
`<repo>/participant` and pointed at `<repo>/fixtures/participant` under test. Every resolved path is
canonicalized and re-verified inside the configured root after symbolic links are followed.

**Reason:** Tests must exercise the real loader against the shipped fixtures without writing into a
participant's live directory, and the schema prefix is part of the published contract, so it is
configuration that moves, not the contract.

## ADR-019 — Python 3.12 or newer

**Decision:** `requires-python = ">=3.12"`. Development and CI run 3.12 and the newest stable release.

**Reason:** `PLANNING-STATUS.md` requires 3.12 or newer. No 3.13-or-later-only syntax is used, so the
floor stays where the plan put it.

## ADR-020 — `jsonschema` against the published schemas, frozen dataclasses internally

**Decision:** Authored and participant documents are validated with `jsonschema` (Draft 2020-12)
against the files in `schemas/`. Validated documents are then converted into frozen dataclasses for
internal use. Pydantic is not used.

**Reason:** The published schemas are the public contract. A Pydantic model layer would restate the
same rules in a second place that can drift from the file a maintainer actually reads.

## ADR-021 — `markdown-it-py` for CommonMark, `nh3` for sanitization

**Decision:** Quest narrative is rendered by `markdown-it-py` with raw HTML disabled, then passed
through `nh3` with an explicit tag and attribute allowlist and a URL-scheme allowlist. Rendered HTML
is carried in a distinct view-model field name (`safe_rendered_html`) so it cannot be confused with
ordinary text.

**Reason:** `PLANNING-STATUS.md` requires CommonMark plus sanitization.
`SECURITY-AND-PRIVACY.md` requires an explicit allowlist and disabled raw HTML. Sanitizing after
rendering means the guarantee does not depend on the renderer's own escaping being complete.

## ADR-022 — The loopback service uses the Python standard library

**Decision:** The local service is built on `http.server.ThreadingHTTPServer` with an explicit route
table. FastAPI, Starlette, and Flask are not used.

**Reason:** Every service requirement in `ARCHITECTURE.md` and `SECURITY-AND-PRIVACY.md` is a
*restriction* — loopback binding, per-run token, origin checks, body-size caps, allowlisted route IDs,
no filesystem paths from callers. A framework adds dependencies and abstracts the exact request
surface those restrictions apply to. The service handles a single local user and needs no concurrency
model beyond threads.

## ADR-023 — `pytest`, Playwright, and axe-core

**Decision:** `pytest` for unit, contract, semantic, golden, integration, and security layers.
Playwright for participant and reviewer flows. axe-core through Playwright for automated accessibility
checks.

**Reason:** Named in `IMPLEMENTATION-PLAN.md`.

## ADR-024 — `ruff` for format and lint, `mypy --strict` for types

**Decision:** `ruff format` and `ruff check` are the formatter and linter. `mypy --strict` type-checks
`quest_app/` and `validators/`.

**Reason:** One tool covering format and lint keeps the local commands and CI identical. Strict typing
is affordable on a codebase this size and prevents the view-model contract from decaying into
untyped dictionaries.

## ADR-025 — YAML is parsed with `safe_load` only

**Decision:** Every YAML read uses `yaml.safe_load`. `yaml.load` and custom constructors are forbidden
and a lint rule enforces it.

**Reason:** `IMPLEMENTATION-PLAN.md` Stage 2 requires safe YAML parsing. Authored content, participant
state, and review records are all inputs that can arrive from a pull request.
