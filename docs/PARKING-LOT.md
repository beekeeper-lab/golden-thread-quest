# Parking Lot

Ideas and out-of-scope findings that arrive during a phase. Nothing here is acted on
mid-phase. At each gate every item is scheduled into a phase, left here, or cut
(`docs/design/07-status-and-remaining-work.md`, Section 7.3).

Add one row per item. Say where it came from and why it might matter; leave the decision
column empty until the gate.

| Added | Phase | Item | Source | Why it might matter | Gate decision |
|---|---|---|---|---|---|
| 2026-09-29 | 0 | Round 17's pointers for round 18: the proof-path mapping, the new validator run parameters, the approval re-scan, the merged scanner as a whole | `docs/audits/round-17-independent-audit.md`, Verdict | Recently changed code that no second review has read. Phase 1's flows 3 and 4 exercise the proof path and the approval re-scan || Gate 1: cut. Phase 1's browser flows exercised the proof path and the approval re-scan |
| 2026-09-29 | 1 | Submission is accepted while required proof files are *Not detected*; the reviewer catches it, but only then | Phase 1 flow 3, browser run | A participant can reach "submitted" believing the package is complete. No specification says submission must refuse it, so it is a product decision: refuse, warn at submit, or leave it to the reviewer || Gate 1: Phase 2A, item 1 |
| 2026-09-29 | 1 | The repository-foundation check reports "passed with advisories" on an empty evidence package: it checks ignore rules, secrets and `PROOF.md` headings, not the quest's required files | Phase 1 flow 3, browser run | "Passed" on an empty package may read to a participant as "done". Either the check covers the required files or its result says what it does not check || Gate 1: Phase 2A, item 2 |
| 2026-09-29 | 1 | Before a quest is started, its page shows a proof path under `attempt-001/`; after starting, under the real `base-attempt-001/` | Phase 1 verify pass | A participant reading ahead may create files in the wrong folder || Gate 1: left here; revisit with the pilot report |
| 2026-09-29 | 1 | With the only available quest submitted, Home says "Nothing to recommend right now" without pointing at the pending review | Phase 1 verify pass | A participant waiting on a reviewer gets no signpost || Gate 1: left here; revisit with the pilot report |
| 2026-09-29 | 1 | About 25 `GET /` requests in the service log right after start-up, before any browser step | Phase 1 verify pass | Not investigated; may be another process on the machine || Gate 1: left here; revisit with the pilot report |
| 2026-09-29 | 2A | The secret check flags a redaction placeholder wrapped in parentheses, an ordinary redaction, and advises rotating the value | Phase 2A verify pass | A participant writing the redacted output a quest asks for gets stuck. `PILOT.md` now names a form that passes | |
| 2026-09-29 | 2A | **Mark evidence ready** is accepted with every required file missing, and says "You assembled the required proof" | Phase 2A verify pass | Submission now refuses it, but the earlier message still claims something untrue | |
| 2026-09-29 | 2A | After Base Camp, the home page recommends a Jira quest, not the pilot's BA Ruins quest | Phase 2A verify pass | `PILOT.md` tells participants where to find it. A track for the pilot would say it in the product | |
| 2026-09-29 | 2A | The reviewer page names the participant by their operating-system user name | Phase 2A verify pass | A reviewer of several people sees names like `gregg` rather than the person | |
