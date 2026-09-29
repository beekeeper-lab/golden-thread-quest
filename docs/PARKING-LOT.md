# Parking Lot

Ideas and out-of-scope findings that arrive during a phase. Nothing here is acted on
mid-phase. At each gate every item is scheduled into a phase, left here, or cut
(`docs/design/07-status-and-remaining-work.md`, Section 7.3).

Add one row per item. Say where it came from and why it might matter; leave the decision
column empty until the gate.

| Added | Phase | Item | Source | Why it might matter | Gate decision |
|---|---|---|---|---|---|
| 2026-09-29 | 0 | Round 17's pointers for round 18: the proof-path mapping, the new validator run parameters, the approval re-scan, the merged scanner as a whole | `docs/audits/round-17-independent-audit.md`, Verdict | Recently changed code that no second review has read. Phase 1's flows 3 and 4 exercise the proof path and the approval re-scan | |
| 2026-09-29 | 1 | Submission is accepted while required proof files are *Not detected*; the reviewer catches it, but only then | Phase 1 flow 3, browser run | A participant can reach "submitted" believing the package is complete. No specification says submission must refuse it, so it is a product decision: refuse, warn at submit, or leave it to the reviewer | |
| 2026-09-29 | 1 | The repository-foundation check reports "passed with advisories" on an empty evidence package: it checks ignore rules, secrets and `PROOF.md` headings, not the quest's required files | Phase 1 flow 3, browser run | "Passed" on an empty package may read to a participant as "done". Either the check covers the required files or its result says what it does not check | |
