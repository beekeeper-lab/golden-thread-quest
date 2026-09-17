# Component Catalog

Every production component must use normalized view-model data. The component name describes a reusable concept, not a specific quest.

## C01 — App Shell

**Purpose:** Provide global landmarks, navigation, responsive behavior, and application status.

**Required states:** default, navigation expanded, navigation collapsed, service unavailable.

**Accessibility:** skip link, semantic landmarks, current page, focus return from mobile drawer.

## C02 — Participant Summary

**Purpose:** Identify the participant, current track, claimed XP, and verified XP.

**Variants:** compact navigation version; full passport version.

**Rule:** Never combine claimed and verified XP into an unlabeled single total.

## C03 — Progress Meter

**Purpose:** Show completion toward a defined total.

**Inputs:** value, maximum, label, verification authority, optional secondary value.

**Accessibility:** exposes readable value and maximum; text remains available without color.

## C04 — Region Card

**Purpose:** Summarize a curriculum region.

**Inputs:** title, summary, outcomes, accent token, quest counts by state, claimed and verified progress, route.

**States:** untouched, active, completed, unavailable by track policy.

## C05 — Quest Card

**Purpose:** Support scanning, comparison, and selection.

**Inputs:** title, summary, state, region, level, XP, estimate, tags, prerequisites summary, recommendation reasons.

**Variants:** standard, compact list, recommended.

**Rule:** The whole card may be visually grouped, but nested controls must remain valid and keyboard-usable.

## C06 — State Badge

**Purpose:** Communicate one canonical quest state.

**Inputs:** state, display label, authority, timestamp where useful.

**Accessibility:** icon and text accompany color.

## C07 — Tag Chip

**Purpose:** Display or manipulate a tag/filter.

**Variants:** informational, removable filter, selectable filter.

**Rule:** Do not make informational tags keyboard-focusable.

## C08 — Recommendation Panel

**Purpose:** Present the recommended next quest and transparent rationale.

**Inputs:** quest summary, availability, primary action, at least three rationale strings, alternative route.

**States:** recommendation available, environment blocked, no eligible quest, track complete.

## C09 — Prerequisite List

**Purpose:** Explain readiness and locks.

**Inputs:** prerequisite quest ID/title/state/route, satisfaction rule.

**Rule:** Unmet prerequisites are links and provide a resolution path.

## C10 — Acceptance Criteria List

**Purpose:** Present evaluation expectations clearly.

**Inputs:** stable criterion IDs and rendered text.

**Variants:** participant view, evidence-status view, reviewer decision view.

## C11 — Proof Requirement

**Purpose:** Connect a proof rule with current detected evidence.

**Inputs:** proof ID/type/description/required flag/status/artifact reference/validator reference.

**States:** missing, detected, warning, validated, reviewer-confirmed, stale.

## C12 — Validator Action

**Purpose:** Run an allowlisted validator and display its latest status.

**Inputs:** validator ID, display name, last result, eligibility, estimated behavior.

**States:** ready, running, passed, failed, warning, timed out, inconclusive, unavailable.

**Rule:** Never accept or display an editable raw command string.

## C13 — Validation Finding

**Purpose:** Explain one check outcome.

**Inputs:** severity, classification, summary, evidence, suggested action, affected artifact.

**Accessibility:** structured heading and severity text; expandable detail uses proper disclosure semantics.

## C14 — Environment Check

**Purpose:** Display readiness of one dependency or safety condition.

**Inputs:** name, importance, status, detected version/value, remediation.

**States:** pass, warning, fail, optional, unknown.

## C15 — Badge Tile

**Purpose:** Explain an achievement and its authority.

**Inputs:** name, description, icon token, award type, state, criteria progress, award record.

**States:** locked, in progress, pending review, earned.

## C16 — Activity Timeline

**Purpose:** Present quest, validation, submission, and review events.

**Inputs:** event type, actor/authority, time, summary, related route.

**Rule:** Sort consistently and preserve full timestamps for auditability.

## C17 — Alert

**Purpose:** Communicate contextual information, warning, failure, or success.

**Variants:** information, success, warning, error.

**Rule:** Critical errors persist. Success alerts do not receive assertive live-region behavior.

## C18 — Review Decision Form

**Purpose:** Capture reviewer approval, needs-changes, or rejection.

**Inputs:** decision, verification statement, findings, reviewer identity, attempt/content identity.

**Guards:** approval confirmation; needs-changes requires a finding; changed evidence blocks approval until acknowledged.

## C19 — Git Status Summary

**Purpose:** Show branch, upstream, changed files, untracked files, and whether evidence is committed.

**Rule:** This component reports and advises. It must not silently commit, push, merge, or clean files.

## C20 — Empty State

**Purpose:** Explain why content is absent and what the user can do.

**Variants:** new participant, no filter results, no evidence, no review submissions, service unavailable.

## C21 — Confirmation Dialog

**Purpose:** Confirm a consequential local or external operation.

**Requirements:** exact target, summary of changes, reversibility, explicit confirm label, safe default focus, cancel support.

**Rule:** External write confirmation occurs immediately before the write, not at the beginning of a multi-step workflow.

## C22 — Build/Error Report

**Purpose:** Present content and generation errors to maintainers.

**Inputs:** filename, field path, line when available, error code, message, expected rule, suggested correction.

**States:** error list, warning list, clean build.

## Cross-component requirements

- Every component has an intentional empty state.
- Components render safely with long titles and translated-length text.
- Components never rely on hover for required information.
- IDs, status labels, route fragments, and raw timestamps use shared helpers.
- Dates are stored in ISO 8601 and displayed in the user's local time with access to the original value.
- Icons are decorative unless they communicate status; status icons have accessible text.
