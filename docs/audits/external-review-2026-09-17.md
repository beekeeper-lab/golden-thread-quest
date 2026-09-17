# External Review — 2026-09-17

An outside reviewer audited the repository at `a69a8b8`. Unlike the three release rounds,
this one was not run by the author of the code. Its verdict: the engine is a release
candidate, the participant journey is not, and the reason is curriculum rather than code.

The reviewer independently reran formatting, linting, strict typing, the YAML-safety rule,
the secret scan, the non-browser suite, content validation, the site build, and a clean-clone
setup, validation and build. All passed. They could not run the browser suite because the
Playwright browser download timed out in their environment — an environment limit, not an
observed failure, and the same egress problem participants on sandboxed surfaces will hit.

## Findings and disposition

| # | Finding | Severity | Disposition |
|---|---|---|---|
| 1 | Platform far more complete than curriculum: 3 quests, 8 regions, 5 empty, 1 unearnable badge | High | **Accepted, deferred.** Sequenced after the CLI action layer; writing quests against a workflow the audience cannot execute is the expensive order. |
| 2 | `__GTQ_FLASH__` renders as literal text on every statically built page | High | **Fixed** in `a69a8b8`. Now an HTML comment; regression test added. |
| 3 | Release governance documents disagree on audit rounds and acceptance counts | Medium | **Fixed.** Counts synced and now test-enforced; this file and the audit index reconciled. |
| 4 | Tracked `.claude/settings.json` carries absolute paths and `Bash(rm:*)` | Medium | **Fixed** in `a69a8b8`. Tracked file is generic; machine-specific rules moved to untracked local settings. |
| 5 | Release ZIP is ~89 MB and ships `.venv`, `.git`, caches and local settings | Medium | **Fixed.** `make package` exports tracked files only: 4.7 MB, 213 files. `make verify-package` proves the export installs and builds. |
| 6 | `uv.lock` exists but setup and CI install from ranges | Medium | **Fixed by choosing.** The lockfile is removed and the floating contract is stated in `docs/SETUP.md`. A lockfile would hand a participant on a different Python patch a resolution failure instead of a working install. |
| 7 | Central modules large; no complexity thresholds enforced | Low | **Accepted, deferred.** `serve.py` is restructured by the CLI action layer; decomposing first would refactor code about to move. |
| 8 | Documented test counts stale by five | Low | **Fixed**, and `tests/test_release_facts.py` now fails when any document drifts from what pytest collects. |
| 9 | Gamification shallower than the quest framing implies | Low | **Accepted, deferred.** Follows the curriculum work, as the reviewer recommends. |
| 10 | Reviewer identity conventional, validators not strongly sandboxed | Low | **Accepted, already documented** as limitations 1 and 5 in `docs/RELEASE-NOTES.md`. |

## Two recommendations not taken

**Closing DH1 on the reviewer's manual clean-clone run.** They completed it successfully and
suggested that closes the criterion. It should not close on a manual pass, because the same
review could not install the browsers — which is precisely what a clean-clone check exists to
surface. `make verify-package` now automates the export-install-validate-build path; DH1
closes when that runs in CI.

**Running the Chromium suite in CI.** Already the case: `.github/workflows/ci.yml` runs it as
a separate job, and `make check` deselects UI tests so installation soundness never depends on
a browser download.

## What the reviewer saw that three internal rounds did not

The placeholder defect was visible on every generated page and no test caught it, because
every browser test reaches pages through the service that substitutes the marker. No test
ever looked at what a participant sees opening `generated/index.html` from disk.

This is the same shape as every earlier finding on this project: the defect lived in a state
no fixture occupied. It is the fourth time that pattern has produced the audit's most serious
item, which is the strongest argument yet for fixtures that start from nothing and from every
state the product defines.
