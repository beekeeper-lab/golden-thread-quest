# Audit: curriculum step C3, Scrum Village (2026-10-20)

Scope: eight new quests under `content/quests/scrum-village/` and the count updates in README.md and RELEASE-NOTES.md.

Method: independent fresh-context review against the authoring guide, the backlog rows and the security document; then `make check` (1470 passed, 57 browser tests deselected).

Result: no Blocking and no High findings. Five Medium groups and several Low ones.

Fixed: every acceptance criterion the review found unevidenced now has a matching proof requirement (net total in scope-change, time box and ordering rule in both agendas, risk trigger in the stakeholder summary, known issues and a repeat-run check in release notes, drop attribution and survival count in retro follow-through); review-agenda and release-notes now require unfinished items and a synthetic evidence folder so their checks can fail; retro-analysis requires a seeded instruction-like line and a no-person-named check, and its stretch goal counts speakers anonymously; four quests no longer require the stand-up digest, with prerequisites chosen for what each needs (scope-change on sprint-health, retro-follow-through on safe rerun, the rest on repository safety); related quests are set; three subjective criteria were reworded to be testable.

Left as written: version stays at 1 because the quests are unreleased.
