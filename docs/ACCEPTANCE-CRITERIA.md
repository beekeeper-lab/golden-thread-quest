# Release Acceptance Criteria

## Content and generation

- [ ] All authored content validates against versioned schemas.
- [ ] Cross-document validation detects duplicate IDs, broken references, and prerequisite cycles.
- [ ] A maintainer can add a quest without editing Python, Jinja2, JavaScript, or CSS.
- [ ] A valid new quest automatically appears in its region, catalog, filters, search, and prerequisite graph.
- [ ] Invalid content prevents publication and produces an actionable error.
- [ ] Generated output is deterministic for equivalent inputs, excluding documented build metadata.
- [ ] A failed build preserves the last known valid output.

## Participant experience

- [ ] A participant can see overall progress and a reasoned next-quest recommendation.
- [ ] A participant can browse all regions and filter the catalog.
- [ ] A quest page communicates mission, outcomes, prerequisites, acceptance criteria, safety, proof, validators, XP, and estimate.
- [ ] Starting a quest persists state outside browser storage.
- [ ] Restarting the application restores the same state.
- [ ] The evidence workspace can create and display a standard proof package.
- [ ] Validation results distinguish pass, fail, warning, environment failure, and inconclusive.
- [ ] Claimed and verified progress are visibly distinct.

## Reviewer experience

- [ ] A reviewer can see the exact quest version and attempt being reviewed.
- [ ] A reviewer can inspect required proof and linked artifacts.
- [ ] A reviewer can see validator results and reproduction instructions.
- [ ] A reviewer can approve, request changes, or reject with findings.
- [ ] Only approval changes the attempt to verified.
- [ ] Evidence changes after approval can be detected and surfaced.

## Filesystem and Git safety

- [ ] Program updates do not overwrite participant-owned files.
- [ ] Local actions cannot write outside approved roots.
- [ ] Symbolic-link and traversal tests pass.
- [ ] Generated and local runtime data are Gitignored.
- [ ] Secrets are excluded from logs and submission preparation.
- [ ] Git status is shown before actions that prepare submissions.

## Validator safety

- [ ] Only registered validators can run.
- [ ] Validator arguments are typed and allowlisted.
- [ ] No caller-provided shell command is executed.
- [ ] Timeout, output limits, and interrupted execution are handled.
- [ ] A validator cannot mark work reviewer-verified.
- [ ] Validation results use the published result schema.

## UI and accessibility

- [ ] All required screens and component states are implemented.
- [ ] Primary navigation works with keyboard only.
- [ ] Visible focus and skip navigation are provided.
- [ ] Status is not expressed by color alone.
- [ ] Key text and graphical elements meet WCAG 2.2 AA contrast.
- [ ] Pages remain usable at 200% zoom and 390-pixel viewport width.
- [ ] Motion honors reduced-motion preference.
- [ ] Automated accessibility checks pass with no serious or critical findings.

## Documentation and handoff

- [ ] Setup instructions work from a clean clone.
- [ ] Content-authoring instructions include a full quest example.
- [ ] Validator-authoring instructions describe the safety boundary.
- [ ] Update and migration behavior is documented.
- [ ] `docs/IMPLEMENTATION-DETAILS.md` describes actual implementation, not planned behavior.
- [ ] `docs/TRACEABILITY.md` connects these criteria to code and tests.
- [ ] Final audit reports no unresolved blocking or high findings.
