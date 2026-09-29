# Release Audit — Round 17

Status: **complete.** Round 17 found one blocking and five high findings, so it does not
close DH7 under the program owner's rule of 2026-09-28 (a round must find no blocking or
high finding at all). Every accepted finding is fixed or explicitly deferred below. Every
code fix carries a test that was shown to fail with the fix reverted.

Commit under audit: `bc190e9` on `main`, the merge of round 16, plus `9a922f8` (the DH7
closing rule, documentation only).
Predecessor: `docs/audits/round-16-independent-audit.md`.

## Method

Round 17 ran in two passes, because the first was cut off before it was recorded.

**The earlier pass (2026-09-28, the A-series).** A previous session made a lens commit
(`lens/r17`) and six fix branches (`fix/r17-scan`, `-evidence`, `-hash`, `-validator`,
`-web`, `-tests`) under `.worktrees/`. It never wrote a findings record and never merged.
Its findings are known only from its commit messages and the tests it added, so their
severities were not recorded. This pass found the branches, merged every fix that the second
pass had not also made, and relabelled that pass's IDs `A-<id>` in code and documents so
they do not collide with the second pass's.

**The second pass (2026-09-29).** Three lenses, each given a shallow clone
(`git clone --depth 1`, remote removed) of `b257b04`, a throwaway commit on top of
`9a922f8` that deletes `docs/audits/` and the design guide's status part:

- **Engine:** the secret scanner, evidence hash, local service, state machine, build and
  validator runner, with 27 adversarial 2 MB inputs for super-linear behaviour.
- **Curriculum:** all eight quests completed and reviewed through a real Chromium browser
  driven by Playwright, as participant and reviewer, including a new quest added by
  following the authoring guide.
- **Tooling:** setup and every gate from a fresh clone, on Python 3.14 and on the 3.10
  floor; 64 mutations of guards; every documentation claim checked against the code.

Every finding was verified here by reproduction or by reading the code at the cited line.

## Findings — second pass

### Engine

| ID | Severity | Finding | Resolution |
|---|---|---|---|
| E1 | High | `private-key-block` matched only the BEGIN line, so redaction left the base64 key body and the END line readable in the generated evidence and review pages while reporting the text redacted. | The match covers armor headers, base64 lines and the END line, bounded at 512 lines and linear however many BEGIN lines repeat. Tests for OpenSSH, encrypted RSA, PGP and a key cut off before its END line. |
| E2 | High | The assignment patterns needed the separator straight after the keyword, so `SECRET_KEY=`, `DB_PASSWORD_PROD=`, `secretKey:`, `passwordHash=` and `TRELLO_KEY=` were never scanned. `mark-evidence-ready` passed a Django secret key. | A bounded identifier tail is allowed after the keyword, with an upper-case `_KEY` keyword. A tail that says the value describes a credential (`password_file`, `token_expires_at`, `tokenizer`, `total_tokens`) excuses it. The earlier pass's A-E1 made the same fix, and its tests were ported. |
| E3 | Medium | The call-expression exemption made the close optional and ran on the lowered value, so `Pa55word(Winter2026!`, `Hunter2[prod-2026`, `Sup3rS3cretValue9)`, `{Sup3rS3cretValue9}` and `(Ab3dEfGh12xy)` were excused. | Merged with A-E5's `_is_code_expression`. A callee that mixes an upper-case letter with a digit is not code, and a placeholder or annotation admits no digit. Tests through the quoted and unquoted paths. |
| E4 | Medium | Missed: a quoted value holding the other quote or an escaped quote, `:=` and `=>`, `--password <value>`, `docker login -p`, `mysql -p…`, and cookies. | A quote branch for each quote type with escapes, the two separators, and three new patterns (`cli-flag-credential`, `cli-login-password`, `cookie-header`). A bare `$NAME` is a reference, like `${NAME}`. Tests. |
| E5 | Medium | An approval did not re-run the scan, so evidence edited after submission could be verified while holding a token the submission gate refuses. | `record_decision` scans on approval and refuses on any finding. A needs-changes or rejected decision still records. The review page and `docs/guides/REVIEWER.md` say so. Test. |
| E6 | Low | The evidence hash has no type tags: an empty directory and a file containing `dir` hash alike. | **Deferred (D13).** Tagging every chunk changes every stored digest, so every approved attempt would read as "changed since approval". The collision hides nothing a reviewer needs to see. |
| E7 | Low | `GIF87a`, `GIF89a` and `%PDF-` are plain ASCII, so a text file opening with one was skipped unread. | A file with one of those three signatures is skipped only when its first 64 KB are not NUL-free UTF-8. It is read with the same non-blocking regular-file read A-E13 introduced. The earlier pass's A-E12 made an equivalent fix and was superseded by this one. Test. |
| E8 | Low | Findings were deduplicated by excerpt, which for a value under 12 characters is only its length, so two passwords of one length showed as one. | Each match carries a truncated SHA-256 fingerprint of its value, and deduplication uses it. A-E16 was superseded. A-E10's preview check uses the same fingerprint. Test. |
| E9 | Low | `atomic_write` did not fsync the directory after the rename. | A best-effort directory fsync after the rename. Test. |
| — | Suspicion | A validator that never reads a spec larger than the pipe buffer could block the runner's stdin write. A validator calling `setsid` escapes the timeout kill. | Not reproduced, since the shipped bootstrap reads stdin first. The second is release-notes limitation 11. |

