<!-- Report of a second independent AI reviewer (a fresh Claude subagent), 2026-11-11, asked two narrow questions about the tool AFTER the fixes that followed review 1. Copied by script from the reviewer's output, not retyped. Its finding numbers (F1-F7) are its own and are not the same as review 1's. -->

## Findings (all on copies in a temp folder; originals compared byte-identical to my copies at the end)

**F1. Q1 answer: no. 0 of 92 changed files passed.** Reproduced. With the anchor copy unchanged (asserted byte-equal after each run), every file that differed from the log copy got `check` exit 1. The unchanged control got exit 0. Limits of this claim: it covers the 92 attempts listed below, not every possible file. Inferred from reading the code, not run: the only remaining route is a 64-bit truncated SHA-256 match on the last Chain value, which I did not attempt.

**F2. `append` crashes with a Python traceback on a `--ref` of more than 4300 digits.** Reproduced 3 of 3 (4301 nines, 5000 nines, 4300 zeros then `1`). Exit 1, `ValueError: Exceeds the limit (4300 digits) for integer string conversion`. Log and anchor unchanged, `check` afterwards exit 0. 4300 digits (`0`*4299 + `1`) is accepted as Ref 1.
Repro: `python3 auditlog.py append COPY.md --kind read --action a --target t --actor a --confirmed n/a --outcome o --ref "$(python3 -c "print('9'*4301)")"`

**F3. `check` crashes with the same traceback if a Ref cell in the file holds 5000 digits.** Reproduced once (Q1 attempt 92). Exit 1, which is the same exit code as an ordinary failed check, but no `PROBLEM:` or `CHECK FAILED` line is printed. It is not a pass.

**F4. `append` crashes with a traceback when an argument holds bytes that are not valid UTF-8.** Reproduced 4 of 4 for `--action` (0xFF, and ED A0 80), `--actor` (0x80), `--ref` (0xFF). Exit 1, `UnicodeEncodeError: 'utf-8' codec can't encode character '\udcff'`. Nothing written, `check` afterwards exit 0. The same byte in `--kind` is refused cleanly (exit 2).
Repro (zsh): `python3 auditlog.py append COPY.md --kind read --action $'a\xffb' --target t --actor a --confirmed n/a --outcome o`

**F5. Long letter-only values make `append` and every later `check` slow, growing with the square of the length.** Reproduced. Measured, single field of the letter `a` repeated:

| letters | append | check afterwards |
|---|---|---|
| 10,000 | 0.7 s, exit 0 | 0.4 s, exit 0 |
| 20,000 | 2.3 s, exit 0 | 1.2 s, exit 0 |
| 40,000 | 9.5 s, exit 0 | 4.9 s, exit 0 |
| 200,000 | no result after 20 s (killed by my harness); an earlier run of the same list was still at 99% CPU after 2 min 5 s when I killed it | not reached |

Cause observed by timing each rule on 20,000 letters: the "partly masked value" pattern took 1.21 s, the other five 0.00 s. 240,000 characters with spaces (`"ab " * 80000`) appended instantly. I did not see 200,000 letters finish or fail, so "hangs" is not established, only "no result in the time given". Nothing was written when killed.

**F6. `append` accepts invisible and blank characters outside the four Unicode categories it screens, and `check` passes them.** Reproduced, each `append` exit 0 then `check` exit 0:
U+034F, U+FE0F, U+E0100, U+17B5 (all invisible, category Mn), U+3164, U+115F, U+FFA0 (blank Hangul fillers, category Lo), U+2800 (blank braille, So). A value made only of U+3164, or only of U+2800, satisfies the "not empty" rule, so a required cell can look empty. U+034F was also accepted in target, actor, confirmed and outcome. Separately, a log + anchor rewritten together with U+034F in a cell passes `check` (exit 0), while the same with U+200B fails on the hidden-character rule.
Also accepted, check passes: Cyrillic look-alikes, U+FF5C / U+2502 / U+2223 / U+01C0 (pipe look-alikes), `&#124;`, `&vert;`, `<br>`, `<!-- x`, `<script>...`, a `javascript:` Markdown link, `---`, a lone combining mark, 200 stacked combining marks, private-use, noncharacter and unassigned code points. What a renderer shows for these was NOT ASSESSED (no renderer run).

**F7. Not found: any accepted value after which `check` fails.** 0 of 152 attempts. Every `append` exit 0 was followed by `check` exit 0, and every refusal or crash left both files byte-identical.

## Document sentences my runs contradict

