---
Project: The Golden Thread Quest
Purpose: Diagrams for docs/USER-GUIDE.md
Style: Professional expedition field guide. Deep ink navy (#172433) and warm parchment
  (#f7f4ec) foundation, restrained amber-gold (#c8962f) used only for verified achievement
  and progress, muted region accents. Clean geometric shapes, generous whitespace, precise
  thin strokes. Flat vector illustration with subtle paper texture. No gradients on text,
  no drop shadows, no 3D, no photorealism, no cartoon characters, no gamified trophies or
  confetti. It should look at home in an enterprise training programme, not a mobile game.
Generator: gemini-3-pro-image-preview
Quality: high
Size: 1536x1024
Aspect ratio: 3:2
Background: warm parchment (#f7f4ec), opaque
---

# Image Plan — User Guide

Five diagrams for `docs/USER-GUIDE.md`. Each one carries an idea the prose states but that a
reader skimming will miss, and each is placed where a reader would otherwise have to hold
three things in their head at once.

Entries are numbered in the order a reader meets them.

**Every image must teach something the sentence beside it does not.** An image that restates
its caption is decoration and does not belong here, however good it looks.

**Deliberately not planned:** screenshots of the application. Those go stale the moment a
template changes, and the guide already describes the screens in words. These five are
conceptual, so they stay true across releases.

**Text in images is rationed.** Generated text degrades badly past a handful of short labels,
and a mangled word in a diagram costs more credibility than a missing one. Each entry below
caps its own word count, and anything essential is in the prose beside the image. None of
these images is the only source of any information in the guide.

**Paths.** Images land in `docs/media/images/` because `docs/USER-GUIDE.md` references them
relatively. A repository-root `media/` directory would leave every image on the page broken.

---

### Image 1: 01-first-hour-flow

- **File**: docs/media/images/01-first-hour-flow.png
- **Page**: User guide, Section 3 — Your first hour
- **Alt text**: "Your first hour splits in two: the application handles starting the quest,
  recording validation and submitting, while you do the actual work in your own repository and
  commit and push it yourself. The application never touches your Git history."
- **Description**: A horizontal band divided into two lanes that share one continuous path.
  The upper lane is labelled "in the app" and holds four small filled ink-navy markers; the
  lower lane is labelled "in your terminal" and holds three outlined ink-navy markers. The
  single path weaves between the two lanes, crossing the divider each time authority changes
  hands, so the eye follows one route rather than reading two rows. The final marker sits in
  the lower lane after a visible gap, alone, in amber-gold outline — it is the participant's
  own act of committing and pushing, and nothing in the upper lane reaches it. Short lowercase
  labels sit beside markers, not beneath, to keep the composition wide and calm.
- **Prompt**:
  Goal: Make clear which steps the application performs and which the participant performs
    themselves, especially that committing and pushing is theirs alone and the application
    never does it.
  Scene: Two horizontal lanes labelled "in the app" and "in your terminal", with one
    continuous thin path weaving between them and crossing the divider whenever authority
    changes; filled markers in the upper lane, outlined markers in the lower; a visible gap
    before a final solitary amber-gold outlined marker in the lower lane.
  Style: Flat vector field-guide illustration, thin precise strokes, subtle paper texture,
    muted palette, generous whitespace, no shadows, no gradients.
  Aspect ratio: 3:2
  Background: warm parchment #f7f4ec
  Text in image: two lane labels "in the app" and "in your terminal", and seven short
    lowercase marker labels — start quest, do the work, write proof, run checks, record
    result, submit, commit and push. No other text.
  Avoid: swimlane business diagrams, UML, numbered step badges, screenshots, browser chrome,
    cursors, arrows with heavy heads, any sentence-length text, human figures

---

### Image 2: 02-state-authority

- **File**: docs/media/images/02-state-authority.png
- **Page**: User guide, Section 4 — The eight states
- **Alt text**: "Eight quest states in three columns by who sets them: the application sets
  locked and available; you set in progress, evidence ready, locally validated and submitted;
  only a reviewer sets needs changes and verified."
- **Description**: Eight state chips arranged in three labelled columns by authority: the
  application, you, the reviewer. Each chip is a rounded pill carrying its state name, in the
  muted colour that state uses in the real interface — slate for locked and available, violet
  for in progress, blue for evidence ready and submitted, green for locally validated, orange
  for needs changes, amber-gold for verified. A thin vertical rule separates the reviewer
  column from the other two, and the gap at that rule is wider than the gap between the first
  two columns, so the boundary reads as a threshold rather than a divider. The verified chip
  is the only solid amber element in the image; every other chip is outlined.
- **Prompt**:
  Goal: Show at a glance that verified completion is the reviewer's alone, and that the
    participant cannot reach it however much work they do.
  Scene: Eight rounded state chips in three labelled authority columns; a thin vertical rule
    before the reviewer column with noticeably wider spacing at that rule; every chip outlined
    except the verified chip, which is solid amber-gold.
  Style: Flat vector, rounded pills, muted status colours, thin rules, generous whitespace,
    no shadows, no gradients.
  Aspect ratio: 3:2
  Background: warm parchment #f7f4ec
  Text in image: three column headings "application", "you", "reviewer", and eight chip
    labels — locked, available, in progress, evidence ready, locally validated, submitted,
    needs changes, verified. No caption, no other text.
  Avoid: padlock cliches, red and green as the only distinction, traffic lights, arrows
    between chips, flowchart connectors, gradients, any sentence-length text

---

### Image 3: 03-ownership-zones

- **File**: docs/media/images/03-ownership-zones.png
- **Page**: User guide, Section 6 — What the application writes
- **Alt text**: "Three ownership zones side by side: programme-owned content and application
  code, your own work and evidence, and machine-owned generated output that is disposable.
  Only the middle zone is yours, and nothing the application does replaces it."
- **Description**: Three adjacent rectangular regions in a single row, drawn as areas on a
  field map rather than boxes in a diagram, separated by narrow parchment gutters and never
  overlapping or nested. Left: programme-owned, flat ink-navy fill with a solid border.
  Centre: participant-owned, warm parchment fill with an amber-gold border, drawn noticeably
  taller and wider than its neighbours so it anchors the composition. Right: machine-owned,
  pale grey fill with a dashed border to suggest impermanence. Small folder glyphs sit inside
  each region with short labels. A compact two-line key in the lower right corner marks which
  zones are in Git, using a filled dot and a hollow dot rather than words repeated per region.
- **Prompt**:
  Goal: Make it immediately obvious which files belong to the participant, and that the
    machine-owned zone is disposable and safe to delete.
  Scene: Three adjacent map regions in one row, not nested and not overlapping — left solid
    ink-navy with a solid border, centre warm parchment with an amber-gold border and visibly
    larger than both neighbours, right pale grey with a dashed border — each holding two or
    three small folder glyphs, plus a compact key in the lower right using a filled dot and a
    hollow dot.
  Style: Flat vector field-guide map, thin precise borders, dashed border on the disposable
    zone only, muted palette, generous whitespace, no shadows.
  Aspect ratio: 3:2
  Background: warm parchment #f7f4ec
  Text in image: three zone names "programme", "yours", "machine"; six short folder labels —
    content, quest app, participant, evidence, generated, local data; key words "in git" and
    "not in git". No other text.
  Avoid: cloud icons, server racks, padlocks, database cylinders, 3D isometric views, nested
    or overlapping regions, any sentence-length text

---

### Image 4: 04-evidence-package

- **File**: docs/media/images/04-evidence-package.png
- **Page**: User guide, Section 7 — Evidence that holds up
- **Alt text**: "Forms of evidence, strongest first: a repository artifact, then reproducible
  instructions, then automated execution evidence, then a demonstration. Above them all and
  separated from them sits reviewer approval, which evidence earns but never becomes."
- **Description**: A vertical stack read top to bottom in the same order the guide numbers it.
  Four bands of evidence sit together: a repository artifact at the top as the widest and
  most solid ink-navy band, then reproducible instructions, then execution evidence, then a
  demonstration at the bottom as the narrowest and palest, its border dashed to mark it as the
  weakest form on its own. Above the four, separated by a clear empty gap that no connector or
  arrow crosses, sits a single amber-gold band for reviewer approval — the participant builds
  the four, and cannot build the fifth. A slim vertical scale runs up the left edge, labelled
  only at its ends. The stack sits left of centre with open parchment to the right, so it
  reads as a field-guide plate rather than a marketing pyramid.
- **Prompt**:
  Goal: Show that evidence has a strength order with a repository artifact strongest and a
    demonstration weakest, and that reviewer approval sits above the whole scale and is
    reached only by the reviewer.
  Scene: Four stacked horizontal bands, widest and most solid at the top narrowing and paling
    downward, the bottom band with a dashed border; above them a clear empty gap with nothing
    crossing it; above that gap a single solid amber-gold band; a slim vertical scale at the
    left edge labelled only at its two ends; the stack positioned left of centre.
  Style: Flat vector, flat fills, thin precise strokes, muted palette, generous whitespace,
    subtle paper texture, no shadows, no gradients.
  Aspect ratio: 3:2
  Background: warm parchment #f7f4ec
  Text in image: five band labels — reviewer approval, an artifact, instructions to reproduce,
    execution evidence, a demonstration; and two scale end words "stronger" at the top and
    "weaker" at the bottom. No other text.
  Avoid: classic marketing funnel shapes, Maslow pyramid styling, arrows climbing the stack,
    numbered tiers, trophies, checkmark clipart, any sentence-length text

---

### Image 5: 05-passport-outcome

- **File**: docs/media/images/05-passport-outcome.png
- **Page**: User guide, Section 11 — Knowing when you are finished
- **Alt text**: "The passport shows claimed and verified progress as two separate totals that
  are never added together: a set of region marks, some outlined for claimed and some filled
  amber for verified, with the two counts kept deliberately apart."
- **Description**: A single flat passport page, centred, with a restrained ruled header. Its
  body is one row of eight small square region marks: five outlined in ink-navy for claimed,
  three filled solid amber-gold for verified, so the difference is visible without reading a
  legend. Beneath the row sit two separate totals, set well apart with clear parchment between
  them and no bar, no arrow and no plus sign joining them — one labelled claimed, one labelled
  verified. The composition holds nothing else: no document stack, no reviewer column, no
  secondary panel. It should read as a surveyor's record, formal and slightly sparse, and the
  emptiness between the two totals is the point of the image.
- **Prompt**:
  Goal: Show that claimed progress and verified progress are two separate figures that the
    application never combines, and that only verified marks are gold.
  Scene: One flat passport page with a thin ruled header, a single row of eight small square
    region marks — five outlined ink-navy, three solid amber-gold — and two clearly separated
    totals below with open parchment between them and nothing joining them.
  Style: Flat vector, restrained and formal, thin rules, generous whitespace, subtle paper
    texture, amber-gold used only for verified marks, no shadows.
  Aspect ratio: 3:2
  Background: warm parchment #f7f4ec
  Text in image: the word "passport" in the header, and two labels "claimed" and "verified".
    No region names, no numbers, no other text.
  Avoid: trophies, medals, stars, ribbons, rosettes, a single progress bar merging the two
    values, percentage rings, confetti, celebration imagery, document stacks, any
    sentence-length text

---

## What was considered and left out

| Candidate | Why not |
|---|---|
| The golden thread as seven waypoints | It restates the one sentence it would sit beside. The thread is the product's name, not an idea a reader struggles with. Decoration. |
| Screenshots of any screen | Stale the moment a template changes. The guide describes the screens in words that stay true. |
| The review decision flow (Section 8) | Two outcomes, approve or request changes. Prose carries it in a sentence; a diagram would add a box per word. |
| Troubleshooting (Section 9) | Already a table. A table is the right shape for lookup. |
| Taking curriculum updates (Section 10) | A command sequence. Text is precise here and an image would be less so. |
| Known limitations (Section 12) | A list of eight independent facts with no structure between them. Nothing to draw. |

## Cost

| | |
|---|---|
| Images | 5 |
| Provider | Gemini `gemini-3-pro-image-preview` |
| Estimated cost | **~$0.60** (5 × ~$0.12) |

## If a take is wrong

Refinement is a new entry, not an edit: `01-first-hour-flow-v2.png` alongside the original,
its own plan entry, its own approval. Both versions stay on disk so they can be compared, and
the sidecar JSON records what changed between them.

## Not yet approved

Nothing here has been generated. These entries are a proposal.
