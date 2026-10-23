# Audit: curriculum step C9, Trap Cards (2026-10-21)

Scope: seven new quests under `content/quests/trap-cards/`, a new ninth region `content/regions/trap-cards.yaml`, and the region and quest counts in README.md, PACKAGE-MANIFEST.md and RELEASE-NOTES.md.

Method: independent fresh-context review of the drafts against the authoring guide, both schemas and the backlog, including a scratch-copy validation (9 regions, no warnings) and a search for hard-coded region counts; fixes; then the checks below.

Result: no Blocking and no High findings. Five Medium findings were fixed: a near-miss item is required in the mimic trap; the flaky-phantom trap requires the diff of the fix (no retry, sleep, longer timeout or skip) and a hundred clean runs after the fix, with a one-in-five to one-in-three failure band; false-victory reviews repairs written by someone else, and its honest repair follows an intended behavior change rather than a regression; the fake service in vanishing-path is a runnable script; and each trap now requires something its predecessor does not (a tool-result and a chained injection; a change made a minute after retrieval; a different identifier format and a changed title across the three systems), so a participant cannot earn a Boss's XP by reusing the earlier quest's artifacts. Redundant prerequisites were removed.

Known weaknesses: `accent: teal` repeats the Trello region's, because the schema allows eight accents and all are in use; the `trap` icon has no dedicated rendering.

Tests: 1654 non-browser tests passed in total (static checks; 280 quest-chain tests in 8 shards; 1373 others in the concurrent run plus the one concurrency-sensitive test rerun alone and passing). The browser tests were not run.
