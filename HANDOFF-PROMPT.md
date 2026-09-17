# Prompt for Claude Code

Copy the prompt below into Claude Code after extracting this package and opening the repository folder.

---

You are receiving the planning and design package for **The Golden Thread Quest**, a local-first training application within **The AI Context Engineer Journey**.

Your job is to audit the plan first and then build the application in controlled, reviewable stages.

Begin by reading `CLAUDE.md`, `PLANNING-STATUS.md`, and every file in the required reading order defined by `CLAUDE.md`. Then inspect the schemas, sample content, fixtures, Jinja design contracts, and the clickable prototype under `prototype/`.

Do not implement anything until you have completed **Stage 0 — Planning and feasibility audit** in `docs/IMPLEMENTATION-PLAN.md`.

Mandatory rules:

1. Create a descriptive feature branch before making implementation changes. Never work directly on `main`.
2. Treat the Markdown/YAML content, JSON Schemas, written UI specification, and prototype as one design package. Identify contradictions rather than silently choosing one.
3. Record the Stage 0 audit in `docs/audits/stage-00-planning-audit.md` with severity, evidence, and recommended correction.
4. Correct blocking and high-severity planning findings before beginning Stage 1.
5. Follow `docs/IMPLEMENTATION-PLAN.md` in order, one stage at a time.
6. At the end of each stage, use a fresh review context or review subagent when available to audit the completed stage.
7. Fix every blocking and high-severity finding, rerun the audit, and only then check the stage complete.
8. Update the restart log whenever work pauses so another session can resume accurately.
9. Preserve the architecture boundary: curriculum is Markdown/YAML, schemas define contracts, Python creates normalized view models, Jinja2 renders HTML, participant files are isolated, and generated files are disposable.
10. Never introduce arbitrary browser-triggered command execution, unapproved filesystem access, hidden external writes, or participant-controlled reviewer verification.
11. Do not weaken schemas, tests, validator constraints, or acceptance criteria merely to make the build pass.
12. Record every approved architecture deviation in `docs/DECISIONS.md`.

Before each stage, summarize:

- the stage goal;
- files expected to change;
- tests and acceptance criteria that will prove completion;
- material risks.

After each stage, summarize:

- what was implemented;
- what was tested;
- audit findings and fixes;
- remaining advisories;
- exact next stage.

At final completion, create `docs/IMPLEMENTATION-DETAILS.md`, `docs/TRACEABILITY.md`, and `docs/audits/final-audit.md`. Compare the original specification, actual implementation, automated tests, UI behavior, security boundary, and implementation-details document before recommending release.

Start now with Stage 0 only.

---
