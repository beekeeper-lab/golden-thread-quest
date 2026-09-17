# Stage 0 — Planning and Feasibility Audit

**Stage:** 0 — Planning and feasibility audit
**Branch:** `feature/golden-thread-implementation`
**Auditor:** Claude Code (implementation agent, first pass)
**Date:** 2026-09-16
**Result:** `pass-with-advisories` — no blocking findings; all high findings resolved in this stage.

## Method

1. Read every document in the `CLAUDE.md` required reading order, plus `VIEW-MODEL-CONTRACT.md`,
   `VALIDATOR-CONTRACT.md`, `CONTENT-AUTHORING-GUIDE.md`, `CURRICULUM-BACKLOG.md`,
   `PROTOTYPE-REVIEW.md`, and the template and prototype READMEs.
2. Inspected all eight JSON Schemas, all sample content, all fixtures, and the Jinja2 contracts.
3. Executed a machine check of the package against its own schemas: every quest, region, badge,
   track, the site configuration, participant progress, both validation results, and the review
   record were validated with `jsonschema` Draft 2020-12.
4. Executed cross-document reference checks: region, prerequisite, related-quest, track, and badge
   references; prerequisite cycles; duplicate proof IDs; proof-to-validator linkage; evidence paths
   on disk; `verified` state without a review reference.
5. Compared the prototype's state vocabulary and routes against `SCREEN-SPECS.md`,
   `UI-SPECIFICATION.md`, and `PROTOTYPE-REVIEW.md`.
6. Assessed feasibility of the Python/Jinja2/loopback-service approach against the first-release scope.

## Machine-check result

| Check | Result |
|---|---|
| Schema validation of all authored content and fixtures | **0 errors** |
| Region / prerequisite / related-quest / track / badge references | **0 broken** |
| Prerequisite cycles | **none** |
| Duplicate proof IDs within a quest | **none** |
| Proof `validator` references present in the quest `validators` list | **0 mismatches** |
| Participant evidence paths present on disk | **0 missing** |
| `verified` attempt without a review reference | **none** |
| Canonical quest body headings present | **all three quests** |

Content inventory: 3 quests, 8 regions, 4 badges, 1 track, 1 participant fixture, 2 validation
results, 1 review record.

The design package is internally consistent. Every finding below is a **specification gap or
contradiction**, not a data defect.

## Findings

Severities follow `CLAUDE.md`: Blocking, High, Medium, Low.

### F1 — High — Acceptance criteria require stable IDs that no contract defines

**Evidence.** `docs/ui/COMPONENT-CATALOG.md` C10 requires "stable criterion IDs and rendered text".
`docs/VIEW-MODEL-CONTRACT.md` requires "acceptance criteria with stable IDs".
`templates/pages/quest-detail.html.j2` iterates `quest.acceptance_criteria` reading `criterion.dom_id`
and `criterion.text`. But `schemas/quest.schema.json` has no acceptance-criteria field, and
`docs/CONTENT-MODEL.md` places acceptance criteria in the Markdown body under `## Acceptance criteria`
while explicitly forbidding a second copy in front matter.

**Why it matters.** Reviewer decisions and evidence status attach to individual criteria. Without a
defined, stable derivation, a criterion's identity changes whenever an author reorders the list, and
prior review findings silently re-point at different text.

**Correction applied.** Recorded as **ADR-016**: acceptance criteria are parsed from the ordered list
under the `## Acceptance criteria` heading; each criterion receives the positional ID `ac-<n>`
(1-based) plus a `text_hash`. The positional ID is what the UI and reviewer records use; the
`text_hash` is what detects that a criterion's meaning changed under a stable ID, which the quest
`version` rule already requires an author to acknowledge. Loader emits a semantic error when the
heading is absent or holds no ordered list.

### F2 — High — The architecture state diagram contradicts the failure-handling requirement

**Evidence.** `docs/ARCHITECTURE.md` state diagram: `EvidenceReady --> InProgress: Validation fails`.
`docs/ui/SCREEN-SPECS.md` U06 failure state: "Preserve all work, identify which checks failed... Never
convert a validator failure directly into 'quest failed'." `docs/ACCESSIBILITY-AND-DESIGN.md`:
"Failure states preserve the participant's work."

