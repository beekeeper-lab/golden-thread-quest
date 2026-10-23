# Audit: curriculum step C6, Jira Jungle (2026-10-21)

Scope: twenty-two new quests under `content/quests/jira-jungle/`, seven of which declare `risk.external_write: true` (the first in the repository); the rewritten external-write test in `tests/test_release_facts.py`; the rewritten "External-system writes" section of `docs/SECURITY-AND-PRIVACY.md`; count updates in README.md and RELEASE-NOTES.md.

Method: independent fresh-context review of the drafts, fixes, a second fresh-context review of the fixed files and test, then fixes of what that found; then `make check` (1574 passed, 57 browser tests deselected).

Result: no Blocking findings. The first review reported five High findings (the repository test and docs contradicting the new content; permission and duplicate checks missing from six write quests; no proof the target was an allowlisted sandbox; four write quests with unevidenced criteria). All are fixed. The second review reported no Blocking or High findings and four Medium proof gaps, which are also fixed.

The external-write control: `test_release_one_ships_no_external_write` asserted that no quest declares a write. It is replaced by `test_a_quest_that_writes_to_an_external_system_carries_the_stated_controls`, which is stricter in what it protects. The set of write quests is named in the test, so adding one is a deliberate edit; any quest tagged `write` must declare the write; every writer must show in its required proof a preview with permission and duplicate checks, a confirmation, a result record with a timestamp, a second-run record and a sandbox allowlist; must follow `base-camp-write-preview`; must name a sandbox in its risk note; and must rule out production in its safety constraints. The validator `network: denied` assertion is kept. Checked by hand: removing the word allowlist from one quest makes the test fail. The review notes a residual weakness, that keyword matching is pooled over all proof descriptions and could be satisfied by unrelated words; the named-set and tag assertions bound that, and a stronger check would need structured control fields in the quest schema, which is a schema change for a gate.

Not enforced by the application: the SECURITY document says plainly that the controls are content properties evidenced by the participant's records and read by a reviewer, and that the application performs no write.

Open for the gate: where a participant without a Jira sandbox gets one (the write quests say to ask the pilot lead and not to substitute production).

Test duration: the full suite took 91 minutes in this run, up from about 9 at eight quests, because many tests are parametrized over the quest list. A scheduled CI job or a faster fixture belongs to the engineering-hygiene phase.
