# Content Authoring Guide

## Authoring principle

Write quests as professional, demonstrable work—not trivia and not instructions to click a checkbox. A quest should cause the participant to create a reusable artifact or demonstrate a meaningful behavior.

## Add a quest

1. Choose a stable ID.
2. Select an existing region or add a region definition.
3. Copy a representative quest file from `content/quests/`.
4. Complete the YAML front matter.
5. Write the Markdown body using the canonical headings.
6. Define proof that another person can inspect or reproduce.
7. Reference only registered validators, and add the new quest's ID to each one's `quest_ids`
   list in `validators/registry.yaml`: a validator runs only for the quests it names, so a
   copied quest that keeps its source's `validators:` fails validation until it is listed
   there (round 17 D5). A quest with no validators needs no registry change.
8. Validate content before opening a pull request.
9. Review the rendered page, evidence workspace, catalog entry, and prerequisite links.
10. Run `make check`. Adding a quest, region, badge, or track changes the numbers two
    documents state about the project, and `make check` fails on purpose until they are
    corrected:
    - README.md's release-facts table: the **Sample curriculum** row (regions, quests,
      badges, tracks) and the **Tests** row's `make check`/browser counts — a new quest
      usually adds parametrized cases to existing test files, so the total moves even
      though no test file changed.
    - docs/RELEASE-NOTES.md's release-facts table: the same **Tests** row.

    `tests/test_release_facts.py` names the exact row and the number it expects; copy that
    number in. Do not weaken or skip this check to make a quest addition pass — it exists so
    the front page's own claims about the project stay true.

Do not edit templates, Python, JavaScript, or CSS merely to make a normal quest appear.

## Write a strong mission

A mission explains the capability being demonstrated in one or two paragraphs. It should answer:

- What will the participant build or prove?
- Why does that capability matter to an AI Context Engineer?
- What meaningful failure is the exercise designed to expose?

## Write measurable acceptance criteria

Strong criteria are observable and specific.

Weak:

> The Jira integration should be robust and user-friendly.

Strong:

> The synchronization retrieves every result page, preserves participant-authored notes, records the last successful source update time, and reports inaccessible items instead of deleting them.

Avoid vague terms such as fast, intuitive, scalable, robust, secure, adequate, seamless, or easy unless the quest defines how they are evaluated.

## Choose proof

Prefer proof in this order:

1. Repository artifact
2. Reproduction instructions
3. Structured validator result
4. Peer demonstration
5. Reviewer decision

Use screenshots only where visual state is itself meaningful. A screenshot of a passing terminal command should not replace the command output, source, and reproduction instructions.

Every required proof item needs:

- a stable proof ID;
- a type;
- a precise description;
- an exact participant-relative path or registered validator ID when applicable.

## Choose prerequisites

Add a prerequisite only when the earlier capability is genuinely required. Do not force a long linear path merely because quests were authored in that order.

The prerequisite graph must be acyclic. Related but optional background belongs in `related_quests`.

## Choose level, XP, and estimate

- **Scout / 10 XP:** one focused concept or safe read-only demonstration.
- **Explorer / 20 XP:** a small reusable workflow.
- **Builder / 30 XP:** a multi-artifact implementation.
- **Navigator / 50 XP:** cross-system work or substantial judgment.
- **Boss / 100 XP:** synthesis, adversarial challenge, or large end-to-end workflow.

Time is an estimate, not a deadline. Do not reduce quality expectations to preserve an estimate.

## Describe risk

Mark whether the quest:

- performs an external write;
- may handle sensitive data;
- requires a sandbox or nonproduction target;
- needs explicit preview and confirmation;
- contains untrusted third-party text such as tickets, transcripts, or comments.

The page presentation and validators may derive safety warnings from these fields.

## Version a quest

Increment `version` when changing:

- outcomes;
- material acceptance expectations;
- required proof;
- validators;
- XP;
- prerequisites;
- safety constraints;
- meaning of completion.

Do not increment for spelling, formatting, or an equivalent clarification that cannot affect evaluation.

## Review checklist

- [ ] The stable ID follows the naming rules.
- [ ] The mission describes professional capability and purpose.
- [ ] Acceptance criteria are observable.
- [ ] Proof is reproducible and proportionate.
- [ ] Required paths are participant-relative and safe.
- [ ] Prerequisites are necessary and valid.
- [ ] Safety and external-write behavior are explicit.
- [ ] The quest does not instruct the participant to expose secrets.
- [ ] The exercise can be completed independently and resumed after interruption.
- [ ] The rendered page works at narrow width and with keyboard navigation.
- [ ] A reviewer can decide completion without hidden facilitator knowledge.
- [ ] `make check` passes, including README.md's and docs/RELEASE-NOTES.md's release-facts
      tables (see step 10 above).
