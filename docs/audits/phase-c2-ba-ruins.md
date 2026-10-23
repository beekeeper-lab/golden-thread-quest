# Audit: curriculum step C2, BA Ruins (2026-10-20)

Scope: twelve new quests under `content/quests/ba-ruins/`, one fix to the test helper `unlock`, count updates in README.md and RELEASE-NOTES.md, and a rewording in the curriculum plan.

Method: independent fresh-context review against the authoring guide, the backlog rows and the security document; then `make check`.

Result: no Blocking and no High findings. Seven Medium findings and several Low ones.

Fixed: the Boss quest now lists `base-camp-write-preview` and `base-camp-prompt-injection` as prerequisites and its proof shows the confirmation, a linked duplicate and the question list; `detect-ambiguity` no longer requires a transcript and requires one finding of each type; `nonfunctional-analysis` requires its story as proof; every quest requires its `PROOF.md` as a proof item; `change-impact` depends on repository safety only; the two question quests have distinct proof ids; the transcript safety line is dropped from quests that use no transcript, and transcript-based quests say to use the transcript from the ingest quest.

Reachability (finding 7): the plan's definition of done now reads "reachable from a quest with no prerequisites". BA Ruins starts at `ba-ingest-transcript`, which the pilot's analysts take first. The pilot quest itself was not edited, so Tom's verified attempt is unaffected.

Left as written: the Low findings on terms without a stated test in a few criteria (for example "short enough to answer without a meeting"), and the exactly-one-slice rule in `slice-story`.

Test run: 1453 passed. One failure, `test_the_service_removes_its_own_entry_when_it_stops`, followed a process kill I made during the run that left a stray service running; the test class passes when run alone.

Test helper: `unlock` in `tests/integration/test_cli_actions.py` now skips a prerequisite that is already verified, so a quest reachable by two paths can be unlocked. This was the limitation noted in the C1 audit.
