# Prototype Review Checklist

Use this before implementation and after material UI changes.

## Information architecture

- [x] Home answers “what should I do next?”
- [x] The map communicates the full journey without relying on drawn connecting lines.
- [x] Quest detail separates mission, criteria, proof, and safety.
- [x] Evidence and reviewer views share terminology but different authority.
- [x] Passport communicates demonstrated capability rather than only points.

## Content separation

- [x] Fixture content is outside `prototype/index.html`.
- [x] Screens are rendered from stable IDs and structured data.
- [x] No quest title, region list, XP rule, or badge rule is embedded in the rendering logic.
- [x] The same quest record can appear on Home, Map, Catalog, Evidence, and Review without duplication.

## States

- [x] Locked
- [x] Available
- [x] In progress
- [x] Evidence ready
- [x] Locally validated
- [x] Submitted
- [x] Needs changes
- [x] Verified
- [x] Service unavailable
- [x] Empty filter result
- [x] Validation failure

## Visual and responsive

- [x] Professional field-guide direction is clear but restrained.
- [x] Claimed and verified metrics are visually distinct.
- [x] Main content is readable at normal laptop width.
- [x] Navigation works at narrow widths.
- [x] No horizontal page scrolling at 390 pixels.
- [x] Dense review data remains understandable.

## Accessibility

- [x] Skip link works.
- [x] Keyboard focus is always visible.
- [x] Hash navigation moves focus or announces screen changes appropriately.
- [x] Buttons and links have clear accessible names.
- [x] Status is not communicated by color alone.
- [x] Reduced motion is respected.
- [x] Form controls have labels.
- [x] Contrast meets target.

## Outcome

Completed against the **production UI**, not the prototype — `prototype/README.md` is explicit
that the prototype is a design reference and the production pages are what must satisfy this.

- **Reviewer:** independent review agent (Stage 6 audit) plus the implementation, re-verified
  in a real browser after fixes
- **Date:** 2026-09-17
- **Result:** `pass-with-advisories`
- **Blocking findings:** one, now closed — no state-changing action was reachable through the
  UI at all (recorded as F1 here and B2 in the final release audit)
- **Advisory findings:** quest-state CSS class names are reused for validator outcomes and
  proof-detection status; the labels beside them are correct, but the reuse is worth removing
  the next time the stylesheet is touched
- **Approved deviations:**
  - Catalog filtering requires JavaScript. A static page cannot filter itself; the
    scripting-free routes are real generated pages — regions and tags — linked from every card
    and every quest.
  - Environment Health reports what was true at build time and labels itself as such. Live
    checks are deferred (D7).
  - Two prototype colors were darkened and two inverse tokens added, to meet WCAG 2.2 AA.
    Documented in `docs/audits/stage-06-ui-audit.md`.

Every state in the list above is exercised by `tests/ui/test_states.py` rather than inspected
once, so this review does not have to be repeated by hand to stay true.
