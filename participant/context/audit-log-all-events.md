# Audit log (chained)

Written only by `auditlog.py append`. New rows go at the bottom. Earlier rows are never
edited or removed; a correction is a new row. The fields, the five kinds and the chain
are explained in `participant/context/audit-log-format.md`.

| Seq | Time (UTC) | Kind | Action | Target | Actor | Confirmed | Outcome | Ref | Chain |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 2026-11-11 15:36:22 | read | Read the ticket's current assignee | pretend tracker, ticket SIM-101, field assignee | beaubrown (ran run_workflow.py) | n/a | Done. Assignee is user-a. Nothing changed. |  | 57d9f564d0a86882 |
| 2 | 2026-11-11 15:36:22 | preview | Previewed changing the assignee from user-a to user-b | pretend tracker, ticket SIM-101, field assignee | beaubrown (ran run_workflow.py) | Not yet. Asked at the prompt; the answer is in a later row. | Shown on screen. Nothing changed. |  | 14f8e036b03aeaa6 |
| 3 | 2026-11-11 15:36:25 | failure | Tried to change the assignee from user-a to user-b (attempt 1) | pretend tracker, ticket SIM-101, field assignee | beaubrown (ran run_workflow.py) | Yes, typed at the prompt | Failed. Reason: the pretend tracker did not answer in time (code SIM_TIMEOUT). The tool does not yet know whether the change was applied. | 2 | 3b049cd28d79e33f |
| 4 | 2026-11-11 15:36:25 | recovery | Read the ticket again after the failure | pretend tracker, ticket SIM-101, field assignee | beaubrown (ran run_workflow.py) | n/a | Assignee is still user-a. The failed attempt changed nothing. The same change can be tried again. | 3 | f289a2f03a67ed3f |
| 5 | 2026-11-11 15:36:30 | confirmed write | Changed the assignee from user-a to user-b | pretend tracker, ticket SIM-101, field assignee | beaubrown (ran run_workflow.py) | Yes, typed at the prompt | Done. Applied once, on attempt 2. | 2 | 666ee70460346ef4 |
| 6 | 2026-11-11 15:36:30 | read | Read the ticket back to confirm the change | pretend tracker, ticket SIM-101, field assignee | beaubrown (ran run_workflow.py) | n/a | Done. Assignee is user-b. |  | 57fdd8a580aadb9b |
