# Stage 6 — Participant UI and Interaction Polish Audit

**Audited commits:** `9502ab3`, re-checked at `128617e`
**Auditor:** independent review agent, fresh context, read-only, 105 tool calls, real browser
**Result:** `fail` — 1 blocking, 2 high, 3 medium, 1 low
**Status after fixes:** every finding closed; the blind spot that hid the high finding is closed too.

## The finding that matters most

**F3 — the evidence workspace scrolled sideways by 179px at phone width and 246px at 200%
zoom, and the test suite could not see it.** `test_no_horizontal_scrolling` checked four
hand-picked routes; the evidence workspace was not one of them. `test_usable_at_two_hundred_percent_zoom`
checked one.

This is the same shape as the defects the final release audit found: **a check that covers a
chosen subset will miss whatever is outside the subset, and the subset is chosen by the
person least likely to know what is missing.** Both responsive tests now run over the same
`AUDITED_PAGES` list the accessibility audit uses, so adding a page adds it to all three.

**Cause.** A CSS grid's implicit track and a flex item both size to max-content and refuse to
shrink. A long proof description and a repository path in a `<code>` element — which has no
break opportunity at all — pushed the page wider than the viewport. Fixed with explicit
`minmax(0, …)` tracks, `min-width: 0` on flex containers and their children, and
`overflow-wrap: anywhere` where content is a path.

## Findings and resolutions

| ID | Severity | Finding | Resolution |
|---|---|---|---|
| F1 | Blocking | No state-changing action was reachable through the UI: zero POST forms, every action hard-coded disabled, because `build_site` always used `offline_service_view()` — including when the running service built the page | Closed as B2 of the final audit |
| F2 | High | axe `color-contrast`, **serious, on all twelve pages**: sidebar labels at 2.58:1 | Closed by the inverse colour tokens; re-run gives zero serious or critical findings |
| F3 | High | Evidence workspace overflowed at 390px and 200% zoom, invisible to the suite | Fixed; both responsive tests now cover every audited page |
| F4 | Medium | All eight states render, but four appear only as legend text — no fixture and no test put a real quest in them | `tests/ui/test_states.py`: every storable state, plus locked, needs-changes, failed validation and service-unavailable |
| F5 | Medium | `role="alert"` — assertive — on five statically rendered blocks, so some screen readers interrupt on load | All changed to `role="status"`; `alert` is reserved for script-injected urgent messages |
| F6 | Medium | `/health/` offered a scroll container with no `tabindex` and no accessible name, so a keyboard user could not scroll it | Every `.table-scroll` is focusable, has `role="region"` and a label, with a visible focus ring; asserted by test |
| F7 | Low | Two `<section>` landmarks on a quest page both labelled "Required evidence" | The proof-list macro takes a slug, so the two sections have distinct anchors |
| — | Low | `routes.catalog_filtered()` had no caller; `__import__` in the build manifest | Both wired and removed |

## Also corrected

**The keyboard journey test used a mouse.** `test_the_primary_journey_is_reachable_by_keyboard`
called `.click()` and stopped at a region page, despite a docstring promising the evidence
workspace. Every step is now a real key press, focus is asserted before each one, and the
journey ends where the docstring says.

**A commit message overstated the browser coverage** — "29 in a browser" when thirteen drove
a browser and sixteen parsed static HTML. Recorded here because an inflated number in a
commit message is the kind of thing that later gets quoted as evidence.

## Confirmed sound

Keyboard: the drawer opens on Enter, Escape closes it and returns focus to the toggle, and
**zero** focusable elements lack a focus indicator. Responsive at 1440×900, 1280×720 and
768×1024 across every route. No-JavaScript: every page renders its heading, navigation and
content, and the sidebar is visible without script. Hover: no essential workflow depends on
it — every `:hover` rule changes colour or underline only, nothing toggles visibility, and no
page uses `title` as its only source of information.

## Sub-finding accepted as-is

Quest-state CSS classes are reused for non-state meanings: `state-locally_validated` labels a
validator outcome, and `state-locked` labels an undetected proof item. The auditor is right
that this cuts against the verified-versus-claimed discipline. It is cosmetic reuse of a
class name rather than a claim in the interface — the labels beside them read "pass" and "Not
detected" — and it is recorded here rather than changed, so the next person to touch the
stylesheet knows it was noticed.

## Gate

- [x] `docs/ui/PROTOTYPE-REVIEW.md` completed against the production UI (see that file).
- [x] Text, states, authority labels and actions compared to specification.
- [x] Responsive behaviour and keyboard flow reviewed in a real browser.
- [x] Findings fixed and re-verified: 467 tests plus 42 browser-driven.
