# Screen Specifications

## U01 — Home / Continue

### User question

“Where am I, and what is the best useful thing to do next?”

### Required sections

- Participant greeting and current track
- Claimed versus verified progress
- Primary recommended quest with reasons
- Alternative available quests
- Region progress summary
- Recent validation or review activity
- Environment warning when action is needed

### Primary action

Continue an in-progress quest; otherwise view the recommended quest.

### Empty state

New participants see Base Camp orientation, setup health, and the first available quest.

## U02 — Quest Map

### User question

“What does the full journey contain, and how far have I traveled?”

### Required sections

- Overall verified progress
- The map: each region drawn as land, with its name and how many of its quests are verified
- Region cards in configured order, as a list
- Region outcomes
- Quest state distribution per region
- Prerequisite or recommended progression cues
- Legend explaining states

### Behavior

The map is a drawing of the curriculum, in the style of an atlas: a dark sea, a continent with a rough coastline and shaded relief, rivers, lakes, mountain ranges and forests, and a dotted trail joining the regions in curriculum order. A region whose `terrain` is `islands` lies out at sea as a separate island. The scenery is decoration, generated from the layout and hidden from assistive technology; a region's marker glows brighter as more of its quests are verified. Each region is a stretch of land whose area follows its quest count, with a picture chosen by the region's `terrain` (a fixed vocabulary in `schemas/region.schema.json`) and a label giving its name and `N of M verified`. The label is the real, focusable link; the drawing is hidden from assistive technology. With scripting on, selecting a label opens the region's card in a modal dialog, with a link to the region page and a Close button, and Escape closes it. Without scripting the label goes to the region page. The same cards remain below the map as a list (a disclosure, closed by default), so no one has to read a picture to see progression. The layout is designed for up to 18 regions; beyond that the labels may overlap, and the list stays complete. The layout is computed from quest counts alone (`quest_app/map_layout.py`) and is the same on every build. The map scrolls inside its own box on narrow screens; the page itself never scrolls sideways.

## U03 — Region

### User question

“What can I learn and demonstrate in this area?”

### Required sections

- Region description and outcomes
- Region claimed and verified totals
- Quest list
- Filters relevant to the region
- Region badges
- Suggested sequence with explanation

## U04 — Catalog

### User question

“Find a quest matching the capability, tool, risk, difficulty, or time I care about.”

### Required sections

- Search
- Active-filter chips
- Region, state, level, time, tag, risk, and bookend filters
- Sort by recommended, configured order, title, time, XP, or state
- Result count
- Quest cards/list

### Empty state

Explain that no quests match and provide a one-action filter reset.

## U05 — Quest Detail

### User question

“What exactly do I need to build, why does it matter, and how will it be judged?”

### Required sections

- Title, summary, state, region, version
- Mission and scenario
- Outcomes
- Acceptance criteria
- Required and optional evidence
- Safety constraints
- Hints, reflection, and stretch goals
- Prerequisites and related quests
- XP, level, estimate, tags, and tools
- Primary state transition action

### Locked state

Show the quest content when policy permits, but disable start and list every unmet prerequisite with a link.

### New-version state

Show current attempt version and available version. Do not silently migrate an in-progress attempt.

## U06 — Evidence Workspace

### User question

“Have I assembled credible proof, and what remains?”

### Required sections

- Quest and attempt identity
- Required proof checklist
- Detected artifacts
- PROOF.md preview or edit link
- Validator actions and latest results
- Git change summary
- Redaction and secret-scan status
- Mark-evidence-ready action
- Submit-for-review action when eligible

### Failure state

Preserve all work, identify which checks failed, and show specific next actions. Never convert a validator failure directly into “quest failed.”

## U07 — Validation Result

### User question

“What passed, what failed, why, and how do I reproduce it?”

### Required sections

- Outcome and classification
- Validator version and run ID
- Start time, duration, environment
- Checks with evidence
- Findings ordered by severity
- Redacted output and full local result location
- Rerun and return-to-evidence actions

## U08 — Passport

### User question

“What have I credibly demonstrated?”

### Required sections

- Participant identity
- Current track
- Verified versus claimed XP
- Region capability matrix
- Earned, pending, and available badges
- Verified quest timeline
- Capability breadth suggestions
- Sanitized public-progress preview/export

## U09 — Environment Health

### User question

“Is my local environment ready, safe, and connected enough for the quest I want?”

### Required sections

- Application and content version
- Python and required dependency status
- Git repository, branch, upstream, and working-tree status
- Participant directory write test
- Generated/local-data directory state
- External CLI presence without displaying secrets
- Local service binding and security status
- Actionable remediation commands

Checks must distinguish required, optional, warning, and informational.

## U10 — Reviewer View

### User question

“Does this evidence demonstrate the quest outcomes strongly enough to verify?”

### Required sections

- Participant, quest, version, attempt, and submission identity
- Outcomes and acceptance criteria
- Required proof status
- Artifact links and reproduction instructions
- Validation results
- Secret/redaction status
- Changed-since-review warning
- Findings editor
- Approve, needs-changes, and reject decisions
- Prior review history

### Approval guard

Approval requires all mandatory reviewer fields and an explicit verification statement. Automated validation may support but never perform approval.

## U11 — Content Author Error

### User question

“Why did the build reject my content, and how do I fix it?”

### Required sections

- Build failure summary
- Filename and line/field path
- Entity ID when known
- Expected rule and received value
- Suggested correction
- Related schema or documentation link
- All errors, not only the first, when safe and useful

The application should also emit a terminal-friendly version of the same information.
