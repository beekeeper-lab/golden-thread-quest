# Audit: curriculum step C5, Playwright Labyrinth (2026-10-20)

Scope: nineteen new quests under `content/quests/playwright-labyrinth/` and the count updates in README.md and RELEASE-NOTES.md.

Method: independent fresh-context review of the drafts, fixes, and a second fresh-context review of the fixed files; then `make check` (1530 passed, 57 browser tests deselected).

Result: no Blocking findings. The first review reported six High findings (acceptance criteria no proof item would show) and the second reported five more after the first fixes; both rounds' High findings are fixed.

Fixed: every unevidenced criterion now has a proof requirement; the target is an application the participant runs themselves, not a public site; five quests that can capture credentials or personal data are flagged `sensitive_data: true`; each quest whose proof is a check requires the check's script; the planted-secret scan reports file and line only so evidence does not trip the secret scan; the failure-triage quest requires a ground-truth file; project-setup requires pinned dependencies and zero or justified retries.

Not done, for a gate decision: the curriculum plan said this region needs a validator for test quality beyond `validate-playwright-quality`. None of the quests names a validator, because that validator only inspects files named `*test*` and would return inconclusive on most of these specs; proof is files and command records, and the reviewer decides. Adding a validator is a separate scope item.

Test infrastructure: an earlier full run showed 744 errors from pytest temp-directory collisions after an interrupted run overlapped a second one. A clean rerun passed.
