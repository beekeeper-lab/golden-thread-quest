# Audit: curriculum step C7, GitHub Caverns (2026-10-21)

Scope: seventeen new quests under `content/quests/github-caverns/`, six of which declare `risk.external_write: true`; the six names added to `EXPECTED_WRITE_QUESTS` in `tests/test_release_facts.py`; count updates in README.md and RELEASE-NOTES.md.

Method: independent fresh-context review against the authoring guide, the backlog rows, the security document and the already-audited Jira quests, fixes, then the checks below.

Result: no Blocking and no High findings. Medium findings were fixed: the link-delivery quest now requires a pull request's merge state and treats one closed unmerged as not delivered, and states that the write is a comment of cross-references that never pastes evidence files; node identifier, index row count, different-title duplicate and three-signals-beyond-the-title are now in required proof; related quests link each GitHub quest to its Jira counterpart.

Tests: 1608 non-browser tests passed (static checks, then 234 quest-chain tests in 8 shards and 1374 others in one process). The browser tests were not run.

Test infrastructure, for the record: the first sharded run was invalid because the collection step returned no ids, so each shard ran the whole suite (two hours), and the second had a quoting fault for ids containing spaces. Both were fixed in the runner, which lives outside the repository. The 24-way run before that filled `/tmp`. None of this changed any file in the repository.
