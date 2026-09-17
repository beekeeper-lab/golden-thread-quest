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

**Deliberately not planned:** screenshots of the application. Those go stale the moment a
template changes, and the guide already describes the screens in words. These five are
conceptual, so they stay true across releases.

**Text in images is kept to short labels only.** Generated text is unreliable at sentence
length, and anything essential is in the prose beside the image — the diagrams support the
guide, they do not carry it alone.

**Accessibility.** Every image needs alt text when it lands; the alt text is written below
with each entry so it is decided now rather than improvised later. None of these images is
the only source of any information in the guide.

---

### Image 1: 01-golden-thread

- **File**: media/images/01-golden-thread.png
- **Page**: User guide, Section 1 — What this actually is
- **Alt text**: "The golden thread: a conversation becomes a requirement, a work item, an
  implementation, a test, evidence, and finally a verified outcome — one continuous line
  through seven stages."
- **Description**: A single continuous golden thread running left to right across a warm
  parchment field, passing through seven small ink-navy waypoint markers. Each marker is a
  simple geometric glyph suggesting its stage: a speech bubble, a document, a card, angle
  brackets, a checkmark in a circle, a folder, and a seal. The thread is thin and deliberate,
  not decorative; it never loops or tangles. Short lowercase labels sit beneath each marker.
  The final seal is the only element rendered in solid amber-gold; everything else is ink on
  parchment. Wide margins, horizontal composition, the feeling of a route drawn on a field
  map rather than a flowchart.
- **Prompt**:
  Goal: Show that the curriculum is one unbroken line from human conversation to verified
    outcome, and that only the last step is gold.
  Scene: Seven waypoint markers on a single horizontal golden thread, left to right, each a
    simple ink-navy geometric glyph, with the final marker a solid amber-gold seal.
  Style: Flat vector field-guide illustration, thin precise strokes, subtle paper texture,
    generous whitespace, no gradients, no shadows.
  Aspect ratio: 3:2
  Background: warm parchment #f7f4ec
  Text in image: seven short lowercase labels only — conversation, requirement, work item,
    implementation, test, evidence, outcome
  Avoid: arrows with heavy heads, corporate stock imagery, glossy 3D, trophies, confetti,
    any sentence-length text, any human faces

---

### Image 2: 02-first-hour-flow

- **File**: media/images/02-first-hour-flow.png
- **Page**: User guide, Section 3 — Your first hour
- **Alt text**: "The first hour: read the quest, start it, do the work in your repository,
  write PROOF.md, run the checks, submit, then commit and push yourself. The application
  handles the middle steps; you handle the first and last."
- **Description**: Eight numbered steps arranged as a gentle arc across the page, like stages
  on a trail rather than boxes in a flowchart. Each step is a small ink-navy circle with its
  number and a two-word label beneath. Steps that happen in the browser and steps that happen
  in the participant's own terminal are distinguished by a subtle difference in the marker —
  filled versus outlined — with a small legend in the lower corner. The last step, commit and
  push, sits slightly apart with a small gap before it, signalling that it is the
  participant's own act and not the application's.
- **Prompt**:
  Goal: Make clear which steps the application performs and which the participant performs
    themselves, especially that committing and pushing is theirs alone.
  Scene: Eight numbered waypoints along a gentle arc; filled markers for browser steps,
    outlined markers for terminal steps; a visible gap before the final step.
  Style: Flat vector field-guide illustration, thin strokes, muted palette, small legend,
    generous whitespace.
  Aspect ratio: 3:2
  Background: warm parchment #f7f4ec
  Text in image: numbers 1 to 8 and two-word labels only — read quest, start quest, do work,
    write proof, run checks, evidence ready, submit, commit push; legend words "in the app"
    and "in your terminal"
  Avoid: swimlane diagrams, UML, screenshots, browser chrome, cursors, any sentence-length
    text, human figures

---

### Image 3: 03-state-authority

- **File**: media/images/03-state-authority.png
- **Page**: User guide, Section 4 — The eight states
- **Alt text**: "Eight quest states in three columns by who sets them: the application sets
  locked and available; the participant sets in progress, evidence ready, locally validated
  and submitted; only a reviewer sets needs changes and verified."
- **Description**: Eight state chips arranged in three labelled columns by authority: the
  application, the participant, the reviewer. Each chip is a rounded pill with its state name
  and a small glyph, in the muted colour that state uses in the real interface — slate for
  locked and available, violet for in progress, blue for evidence ready and submitted, green
  for locally validated, orange for needs changes, and amber-gold for verified. The reviewer
  column is set slightly apart with a thin vertical rule, and the two chips in it are the only
  ones carrying weight — verified is the sole solid amber element in the whole image. A single
  short caption sits under the reviewer column.
