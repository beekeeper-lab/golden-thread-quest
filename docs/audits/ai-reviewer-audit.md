# Audit: automatic reviewer (ADR-046)

Reviewed in a fresh context by a review subagent on 2026-10-29, against
`docs/design/08-ai-reviewer-specification.md`. Nothing blocking.

| Severity | Finding | Resolution |
|---|---|---|
| High | The sample was chosen by a hash of a participant-written id, so an id could be picked to dodge it | Salted with a secret the participant lacks. Tested |
| High | A quest with no acceptance criteria could be approved with no quote | Escalates. Tested |
| Medium | A quote was not tied to its criterion (a heading, the participant's claim, one line for every criterion) | 20-character minimum, may not repeat the criterion, one line proves at most three. Tested |
| Medium | A dispatch and the sweep could apply one review twice, and the loser escalated a decided hand-in | A lost race, or an attempt already decided, is skipped. Tested |
| Medium | One failed review leg blocked every apply | Each apply tolerates a missing plan. Workflow |
| Medium | A live push made the pre-check clear the reviewer's labels a minute after they were set | Live mode adds none; documented |
| Medium | If the bot's real login differed from the commit's, decisions were never announced | The commit is made under the token's own login and no-reply address |
| Medium | A clone timeout or a deleted fork crashed apply with a traceback | Any failure escalates. Tested |
| Low | A dangling link in the clone slipped the link check | `is_symlink` without `exists`. Tested |
| Low | System Git config and a test-only protocol setting applied in production | `GIT_CONFIG_NOSYSTEM`; setting removed |
| Low | Apply did not compare the fetched commit with the plan's | Compared; mismatch skips |
| Low | Code under a hidden folder was invisible to the "proof depends on code" rule | Recorded before the hidden-folder skip |
| Low | A re-run re-sends the "needs a person" notification | Accepted: each participant push is a new evaluation, and the comment is protected by its marker |

Residual limits are in the specification (section 9) and ADR-046.
