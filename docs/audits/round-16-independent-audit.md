# Release Audit — Round 16

Status: **complete.** Twenty-two findings returned. Twenty were accepted after verification,
one is a question for the program owner, and one suspicion was not reproduced. Every accepted
finding is fixed or documented. Every code fix carries a test that was shown to fail with the
fix reverted.

Commit under audit: `a31bbf9` on `main`, the merge of round 15.
Predecessor: `docs/audits/round-15-independent-audit.md`.

## Method

Three lenses, each given a shallow clone (`git clone --depth 1`, remote removed) of
`7a8f00e`, a throwaway commit that deletes `docs/audits/` and the design guide's status part.
The engine lens ran on the larger model. The curriculum lens drove every action through a
real Chromium browser. An API spend limit stopped all three partway; each was resumed from its
own transcript after checking its working copy for leftover state. The tooling lens reports
that a second copy of itself worked in the same working copy after the resume. Neither used
a Git write command, and the copy was clean at the end.

## Findings

Every finding was verified here by reproduction or by reading the code at the cited line.

### Curriculum

| ID | Severity | Finding | Resolution |
|---|---|---|---|
| L1 | Low | Recording a decision does not re-run the secret scan. The review page warns from the last build, and an approval is not blocked by a finding. | Kept as designed: the scan is the participant's gate. `docs/guides/REVIEWER.md` and the review page say the scan is not re-run at decision time and does not block approval. |
| L2 | Question | DH7's title reads "no unresolved blocking or high findings", while its note and every round so far require a round that finds nothing. | Not changed. Which reading closes DH7 is the program owner's decision. Rounds continue on the stricter one. |

### Engine

| ID | Severity | Finding | Resolution |
|---|---|---|---|
| E1 | High | The `openai-key` digit lookahead was unbounded, so `sk-sk-sk-…` was quadratic: 80 KB took 6 seconds and a 2 MB file did not finish in 14 CPU-minutes, holding the locks during `mark-evidence-ready`, submission and `build`. Timed here: 20 KB 0.35 s, 40 KB 1.38 s. | The lookahead is bounded at 200 characters. A test checks every pattern scales near-linearly (4× input, ratio under 8) rather than against a wall-clock limit. |
| E2 | High | `scan_text` compared each match with every earlier one. 95,000 distinct `AKIA…` keys in 2 MB took 497 seconds. | Matches are merged as sorted, disjoint spans in linear time. Scaling test. |
| E3 | Medium | The `PROOF.md` preview decoded UTF-8 only, so a UTF-16 token that `mark-evidence-ready` refused was readable in the generated evidence and review pages. | The preview uses the scan's decoding before redaction. Test. |
| E4 | Medium | `password=[Pr0d]Sup3rS3cretValue` redacted to `password=[REDACTED]Sup3rS3cretValue`, which then scanned clean, and `password=[REDACTED]realvalue` was never detected. | The bracket capture takes the text glued after the bracket, so redaction covers the whole value. Tests. |
| E5 | Medium | `${DB_PASSWORD:-Sup3rS3cretValue9}`, the docker-compose default shape, was a placeholder because only the leading `${` was checked. | Only an exact `${NAME}` wrap is a placeholder. Test. |
| E6 | Medium | An unquoted `DB_PASSWORD=Tr0ub4dor(3)xyz` was not detected, though the docs said it was. | A paren or brace excuses a value only when the value has the shape of a call or subscript. Test. |
| E7 | Medium | Dotted passphrases such as `correct.horse.battery.staple` were treated as attribute paths. | The exemption applies only to known code roots (`self`, `config`, `os` and similar). Test. |
| E8 | Low | `render_inline` did not neutralize the request-token placeholder, so an authored acceptance criterion could show the live token on a served quest page. Low because only the curriculum author writes that text. | Every render path neutralizes it. Test against a served page. |
| E9 | Low | The suggested `git add` printed proof paths unquoted, including spaces and `$(…)`. | Each path is shell-quoted. Test. |
| E10 | Low | The hash folded CR bytes in any content without a NUL byte, so UTF-16 text with no ASCII collided: changing 不 to 上 kept the hash. | Line endings are folded only in content that is valid UTF-8 and has no NUL byte. ADR-031 amended. Tests. |
| E11 | Low | Misses: XML `<password>` elements, YAML block scalars under a secret key, `curl -u user:token`, the keywords `DB_PASS` and `PWD`. | Patterns and keywords added. Bare `pass` stays out, because it collides with `bypass` and with the vendored axe bundle. Tests. |
| E12 | Low | Files were skipped by extension only, so a plaintext token in `terminal.pdf` or `env-backup.zip` passed. | Files are skipped by their leading bytes (PDF, ZIP, PNG, JPEG, GIF, WEBP), so a renamed text file is scanned. Office documents share the ZIP signature and stay unread, as documented. Test. |
| S1 | Low | The participant-root refusal compared paths case-sensitively, so `./Content` would pass on a case-insensitive filesystem. Suspected by the lens and fixed without a macOS reproduction. | Paths are compared casefolded. Test. |
| S2 | Low | Review archives were named to the second, so two decisions in one second overwrote the older archive. Suspected by the lens and reproduced by the fix branch with a frozen clock. | Archive names carry the random suffix review and submission IDs already use. Test. |

