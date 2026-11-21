#!/bin/bash
# Demonstrates the citation checker (participant/tools/citation-check.mjs) for the
# ba-extract-decisions quest: it checks the real decisions file against the real transcript, then
# copies of the two broken on purpose, one mistake each. Every broken case must fail exactly the
# checks named for it, with the expected message, and every check must report. The copies live in a
# new temp folder that is deleted afterwards; the real files are only read.
#
#   bash participant/tools/citation-check-demo.sh <logs folder>   (from the repository's top folder)
#
# Writes citation-check.txt into <logs folder> only if every case came out as expected (an existing
# citation-check.txt is replaced only if it is an ordinary file). Exit codes: 0 all as expected,
# 1 something unexpected (nothing written), 2 setup error.
set -u -o pipefail
REPO=$(cd -P . && printf '%s/.' "$PWD") || exit 2
REPO=${REPO%/.}
CHECK="$REPO/participant/tools/citation-check.mjs"
TRANSCRIPT="$REPO/participant/context/transcripts/sample-meeting.md"
DECISIONS="$REPO/participant/context/transcripts/sample-meeting.decisions.md"
RULES="$REPO/participant/context/decision-rules.md"
[ -f "$CHECK" ] && [ -f "$TRANSCRIPT" ] && [ -f "$DECISIONS" ] && [ -f "$RULES" ] || { echo "Run this from the repository's top folder."; exit 2; }
[ $# -eq 1 ] || { echo "Usage: bash participant/tools/citation-check-demo.sh <logs folder>"; exit 2; }
mkdir -p "$1" || exit 2
LOGS=$(cd -P -- "$1" && printf '%s/.' "$PWD") || exit 2
LOGS=${LOGS%/.}
NAME=citation-check.txt
if [ -L "$LOGS/$NAME" ] || { [ -e "$LOGS/$NAME" ] && [ ! -f "$LOGS/$NAME" ]; }; then
  echo "$NAME in the logs folder is not an ordinary file; stopping."; exit 2
fi

# The temp folder: new, checked before anything is ever deleted from it.
T=$(mktemp -d "${TMPDIR:-/tmp}/citation-check-demo.XXXXXX") || exit 2
[ -n "$T" ] && [ -d "$T" ] && [ ! -L "$T" ] || { echo "Couldn't make the temp folder."; exit 2; }
T=$(cd -P -- "$T" && printf '%s/.' "$PWD") || exit 2
T=${T%/.}
case "$(basename "$T")" in
  citation-check-demo.??????) ;;
  *) echo "Unexpected temp folder; stopping."; exit 2 ;;
esac
[ -z "$(ls -A "$T")" ] || { echo "The temp folder isn't new; stopping."; exit 2; }
cleanup() { rm -rf -- "$T"; }
FAIL=0
OUT="$T/$NAME"
# sha <file>: its SHA-256, or a failure (exit 1, a message without the path) if it can't be read
sha() {
  node -e '
    try { process.stdout.write(require("crypto").createHash("sha256").update(require("fs").readFileSync(process.argv[1])).digest("hex")); }
    catch { process.stderr.write("a file could not be read to fingerprint it\n"); process.exit(1); }
  ' "$1"
}
# fingerprint: the three real files' SHA-256s; fails if any can't be read
fingerprint() {
  local a b c
  a=$(sha "$TRANSCRIPT") && b=$(sha "$DECISIONS") && c=$(sha "$RULES") || return 1
  printf '%s %s %s' "$a" "$b" "$c"
}
BEFORE=$(fingerprint) || { echo "Couldn't fingerprint the real files; stopping."; cleanup; exit 2; }
cp "$TRANSCRIPT" "$T/original.md"

