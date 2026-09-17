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

## Round 2 — corrections

Round 1 generated all five. `03-ownership-zones` and `04-evidence-package` are correct and
final. The other three each rendered clean text but got the content wrong, so each gets a v2
entry rather than an edit. The v1 files stay on disk for comparison.

What went wrong, and the lesson for later entries: a prompt that describes a *pattern*
("filled markers in the upper lane") lets the generator choose which item goes where. Every
v2 entry below assigns each item to its position by name, leaving nothing to infer.

---

### Image 6: 01-first-hour-flow-v2

- **File**: docs/media/images/01-first-hour-flow-v2.png
- **Page**: User guide, Section 3 — Your first hour
- **Fixes**: v1 placed "run checks" and "submit" in the terminal lane. Both happen in the
  application (guide steps 6 and 7). Lane membership is now stated per marker.
- **Alt text**: "Your first hour splits in two: the application handles starting the quest,
  running checks, recording the result and submitting, while you do the work in your own
  repository, write PROOF.md, and commit and push it yourself."
- **Description**: A horizontal band divided into two lanes by a thin rule. The upper lane is
  labelled "in the app" and the lower lane "in your terminal". One continuous thin path runs
  left to right, crossing the divider exactly three times, visiting seven markers in this
  fixed order and no other: start quest in the upper lane, do the work in the lower lane,
  write proof in the lower lane, run checks in the upper lane, record result in the upper
  lane, submit in the upper lane, and finally commit and push in the lower lane. Markers in
  the upper lane are solid filled ink-navy; markers in the lower lane are outlined ink-navy.
  The last marker, commit and push, sits after a clear horizontal gap that the path does not
  cross, and it alone is amber-gold — it is the participant's own act, and the path from the
  application never reaches it.
- **Prompt**:
  Goal: Make clear which steps the application performs and which the participant performs
    themselves, especially that committing and pushing is theirs alone.
  Scene: Two horizontal lanes separated by a thin rule, upper labelled "in the app", lower
    labelled "in your terminal". Seven markers in this exact placement, left to right —
    marker 1 "start quest" in the UPPER lane, marker 2 "do the work" in the LOWER lane,
    marker 3 "write proof" in the LOWER lane, marker 4 "run checks" in the UPPER lane,
    marker 5 "record result" in the UPPER lane, marker 6 "submit" in the UPPER lane, marker 7
    "commit and push" in the LOWER lane. Upper-lane markers are solid filled; lower-lane
    markers are outlined. A single continuous thin path connects markers 1 through 6 only,
    crossing between lanes where the lane changes. After marker 6 there is a clear empty gap
    that no path crosses, and marker 7 stands alone beyond it in amber-gold.
  Style: Flat vector field-guide illustration, thin precise strokes, subtle paper texture,
    muted palette, generous whitespace, no shadows, no gradients.
  Aspect ratio: 3:2
  Background: warm parchment #f7f4ec
  Text in image: two lane labels "in the app" and "in your terminal", and seven marker labels
    — start quest, do the work, write proof, run checks, record result, submit, commit and
    push. No other text, no numbers.
  Avoid: swimlane business diagrams, UML, numbered step badges, screenshots, browser chrome,
    cursors, arrows with heavy heads, a path that continues into the final marker, any
    sentence-length text, human figures

---

### Image 7: 02-state-authority-v2

- **File**: docs/media/images/02-state-authority-v2.png
- **Page**: User guide, Section 4 — The eight states
- **Fixes**: v1 put "locally validated" in the reviewer column. It is a participant state, and
  its presence there contradicted the one thing the image exists to say. Column membership is
  now stated exhaustively, and the reviewer column is explicitly limited to two chips.
- **Alt text**: "Eight quest states in three columns by who sets them: the application sets
  locked and available; you set in progress, evidence ready, locally validated and submitted;
  only a reviewer sets needs changes and verified."
- **Description**: Three labelled columns of rounded state chips. The first column is headed
  "application" and contains exactly two chips: locked, available. The second is headed "you"
  and contains exactly four chips: in progress, evidence ready, locally validated, submitted.
  The third is headed "reviewer" and contains exactly two chips and no others: needs changes,
  verified. Column headings are plain text above each column, not chips. One single thin
  vertical rule sits between the second and third columns and nowhere else, with wider
  spacing at that rule than between the first two columns. Every chip is outlined in its
  muted status colour except verified, which is solid amber-gold with light text.
