# Templates

Production Jinja2 templates. They receive normalized view models from `quest_app.view_models`
and nothing else.

## Layout

- `layouts/base.html.j2` — the application shell (C01): landmarks, skip link, navigation,
  participant summary, service status, footer.
- `components/` — the reusable component macros from `docs/ui/COMPONENT-CATALOG.md`.
- `pages/` — one template per screen in `docs/ui/SCREEN-SPECS.md`.

## Rules

- Templates receive route-ready, display-ready view models. They never open a file, parse
  front matter, calculate progress, resolve prerequisites, inspect Git, decide authority,
  run a validator or infer a route.
- Autoescaping is on. Rendered Markdown arrives already sanitized, in a field named
  `safe_rendered_html` so it cannot be confused with text that still needs escaping.
- No quest-specific text or business rule appears in a template. The only content-derived
  hooks are the generic `accent-*` and `state-*` classes the view model supplies, which is
  what makes "add a quest without touching UI code" true.
- URLs come from the `url()` helper, which resolves a route relative to the current page so
  the generated site works both served and opened from disk.
- Shared components own the state and authority labels, so "Locally validated" never
  becomes "Verified" on one page and not another.

## History

This directory originally held three illustrative contract files
(`components/quest-card.html.j2`, `components/app-navigation.html.j2`,
`pages/quest-detail.html.j2`). They were design contracts for the implementation agent, not
a theme, and they were removed in Stage 3 once the production templates existed — two files
named `quest-card` and `quest_card` in one directory is a trap for the next maintainer. The
contracts they expressed are the rules above, and the Git history still holds them.