Paragraph beginning "`append` refuses a field that contains":
- Sentence 1 ("...or a control or hidden character..."): contradicted in part by F6. The four examples it names (tab, U+2028, zero-width, direction-override) were all refused. The broader phrase "hidden character" is not true for the eight characters in F6. Also, F4: invalid-byte values are not "refused", they crash.
- Sentence 3 ("`check` applies both rules to rows already in the log"): consistent for U+200B and for `Bearer abcdefgh12345` (each isolated in a rewritten log + anchor, exit 1 with the matching PROBLEM line). Same F6 caveat applies to "hidden".
- Sentence 4 (append refuses a failing log): consistent, 2 of 2 (note under table; one changed cell). Exit 2, files unchanged.
- Sentence 2 (credential shapes): NOT ASSESSED, apart from the bearer case above.

Numbered list under "How a changed row is caught":
- Item 1: every example it lists failed as stated. No contradiction.
- Item 2, last sentence ("If a cell is changed, or a row is removed or moved, that row's Chain value or the next row's no longer matches"): contradicted for removing the last row. That run printed exactly one problem, `anchor file records 6 rows but the log has 5`, and no chain problem. It is caught, but by item 3, not by the chain. Removing row 3 did produce a chain problem, as the sentence says.
- Item 3: consistent (rows cut from end, exit 1; every chain recomputed after an edit, exit 1 on anchor mismatch). "`append` updates it" consistent with the control.
- Item 4 (`--anchor-git-ref`): NOT ASSESSED.

## Q1 attempt table (anchor unchanged; all "differs = yes" except control; no tracebacks except 92)

| # | attempt | exit |
|---|---|---|
| 0 | control, unchanged | 0 |
| 1-6 | above the heading: text line; second table; whole log duplicated; BOM; blank line; one space | 1 each |
| 7-9 | heading text: one letter; one word; trailing space | 1 each |
| 10-13 | column labels: Actor to Agent; Seq to seq; Cyrillic A; two labels swapped | 1 each |
| 14-16 | separator row `:--`; separator with spaces; heading with CRLF | 1 each |
| 17-19 | between heading and rows: blank line; HTML comment; extra well-formed row 0 | 1 each |
| 20-22 | between rows: blank line; HTML comment line; `<!--` / `-->` lines around row 3 | 1 each |
| 23-25 | after rows: note with blank line; note without; `<style>` block | 1 each |
| 26-34 | end of file: extra newline; no final newline; trailing space, NUL, form feed, 0x1A; final newline replaced by U+2028, U+0085, CR | 1 each |
| 35-36 | CRLF everywhere; CRLF on one row | 1 each |
| 37-40 | row edge: trailing space, tab, 0x1F; leading space | 1 each |
| 41-46 | padding: doubled; removed; tab; NBSP; empty Ref cell with 1 space; with 3 spaces | 1 each |
| 47-50 | doubled leading pipe; doubled trailing pipe; no outer pipes; 11th empty cell | 1 each |
| 51-53 | inside a cell: double space; space to NBSP; case change | 1 each |
| 54-56 | one cell changed, chains kept; all chains recomputed; last row changed and rechained | 1 each |
| 57-61 | Cyrillic look-alike; U+200B; U+034F; U+202E; combining mark | 1 each |
| 62-65 | render tricks in a cell: `user\-a`; `user&#45;a`; `<s>..</s>`; `<!--` | 1 each |
| 66-70 | time +1 s; `T` separator; Seq `01`; Seq fullwidth digit; Ref `02` | 1 each |
| 71-74 | chain uppercased (row 3; last row); 17th hex char added; kind `Read` | 1 each |
| 75-78 | duplicate last row; first row; row 3 in place; duplicate last row renumbered and rechained | 1 each |
| 79-84 | swap rows 1/2; swap rows 5/6; delete last row; delete row 3; delete row 3 and rechain; delete all rows | 1 each |
| 85-87 | empty file; hand-chained row 7 with anchor not updated; 6 rows rebuilt and rechained | 1 each |
| 88-91 | overlong UTF-8 space; byte 0xFF; UTF-16 with BOM; UTF-16LE without | 1 each |
| 92 | Ref cell of 5000 digits | 1, traceback (F3) |

## Q2 attempt table (fresh copy per attempt; value in `--action` unless stated; "ok" = append exit 0 then check exit 0)