### Tooling, tests, documentation

| ID | Severity | Finding | Resolution |
|---|---|---|---|
| F1 | Medium | The strictly-older `quest_version` rule had no test at the boundary, so `<` changed to `<=` passed. The lens rated F1 to F3 High. They are Medium here: the code was right. | Test at the same version. |
| F2 | Medium | No test posted the real shape of an unchecked checkbox, with the acknowledge key absent. | Test, failing when the default is flipped. |
| F3 | Medium | The JWT header bound was guarded only by a timing test that passed at 0.76 s and 2.85 s on two machines with the bound reverted. | A direct test of the bound, independent of speed. |
| F4 | Medium | Following the authoring guide to add a quest left `make check` failing on the README's quest and test counts, which the guide never mentioned. | The guide names the rows to update, and the count tests' messages say which row and point at the guide. |
| D1 | Medium | The design guide's security and data parts described the scanner and hash of three rounds ago. | Updated and regenerated as v1.2.0. The status part says round 16 is in progress. |
| D2 | Low | A stale test count in `docs/TRACEABILITY.md`. | Reworded without a count. |

## Gates

| Gate | Result |
|---|---|
| `make check` | pass — 1181 passed, 56 deselected |
| `make test-ui` | pass — 56 passed |
| `make validate-content` | pass — 8 quests, 8 regions, 4 badges, 1 track, 0 warnings |
| `make verify-package` | pass |
| Clean clone at `7a8f00e`, by the tooling lens | pass, apart from F4 with a sample quest added |
| A new quest added by following the authoring guide | picked up by the catalog, region page, tag pages and all four indexes, with no template or code change |
| Each fix reverted one at a time | every new test failed with its fix reverted, by the branch that wrote it |
| Guards mutated by the tooling lens | 21 mutations, 18 caught, apart from F1 to F3 |
| CI on this branch | see the pull request |

The three fix branches (`fix/r16-scan`, `fix/r16-web`, `fix/r16-integrity`) merged without a
conflict. The test counts were recounted once after the merge.

## Verdict

**Round 16 does not close DH7.** It found two high findings and no blocking one. Both are
the same kind as round 15's E5: a pattern or a loop whose cost grows with the square of the
input, reached with a 2 MB evidence file. The timing test round 15 added could not see them,
because it tried three inputs and not every pattern. The new test checks how each pattern's
time grows, so it does not depend on the machine's speed.

The curriculum lens found nothing above Low. All eight quests were completed and reviewed
through real browser forms with realistic redacted evidence, a CRLF-only edit did not count
as changed, and every planted token was caught.

Round 17 should run against the merge commit with the same three lenses, each in a shallow
clone. Point it at the new patterns and placeholder rules (E4 to E7, E11), content-based
skipping (E12), the UTF-8 rule in the hash (E10), and the tests added this round, mutated the
same way.
