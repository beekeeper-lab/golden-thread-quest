# 8. Curriculum plan: closing the backlog

Written 2026-10-20 at the program owner's instruction. It turns the sketch under "Phase 4
onward" in `07-status-and-remaining-work.md` into a sequence. The 128 quests in
`docs/CURRICULUM-BACKLOG.md` are the inventory; eight were built when this was written, so **120 remained**. Step C1 has since built Base Camp (16 built, 112 remain).

## 8.1 Where the gap is (before C1)

| Region | Backlog | Built | To build |
|---|---|---|---|
| Base Camp | 9 | 1 | 8 |
| BA Ruins | 13 | 1 | 12 |
| Scrum Village | 9 | 1 | 8 |
| Context Library | 12 | 1 | 11 |
| Playwright Labyrinth | 20 | 1 | 19 |
| Jira Jungle | 23 | 1 | 22 |
| GitHub Caverns | 18 | 1 | 17 |
| Trello Islands | 17 | 1 | 16 |
| Hidden and adversarial | 7 | 0 | 7 |
| **Total** | **128** | **8** | **120** |

## 8.2 Order

One region per step, each ending at a gate. The order puts safety first, then what the pilot
audience (BAs and manual testers) can use, then the regions that write to outside systems.

| Step | Region | Quests | Why here |
|---|---|---|---|
| C1 | Base Camp | 8 | Every other region builds on Base Camp's safety habits; later quests should list the specific Base Camp quest they need. Includes the write-preview quest that later write quests depend on. |
| C2 | BA Ruins | 12 | The pilot participants are analysts; read-only and local, so no new capability. |
| C3 | Scrum Village | 8 | Builds on BA Ruins' records; local reports. |
| C4 | Context Library | 11 | The shared context catalog the integration regions feed. |
| C5 | Playwright Labyrinth | 19 | Testers' region; needs a validator for test quality beyond the existing one. |
| C6 | Jira Jungle | 22 | First region with external writes; carries the preview-and-confirm capability as its own scope item (`docs/SECURITY-AND-PRIVACY.md`). |
| C7 | GitHub Caverns | 17 | Reuses the Jira capability. |
| C8 | Trello Islands | 16 | Reuses it again. |
| C9 | Hidden and adversarial | 7 | Trap cards that need the integration regions to exist. |

Steps are C1 to C9 so they do not collide with Phases 5 to 7 in document 07 (hygiene, security,
new capabilities); C1 is the "Phase 4 onward: Curriculum" item there. The order is a recommendation; each gate may change it.
Steps C2 to C9 are sketches until their gate and are planned in full only then.

## 8.3 How each curriculum step runs

1. Branch `phase-C<n>/<region>`. Add only content files under `content/quests/<region>/`, plus
   registry entries and tests that the authoring guide names. No template, Python or CSS change
   to make a quest appear.
2. Each quest follows `docs/CONTENT-AUTHORING-GUIDE.md`: observable criteria, proof another
   person can inspect, prerequisites only where the earlier capability is truly needed.
3. A quest needs a validator only when a program can establish a fact the reviewer would
   otherwise check by hand. Otherwise its proof is files and command records and the reviewer
   decides. A validator is added in the same step as the quests that name it.
4. `make check` passes, including the release-facts tables (README and RELEASE-NOTES counts).
5. Fresh-context audit recorded in `docs/audits/phase-NN-*.md`; fix blocking and high findings.
6. Merge, then stop at the gate. Participants install tagged releases, not `main`, so merged
   quests reach them only when the program owner cuts a release at the gate. Building ahead does
   not change what the pilot sees.

## 8.4 Definition of done for a region

- Every backlog row for the region has a quest file with its proposed ID, name and level.
- Prerequisites are acyclic and every quest is reachable from a quest with no prerequisites. A
  region may have its own first quest (BA Ruins starts at `ba-ingest-transcript`, which the
  pilot's analysts take first) rather than forcing every participant through Base Camp.
- A reviewer can decide each quest without facilitator knowledge.
- Quests that write to an external system declare it in `risk` and require preview and
  confirmation.

## 8.5 Risks

- **Volume over quality.** 120 quests written fast will read as filler. Mitigation: one region
  per step with an audit, and pilot findings feed each next region.
- **Reviewer load.** More quests mean more reviews. The pilot report should say how long a
  review takes before more than two regions are built.
- **Capability gaps.** External-write quests cannot ship before preview-and-confirm exists for
  that system. Step C6 owns it.