- **Prompt**:
  Goal: Show at a glance that verified completion is the reviewer's alone, and that the
    participant cannot reach it however much work they do.
  Scene: Three columns of rounded pill chips under plain text headings. Column 1 heading
    "application" with exactly these two chips: locked, available. Column 2 heading "you"
    with exactly these four chips: in progress, evidence ready, locally validated, submitted.
    Column 3 heading "reviewer" with exactly these two chips and nothing else: needs changes,
    verified. Exactly one thin vertical rule, placed between column 2 and column 3, with a
    wider gap there than between columns 1 and 2. All chips outlined except verified, which
    is solid amber-gold.
  Style: Flat vector, rounded pills, muted status colours, thin rules, generous whitespace,
    no shadows, no gradients.
  Aspect ratio: 3:2
  Background: warm parchment #f7f4ec
  Text in image: three plain headings "application", "you", "reviewer", and the eight chip
    labels exactly as assigned above. No caption, no numbers, no other text.
  Avoid: headings drawn as pills or boxes, more than one vertical rule, any chip in a column
    other than the one assigned, padlock cliches, traffic lights, arrows or connectors
    between chips, gradients, any sentence-length text

---

### Image 8: 05-passport-outcome-v2

- **File**: docs/media/images/05-passport-outcome-v2.png
- **Page**: User guide, Section 11 — Knowing when you are finished
- **Fixes**: v1 invented the figures 10601 and 10602, showing verified higher than claimed.
  Verified is always a subset of claimed, so the image asserted something the application
  cannot produce. The two figures are now fixed values that agree with the marks drawn, and
  v1's large empty centre is filled by enlarging the mark row.
- **Alt text**: "The passport shows claimed and verified progress as two separate totals that
  are never added together: eight region marks, five outlined for claimed and three filled
  amber for verified, with claimed at eight and verified at three kept deliberately apart."
- **Description**: A single flat passport page, centred, with a thin ruled header carrying the
  word passport. Its body is one row of eight square region marks, sized large enough to fill
  the page width comfortably: the first five outlined in ink-navy, the last three solid
  amber-gold. Beneath the row sit two separate boxed totals, set far apart with open parchment
  between them and nothing joining them — the left reads claimed 8, the right reads verified
  3. The figures agree with the marks above: eight marks in total, three of them gold. Nothing
  else appears on the page.
- **Prompt**:
  Goal: Show that claimed progress and verified progress are two separate figures the
    application never combines, that verified is always the smaller, and that only verified
    marks are gold.
  Scene: One flat passport page with a thin ruled header reading "passport". Below it, a
    single row of eight large square marks — the first five outlined ink-navy, the last three
    solid amber-gold. Below that, two separated boxed totals with wide open parchment between
    them and no line, bar or arrow joining them: the left box reads "claimed 8" and the right
    box reads "verified 3".
  Style: Flat vector, restrained and formal, thin rules, generous whitespace, subtle paper
    texture, amber-gold used only for verified marks, no shadows, no gradients.
  Aspect ratio: 3:2
  Background: warm parchment #f7f4ec
  Text in image: exactly four pieces of text — "passport", "claimed 8", "verified 3". No
    region names, no other numerals, no other text.
  Avoid: any number other than 8 and 3, a verified figure larger than the claimed figure,
    trophies, medals, stars, ribbons, a single progress bar merging the two values,
    percentage rings, confetti, document stacks, large empty areas, any sentence-length text

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
| Images | 5 generated, 3 corrections pending |
| Provider | Gemini `gemini-3-pro-image-preview` |
| Round 1 actual | **$0.70** (5 images, 9,939 tokens, 89s) |
| Round 2 estimate | **~$0.36** (3 × ~$0.12) |

## If a take is wrong

Refinement is a new entry, not an edit: `01-first-hour-flow-v2.png` alongside the original,
its own plan entry, its own approval. Both versions stay on disk so they can be compared, and
the sidecar JSON records what changed between them.

## Approval state

Round 1 (images 1-5) was approved and generated on 2026-09-17.
Round 2 (images 6-8) is a proposal and has not been generated.