- **Prompt**:
  Goal: Show at a glance that verified completion is the reviewer's alone, and that the
    participant cannot reach it however much they do.
  Scene: Eight rounded state chips in three authority columns, reviewer column separated by a
    thin vertical rule, the verified chip the only solid amber element.
  Style: Flat vector, rounded pills, muted status colours, thin rules, generous whitespace,
    no shadows.
  Aspect ratio: 3:2
  Background: warm parchment #f7f4ec
  Text in image: column headings "application", "you", "reviewer"; eight chip labels —
    locked, available, in progress, evidence ready, locally validated, submitted, needs
    changes, verified; one short caption "only a reviewer can verify"
  Avoid: padlock cliches, red and green as the only distinction, traffic lights, gradients,
    any sentence-length text beyond the single caption

---

### Image 4: 04-ownership-zones

- **File**: media/images/04-ownership-zones.png
- **Page**: User guide, Section 6 — What the application writes
- **Alt text**: "Three ownership zones: programme-owned content and application code,
  participant-owned work and evidence, and machine-owned generated output that is disposable.
  Only the participant zone belongs to you, and nothing replaces it."
- **Description**: Three nested or adjacent regions drawn as areas on a field map, each with a
  distinct treatment: programme-owned rendered in flat ink-navy with a solid border,
  participant-owned in warm parchment with an amber-gold border and slightly larger than the
  others, machine-owned in pale grey with a dashed border suggesting impermanence. Small file
  and folder glyphs sit inside each region naming what lives there. A small key in the corner
  states whether each zone is in Git. The participant region is visually the anchor of the
  composition.
- **Prompt**:
  Goal: Make it immediately obvious which files belong to the participant and that the
    machine-owned zone is disposable.
  Scene: Three map-like regions — programme-owned solid ink, participant-owned parchment with
    an amber border and visually dominant, machine-owned pale grey with a dashed border — each
    holding small folder glyphs, with a small key in one corner.
  Style: Flat vector field-guide map, thin precise borders, dashed border for the disposable
    zone, muted palette, generous whitespace.
  Aspect ratio: 3:2
  Background: warm parchment #f7f4ec
  Text in image: zone names "programme", "yours", "machine"; folder labels content, schemas,
    quest app, participant, evidence, generated, local data; key words "in git" and "not in
    git"
  Avoid: cloud icons, server racks, padlocks, database cylinders, 3D isometric views, any
    sentence-length text

---

### Image 5: 05-passport-outcome

- **File**: media/images/05-passport-outcome.png
- **Page**: User guide, Section 11 — Knowing when you are finished
- **Alt text**: "What you end up with: a passport of verified capability by region, a
  repository of real artifacts, and a review history of named people confirming your evidence
  held up — with claimed and verified progress always shown separately."
- **Description**: A field-guide passport page rendered as a flat document, showing a small
  grid of region capability marks — some filled amber for verified, some outlined for claimed
  — beside two clearly separate totals labelled claimed and verified, never combined. To one
  side, two smaller supporting elements: a stack of document glyphs representing repository
  artifacts, and a short list of initialled review marks representing named reviewers. The
  composition should read as a professional credential, restrained and slightly formal — closer
  to a surveyor's record than a game achievement screen.
- **Prompt**:
  Goal: Show that the outcome is a credential backed by artifacts and named reviewers, with
    claimed and verified progress deliberately kept apart.
  Scene: A flat passport page with a grid of region capability marks, two separate totals
    labelled claimed and verified, a stack of document glyphs, and a short column of initialled
    review marks.
  Style: Flat vector, restrained and formal, amber-gold used only for verified marks, thin
    rules, generous whitespace, subtle paper texture.
  Aspect ratio: 3:2
  Background: warm parchment #f7f4ec
  Text in image: headings "passport", "claimed", "verified"; region words base camp, jira,
    trello, github, context, analysis, scrum, playwright
  Avoid: trophies, medals, stars, badges with ribbons, progress bars that merge two values,
    confetti, celebration imagery, any sentence-length text

---

## Cost

| | |
|---|---|
| Images | 5 |
| Provider | Gemini `gemini-3-pro-image-preview` |
| Estimated cost | **~$0.60** (5 × ~$0.12) |

## If a take is wrong

Refinement is a new entry, not an edit: `01-golden-thread-v2.png` alongside the original, its
own plan entry, its own approval. Both versions stay on disk so they can be compared, and the
sidecar JSON records what changed between them.

## Not yet approved

Nothing here has been generated. These entries are a proposal.
