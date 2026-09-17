# Content Model and Authoring Contract

## Design objective

Curriculum maintainers must be able to add quests, regions, badges, tracks, and glossary content without editing Python, templates, JavaScript, or CSS.

The application must transform authored content into normalized view models. Templates never read raw front matter directly.

## Format allocation

| Content | Canonical format | Notes |
|---|---|---|
| Quest narrative | Markdown with YAML front matter | One quest per file |
| Region definition | YAML | Ordering, theme token, outcomes |
| Track definition | YAML | Ordered or rule-based quest selection |
| Badge definition | YAML | Machine-evaluable or reviewer-awarded criteria |
| Site configuration | YAML | Identity and generic navigation labels |
| Participant profile and journals | Markdown | Human narrative |
| Participant progress | YAML | Machine-readable, Git-friendly state |
| Evidence narrative | Markdown | One `PROOF.md` per attempt |
| Validator result | JSON | Machine-created, immutable result record |
| Review decision | YAML | Reviewer-created or reviewer-approved |
| Search and page indexes | JSON | Generated, not authoritative |

## Stable identifiers

IDs must:

- use lowercase ASCII letters, numbers, and hyphens;
- begin with a letter;
- remain stable even if the display title or filename changes;
- be unique within their entity type;
- never be silently reused for a different concept.

Examples:

- `jira-read-assigned-stories`
- `playwright-first-independent-test`
- `context-cartographer`

## Quest front matter

Required fields:

- `id`
- `version`
- `title`
- `summary`
- `region`
- `level`
- `xp`
- `estimated_minutes`
- `tags`
- `outcomes`
- `proof`

Optional fields:

- `prerequisites`
- `tools`
- `risk`
- `validators`
- `related_quests`
- `author`
- `last_reviewed`
- `deprecated`

### Difficulty levels

| Level | Typical XP | Intended scope |
|---|---:|---|
| Scout | 10 | A focused concept or safe read-only exercise |
| Explorer | 20 | A small reusable workflow |
| Builder | 30 | A multi-part implementation with evidence |
| Navigator | 50 | Cross-system or judgment-heavy workflow |
| Boss | 100 | Large synthesis or adversarial challenge |

The schema validates allowed values. A semantic warning should flag unusual XP for the chosen level without forbidding deliberate exceptions.

## Quest Markdown body

Use these canonical headings when applicable:

1. `# <Title>`
2. `## Mission`
3. `## Scenario`
4. `## Acceptance criteria`
5. `## Required evidence`
6. `## Safety constraints`
7. `## Hints`
8. `## Reflection`
9. `## Stretch goals`

The front matter contains machine-readable outcomes and proof rules. The body explains intent, context, and judgment. Do not maintain two copies of the same long acceptance-criteria list.

## Proof definition

Each quest contains a `proof.required` array and may contain `proof.optional`.

Supported proof types for release one:

- `file` — a file exists at a participant-relative glob-free path;
- `directory` — an approved directory exists and is nonempty;
- `validator` — a registered validator returns a qualifying result;
- `command-record` — a saved execution record from an allowlisted command;
- `screenshot` — supporting image with description and redaction declaration;
- `demonstration` — reviewer records a live demonstration;
- `review` — an approval decision satisfying a defined review rule.

Proof rules use participant-relative paths. Absolute paths and `..` segments are invalid.

## Quest versioning

- `version` is a positive integer.
- Editorial changes that cannot affect evaluation need not increment the version.
- Changes to outcomes, acceptance expectations, proof, validators, XP, prerequisites, or safety rules increment the version.
- An attempt records the quest version and a content hash.
- Previously verified attempts remain verified unless a documented program policy explicitly revokes them.
- The UI should indicate when a newer quest version is available.

## Participant progress

`participant/progress.yaml` contains participant-generated state but must still validate.

Key concepts:

- participant identity or display handle;
- schema version;
- quest attempts keyed by quest ID;
- attempt ID;
- quest version and content hash;
- state;
- start/update timestamps;
- evidence path;
- validation result references;
- submission reference;
- review decision reference;
- claimed XP and verified XP derived by the application, not trusted as authoritative input.

Participant notes should normally live in `QUEST-LOG.md` or the quest's evidence directory rather than bloating state YAML.

## Evidence package

Recommended structure:

```text
participant/evidence/{quest-id}/{attempt-id}/
├── PROOF.md
├── manifest.yaml
├── validation/
│   └── {run-id}.json
├── screenshots/
├── logs/
└── review.yaml
```

`PROOF.md` should answer:

- What was built?
- Where are the important artifacts?
- How can another person reproduce the behavior?
- What tests or validators were run?
- What limitations remain?
- Were any sensitive values removed?

The evidence manifest references artifacts; it does not duplicate their contents.

## Review decision

A review decision records:

- review ID and timestamp;
- reviewer display identity;
- quest and attempt IDs;
- decision: `approved`, `needs-changes`, or `rejected`;
- findings with severity and evidence;
- validator results considered;
- explicit verification statement for approval;
- optional expiration or re-review condition.

Only an approved review matching the current attempt may yield verified state and verified XP.

## Badge rules

Badges may be:

- **Automatic:** entirely determined from verified quest IDs, tags, regions, or XP.
- **Reviewer-awarded:** requires a review record and supporting reason.
- **Program-awarded:** issued outside a normal quest, such as mentor recognition.

Badge presentation must say which authority awarded it.

## Content-to-UI rules

1. Region ordering comes from region content, never template order.
2. Quest ordering uses explicit order when supplied and a documented stable fallback.
3. Tags automatically populate catalog filters.
4. Prerequisites automatically influence locks, quest links, and recommended-next calculations.
5. Proof rules automatically populate the evidence workspace.
6. Validator references automatically populate available validation actions.
7. Outcomes appear on quest detail and review views.
8. Badge criteria drive progress displays without duplicate JavaScript rules.
9. Search indexes are generated from normalized content.
10. Content marked deprecated remains linkable for historical attempts but is not recommended to new participants.

## Recommended-next algorithm

The first release uses an explainable deterministic score rather than AI inference.

Consider:

- quest is available;
- track membership;
- prerequisite continuity;
- participant's selected focus tags;
- estimated time versus stated session capacity;
- whether the quest completes a badge or region milestone;
- balanced development across intent and validation bookends;
- optional maintainer priority.

The UI must show at least three reasons for the recommendation and allow the participant to browse alternatives.

## Authoring validation behavior

An authoring error must report:

- source filename;
- document ID if available;
- field path;
- expected rule;
- received value or reason;
- suggested correction where feasible.

Example:

> `content/quests/jira-jungle/read-stories.md`: `prerequisites[0]` references unknown quest `jira-connect`. Did you mean `jira-verify-connection`?

## Adding content without UI code

A content-only pull request adding a valid quest should require changes only under `content/` plus any quest-specific registered validator under `validators/`. The build must automatically create:

- quest detail page;
- region listing;
- catalog entry;
- tag filters;
- prerequisite and related-quest links;
- search record;
- proof workspace definition;
- progress calculations.
