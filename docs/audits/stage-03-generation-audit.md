# Stage 3 — Deterministic Site Generation Audit

**Audited commit:** `264de55` (the tree advanced to `dce4edf` while the audit ran; the auditor
pinned to the requested commit with `git archive` and ran every probe there)
**Auditor:** independent review agent, fresh context, read-only, 74 tool calls
**Result:** `fail` — 1 blocking, 4 high, 8 medium, 5 low
**Status (2026-09-17):** every finding fixed, each with a regression test, and verified by an independent re-audit that recorded `pass with residuals`. See the resolution log at the end of this file.

Two findings are already closed at `dce4edf`, verified at HEAD and marked below. Everything
else is open.

## What passed

Worth stating, because it bounds the work: the generation engine itself is sound.

- **Escaping.** `select_autoescape(default_for_string=True, default=True)` plus
  `StrictUndefined`. Exactly three `| safe` uses, all on nh3-sanitized values whose field
  names say so. No template interpolates into an attribute or URL context unescaped.
- **Sanitization.** Allowlisted tags, attributes and schemes; `link_rel` set by nh3 with
  `rel` deliberately excluded from author-supplied attributes so content cannot drop
  `noopener`; `<img>` excluded; `ftp://` stripped.
- **Determinism.** Two builds differ only in `built_at`. Every index is written with sorted
  keys; sets are used for membership only and never iterated into output; `datetime.now(UTC)`
  is the single, injectable time source.
- **Atomic swap.** Rendering completes before the rename, so a mid-render failure leaves the
  published site untouched.
- **Empty participant.** Building against an empty directory succeeds with no crash and no
  divide-by-zero.
- **Accessibility.** Skip-link target focusable, `aria-current` on every page, every control
  labelled, tables captioned with scopes, status never colour-only. The meter's
  `role="img"` plus `aria-label` is the right choice over `progressbar`, which can expose
  only one value and would collapse the claimed-versus-verified distinction.

## Blocking

### S3-B1 — A template hard-codes curriculum content, and the guarding test cannot see it

`templates/pages/home.html.j2:38-39` contains `'Start at Base Camp'` and editorial copy
naming Base Camp. That is the `title` of `content/regions/base-camp.yaml`, and it breaks the
`CLAUDE.md` non-negotiable "Templates contain no quest-specific content". Any program whose
first region is not Base Camp gets a wrong new-participant empty state and no error.

Worse than the violation is why it survived: `tests/unit/test_templates_are_generic.py`
collects only quest IDs, quest titles and badge titles. It never reads `content/regions/`,
`content/tracks/` or `content/site.yaml`, so region titles, track titles and tag names are
invisible to it. Writing `<h1>Golden Thread Foundations</h1>` into a template passes the
suite today, while the test's own docstring claims it is "the mechanical half" of the
add-content-without-code promise.

**Correction:** derive the empty state from `bundle.ordered_regions()[0]`, and extend
`content_identifiers()` to region titles, track titles and site fields. Fix the test first,
watch it fail, then fix the template.

## High

### S3-H1 — The Content Security Policy blocks the application's own styles

`style-src 'self'` with no `'unsafe-inline'`, while `meter.html.j2` emits
`style="width: …%"`. Inline style *attributes* fall under `style-src-attr`, which falls back
to `style-src`, so every progress meter on home, map, region and passport renders with a
zero-width fill.

On `file://` it is worse: the document origin is opaque, `'self'` matches nothing, and the
stylesheet and script are blocked outright — an unstyled, script-less page. `docs/SETUP.md`
and `tests/integration/test_build.py` both assert that opening from disk works, and the
template comment claims the policy is what makes it work.

**Correction:** move the widths into a generated stylesheet as custom properties or a
class-based step scale, then either relax the policy to something that functions on
`file://` or state in the documentation that disk-opening needs the local service. Verify in
a real browser before closing; the auditor could not run one.

### S3-H2 — Catalog filtering does not work without JavaScript, and the template says it does

`catalog.html.j2` claims filtering "works with JavaScript disabled by reloading with a query
string". Nothing reads `location.search`: the build passes `"selected": {}` and the page is
static, so submitting the form reloads and shows everything with the selects reset.

