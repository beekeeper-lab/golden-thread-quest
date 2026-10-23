# Audit: curriculum step C8, Trello Islands (2026-10-21)

Scope: sixteen new quests under `content/quests/trello-islands/`, six of which declare `risk.external_write: true`; the six names added to `EXPECTED_WRITE_QUESTS`; count updates in README.md and RELEASE-NOTES.md.

Method: independent fresh-context review against the authoring guide, the security document and the already-audited Jira and GitHub quests, including whether the quests use Trello's own model rather than renamed Jira text; fixes; then the checks below.

Result: no Blocking and no High findings. The review confirmed the quests use Trello concepts (lists and position as status, activity-driven delta sync, token scope and expiry, credentials in query strings, archived cards, checklist state, a key stored on the card). Medium findings were fixed: the move, checklist, next-work, attachment, duplicate-search and reconciliation proof now show the criteria they claim (source and destination list, a refused disallowed move, an archived card excluded, no request to link targets, a recommendation from a fixed set, a distinct moved state), and every write preview now records the token's write scope and expiry.

Tests: 1640 non-browser tests passed (static checks; 266 quest-chain tests in 8 shards; 1373 others in the concurrent run, plus the one test that failed there rerun alone). That test, `TestThePortFileLifecycle::test_the_service_removes_its_own_entry_when_it_stops`, fails only while shards run in parallel, because they share the service port file, and passes alone. The browser tests were not run.
