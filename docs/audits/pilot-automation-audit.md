# Audit: pilot pre-check, review pick-up button (ADR-045)

Reviewed in a fresh context by a review subagent on 2026-10-29, over the staged diff.

| Severity | Finding | Resolution |
|---|---|---|
| High | The bot announced a decision read from `review.yaml`, a file a participant can also write, so a forged "Verified" would have emailed the participant and hidden the ready-for-review label | Decisions are announced only when a commit by someone other than the pull request's author is on the branch (`--trust-reviews`). `tests/integration/test_precheck.py` |
| Medium | Text from the pull request (file names, loader messages) went into a bot comment unescaped, allowing mentions and links | `_safe` strips code-span, link and mention characters at each source. Tested |
| Medium | `check-for-review` could merge a branch carrying changes outside `participant/` into the copy the app runs from | Refused before merging when the incoming diff leaves `participant/`. `test_handin.py` |
| Low | A failed extraction read as "nothing submitted" | The empty-folder fallback now applies only when `participant/` is absent |
| Low | A symlink in the pull request could be followed on the runner | Links are deleted after extraction |
| Low | `fork_owner` is interpolated into a jq filter | Not changed: it comes from the participant's own Git remote, so only they can affect their own output |
| Low | Actions pinned by tag, not commit SHA | Not changed: matches the existing CI workflow; noted for a later hardening pass |

Residual limit: commit authorship is not signed, so a participant who sets another person's
email on a commit can still make the bot treat a forged review as trusted. The comment says
what the record contains; verified completion still requires the recorded decision, which the
application's own guards produce.