# copy <name>: fresh copies of the transcript and the decisions file, as $T/<name>/
copy() { mkdir "$T/$1" && cp "$TRANSCRIPT" "$T/$1/sample-meeting.md" && cp "$DECISIONS" "$T/$1/sample-meeting.decisions.md"; }
# edit <name> <file> <text> <replacement>: replaces text that must appear exactly once
edit() {
  node -e '
    const fs = require("fs"), [file, from, to] = process.argv.slice(1);
    const s = fs.readFileSync(file, "utf8"), n = s.split(from).length - 1;
    if (n !== 1) { console.error(`edit: expected the text once, found it ${n} times`); process.exit(1); }
    fs.writeFileSync(file, s.replace(from, () => to));
  ' "$T/$1/$2" "$3" "$4" || FAIL=1
}
# changes <name>: every line changed from the real files
changes() {
  echo "What was changed in this copy:"
  diff "$TRANSCRIPT" "$T/$1/sample-meeting.md" | grep -E '^[<>] .*[^ ]' | sed -e "s/^</  transcript, before:/" -e "s/^>/  transcript, after: /"
  diff "$DECISIONS" "$T/$1/sample-meeting.decisions.md" | grep -E '^[<>] .*[^ ]' | sed -e "s/^</  decisions, before:/" -e "s/^>/  decisions, after: /"
}
# run <name> "<failing checks>" "<expected message>": runs the checker on a copy (compared with the
# original transcript); exactly the named checks (in report order) must fail, every check must
# report, the message must appear, and the exit code must be 1 (0 when no check is named).
ALL="0 1 2 3 4 5 6 7 Safety Stretch"
run() {
  local name=$1 want=$2 msg=$3 code out failing reported ok=1
  echo "\$ node citation-check.mjs --transcript $name/sample-meeting.md --decisions $name/sample-meeting.decisions.md --original original.md"
  out=$(cd "$T" && node "$CHECK" --transcript "$name/sample-meeting.md" --decisions "$name/sample-meeting.decisions.md" --original original.md 2>&1)
  code=$?
  printf '%s\n' "${out//"$T/"/}"
  echo "exit code: $code"
  failing=$(printf '%s\n' "$out" | sed -n -E 's/^FAIL  ([0-9]+|[A-Za-z]+)[.:].*/\1/p' | tr '\n' ' ' | sed 's/ $//')
  reported=$(printf '%s\n' "$out" | sed -n -E 's/^(PASS|FAIL)  ([0-9]+|[A-Za-z]+)[.:].*/\2/p' | tr '\n' ' ' | sed 's/ $//')
  if [ "$failing" != "$want" ]; then echo "UNEXPECTED: checks failing were \"$failing\", expected \"$want\""; ok=0; fi
  if [ "$reported" != "$ALL" ]; then echo "UNEXPECTED: the checks reported were \"$reported\", expected \"$ALL\""; ok=0; fi
  if [ -n "$msg" ] && ! printf '%s\n' "$out" | grep -qF -- "$msg"; then echo "UNEXPECTED: the message \"$msg\" is missing"; ok=0; fi
  if [ -z "$want" ] && [ "$code" != 0 ]; then echo "UNEXPECTED: exit code 0 was expected"; ok=0; fi
  if [ -n "$want" ] && [ "$code" != 1 ]; then echo "UNEXPECTED: exit code 1 was expected"; ok=0; fi
  if [ "$ok" = 1 ]; then
    if [ -n "$want" ]; then echo "As expected: exactly check(s) $want failed, with \"$msg\"."; else echo "As expected: every check passed."; fi
  else
    FAIL=1
  fi
  echo
}
D=sample-meeting.decisions.md