**Why it matters.** An automatic backward transition on validator failure makes a registered validator
an authority over participant state, which `ADR-011` and the whole claimed-versus-verified model deny
it. It also destroys the `evidence_ready` assertion the participant deliberately made.

**Correction applied.** Recorded as **ADR-017**: a validation run never changes attempt state. It
appends a result record. `locally_validated` is reached only when the participant requests validation
and every required validator returns a qualifying outcome; a failing run leaves the attempt in its
current state and surfaces the findings. The reverse edge is removed from the implemented transition
table. `docs/ARCHITECTURE.md` retains the diagram as authored with a note pointing at ADR-017.

### F3 — Medium — Stored and derived states are presented as one list

**Evidence.** `docs/ui/UI-SPECIFICATION.md` lists eight "internal states" including `locked` and
`available`. `schemas/progress.schema.json` permits only six: `in_progress`, `evidence_ready`,
`locally_validated`, `submitted`, `needs_changes`, `verified`.

**Assessment.** The schema is right and the table is incomplete rather than wrong: `locked` and
`available` are computed from prerequisites and must never be writable. Left as-is in the
specification; the implementation marks the distinction explicitly through the `authority` field that
`docs/VIEW-MODEL-CONTRACT.md` already requires, and a test asserts the progress schema rejects a
written `locked`, `available`, or otherwise underivable state.

### F4 — Medium — The prototype does not demonstrate every state its own review checklist requires

**Evidence.** `docs/ui/PROTOTYPE-REVIEW.md` requires all eight quest states plus service-unavailable,
empty-filter, and validation-failure states. `prototype/data/prototype-data.js` contains only
`locked`, `available`, `in_progress`, `evidence_ready`, `needs_changes`, and `verified`.
`locally_validated` and `submitted` never appear.

**Assessment.** A prototype gap, not a specification defect. The two missing states are exactly the
ones that carry the claimed-versus-verified distinction, so they must be present in production.
Carried to Stage 6 as a required acceptance item; the production UI, not the prototype, is the object
the checklist is completed against.

### F5 — Medium — `content/glossary/` has no schema, no sample, and no consumer

**Evidence.** `docs/ARCHITECTURE.md` target tree lists `content/glossary/`.
`docs/CONTENT-MODEL.md` format-allocation table does not mention glossary content, no
`schemas/glossary.schema.json` exists, and no screen in `SCREEN-SPECS.md` renders one.

**Assessment.** Out of first-release scope. Entered in the deferred-work register rather than invented.
The build must not create an empty directory that implies an unimplemented feature.

### F6 — Medium — The participant root differs between the package and the production tree

**Evidence.** `docs/ARCHITECTURE.md` places participant files at `participant/` in the repository root.
The package ships them at `fixtures/participant/`. `schemas/progress.schema.json` pins
`evidence_path` to the literal prefix `participant/evidence/`, and
`schemas/validation-result.schema.json` pins `result_path` the same way.

**Why it matters.** With a hardcoded root, tests cannot exercise the real loader against the shipped
fixtures without writing into the participant's live directory.

**Correction applied.** Recorded as **ADR-018**: paths inside participant records stay
`participant/`-prefixed as the schemas require — that prefix is part of the contract and is not
relaxed. The *base directory* those paths resolve against is injected configuration
(`participant_root`), defaulting to `<repo>/participant` and set to `<repo>/fixtures/participant` in
tests. Every resolution is canonicalized and re-checked inside the configured root after following
symbolic links.

### F7 — Medium — Two contracts required by later stages do not exist

**Evidence.** Stage 5 requires a "validator registry with typed parameters" and Stage 7 requires a
"submission record". `docs/VALIDATOR-CONTRACT.md` gives a *conceptual* registry entry and explicitly
leaves storage format to implementation. No submission shape is specified anywhere.

**Correction applied.** Two schemas will be authored as part of their own stages —
`schemas/validator-registry.schema.json` in Stage 5 and `schemas/submission.schema.json` in Stage 7 —
following the field lists in `VALIDATOR-CONTRACT.md` and `IMPLEMENTATION-PLAN.md` Stage 7. Noted here
so the gap is not discovered as a surprise mid-stage.