### Curriculum

| ID | Severity | Finding | Resolution |
|---|---|---|---|
| L1 | Blocking | A file at the literal authored path (`…/<quest>/attempt-001/…`) counted as detected. The secret scan, evidence hash and proof digests read only the real `<prefix>-attempt-001` package, so a token there was submitted with `secret_scan_clean: true` and could change after approval with no banner. | A proof path in the quest's own evidence area is only looked for inside the real package. Test that writes a token at the literal path. |
| L2 | High | Every proof row showed the authored `attempt-001` path, which never exists. This caused L1 and sent reviewers to a missing file. | `proof_location` shows the path inside the participant's actual package on the quest, evidence and review pages. Test. |
| L3 | High | `.card { display: flex }` beat the browser's `[hidden]` rule, so catalog and region filtering changed the count and hid nothing. The UI test checked the attribute, not visibility. | `[hidden] { display: none !important }`. The browser test counts visible cards. It failed with the rule removed. (A previous session's `fix/r17-web` had the same fix.) |
| L4 | High | The Jira quest asks for a run against a chosen fixture, but only the JSON API could pass `fixture_set`. The quest never said the output must carry the fixture's keys, and the failure blamed pagination. | An enum choice beside the run button and on the result page, `--param NAME=VALUE` on the CLI, and the run's parameters recorded in the result. The quest text says to sync against the fixture, and the hint names it. The clarification is not a version bump, per the authoring guide. Tests through the form and the CLI. |
| L5 | Medium | Evidence that changed after approval was flagged only on that attempt's review page, which nothing links to once it is verified. | Listed as "Changed since approval" on the review queue and on the evidence page. Test. |
| L6 | Medium | Environment Health lacked the build-time rows U09 asks for, and said "Unknown" for the service on a page the service built. | Application and content, Git, and output-directory rows, and the service's own status when it built the page. The write test and CLI presence stay under D7. Test. |
| L7 | Medium | The result page's rerun control was hard-coded disabled, and the page did not show the result file. | Enabled from the service's availability, with the parameter choice. The result file is listed. Test. |
| L8 | Medium | A refused review decision threw away the name, statement and findings. | The page script keeps the fields for that tab and restores them only when the page returns with a refusal. Checkboxes and the token are never kept. Browser test. |
| L9 | Medium | Findings could not name their acceptance criterion (ADR-016) or say what to change, though the schema had `required_change`. | An optional `criterion` (`ac-<n>`, refused when the quest has no such criterion) and "What to change" in the form, and `severity@ac-N:…::change` on the CLI. Both are shown to the participant and in the history. Tests. |
| L10 | Medium | Missed: a percent-encoded `%3Ftoken%3D…`, a Slack webhook URL, an Azure `AccountKey=`. | Encoded query parameters, plus `slack-webhook` and `azure-connection-key` patterns. Tests. The two low-grade misses, a base64-encoded token and a token in a PNG `tEXt` chunk, stay under D10. |
| L11 | Low | The evidence page explained "Locally validated" only in a tooltip. | The explanation is visible, as on the quest page. Test. |
| L12 | Low | Validator labels came from the ID. | The registry's `display_name`. Test. |
| L13 | Low | Old findings led a resubmitted attempt's page as a live alert. The queue was sorted by title. History dropped each finding's evidence. There is no success notice. | Findings show as "last time" once resubmitted, the queue is oldest first, and history shows evidence, criterion and change. **Success notices deferred (D14):** the rebuilt page already shows the new state. |
| L14 | Low | Verified and locally validated shared the ✓ glyph. | Locally validated is ☑; verified keeps the prototype's ✓. Test. |
| L15 | Low | The quest page repeats "Required evidence" and orders sections after stretch goals. A region with no badge had no badges section (U03). | The badges section always renders. **Section order deferred (D15):** the body renders in authored order and the repeated heading has its own landmark name (round 13 C3). |
| L16 | Low | "Why this one" reasons appeared twice, and a participant with everything verified was told to browse for more. | The card omits reasons the panel lists, a completion state was added, and "Available XP" is relabelled "XP in the curriculum". Test. |
| R1 | Low | Found while fixing E5: an unreadable file was worded as "something secret-like". | Its own `unreadable` kind and wording on every surface. Test. |

