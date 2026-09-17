# Accessibility and Visual Design

## Visual direction

The interface should feel like a professional expedition field guide rather than a cartoon game.

Use:

- a dark ink or deep navy foundation;
- warm parchment or soft neutral surfaces;
- restrained amber/gold for progress and verified achievement;
- muted region accent colors;
- precise typography and generous spacing;
- map, compass, thread, and waypoint motifs used sparingly;
- clear status labels and evidence-focused language.

Avoid:

- fantasy fonts for body text;
- excessive animation;
- noisy textures behind content;
- bright colors as the only status distinction;
- ambiguous game terminology where professional language is clearer;
- competitive leaderboards that reward speed over quality.

## Design tokens

Production CSS must define tokens for:

- background, surface, elevated surface, border, and text colors;
- primary, accent, success, warning, danger, and information colors;
- region accent slots;
- spacing scale;
- type scale and line heights;
- border radii;
- shadows;
- content widths;
- animation durations;
- focus-ring treatment;
- status colors and icons.

Components consume tokens rather than literal values wherever practical.

## Accessibility target

Target WCAG 2.2 AA for the generated application.

Minimum requirements:

- Semantic landmarks and heading hierarchy.
- Full keyboard access with visible focus.
- Skip link to primary content.
- AA text and essential graphical contrast.
- Status communicated by text/icon as well as color.
- Form labels, descriptions, and error associations.
- Current navigation indicated programmatically.
- Dialogs, drawers, and menus have correct focus management.
- Motion respects `prefers-reduced-motion`.
- Layout remains usable at 200% zoom.
- Interactive controls meet reasonable target-size guidance.
- Validation output can be understood by assistive technology.
- Tables have appropriate headers and responsive alternatives.

## Responsive behavior

Design desktop-first because participants will normally build in a desktop development environment, but support narrow viewports for reference.

### Wide desktop

- Persistent left navigation.
- Main content and contextual right rail when useful.
- Quest map uses a multi-column region layout.

### Standard laptop

- Persistent or collapsible left navigation.
- Right-rail content moves inline when space is constrained.

### Narrow/mobile

- Navigation becomes an accessible disclosure or drawer.
- Cards use a single column.
- Tables become scrollable with visible labels or use stacked rows.
- Primary actions remain reachable without horizontal page scrolling.

## Interaction principles

- The page title and current state appear near the top.
- The next safe action is visually clear.
- Destructive or externally mutating actions are never styled as ordinary navigation.
- Validation reports lead with summary, then findings, then raw detail.
- Locked content explains why it is locked and what unlocks it.
- “Verified” always identifies the verifying authority and time.
- Empty states explain how data becomes available.
- Failure states preserve the participant's work and offer recovery steps.

## Animation

Use animation only for orientation:

- opening navigation or drawers;
- progress changes;
- revealing validation details;
- acknowledging a successful state transition.

No important content should depend on animation. Avoid autoplay celebration sequences. Disable or reduce effects under reduced-motion preferences.

## Content tone

Use concise professional language with light quest framing.

Preferred:

- “Continue quest”
- “Evidence ready”
- “Run local validation”
- “Reviewer approval required”
- “Three prerequisites remain”

Avoid:

- “Slay this challenge”
- “Epic loot”
- “You failed!”
- language that trivializes privacy, security, or review findings.

## Visual acceptance review

Before release, review at minimum:

- 1440×900 desktop;
- 1280×720 laptop;
- 768×1024 tablet portrait;
- 390×844 phone;
- browser zoom at 200%;
- light sensitivity/reduced-motion preference;
- keyboard-only primary flows;
- automated contrast and accessible-name checks;
- empty, loading, error, locked, needs-changes, and verified states.