### F8 — Low — `bookend` is schema-supported but undocumented in the content model

**Evidence.** `schemas/quest.schema.json` defines `bookend` with enum
`intent | validation | cross-bookend | foundation`. `docs/CONTENT-MODEL.md` lists neither a required
nor an optional field by that name, yet `docs/ui/SCREEN-SPECS.md` U04 requires a bookend filter and
`schemas/track.schema.json` defines `balance` minimums that can only be evaluated from it.

**Correction applied.** Documented in the content-authoring guide during Stage 9 and treated as
optional in the loader; a quest without `bookend` is reported as unclassified and excluded from
balance counts rather than silently defaulted.

### F9 — Low — Badge and region reachability warnings fire on the shipped sample content

**Evidence.** `golden-thread-keeper` requires `verified_quest_count: 8` and the tag `traceability`;
the package ships 3 quests and no quest carries that tag. Five of eight regions contain no quests.

**Assessment.** Correct and expected. `docs/ARCHITECTURE.md` requires exactly these as *warnings*
("unreachable quests, regions with no quests, badges with impossible criteria"). They confirm the
requirement is real and testable. The build must warn and continue, never fail.

## Feasibility assessment

The Python + Jinja2 + loopback-service approach satisfies the first-release scope. Three points
carried into implementation:

1. **Determinism** is achievable but not free. Sorted content discovery, sorted mapping output, and a
   build manifest that isolates the one genuinely varying value (build time) are required from
   Stage 3, not retrofitted.
2. **The no-JavaScript requirement constrains filtering.** Catalog filters must work as ordinary form
   submissions against generated query-string-addressable pages, with JavaScript upgrading them to
   client-side filtering. Building client-only filters first would make the requirement unreachable.
3. **Validator sandboxing is policy, not a library.** The contract's guarantees (argument arrays, no
   shell, explicit roots, environment allowlist, timeout, process-tree kill, output cap, redaction)
   are all implementable with `subprocess` and `os` primitives on Linux. Stronger isolation
   (containers, seccomp) stays a documented future option, as `SECURITY-AND-PRIVACY.md` allows.

## Deferred implementation choices — decided

Recorded in `docs/DECISIONS.md` as ADR-019 through ADR-025.

| Choice | Decision | Reason |
|---|---|---|
| Python | `>=3.12`, developed on 3.14 | Plan requires 3.12+; no 3.13/3.14-only syntax is used |
| Schema validation | `jsonschema` (Draft 2020-12) directly, plus frozen dataclasses | The published schemas are already the contract; Pydantic would create a second, divergent one |
| Markdown | `markdown-it-py` (CommonMark) with raw HTML disabled | CommonMark compliance is the stated requirement |
| Sanitization | `nh3` allowlist over the rendered HTML | Explicit allowlist, maintained, independent of the renderer's own escaping |
| Local service | Python standard library `ThreadingHTTPServer` | Every service requirement is a restriction; a framework adds dependencies and hides the request surface being restricted |
| Tests | `pytest`, plus Playwright for UI and axe-core for accessibility | Named in the plan |
| Format / lint / types | `ruff format`, `ruff check`, `mypy --strict` | One tool for format and lint; strict typing on a small codebase |
| YAML | `PyYAML` `safe_load` only | `safe_load` is the stated safety requirement |

## Audit gate

- [x] No unresolved blocking finding.
- [x] No unresolved high-severity contradiction — F1 and F2 resolved as ADR-016 and ADR-017.
- [x] Every deferred implementation choice has a decision recorded in `docs/DECISIONS.md`.
- [x] The prototype and written specification agree on primary behavior; the one divergence (F4) is
      carried to Stage 6 with an explicit acceptance item.
- [x] Rerun result: `pass-with-advisories`.

## Carried forward

| ID | Carried to | Item |
|---|---|---|
| F4 | Stage 6 | Production UI must render `locally_validated` and `submitted` states |
| F5 | Deferred register | Glossary content type |
| F7 | Stages 5 and 7 | Validator-registry and submission schemas |
| F8 | Stage 9 | Document `bookend` in the authoring guide |
| F9 | Stage 2 | Reachability warnings must warn and continue, with tests |