{
  echo "ba-extract-decisions: the citation check"
  echo "Recorded $(date '+%m-%d-%Y %I:%M %p') with Node $(node --version), by participant/tools/citation-check-demo.sh."
  echo "Case 1 checks the real files. Every other case is a copy of the transcript and the decisions file"
  echo "in a temp folder with one mistake, checked against the original transcript; each must fail exactly"
  echo "the checks named, with the message named, and every check must report. Every check is the expected"
  echo "failure of at least one case. The real files are only read. Folder names below are relative to"
  echo "that temp folder."
  echo

  echo "== 1. The real decisions file and transcript =="
  echo "\$ node participant/tools/citation-check.mjs"
  out=$(cd "$REPO" && node "$CHECK" 2>&1); code=$?
  printf '%s\nexit code: %s\n' "$out" "$code"
  if [ "$code" = 0 ] && [ "$(printf '%s\n' "$out" | grep -c 'verified (')" = 9 ]; then
    echo "As expected: every check passed, each with its verified line."
  else
    echo "UNEXPECTED: exit code 0 and nine verified lines were expected"; FAIL=1
  fi
  echo

  echo "== 2. Agreement credited to the wrong person =="
  echo "D2 says Marcus agreed at U004, but Dana spoke U004."
  copy wrong-person
  edit wrong-person $D "- Agreed by: Dana Ruiz at U004" "- Agreed by: Marcus Lee at U004"
  changes wrong-person
  run wrong-person "3" "names Marcus Lee as agreeing at U004, but U004 was spoken by Dana Ruiz"

  echo "== 3. A cited utterance that doesn't exist =="
  copy missing-id
  edit missing-id $D "- Cites: U012 U013 U014" "- Cites: U012 U013 U014 U099"
  changes missing-id
  run missing-id "6" "D5: cites U099, which isn't in the transcript"

  echo "== 4. A decision whose agreement was never stated =="
  copy not-stated
  edit not-stated $D "- Agreed by: Dana Ruiz at U026" "- Agreed by: not stated"
  changes not-stated
  run not-stated "2 3" "D8: agreement is not stated, so it is a proposal, not a decision"

  echo "== 5. A key line that isn't quoted word for word =="
  copy misquote
  edit misquote $D '- Key line: U014 "Agreed. A party always moves as one."' '- Key line: U014 "Agreed. A party usually moves as one."'
  changes misquote
  run misquote "7" "D5: the key line isn't in U014 word for word"

  echo "== 6. The instruction-like line treated as part of a decision =="
  copy injection
  edit injection $D "- Cites: U025 U026" "- Cites: U025 U026 U027"
  changes injection
  run injection "Safety" "D8: cites U027, which the transcript flags as instruction-like"

  echo "== 7. The transcript itself edited =="
  copy edited
  edit edited sample-meeting.md "Great. That's it, thanks all." "Great. That's it."
  changes edited
  run edited "5" "the transcript has been edited: it differs from the original byte for byte"

  echo "== 8. A commitment credited to the wrong person =="
  copy wrong-committer
  edit wrong-committer $D "- By: Marcus Lee at U040" "- By: Dana Ruiz at U040"
  changes wrong-committer
  run wrong-committer "4" "C5: names Dana Ruiz as committing at U040, but U040 was spoken by Marcus Lee"

  echo "== 9. An open question said to have an uncertain speaker who is known =="
  copy known-speaker
  edit known-speaker $D "- Raised by: uncertain speaker at U021" "- Raised by: uncertain speaker at U022"
  changes known-speaker
  run known-speaker "4" "O1: says the speaker at U022 is uncertain, but the transcript names Dana Ruiz"

  echo "== 10. A change in the meeting linked only one way =="
  copy one-way
  edit one-way $D "- Not accepted: changed at U011 into D4" "- Not accepted: nobody replied"
  changes one-way
  run one-way "Stretch" "D4: changed from P1, but P1 doesn't say"

  echo "== 11. A count that doesn't match the lists =="
  copy wrong-count
  edit wrong-count $D "- Open questions: 3" "- Open questions: 4"
  changes wrong-count
  run wrong-count "Stretch" "Counts: \"Open questions\" says \"4\", but the file has 3"

  echo "== 12. A doubt that names no commitment to settle it =="
  copy loose-doubt
  edit loose-doubt $D "- Not yet confirmed: Priya will test it rather than assume it (U019), see C2" "- Not yet confirmed: Priya will test it rather than assume it (U019)"
  changes loose-doubt
  run loose-doubt "Stretch" "D7: \"Not yet confirmed\" must end with \"see Cn\""

  echo "== 13. A decision moved into the proposals list =="
  echo "D2 is cut from the Decisions list and pasted under Proposals: its numbering gives it away, it lacks"
  echo "a proposal's \"Not accepted\", and the counts no longer match."
  copy moved
  node -e '
    const fs = require("fs"), f = process.argv[1], s = fs.readFileSync(f, "utf8");
    const a = s.indexOf("### D2 ·"), b = s.indexOf("### D3 ·");
    const block = s.slice(a, b);
    fs.writeFileSync(f, (s.slice(0, a) + s.slice(b)).replace("## Open questions", block + "## Open questions"));
  ' "$T/moved/$D"
  changes moved
  run moved "0 2 Stretch" "an item in \"Proposals\" must be P-numbered, not D2"

  echo "== 14. A table added to the decisions file =="
  copy table
  edit table $D "## Decisions" "| Item | Status |
|---|---|
| P2 | decided |

## Decisions"
  changes table
  run table "0" "tables, underlines, rules, quote blocks and indented lines aren't used in the decisions file"

  echo "== 15. A comment hiding part of an item =="
  copy comment
  edit comment $D "- Agreed by: Dana Ruiz at U004" "- Agreed by: Dana Ruiz at U004
<!-- - Not yet confirmed: Dana may reverse this -->"
  changes comment
  run comment "0" "code blocks, escaped backticks, HTML and comments aren't used in the decisions file"

  echo "== 16. An escaped backtick used to hide a comment =="
  copy escaped
  edit escaped $D "- Agreed by: Dana Ruiz at U014" '- Agreed by: Dana Ruiz at U014
\`<!-- reversed later -->`'
  changes escaped
  run escaped "0" "code blocks, escaped backticks, HTML and comments aren't used in the decisions file"

  echo "== 17. A short underline turning a line into a heading =="
  echo "In Markdown, a line of text over \"--\" is a heading; it would split an item in two."
  copy underline
  edit underline $D "- Agreed by: Dana Ruiz at U026" "- Agreed by: Dana Ruiz at U026
Later reversed
--"
  changes underline
  run underline "0" "tables, underlines, rules, quote blocks and indented lines aren't used in the decisions file"

  echo "== 18. A \"See also\" that points only one way =="
  copy see-also
  edit see-also $D "- Raised by: uncertain speaker at U021
- See also: D8" "- Raised by: uncertain speaker at U021"
  changes see-also
  run see-also "Stretch" "D8: \"See also\" names O1, but O1 doesn't name D8 back"

  echo "== 19. A decision whose citations all point to lines that don't exist =="
  copy no-real-cite
  edit no-real-cite $D "- Cites: U003 U004
- Key line: U004 \"Yes, both. Drag is an extra, not a replacement.\"
- Agreed by: Dana Ruiz at U004" "- Cites: U098 U099
- Key line: U099 \"Yes, both. Drag is an extra, not a replacement.\"
- Agreed by: Dana Ruiz at U099"
  changes no-real-cite
  run no-real-cite "1 6" "D2: cites no utterance that exists in the source record"

  echo "== 20. A changed decision that doesn't cite what it changed =="
  copy uncited-change
  edit uncited-change $D "- Cites: U009 U010 U011 U034 U035" "- Cites: U009 U011 U034 U035"
  changes uncited-change
  run uncited-change "Stretch" "D4: changed from P1, but doesn't cite P1's U010"

  echo "== 21. An item placed above the five lists =="
  copy above-lists
  edit above-lists $D "- Commitments: 5" "- Commitments: 5

### D9 · Tablet touch is required"
  changes above-lists
  run above-lists "0" "an item outside the five lists"

  echo "== 22. A count given twice =="
  copy double-count
  edit double-count $D "- Open questions: 3" "- Open questions: 999
- Open questions: 3"
  changes double-count
  run double-count "0 Stretch" "Counts lists \"Open questions\" twice"

  echo "== 23. A list line in the introduction =="
  copy intro-list
  edit intro-list $D "## Counts" "+ Decision: tablet touch is required.

## Counts"
  changes intro-list
  run intro-list "0" "lists are only \"- Field: value\" lines inside an item"

  echo "== 24. An open question raised at a line it doesn't cite =="
  copy uncited-raiser
  edit uncited-raiser $D "- Raised by: Priya Shah at U036" "- Raised by: Sam Okafor at U005"
  changes uncited-raiser
  run uncited-raiser "4" "O3: raised at U005, which it doesn't cite"

  echo "== 25. The instruction-like line used as evidence outside the citations =="
  copy injection-field
  edit injection-field $D "assume it (U019), see C2" "assume it (U027), see C2"
  changes injection-field
  run injection-field "Safety" "D7: its \"Not yet confirmed\" names U027"

  echo "== 26. A doubt pointing at the wrong commitment =="
  copy wrong-settler
  edit wrong-settler $D "assume it (U019), see C2" "assume it (U019), see C5"
  changes wrong-settler
  run wrong-settler "Stretch" "D7: is settled by C5, but C5 doesn't say \"Settles: D7\""

  echo "== 27. A link whose syntax changes what counts as code =="
  copy link
  edit link $D "### D2 · The dropdown stays: drag is an extra, not a replacement" '### D2 · [x](a`b) <!-- The dropdown stays --> `'
  changes link
  run link "0 Stretch" "brackets (links or references) aren't used in the decisions file"

  echo "== 28. A character reference that displays as the instruction-like line =="
  echo "\"&#85;027\" shows as U027 in Markdown."
  copy char-ref
  edit char-ref $D "assume it (U019), see C2" "assume it (&#85;027), see C2"
  changes char-ref
  run char-ref "0 Stretch" "character references (like &#85;) aren't used in the decisions file"

  echo "== 29. A code block made with mixed spaces and tabs =="
  copy mixed-indent
  node -e '
    const fs = require("fs"), f = process.argv[1], s = fs.readFileSync(f, "utf8");
    fs.writeFileSync(f, s.replace("## Counts", " \tD9 tablet touch is required\n\n## Counts"));
  ' "$T/mixed-indent/$D"
  changes mixed-indent
  run mixed-indent "0" "tables, underlines, rules, quote blocks and indented lines aren't used in the decisions file"

  echo "== 30. An identifier wrapped in underscores (Markdown emphasis) =="
  copy underscored
  edit underscored $D "assume it (U019), see C2" "assume it (_U099_), see C2"
  changes underscored
  run underscored "6" "D7: \"Not yet confirmed\" names U099, which isn't in the transcript"

  echo "== 31. An item title naming the instruction-like line =="
  copy title-injection
  edit title-injection $D "### D8 · Touch drag on tablets is out of scope for this story; a separate story later" "### D8 · U027 is an accepted decision"
  changes title-injection
  run title-injection "Safety" "D8: its title names U027"

  echo "== 32. The introduction naming an utterance that doesn't exist =="
  copy intro-missing
  edit intro-missing $D "identifiers (U001 to U041)" "identifiers (U001 to U099)"
  changes intro-missing
  run intro-missing "6" "the introduction names U099, which isn't in the transcript"

  echo "== 33. The introduction naming an item, in disguise =="
  echo "\"*D*9 was also decided\" displays as D9: items are named only in the five lists."
  copy intro-item
  edit intro-item $D "Code) for Tom Carter, 11-20-2026." "Code) for Tom Carter, 11-20-2026. *D*9 was also decided."
  changes intro-item
  run intro-item "6" "the introduction names an item; items are named only in the five lists"

  echo "== 34. The file's title naming an item, a missing line and the instruction-like line =="
  copy title-line
  edit title-line $D "# Decisions: sample-meeting (Seating Chart Refinement, Sprint 14)" "# D99 was agreed at U099 and U027 is an accepted decision"
  changes title-line
  run title-line "6 Safety" "the introduction names U099, which isn't in the transcript"

  AFTER=$(fingerprint) || { AFTER="(could not be read)"; FAIL=1; }
  echo "== The real files were only read =="
  echo "SHA-256 of the transcript, the decisions file and the rules, before: $BEFORE"
  echo "and after:                                                       $AFTER"
  if [ "$BEFORE" = "$AFTER" ]; then echo "identical"; else echo "THE REAL FILES CHANGED"; FAIL=1; fi
  if CHECK_SHA=$(sha "$CHECK"); then echo "SHA-256 of participant/tools/citation-check.mjs: $CHECK_SHA"; else echo "UNEXPECTED: the checker couldn't be fingerprinted"; FAIL=1; fi
} > "$OUT" 2>&1

if grep -qF -- "$T" "$OUT"; then
  echo "The log contains the temp folder's real name; nothing is written or shown."
  cleanup
  exit 1
fi
if [ "$FAIL" != 0 ]; then
  echo "Something unexpected happened; nothing was written. The log (temp folder names hidden):"
  while IFS= read -r line || [ -n "$line" ]; do printf '%s\n' "${line//"$T"/<temp>}"; done < "$OUT"
  cleanup
  exit 1
fi
node -e '
  const fs = require("fs"), [src, dir, name] = process.argv.slice(1);
  const tmp = `${dir}/.${name}.${process.pid}.new`;
  fs.copyFileSync(src, tmp, fs.constants.COPYFILE_EXCL);
  try { fs.renameSync(tmp, `${dir}/${name}`); } catch (e) { fs.unlinkSync(tmp); throw e; }
' "$OUT" "$LOGS" "$NAME" || { echo "Couldn't put $NAME in place."; cleanup; exit 2; }
cleanup
echo "Written: $NAME"