That makes `quest_detail.html.j2`'s `?tag=…` links dead, and `app.js` then calls
`history.replaceState` on the first `apply()`, rewriting the URL to the bare pathname so the
user cannot even see what was ignored. Two more defects in the same place:
`routes.catalog_filtered()` exists for exactly this and has no caller, so the template
hand-builds an unencoded query string; and `replaceState` throws `SecurityError` on a
`file://` page, so every keystroke ends in an uncaught exception.

The `tag` filter logic itself is correct, and `replaceState` rather than `pushState` does not
break the back button.

**Correction:** read `URLSearchParams(location.search)` and prime the form before the first
`apply()`; use `routes.catalog_filtered()`; wrap `replaceState` in `try/catch`.

### S3-H3 — Four required screen sections are missing

- **U03 Region:** no filter UI at all.
- **U04 Catalog:** no active-filter chips (C07's removable variant is unimplemented), no
  estimated-time filter, and no sort control.

### S3-H4 — An `<h2>` before the `<h1>` on all 23 pages — **fixed at `dce4edf`**

The offline alert rendered a heading above `{% block main %}`. Closed independently by the
Stage 6 accessibility work, which found the same defect and made the alert a paragraph.
Verified at HEAD: no heading remains in that alert.

## Medium

| ID | Finding |
|---|---|
| S2-R1 | A list inside a **blockquote** is treated as the first list, so a quoted example silently becomes the acceptance criteria — the exact failure ADR-016 exists to prevent. Refuse to open the first list inside `blockquote_open` |
| S3-M1 | `pages/content_error.html.j2` (U11/C22) has no producer: `build_site` never renders it and `routes.ERRORS` is unused. The screen exists in source, unreachable and untested |
| S3-M2 | C21 Confirmation is `window.confirm` and JavaScript-only. Its Rule is honoured — bound to submit, immediately before the write — but with JS off the form posts with no confirmation, for the one component whose entire purpose is a safety gate. Must not reach the live service in this shape |
| S3-M3 | Acceptance criteria render as plain text, so inline Markdown leaks through as literal asterisks and backticks. `render_inline()` is the right tool and has no caller |
| S3-M4 | U09 Environment Health covers five of eight required sections. The deferral is deliberate and explained in the code, but is not in the deferred-work register |
| S3-M5 | U10 Reviewer: no redaction status, no submission identity, the findings editor is one text input, and `verification_statement` is not `required` client-side |
| S3-M6 | U06: no validator run control, and `proof_document`, `secret_scan_clean` and `git_summary` were hard-coded empty (the latter two are wired at `dce4edf`). U07: findings are not ordered by severity and there is no rerun action |
| S3-M7 | C15 badge tile and C16 activity timeline are copy-pasted inline in two templates each, and the two badge copies already differ. Also unimplemented: C04 region-card states, C05 compact list, C07 removable filter, C08 blocked and complete states, C10 evidence-status variant |
| S3-M8 | `test_a_failed_build_leaves_the_previous_site_intact` never calls `build_site`. The atomic swap is exercised only by the happy path |

## Low

`build.py`'s manifest uses `world.config and __import__(...)` where a module-level import is
meant; the external-write notice has no `role` while the alerts above it do; the drawer has
no focus trap (acceptable — it is `display: none` when closed and Escape restores focus);
`empty_criterion` fires for an item whose only block is a code fence and the suggestion
mentions only paragraphs; every Stage 3 checkbox is unticked.

One further gap the auditor found in the empty-participant path: with no participant, home
drops the "Your progress" section entirely, so U01's required claimed-versus-verified
progress is absent for exactly the user U01's empty state is written for. Passport handles
the same case by showing zeros.

## Required before Stage 3 is complete

1. S3-B1 — fix the test first, then the template.
2. S3-H1 — remove inline style attributes; settle the `file://` policy question in a browser.
3. S3-H2 — make no-JavaScript filtering real or stop claiming it; wire `catalog_filtered()`.
4. S3-H3 — add the missing U03 and U04 sections.
5. S2-R1 and S3-M1 through S3-M8.
6. Rerun this audit and record the result.
