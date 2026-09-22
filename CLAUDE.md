# Claude Code Operating Instructions

## Mission

Build the local-first Golden Thread Quest application described in this repository. Preserve the boundary between authored curriculum, presentation templates, participant work, and machine-generated output.

Do not reinterpret this as a generic learning-management system or a hosted SaaS application.

## Mandatory working rules

1. **Never implement directly on `main`.** Create a descriptive feature branch before modifying production files.
2. **Land your own work.** Commit, push, open the pull request, and merge it to `main` when the stage's audit passes. On this repository the merge is yours to make and does not need to be asked for. Merging an unfinished round is still wrong, but that is a question of readiness, not of permission.
3. Treat this repository as a planning package until the Stage 0 audit passes.
4. Follow `docs/IMPLEMENTATION-PLAN.md` in order.
5. Work on only one stage at a time.
6. Update the checkboxes and stage log as work is completed.
7. At the end of every stage, perform the required audit using a fresh review context or review subagent when available.
8. Record audit findings in `docs/audits/stage-NN-*.md`.
9. Fix every blocking and high-severity finding before starting the next stage.
10. Rerun the audit after fixes and record the result.
11. Do not mark an item complete merely because code exists; its acceptance criteria and tests must pass.
12. Preserve user-authored files and unrelated repository changes.
13. Never weaken validation, tests, or security controls to make a stage pass.

## Required reading order

1. `PLANNING-STATUS.md`
2. `docs/PRODUCT-BRIEF.md`
3. `docs/DECISIONS.md`
4. `docs/ARCHITECTURE.md`
5. `docs/CONTENT-MODEL.md`
6. `docs/ui/UI-SPECIFICATION.md`
7. `docs/ui/SCREEN-SPECS.md`
8. `docs/ui/COMPONENT-CATALOG.md`
9. `docs/SECURITY-AND-PRIVACY.md`
11. `docs/ACCESSIBILITY-AND-DESIGN.md`
12. `docs/ACCEPTANCE-CRITERIA.md`
13. `docs/IMPLEMENTATION-PLAN.md`

Then inspect the schemas, sample content, fixtures, and prototype.

## Non-negotiable architecture rules

- Program-authored content is stored in Markdown and YAML.
- JSON Schema validates authored and state data before rendering.
- Stable IDs—not filenames or titles—connect records.
- Python creates normalized view models and renders Jinja2 HTML.
- Templates contain no quest-specific content.
- Adding valid quest content automatically updates indexes, navigation, filters, and search.
- The browser cannot execute arbitrary commands or access arbitrary filesystem paths.
- Local write operations are allowlisted and constrained to participant-owned locations.
- External-system writes are previewed and require explicit human confirmation.
- Claimed, locally validated, submitted, needs-changes, and verified states remain distinct.
- Only reviewer approval may produce verified completion or verified XP.
- Generated files are reproducible and disposable.

## Prototype policy

The files under `prototype/` are the approved visual and interaction reference. They are not the production implementation and should not be copied wholesale without review.

Production pages must preserve the prototype's:

- information hierarchy;
- component vocabulary;
- professional field-guide tone;
- verified-versus-claimed distinction;
- core navigation;
- responsive and accessible behavior.

Reasonable visual improvements are allowed if they are documented and do not change the product requirements.

## Stage audit method

For every stage:

1. Review the stage goal and acceptance criteria.
3. Inspect all changed files and the Git diff.
4. Run the relevant automated tests and validators.
5. Test the stage's primary user flows.
6. Review accessibility, security, failure behavior, and documentation impact.
7. List findings with severity, evidence, and recommended correction.
8. Fix findings.
9. Rerun affected tests and the audit.
10. Check off the stage only after the audit passes.

Use the following severities:

- **Blocking:** unsafe, data-loss risk, architecture violation, or core flow unusable.
- **High:** material requirement failure or likely participant/reviewer confusion.
- **Medium:** quality, maintainability, accessibility, or resilience weakness.
- **Low:** polish or nonessential improvement.

## Completion deliverables

Before proposing a pull request, create:

- `docs/IMPLEMENTATION-DETAILS.md` describing what was actually built;
- `docs/TRACEABILITY.md` mapping product requirements to implementation and tests;
- `docs/audits/final-audit.md` comparing the specification, implementation, tests, and implementation-details document;
- a clear list of deferred work and known limitations.

The implementation is not complete until another developer can clone it, follow the setup instructions, run the application, add a sample quest without editing UI code, validate evidence, and reproduce the test results.
