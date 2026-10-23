# Audit: curriculum step C1, Base Camp (2026-10-20)

Scope: eight new quests under `content/quests/base-camp/`, `docs/design/08-curriculum-plan.md`, and the count updates in README.md, RELEASE-NOTES.md and doc 07.

Method: independent fresh-context review of the quests against the authoring guide, the backlog rows and the security document; then `make check` (1430 passed, 57 browser tests deselected).

Result: no Blocking and no High findings. Fourteen findings were Medium or Low.

Fixed: secret-handling no longer claims a commit is blocked and requires a clean whole-repository scan with a fake credential; ownership-zones requires a `..` and a symlink refusal in its record; write-preview requires a stale-confirmation refusal and now depends on repository safety only; audit-log uses its own sample-log path; interruption-recovery requires a checksum comparison; prompt-injection's risk note says the content is hostile by design; the plan's counts are dated and its C1 rationale reworded.

Left as written: ownership-zones stays Scout to match the backlog, although its work is near Explorer size (finding 4); the single-file command records for prompt-injection and failure-lab (finding 11).

Found during the work: the test helper `unlock` in `tests/integration/test_cli_actions.py` cannot walk a diamond of prerequisites (a quest reached by two paths). Two quests were authored with such a diamond; their redundant direct prerequisite was removed instead of weakening the test. Worth fixing before a region needs a real diamond.