### Tooling, tests, documentation

| ID | Severity | Finding | Resolution |
|---|---|---|---|
| F1 | Medium | The two scaling tests were flaky under load: a few-millisecond baseline read as 9.5× for 4× input. | Both take the best of three timings. A real quadratic still shows 16×. |
| F2 | Medium | No test pinned the transition table, so `needs_changes → submitted` passed. | `tests/unit/test_state_machine_table.py` pins every state and action. |
| F3 | Medium | The origin port and scheme checks, and full-length token comparison, were untested. | Tests for another port (A-T1, from the earlier pass), `https` on the same host and port, and a token differing only in its last character. |
| F4 | Medium | The strictly-older version rule was untested at equality and above. | Equal (A-T2) and newer cases. |
| F5 | Medium | The mask-ratio threshold was not pinned. | Values either side of 0.6. |
| F6 | Low | The allow pragma's exact form was not pinned. | A line that only mentions the tool is scanned. |
| F7 | Low | The hash's final UTF-8 completeness check was untested. | A file ending in a cut-off character with a lone CR. |
| F8 | Low | Backup guards that duplicate other checks are untested. | No change: each is covered by the check it backs up. Direct tests are optional. |
| F9 | Low | No per-test timeout, so a quadratic regression would hang instead of fail. | **Deferred (D16):** needs a new test dependency. F1's best-of-three keeps the inputs small. |
| F10 | Low | mypy targeted 3.11, above the 3.10 floor. | `python_version = "3.10"`, which is clean. |
| F11 | Low | `make setup-ui` does not install Chromium's system libraries as CI does, and `pre-commit` is not in the extras. | Both are documented in `docs/SETUP.md` and `CONTRIBUTING.md`. |
| F12 | Low | Side note from the tooling lens: `$(echo Sup3r…)` was a template placeholder. | A substitution that only echoes or prints a literal is a value. Test. |
| D1 | Medium | Release notes said recording a decision needs the service; the CLI records one without it. | Reworded. |
| D2 | Low | The release-notes header said "pilot candidate, 2026-09-17", the guide pointer disagreed with the README, and the deferral IDs were wrong. | Corrected. |
| D3 | Low | Implementation details said "six" forms of claim (seven), the stage table stopped at 8, and there was a "Count" column with no counts. | Corrected. |
| D4 | Low | The design guide's ADR count, status part and archive-name form were stale. | Updated and regenerated with this round's status (see Gates). |
| D5 | Low | The authoring guide did not mention the registry's `quest_ids`, so copying a quest with a validator failed. | Step 7 says so. |
| D6 | Low | `PACKAGE-MANIFEST.md` listed eight schemas and called the templates illustrative. | Corrected. |

