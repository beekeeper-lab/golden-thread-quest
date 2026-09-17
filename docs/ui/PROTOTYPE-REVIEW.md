# Prototype Review Checklist

Use this before implementation and after material UI changes.

## Information architecture

- [ ] Home answers “what should I do next?”
- [ ] The map communicates the full journey without relying on drawn connecting lines.
- [ ] Quest detail separates mission, criteria, proof, and safety.
- [ ] Evidence and reviewer views share terminology but different authority.
- [ ] Passport communicates demonstrated capability rather than only points.

## Content separation

- [ ] Fixture content is outside `prototype/index.html`.
- [ ] Screens are rendered from stable IDs and structured data.
- [ ] No quest title, region list, XP rule, or badge rule is embedded in the rendering logic.
- [ ] The same quest record can appear on Home, Map, Catalog, Evidence, and Review without duplication.

## States

- [ ] Locked
- [ ] Available
- [ ] In progress
- [ ] Evidence ready
- [ ] Locally validated
- [ ] Submitted
- [ ] Needs changes
- [ ] Verified
- [ ] Service unavailable
- [ ] Empty filter result
- [ ] Validation failure

## Visual and responsive

- [ ] Professional field-guide direction is clear but restrained.
- [ ] Claimed and verified metrics are visually distinct.
- [ ] Main content is readable at normal laptop width.
- [ ] Navigation works at narrow widths.
- [ ] No horizontal page scrolling at 390 pixels.
- [ ] Dense review data remains understandable.

## Accessibility

- [ ] Skip link works.
- [ ] Keyboard focus is always visible.
- [ ] Hash navigation moves focus or announces screen changes appropriately.
- [ ] Buttons and links have clear accessible names.
- [ ] Status is not communicated by color alone.
- [ ] Reduced motion is respected.
- [ ] Form controls have labels.
- [ ] Contrast meets target.

## Outcome

- Reviewer:
- Date:
- Result: `pass`, `pass-with-advisories`, or `fail`
- Blocking findings:
- Advisory findings:
- Approved deviations:
