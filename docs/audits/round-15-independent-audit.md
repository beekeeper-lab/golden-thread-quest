# Release Audit — Round 15

Status: **complete.** Twenty-one findings returned and all twenty-one were accepted after
verification. Five severities were set differently from the lens. Every accepted finding is
fixed except E10, which is narrowed and stated, and E12's right-hand glue case, which is
documented. Every code fix carries a test that was shown to fail with the fix reverted.

Commit under audit: `95b173e` on `main`, the merge of round 14.
Predecessor: `docs/audits/round-14-independent-audit.md`.

## Method

Three lenses, each given a shallow clone (`git clone --depth 1`, remote removed) of
`3692502`, a throwaway commit that deletes `docs/audits/` and the design guide's status part.
Each clone held one commit, so no earlier audit record was reachable. Each lens was given only
paths, a commit and the areas round 14 named. The engine lens ran on the larger model. The
curriculum lens drove every action through a real Chromium browser.

No lens cited an earlier audit.

## Findings

Every finding was verified here by reproduction or by reading the code at the cited line.

### Curriculum

| ID | Severity | Finding | Resolution |
|---|---|---|---|
| L1 | Medium | The evidence page's repository panel is a reading taken at build time with nothing saying so. It said "Evidence committed: yes, 0 changed" after a committed proof file was edited, until the next rebuild. The lens rated it High. It is Medium here: it is round 14's C4 on another page, and the submission itself re-reads the files. | The panel names the build it reflects, says it is not a live read, and words its answer as "as of this build". `docs/USER-GUIDE.md` says the same. Test against a real repository through commit, edit and rebuild. |
| L2 | Low | An approval that had to acknowledge evidence changed since submission recorded that fact only in the reviewer's free-text statement. | `review.yaml` gains an optional `acknowledged_changed_evidence`, written only when an approval crossed that gate. Older records stay valid. Four tests. |

### Engine

| ID | Severity | Finding | Resolution |
|---|---|---|---|
| E1 | High | The scan flagged the application's own redaction output: `JIRA_API_TOKEN=[REDACTED]` in a log was refused by `mark-evidence-ready`, and so was the masked token `gh auth status` prints. | The unquoted-assignment pattern reads a bracketed value whole, and a value that is mostly mask characters is a placeholder. A test runs the scan over the redaction of every string in the detection corpus and expects nothing. |
| E2 | High | A Jira API token in `Authorization: Basic …`, as a `curl -v` log shows it, passed the scan. Only `Bearer` headers were matched. | `Authorization` and `Proxy-Authorization` headers with the `Basic` or `token` scheme are detected. Three tests. |
| E3 | Medium | A file name that is not UTF-8 crashed the evidence hash, so `build` stopped with a traceback carrying absolute paths and `record-review` failed, while `validate` reported no warning. The lens rated it High. It is Medium here: renaming the file recovers, and nothing is lost. | Names are encoded losslessly. Test. Checked here by submitting a package holding `r\xe9sum\xe9.txt` and building. |
| E4 | High | The evidence hash read raw bytes, so Git's line-ending conversion between a Windows participant and a Linux or macOS reviewer made an ordinary submission read as changed since submission. The same happened for a file name in NFC on one machine and NFD on another. Reviewers would learn to acknowledge by habit. | Content with no NUL byte is hashed with CRLF and lone CR folded to LF, and names are NFC-normalized. Binary content and real edits still change the hash. ADR-031 amended: a package hashed before this change reads as changed once, and the reviewer re-reads it and acknowledges. Seven tests. |
| E5 | Medium | The `basic-auth-url` and `jwt` patterns took quadratic time. A 120 KB file took `build` from under a second to 36 seconds, and a file at the 2 MB ceiling would take hours with the locks held. | Both patterns use bounded quantifiers. A test scans a 2 MB adversarial file under five seconds. |
| E6 | Medium | A token was missed in a UTF-8 log with a UTF-16 tail (what PowerShell 5.1 `>>` appends), in UTF-16 text without a byte-order mark, and in UTF-32 with one. | The scan reads each file under every plausible decoding and merges the findings. Four tests. |
| E7 | Low | Round 14's E8 fix was incomplete: a code span or autolink in `PROOF.md` still produced the exact attribute the service substitutes the request token into. No automatic egress was found. | Rendered Markdown carries the placeholder with its underscores as character references, so no participant or third-party text can hold it. Test against a real server with a code span and an autolink. |
| E8 | Medium | `acknowledge_changed_evidence` was read with `bool()`, so the string `"false"` over the JSON API, and any value at all in a form, approved evidence the reviewer never re-read. | Both paths use the allowlist the confirmation already used. Tests on the action path and the form path. |
| E9 | Medium | `submit-for-review` suggested a `git add` of the package and `progress.yaml` only, leaving out declared proof outside the package, so the reviewer found those proofs missing. The text CLI read the wrong key and printed no next steps at all. | The suggestion names every declared proof path, and the CLI prints it. Three tests. |
| E10 | Low | Round 13's E7 guard on a forged `locally_validated` could be passed by also editing the attempt's `content_hash`. | Narrowed, not closed. The excuse now needs the claimed `quest_version` to be strictly older than the published one, which removes the claimed-future-version case. Forging a hash for a genuinely older version stays possible, because the application keeps no hash of past versions. That is the kind of forgery ADR-030 accepts, and `locally_validated` does not verify anything. A test pins the remaining case as accepted. |
| E11 | Low | The documentation said screenshots were the scanner's only blind spot. `.pdf` and `.zip` are skipped, and `.docx`, `.xlsx`, `.gz` and similar pass as unreadable compressed bytes. | The release notes and the security document list every kind the scan cannot read. |
| E12 | Low | PGP private key blocks were missed, a password holding `(`, `{` or `}` was treated as a placeholder, the Jira quest's own `nextPageToken` was a false positive, and a token glued on its right to `_` or a letter was missed. | The PGP block is detected, the placeholder rule accepts only real template forms, and the pagination fields no longer fire. The right-hand glue case is documented as a known gap: every fix tried here brought false positives back. Tests for the first three. |
| E13 | Low | `GTQ_PARTICIPANT_ROOT` pointed at `content/` was accepted, and participant state was written into the curriculum. | A participant root that is, lies inside, or contains a program-owned folder is refused. Roots elsewhere stay trusted (ADR-042, amended). Eleven tests. |

The engine lens also named three suspicions. S1, NFC against NFD names, was reproduced and
fixed with E4. S2, the runner signalling a reused process-group ID after the child is
reaped, and S3, any local process reading the request token from a served page, were not
reproduced. S3 is within the threat model: the service trusts the local user.

### Tooling, tests, documentation

| ID | Severity | Finding | Resolution |
|---|---|---|---|
| T1 | Medium | No test defended the case sensitivity of the distinctive secret prefixes. | Test for each prefix, in and out of its real case. |
| T2 | Medium | Only the `key` query parameter was tested, not `token`. | Test. |
| T3 | Medium | The endianness guess for UTF-16 without a byte-order mark was untested. | Tests for both byte orders. |
| T4 | Medium | Detection of an empty declared directory was untested. | Test that an empty directory is not detected as present. |
| T5 | Medium | The check that a verified state's review belongs to this attempt, and not another attempt of the same quest, had no test. Deleting it passed the suite. The lens rated it High. It is Medium here, as are T2 and T3: the code was right. | Test with a real approval of another attempt, failing with the check deleted. |
| T6 | Medium | The mapping of a validator's environment failure to "warning" was untested. | Test. |

## Gates

| Gate | Result |
|---|---|
| `make check` | pass — 1109 passed, 56 deselected |
| `make test-ui` | pass — 56 passed |
| `make validate-content` | pass — 8 quests, 8 regions, 4 badges, 1 track, 0 warnings |
| `make verify-package` | pass |
| Clean clone at `3692502`, by the tooling lens | pass: `make setup`, `make check`, and `make check` beside a running server |
| A new quest added by following the authoring guide | picked up by the catalog, region page, prerequisite link, evidence page and search index, with no template or code change |
| Each fix reverted one at a time | every new test failed with its fix reverted, by the branch that wrote it |
| Guards mutated by the tooling lens | 20 mutations of 15 guards, 14 caught, apart from T1 to T6 |
| CI on this branch | see the pull request |

The three fix branches (`fix/r15-scan`, `fix/r15-integrity`, `fix/r15-web`) merged without a
conflict. The test counts in `README.md` and `docs/RELEASE-NOTES.md` were recounted once after
the merge.

## Verdict

**Round 15 does not close DH7.** It found three high findings and no blocking one.

E1, E2 and E4 are all about evidence participants really produce: a redacted log, a `curl -v`
transcript, a file saved on Windows. Earlier rounds tested the scanner and the hash against
tokens and edits. This round tested them against ordinary work, and that is where they failed.

What held: nothing but a reviewer's approval reached verified state. All eight quests were
completed and approved through real browser forms, with claimed and verified XP equal on every
page. The scan caught every token shape the curriculum lens planted, in every proof location,
including declared proof outside the package. axe found no violation at either width.
The host, origin and token checks, the allowlisted actions, the link refusals at every path
the application owns and the scan and hash boundaries for declared proof all held.

Round 16 should run against the merge commit with the same three lenses, each in a shallow
clone. Point it at:

- the scan's multiple decodings and the new header, placeholder and mask rules, for misses
  and for false positives in real evidence;
- the normalized hash, including files that change only in line endings and content
  that is almost text;
- the participant-root refusal (E13) and the placeholder neutralization (E7);
- the next steps and evidence page as a participant on a fresh clone follows them;
- and the tests added this round, mutated the same way.