## Findings — earlier pass (A-series)

From the earlier pass's commit messages; severities were not recorded. Each fix below was
merged with its tests, which pass on the merged branch.

| ID | Finding, as the commit describes it | Status |
|---|---|---|
| A-E1 | Keyword with an identifier suffix | Same as E2; tests ported |
| A-E2 | Quoted, glued, clustered and continued `curl -u` credentials | Merged |
| A-E3 | Short brackets glued to a value; redact through a later `]` | Merged |
| A-E4 | Only a value that is entirely a template is excused | Merged (F12 narrows it further) |
| A-E5, A-C2 | Only real code shapes are call expressions; read past a glued `}` | Merged with E3 |
| A-E6 | Every segment of a dotted attribute path is checked | Merged |
| A-E7 | Compound, attributed and multi-line XML credentials, and attribute values | Merged |
| A-E8 | YAML block-scalar indicators and comments | Merged |
| A-E9 | `PWD`/`OLDPWD` with a path value is not a finding | Merged |
| A-E10 | A PROOF.md preview is withheld when another decoding finds a secret | Merged, using E8's fingerprint |
| A-E11 | Markdown- and HTML-escaped tokens are scanned and redacted | Merged |
| A-E12 | A signature followed by text no longer skips the scan | Superseded by E7 |
| A-E13 | The header read uses `O_NONBLOCK` and an `fstat` check | Merged; E7's text sample uses it too |
| A-E14, A-E15 | The hash folds line endings where Git converts them, and hashes directory link text | Merged; ADR-031 amended; a one-time hash change in the release notes |
| A-E16 | Deduplicate on the value, not the excerpt | Superseded by E8 |
| A-E17 | A value glued across `,` or `;` is read whole | Merged |
| A-C5 | The repository-foundation validator scans with the submission gate's rules | Merged |
| A-T1, A-T2 | Origin port test; version boundary test | Merged (F3, F4) |
| A-D1 | Implementation details omitted `safe_io.py` | Merged |

One regression was caught during the merge. This pass's separator change stopped
`password:` with the value on the next, indented line from being read, which is valid YAML.
A-E1's test pinned that case. The separator may again cross one line break, but only for a
bare credential word; a suffixed name like `class SecretMatch:` does not read that way.

## Deferred

| ID | What | Why |
|---|---|---|
| D13 | Type-tagged evidence hash chunks (E6) | Every approved attempt would read as changed once; the collision hides nothing |
| D14 | Success notices after an action (L13) | The rebuilt page already shows the new state |
| D15 | Quest-page section order (L15) | The body renders in authored order; a content-model decision |
| D16 | A per-test timeout for the scaling tests (F9) | Needs a new test dependency |

D7 (live Environment Health) and D10 (wider scanner coverage) absorb the rest of L6 and L10.

## Gates

| Gate | Result |
|---|---|
| `make check` | GATES-PENDING |
| `make test-ui` | GATES-PENDING |
| `make validate-content` | GATES-PENDING |
| `make verify-package` | GATES-PENDING |
| Repository secret scan | 0 findings |
| Clean clone at `b257b04`, by the tooling lens | pass (1181 and 56; Python 3.14 and 3.10) |
| Each fix reverted one at a time | every new test failed with its fix reverted (see "Mutation check") |

### Mutation check

MUTATION-PENDING

## Verdict

**Round 17 does not close DH7.** It found one blocking finding (L1) and five high (E1, E2,
L2, L3, L4). The blocking one and two of the high ones came from the one lens that drove
the product as a participant would: the path the page showed was not the path the gates
read, and the filter the tests checked was not the filter people saw. The engine's two high
findings were the secret scan covering less than its documentation said.

Round 18 should run against this round's merge commit with the same three lenses, each in a
shallow clone. Point it at the proof-path mapping (L1, L2), the new run parameters (L4), the
approval re-scan (E5), the merged scanner (E1–E4, L10 and the A-series together), and the
tests added this round, mutated the same way.