| attempt | append exit | check after |
|---|---|---|
| control | 0 | 0 |
| `a|b`, `a\|b`, LF, CR, tab, VT, FF, 0x1C, 0x1F, DEL, U+0085, U+2028, U+2029 | 2 refused | 0 |
| U+200B, U+200C, U+200D, U+2060, U+FEFF, U+00AD, U+202E, U+2066, U+061C, U+180E, U+E0041, U+FFF9, emoji with ZWJ | 2 refused | 0 |
| NBSP inside; NBSP at both ends (trimmed); U+3000; U+2003; U+202F; U+1680 | 0 | 0 |
| U+034F, U+FE0F, U+E0100, U+17B5, U+3164, U+115F, U+FFA0, U+2800; only U+3164; only U+2800 | 0 | 0 (F6) |
| lone combining mark; 200 stacked; NFD e-acute; U+FFFD; U+FFFF; U+E000; U+10FFFF; U+0378; emoji | 0 | 0 |
| Cyrillic look-alike; U+FF5C; U+2502; U+2223; U+01C0 | 0 | 0 |
| `---`; `:---:`; `&#124;`; `&vert;`; `<br>`; `<!-- x`; `<script>`; Markdown link; backtick; trailing backslash; `# x`; lone backslash | 0 | 0 |
| empty; spaces only; NBSP only; U+3000 only | 2 refused | 0 |
| `--action=-x`; `--action=--ref`; `--action=--` | 0 | 0 |
| `--action -x` (space form); missing `--outcome`; `--act=x` | 2, argparse usage error, no traceback | 0 |
| `--action` twice (last wins); `--ref=1 --ref=abc` | 0; 2 refused | 0 |
| 100,000 chars with spaces; 240,000 chars with spaces; 5,000 letters; 20,000 letters | 0 | 0 |
| 200,000 letters, no spaces | no result in 20 s (F5) | 0 (unchanged file) |
| target / actor / confirmed / outcome: empty; pipe; tab | 2 refused (12 runs) | 0 |
| target / actor / confirmed / outcome: U+034F | 0 (4 runs) | 0 |
| ref (kind read): `0`, `7`, `8`, `-1`, `+1`, `1.0`, `1e0`, `0x1`, `1_0`, fullwidth 1, Arabic-Indic 3, superscript 2, `abc` | 2 refused | 0 |
| ref: `1|2` | 2 refused | 0 |
| ref: `1`, `01`, `0001`, ` 1 `, `1`+NBSP, `1`+tab (trimmed), 4300 digits ending in 1 | 0 | 0 |
| ref: 4301 nines; 5000 nines; 4300 zeros + `1` | 1, traceback (F2) | 0 |
| kind: `Read`, `READ`, empty, fullwidth r, Cyrillic a, two spaces, NBSP inside, +U+200B, `read|preview`, `correction` | 2 refused | 0 |
| kind: `read ` and `read`+NBSP (trimmed to `read`) | 0 | 0 |
| confirmed write: no ref; ref 1 (a read); ref 2 with different target | 2 refused | 0 |
| confirmed write ref 2; ref `02`; recovery ref 3; failure no ref; preview ref 6 | 0 | 0 |
| recovery ref 1 | 2 refused | 0 |
| invalid bytes: action 0xFF; action ED A0 80; actor 0x80; ref 0xFF | 1, traceback (F4) | 0 |
| invalid byte in kind | 2 refused | 0 |

## Not tried
- A 64-bit chain collision or second preimage (the one route to a Q1 pass that the code leaves open).
- `check --anchor-git-ref` in any form.
- Rendering the Markdown in any viewer; all "hides when rendered" statements are untested there.
- A NUL character in an argument (the OS does not allow it in argv).
- Two `append` runs at the same moment; killing `append` between the log write and the anchor write; disk full; read-only files.
- Values near the 1 MB macOS argument limit; long values in fields other than action.
- The credential rules beyond one bearer case; clock moved backwards; symlinked or oddly named log paths; calling `append()` as a Python function instead of the command line.
- Python versions other than 3.15.0 (the 4300-digit limit and argument decoding can differ by version and platform).
- `tests/planted_bugs.py` (not run, per instruction).

## Other observations
- `git status` in the main checkout shows `participant/ACTIVITY.md` and `participant/progress.yaml` as modified and the audit-log files as untracked. I ran only `cp`, `cmp`, `grep` and `git status` against that folder, so these states were not caused by this run.
- Harness and raw output: `/var/folders/v8/l38z3wd93mv38rtms6v1110c0000gq/T/tmp.kdec7uq0KT/h/q1.py`, `/var/folders/v8/l38z3wd93mv38rtms6v1110c0000gq/T/tmp.kdec7uq0KT/h/q2.py`, `/var/folders/v8/l38z3wd93mv38rtms6v1110c0000gq/T/tmp.kdec7uq0KT/h/q2.out` (Q1 output was printed, not saved). Tool calls used: 9.
