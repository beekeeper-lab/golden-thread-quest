#!/bin/bash
# Demonstrates the decision-log checker (participant/tools/decision-check.mjs) for the
# context-decision-log quest: it checks the real log, then copies of it broken on purpose, one
# mistake each, and a correct promotion checked against the earlier copy. Every broken case must
# fail exactly the checks named for it, with the expected message, and pass every other check. The
# copies live in a new temp folder that is deleted afterwards; the real files are only read.
#
#   bash participant/tools/decision-check-demo.sh <logs folder>   (from the repository's top folder)
#
# Writes log-check.txt into <logs folder> only if every case came out as expected (an existing
# log-check.txt is replaced only if it is an ordinary file). The log ends with the full text of
# sources.md and the checker's SHA-256, so a reader of the log alone can verify every approval.
# Exit codes: 0 all as expected, 1 something unexpected (nothing written), 2 setup error.
set -u -o pipefail
REPO=$(cd -P . && printf '%s/.' "$PWD") || exit 2
REPO=${REPO%/.}
CHECK="$REPO/participant/tools/decision-check.mjs"
REAL="$REPO/participant/context/decisions"
[ -f "$CHECK" ] && [ -f "$REAL/log.md" ] && [ -f "$REAL/rules.md" ] && [ -f "$REAL/sources.md" ] || { echo "Run this from the repository's top folder."; exit 2; }
[ $# -eq 1 ] || { echo "Usage: bash participant/tools/decision-check-demo.sh <logs folder>"; exit 2; }
mkdir -p "$1" || exit 2
LOGS=$(cd -P -- "$1" && printf '%s/.' "$PWD") || exit 2
LOGS=${LOGS%/.}
if [ -L "$LOGS/log-check.txt" ] || { [ -e "$LOGS/log-check.txt" ] && [ ! -f "$LOGS/log-check.txt" ]; }; then
  echo "log-check.txt in the logs folder is not an ordinary file; stopping."; exit 2
fi

# The temp folder: new, checked before anything is ever deleted from it.
T=$(mktemp -d "${TMPDIR:-/tmp}/decision-check-demo.XXXXXX") || exit 2
[ -n "$T" ] && [ -d "$T" ] && [ ! -L "$T" ] || { echo "Couldn't make the temp folder."; exit 2; }
T=$(cd -P -- "$T" && printf '%s/.' "$PWD") || exit 2
T=${T%/.}
case "$(basename "$T")" in
  decision-check-demo.??????) ;;
  *) echo "Unexpected temp folder; stopping."; exit 2 ;;
esac
[ -z "$(ls -A "$T")" ] || { echo "The temp folder isn't new; stopping."; exit 2; }
cleanup() { rm -rf -- "$T"; }
FAIL=0
OUT="$T/log-check.txt"
sha() { node -e 'process.stdout.write(require("crypto").createHash("sha256").update(require("fs").readFileSync(process.argv[1])).digest("hex"))' "$1"; }
fingerprint() { printf '%s %s %s' "$(sha "$REAL/log.md")" "$(sha "$REAL/rules.md")" "$(sha "$REAL/sources.md")"; }
BEFORE=$(fingerprint)

# copy <name>: a fresh copy of the real files, as $T/<name>
copy() { mkdir "$T/$1" && cp "$REAL/log.md" "$REAL/rules.md" "$REAL/sources.md" "$T/$1/"; }
# edit <name> <file> <text> <replacement>: replaces text that must appear exactly once
edit() {
  node -e '
    const fs = require("fs"), [file, from, to] = process.argv.slice(1);
    const s = fs.readFileSync(file, "utf8"), n = s.split(from).length - 1;
    if (n !== 1) { console.error(`edit: expected the text once, found it ${n} times`); process.exit(1); }
    fs.writeFileSync(file, s.replace(from, () => to));
  ' "$T/$1/$2" "$3" "$4" || FAIL=1
}
# view <name>: sets the copy's Current decisions list to what its entries call for (so a case
# fails only for its own mistake, not also for a stale list)
view() {
  local v
  v=$(cd "$T" && node "$CHECK" --dir "$T/$1" --print-view) || { FAIL=1; return; }
  node -e '
    const fs = require("fs"), [file, view] = process.argv.slice(1);
    const s = fs.readFileSync(file, "utf8");
    const a = "<!-- current-decisions: start -->", b = "<!-- current-decisions: end -->";
    fs.writeFileSync(file, s.slice(0, s.indexOf(a) + a.length) + "\n" + view + "\n" + s.slice(s.indexOf(b)));
  ' "$T/$1/log.md" "$v" || FAIL=1
}
# changes <name>: every line changed from the real files (the rebuilt list's rows included)
changes() {
  echo "What was changed in this copy:"
  for f in log.md rules.md sources.md; do
    diff "$REAL/$f" "$T/$1/$f" | grep -E '^[<>] .*[^ ]' | sed -e "s/^</  $f, before:/" -e "s/^>/  $f, after: /"
  done
}
# run <name> "<failing checks>" "<expected message>" [extra arguments...]: runs the checker on a
# copy; exactly the named checks (space-separated, in report order) must fail, the message must
# appear, and the exit code must be 1 (or 0 when no check is named). "As expected" is printed only
# when every one of those holds.
run() {
  local name=$1 want=$2 msg=$3 code out failing ok=1
  shift 3
  echo "\$ node decision-check.mjs --dir $name$( [ $# -gt 0 ] && printf ' %s' "$@")"
  out=$(cd "$T" && node "$CHECK" --dir "$T/$name" "$@" 2>&1)
  code=$?
  printf '%s\n' "${out//"$T/"/}"
  echo "exit code: $code"
  failing=$(printf '%s\n' "$out" | sed -n -E 's/^FAIL  ([0-9]+|[A-Za-z]+)[.:].*/\1/p' | tr '\n' ' ' | sed 's/ $//')
  if [ "$failing" != "$want" ]; then echo "UNEXPECTED: checks failing were \"$failing\", expected \"$want\""; ok=0; fi
  # Every check must report, in order, PASS or FAIL: none may silently go missing.
  local all reported a
  all="0 1 2 3 4 5 6 7 Stretch"
  for a in "$@"; do [ "$a" = "--previous" ] && all="$all History"; done
  reported=$(printf '%s\n' "$out" | sed -n -E 's/^(PASS|FAIL)  ([0-9]+|[A-Za-z]+)[.:].*/\2/p' | tr '\n' ' ' | sed 's/ $//')
  if [ "$reported" != "$all" ]; then echo "UNEXPECTED: the checks reported were \"$reported\", expected \"$all\""; ok=0; fi
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
# record <name> <source heading> <approval line>: adds a new source section with one approval line
record() { edit "$1" sources.md "## DOC-01 ·" "## $2

- $3

## DOC-01 ·"; }
# decision <name> <id> <title> <date> <source> <area> <approver> <approval line> [extra lines...]
decision() {
  local name=$1 id=$2 title=$3 date=$4 src=$5 area=$6 who=$7 line=$8 x
  shift 8
  { printf '\n### %s · %s\n\n- Status: decision\n- Date: %s\n- Source: %s\n- Area: %s\n- Approver: %s\n- Approval: "%s"\n' "$id" "$title" "$date" "$src" "$area" "$who" "$line"
    for x in "$@"; do printf '%s\n' "$x"; done
    printf -- '- Affects: none\n'; } >> "$T/$name/log.md"
}
FEE='Approved by Avery Lane (area: fees): the service fee is $2.50 per ticket, charged on every ticket.'

{
  echo "context-decision-log: the decision-log check"
  echo "Recorded $(date '+%m-%d-%Y %I:%M %p') with Node $(node --version), by participant/tools/decision-check-demo.sh."
  echo "Each case is a copy of the real files (participant/context/decisions/) in a temp folder with"
  echo "one mistake, and its Current decisions list rebuilt so only that mistake can fail. Each must fail"
  echo "exactly the checks named, with the message named. Every check (0 to 7, the stretch check and the"
  echo "history check) is the expected failure of at least one case, so a check that stopped working"
  echo "would make this demonstration fail. The real files are only read. Folder names below are"
  echo "relative to that temp folder."
  echo

  echo "== 1. The real log =="
  echo "\$ node participant/tools/decision-check.mjs"
  out=$(cd "$REPO" && node "$CHECK" 2>&1); code=$?
  printf '%s\nexit code: %s\n' "$out" "$code"
  if [ "$code" = 0 ] \
    && printf '%s\n' "$out" | grep -qF 'verified: superseded decision D-02' \
    && printf '%s\n' "$out" | grep -qF 'verified: proposal P-02'; then
    echo "As expected: every check passed, and the report names the replacement D-02 to D-07 and the"
    echo "promotion P-02 to D-05 it verified."
  else
    echo "UNEXPECTED: exit code 0 and both verified links were expected"; FAIL=1
  fi
  echo

  echo "== 2. Agreement recorded as an approval (the quest's scenario) =="
  echo "P-03 is promoted to a decision whose \"approval\" quotes the meeting's agreement."
  copy agreement
  edit agreement log.md "- Proposed by: Jordan Pike
- Note: everyone in MTG-02" "- Proposed by: Jordan Pike
- Became: D-08
- Note: everyone in MTG-02"
  decision agreement D-08 "Waive the service fee for orders of 6 or more tickets" 10-19-2026 MTG-02 fees "Avery Lane" "Jordan: we could waive the fee for orders of 6 or more tickets. Everyone agreed it was a good idea." "- From: P-03"
  view agreement; changes agreement
  run agreement "2" "agreement is not an approval"

  echo "== 3. A decision with no approver =="
  copy no-approver
  edit no-approver log.md "- Area: pages
- Approver: Avery Lane
- Approval: \"Approved by Avery Lane (area: pages): the buyer's name" "- Area: pages
- Approval: \"Approved by Avery Lane (area: pages): the buyer's name"
  view no-approver; changes no-approver
  run no-approver "1 2" "no approver is recorded"

  echo "== 4. An approval quote that isn't in its source, word for word =="
  copy wrong-quote
  edit wrong-quote log.md "\"$FEE\"" "\"Approved by Avery Lane (area: fees): the service fee is \$2.00 per ticket, charged on every ticket.\""
  view wrong-quote; changes wrong-quote
  run wrong-quote "2" "the approval line isn't in MTG-01, word for word"

  echo "== 5. An approver outside their authority =="
  echo "A new record has the tech lead approving a fee; the decision citing it says so honestly."
  copy no-authority
  record no-authority "MTG-04 · Fee follow-up, 11-10-2026" "Approved by Sam Ortiz (area: fees): the service fee is waived for orders of 6 or more tickets."
  decision no-authority D-08 "The service fee is waived for orders of 6 or more tickets" 11-10-2026 MTG-04 fees "Sam Ortiz" "Approved by Sam Ortiz (area: fees): the service fee is waived for orders of 6 or more tickets."
  view no-authority; changes no-authority
  run no-authority "2" "Sam Ortiz may not approve area \"fees\""

  echo "== 6. An entry claiming a different area from its record =="
  echo "The same fee approval by the tech lead, filed as a 'calculation' decision to pass the authority check."
  copy wrong-area
  record wrong-area "MTG-04 · Fee follow-up, 11-10-2026" "Approved by Sam Ortiz (area: fees): the service fee is waived for orders of 6 or more tickets."
  decision wrong-area D-08 "The service fee is waived for orders of 6 or more tickets" 11-10-2026 MTG-04 calculation "Sam Ortiz" "Approved by Sam Ortiz (area: fees): the service fee is waived for orders of 6 or more tickets."
  view wrong-area; changes wrong-area
  run wrong-area "2" "Area \"calculation\" doesn't match the record's area \"fees\""

  echo "== 7. A decision borrowing another decision's approval =="
  echo "A new D-08 cites D-01's approval of the \$2.50 fee as its own."
  copy borrowed
  decision borrowed D-08 "The service fee is \$2.50 per ticket, charged on every ticket" 10-05-2026 MTG-01 fees "Avery Lane" "$FEE"
  view borrowed; changes borrowed
  run borrowed "2" "uses the same approval as D-01"

  echo "== 8. Work resting on a proposal (a proposal treated as decided) =="
  copy work-on-proposal
  edit work-on-proposal sources.md "| SHOP-17 | Cancel an order from the orders page | D-05 |" "| SHOP-17 | Cancel an order from the orders page | D-05 |
| SHOP-18 | Waive the fee for 6+ tickets at checkout | P-03 |"
  changes work-on-proposal
  run work-on-proposal "3" "work item SHOP-18 rests on P-03, a proposal"

  echo "== 9. A correct promotion, checked against the earlier copy =="
  echo "Avery Lane approves P-01 in a new meeting, and the record says it promotes P-01: a new decision"
  echo "D-08 is added at the end (From: P-01), and P-01 gets one added line (Became: D-08)."
  copy promotion
  cp "$REAL/log.md" "$T/earlier-log.md"
  record promotion "MTG-04 · Seating follow-up, 11-16-2026" "Approved by Avery Lane (area: pages; promotes: P-01): let buyers choose their seats on a seating map."
  edit promotion log.md "- Proposed by: Jordan Pike

### Q-01 ·" "- Proposed by: Jordan Pike
- Became: D-08

### Q-01 ·"
  decision promotion D-08 "Let buyers choose their seats on a seating map" 11-16-2026 MTG-04 pages "Avery Lane" "Approved by Avery Lane (area: pages; promotes: P-01): let buyers choose their seats on a seating map." "- From: P-01"
  view promotion; changes promotion
  run promotion "" "" --previous earlier-log.md

  echo "== 10. A promotion the record doesn't support =="
  echo "P-03 (the fee waiver) is linked as having become D-06, which approves currency display."
  copy wrong-promotion
  edit wrong-promotion log.md "- Proposed by: Jordan Pike
- Note: everyone" "- Proposed by: Jordan Pike
- Became: D-06
- Note: everyone"
  edit wrong-promotion log.md "- Source: SUP-04" "- Source: SUP-04
- From: P-03"
  view wrong-promotion; changes wrong-promotion
  run wrong-promotion "4" "D-06: From P-03, but its approval record promotes nothing"

  echo "== 11. A promotion linked only one way =="
  copy one-way-promotion
  edit one-way-promotion log.md "- Proposed by: Riley Chen
- Became: D-05" "- Proposed by: Riley Chen"
  view one-way-promotion; changes one-way-promotion
  run one-way-promotion "4" "D-05: From P-02, but P-02 doesn't say \"Became: D-05\""

  echo "== 12. A status changed by rewriting the earlier entry =="
  echo "Instead of case 9, P-01 is edited in place into a decision: its earlier wording is lost."
  copy rewrite
  cp "$T/promotion/sources.md" "$T/rewrite/sources.md"
  edit rewrite log.md "### P-01 · Let buyers choose their seats on a seating map

- Status: proposal
- Date: 10-12-2026
- Source: DOC-01
- Proposed by: Jordan Pike" "### P-01 · Let buyers choose their seats on a seating map

- Status: decision
- Date: 11-16-2026
- Source: MTG-04
- Area: pages
- Approver: Avery Lane
- Approval: \"Approved by Avery Lane (area: pages; promotes: P-01): let buyers choose their seats on a seating map.\"
- Affects: none"
  view rewrite; changes rewrite
  run rewrite "1 4 History" "\"- Status: decision\" was added or changed" --previous earlier-log.md

  echo "== 13. A replaced decision that no longer links to its replacement =="
  copy one-way
  edit one-way log.md "- Affects: SHOP-13
- Replaced by: D-07" "- Affects: SHOP-13"
  view one-way; changes one-way
  run one-way "5 Stretch" "D-02 doesn't say \"Replaced by: D-07\""

  echo "== 14. A replacement the record doesn't support =="
  echo "D-02 (the 6-ticket limit) is linked as replaced by D-05, which approves cancelling orders."
  copy wrong-replacement
  edit wrong-replacement log.md "- Replaced by: D-07" "- Replaced by: D-05"
  edit wrong-replacement log.md "- From: P-02" "- From: P-02
- Replaces: D-02"
  edit wrong-replacement log.md "- Replaces: D-02
- Affects: SHOP-13" "- Affects: SHOP-13"
  view wrong-replacement; changes wrong-replacement
  run wrong-replacement "5" "D-05: Replaces D-02, but its approval record replaces nothing"

  echo "== 15. A decision that replaces itself =="
  copy self-replace
  edit self-replace log.md "- Source: SUP-04" "- Source: SUP-04
- Replaces: D-06
- Replaced by: D-06"
  view self-replace; changes self-replace
  run self-replace "5" "must come after D-06, which it replaces"

  echo "== 16. A source that doesn't exist =="
  copy no-source
  edit no-source log.md "- Source: SUP-04" "- Source: SUP-99"
  view no-source; changes no-source
  run no-source "6" "source SUP-99 isn't in sources.md"

  echo "== 17. A date that isn't one =="
  copy bad-date
  edit bad-date log.md "- Date: 10-26-2026" "- Date: 13-26-2026"
  view bad-date; changes bad-date
  run bad-date "6" "date \"13-26-2026\" is not a real MM-DD-YYYY date"

  echo "== 18. A date that doesn't match its record =="
  copy wrong-date
  edit wrong-date log.md "- Date: 10-26-2026" "- Date: 10-25-2026"
  view wrong-date; changes wrong-date
  run wrong-date "6" "dated 10-25-2026, but SUP-04 was recorded on 10-26-2026"

  echo "== 19. A Current decisions view edited by hand =="
  copy stale-view
  edit stale-view log.md "| D-01 | the service fee is \$2.50 per ticket" "| D-01 | the service fee is \$2.00 per ticket"
  changes stale-view
  run stale-view "7" "the Current decisions view doesn't match the entries"

  echo "== 20. A second list of current decisions below the generated one =="
  copy extra-view
  edit extra-view log.md "<!-- current-decisions: end -->" "<!-- current-decisions: end -->

| Decision | What |
|---|---|
| P-03 | waive the fee |"
  changes extra-view
  run extra-view "0 7" "content in \"## Current decisions\" outside the generated list"

  echo "== 21. A decision listing a work item that doesn't exist =="
  copy stretch-link
  edit stretch-link log.md "- Affects: SHOP-15" "- Affects: SHOP-15 SHOP-99"
  view stretch-link; changes stretch-link
  run stretch-link "Stretch" "D-03: affects SHOP-99, which isn't in the work-items table"

  echo "== 22. A table row the parser could miss =="
  copy no-pipe
  edit no-pipe sources.md "| SHOP-17 | Cancel an order from the orders page | D-05 |" "| SHOP-17 | Cancel an order from the orders page | D-05 |
SHOP-18 | Waive the fee | P-03 |"
  changes no-pipe
  run no-pipe "0" "a table line doesn't start with \"|\""

  echo "== 23. A question promoted to a decision =="
  echo "Only a proposal can be promoted; Q-03 is given a 'Became' and a decision claims to come from it."
  copy question
  record question "MTG-04 · Limits follow-up, 11-16-2026" "Approved by Avery Lane (area: ticket limits; promotes: Q-03): there is no limit per buyer across orders."
  edit question log.md "- Source: MTG-03
- Asked by: Riley Chen" "- Source: MTG-03
- Asked by: Riley Chen
- Became: D-08"
  decision question D-08 "There is no limit per buyer across orders" 11-16-2026 MTG-04 "ticket limits" "Avery Lane" "Approved by Avery Lane (area: ticket limits; promotes: Q-03): there is no limit per buyer across orders." "- From: Q-03"
  view question; changes question
  run question "1 4" "D-08: From Q-03, which is a question; only a proposal is promoted"

  echo "== 24. An approval hidden in a comment that opens on a line that also closes one =="
  echo "Readers see no approval in MTG-01 (it sits inside a comment): the comment is reported, and the"
  echo "approval doesn't count."
  copy hidden
  edit hidden sources.md "- $FEE" "<!-- first --> <!--
- $FEE
-->"
  changes hidden
  run hidden "0 2" "comments aren't used in the decision files"

  echo "== 25. An earlier line changed by one space, checked against the earlier copy =="
  copy one-space
  cp "$REAL/log.md" "$T/one-space-earlier.md"
  edit one-space log.md "- Proposed by: Jordan Pike

### Q-01 ·" "- Proposed by:  Jordan Pike

### Q-01 ·"
  changes one-space
  run one-space "History" "\"- Proposed by:  Jordan Pike\" was added or changed" --previous one-space-earlier.md

  echo "== 26. New work for an existing decision: a new row only, checked against the earlier copy =="
  copy new-work
  cp "$REAL/log.md" "$T/new-work-earlier.md"
  edit new-work sources.md "| SHOP-17 | Cancel an order from the orders page | D-05 |" "| SHOP-17 | Cancel an order from the orders page | D-05 |
| SHOP-20 | Show prices with two decimals on receipts | D-06 |"
  changes new-work
  run new-work "" "" --previous new-work-earlier.md

  echo "== 27. A replacement by someone without authority over the replaced decision =="
  echo "The tech lead's calculation decision claims to replace D-01, the product owner's fee decision."
  copy wrong-authority
  record wrong-authority "MTG-04 · Totals follow-up, 11-10-2026" "Approved by Sam Ortiz (area: calculation; replaces: D-01): totals include no service fee."
  edit wrong-authority log.md "- Affects: SHOP-11 SHOP-12

### D-02" "- Affects: SHOP-11 SHOP-12
- Replaced by: D-08

### D-02"
  decision wrong-authority D-08 "Totals include no service fee" 11-10-2026 MTG-04 calculation "Sam Ortiz" "Approved by Sam Ortiz (area: calculation; replaces: D-01): totals include no service fee." "- Replaces: D-01"
  edit wrong-authority sources.md "| SHOP-11 | Show the order total on the event card | D-01 D-04 |" "| SHOP-11 | Show the order total on the event card | D-04 D-08 |"
  edit wrong-authority sources.md "| SHOP-12 | Show the service fee on the event card | D-01 |" "| SHOP-12 | Show the service fee on the event card | D-08 |"
  view wrong-authority; changes wrong-authority
  run wrong-authority "5" "D-08: replaces D-01, an area \"fees\" decision, but Sam Ortiz may not approve area \"fees\""

  echo "== 28. A second \"current decisions\" section further down the log =="
  copy second-section
  printf '\n## Current decisions (continued)\n\n| Decision | What |\n|---|---|\n| P-03 | waive the fee |\n' >> "$T/second-section/log.md"
  changes second-section
  run second-section "0" "log.md has only its title, \"## Current decisions\" and \"## Entries\""

  echo "== 29. Words in the authority table beyond the area names =="
  echo "\"\`calculation\` (not \`fees\`)\" reads as a denial; the checker must not read it as granting fees."
  copy authority-prose
  edit authority-prose rules.md "| Sam Ortiz | Tech lead (made up) | \`calculation\` |" "| Sam Ortiz | Tech lead (made up) | \`calculation\` (not \`fees\`) |"
  changes authority-prose
  run authority-prose "0 2" "must be only area names in backticks"

  echo "== 30. --write-view refuses to write over a log with a problem =="
  echo "The copy from case 7 (a borrowed approval), with its list emptied, is given --write-view."
  copy refuse-write
  cp "$T/borrowed/log.md" "$T/refuse-write/log.md"
  node -e '
    const fs = require("fs"), f = process.argv[1], s = fs.readFileSync(f, "utf8");
    const a = "<!-- current-decisions: start -->", b = "<!-- current-decisions: end -->";
    fs.writeFileSync(f, s.slice(0, s.indexOf(a) + a.length) + "\n" + s.slice(s.indexOf(b)));
  ' "$T/refuse-write/log.md"
  cp "$T/refuse-write/log.md" "$T/refuse-write-before.md"
  run refuse-write "2 7" "was NOT written" --write-view
  if cmp -s "$T/refuse-write-before.md" "$T/refuse-write/log.md"; then echo "The copy's log.md is unchanged, byte for byte."; else echo "UNEXPECTED: the log was written"; FAIL=1; fi
  echo

  echo "== 31. --write-view repairs a stale list, even one naming a proposal =="
  echo "It writes log.md.new and leaves log.md alone; the log.md.new is then moved into place and checked."
  copy repair
  edit repair log.md "| D-06 |" "| P-03 | waive the fee | fees | Avery Lane | 10-19-2026 | MTG-02 |
| D-06 |"
  cp "$T/repair/log.md" "$T/repair-before.md"
  run repair "" "Wrote log.md.new" --write-view
  if cmp -s "$T/repair-before.md" "$T/repair/log.md"; then echo "log.md itself is unchanged, byte for byte."; else echo "UNEXPECTED: log.md was changed"; FAIL=1; fi
  mv "$T/repair/log.md.new" "$T/repair/log.md"
  echo "\$ mv repair/log.md.new repair/log.md"
  run repair "" ""

  echo "== 32. A decision title that says something its approval doesn't =="
  echo "D-06 is retitled \"Waive the service fee\"; its approval is about showing prices in US dollars."
  copy wrong-title
  edit wrong-title log.md "### D-06 · Prices are shown in US dollars, with two decimal places" "### D-06 · Waive the service fee"
  changes wrong-title
  run wrong-title "2" "its title \"Waive the service fee\" isn't the approved words"

  echo "== 33. A lone carriage return hiding a work-item row =="
  echo "A row added after a bare CR (an old Mac line break): some readers show it as a line, so it's refused."
  copy bare-cr
  node -e '
    const fs = require("fs"), f = process.argv[1], s = fs.readFileSync(f, "utf8");
    const row = "| SHOP-17 | Cancel an order from the orders page | D-05 |";
    fs.writeFileSync(f, s.replace(row, row + "\r| SHOP-18 | Waive fee | P-03 |"));
  ' "$T/bare-cr/sources.md"
  echo "\$ node decision-check.mjs --dir bare-cr"
  out=$(cd "$T" && node "$CHECK" --dir "$T/bare-cr" 2>&1); code=$?
  printf '%s\nexit code: %s\n' "${out//"$T/"/}" "$code"
  if [ "$code" = 2 ] && printf '%s\n' "$out" | grep -qF "carriage return that isn't followed by a line feed"; then
    echo "As expected: refused (exit code 2) before anything was checked."
  else
    echo "UNEXPECTED: exit code 2 and the carriage-return message were expected"; FAIL=1
  fi
  echo

  echo "== 34. An indented paragraph after a blank line, under an approval =="
  copy blank-continued
  edit blank-continued sources.md "- $FEE" "- $FEE

  Only after separate confirmation."
  changes blank-continued
  run blank-continued "0" "an indented line after the approval on line"

  echo "== 35. A decision title differing only in capital letters inside it =="
  copy title-case
  edit title-case log.md "### D-06 · Prices are shown in US dollars, with two decimal places" "### D-06 · Prices are shown in us dollars, with two decimal places"
  changes title-case
  run title-case "2" "its title \"Prices are shown in us dollars, with two decimal places\" isn't the approved words"

  echo "== 36. A decision title that leaves part of the approval out =="
  echo "D-01's title drops \", charged on every ticket\": shorter, but no longer exactly what was approved."
  copy short-title
  edit short-title log.md "### D-01 · The service fee is \$2.50 per ticket, charged on every ticket" "### D-01 · The service fee is \$2.50 per ticket"
  changes short-title
  run short-title "2" "its title \"The service fee is \$2.50 per ticket\" isn't the approved words"

  echo "== 37. An approval that continues onto a second line =="
  copy continued
  edit continued sources.md "- $FEE" "- $FEE
  only after a separate written confirmation."
  changes continued
  run continued "0" "continues the approval on line"

  echo "== 38. A table above the Current decisions list =="
  copy preamble-table
  edit preamble-table log.md "## Current decisions" "| Decision | Status |
|---|---|
| P-03 | approved |

## Current decisions"
  changes preamble-table
  run preamble-table "0" "a table outside the generated Current decisions list"

  echo "== 39. The Current decisions list moved below the entries =="
  copy moved-view
  node -e '
    const fs = require("fs"), f = process.argv[1], s = fs.readFileSync(f, "utf8");
    const a = s.indexOf("## Current decisions"), b = s.indexOf("## Entries");
    fs.writeFileSync(f, s.slice(0, a) + s.slice(b).replace(/\n*$/, "\n\n") + s.slice(a, b).replace(/\n*$/, "\n"));
  ' "$T/moved-view/log.md"
  run moved-view "0" "\"## Current decisions\" must come before \"## Entries\""

  echo "== 40. A ### subsection inside a source =="
  echo "MTG-01's approvals are put under a \"### Approvals\" subheading; they still belong to MTG-01."
  copy subsection
  edit subsection sources.md "- Avery proposed a service fee" "### Approvals

- Avery proposed a service fee"
  changes subsection
  run subsection "" ""

  echo "== 41. A leftover log.md.new from an earlier run =="
  echo "It may be out of date, so --write-view refuses and says to delete it, not to move it into place."
  copy leftover
  edit leftover log.md "| D-06 |" "| P-03 | waive the fee | fees | Avery Lane | 10-19-2026 | MTG-02 |
| D-06 |"
  printf 'an older log.md.new\n' > "$T/leftover/log.md.new"
  echo "\$ node decision-check.mjs --dir leftover --write-view"
  out=$(cd "$T" && node "$CHECK" --dir "$T/leftover" --write-view 2>&1); code=$?
  printf '%s\nexit code: %s\n' "${out//"$T/"/}" "$code"
  if [ "$code" = 2 ] && printf '%s\n' "$out" | grep -qF "may be out of date: don't move it into place" && [ "$(cat "$T/leftover/log.md.new")" = "an older log.md.new" ]; then
    echo "As expected: refused (exit code 2), and the old log.md.new was left untouched."
  else
    echo "UNEXPECTED: exit code 2, the out-of-date message and an untouched log.md.new were expected"; FAIL=1
  fi
  echo

  echo "== 42. A table inside a meeting's notes =="
  echo "A table in MTG-02 listing P-03 as approved: tables belong only in the checked places."
  copy notes-table
  edit notes-table sources.md "- Riley: should a cancelled order give the fee back? Nobody knew yet." "- Riley: should a cancelled order give the fee back? Nobody knew yet.

| Decision | Status |
|---|---|
| P-03 | approved |
"
  changes notes-table
  run notes-table "0" "a table outside its one checked table"

  echo "== 43. A table written without leading pipes =="
  echo "Markdown shows \"Decision | Status\" over \"--- | ---\" as a table too; it is reported."
  copy pipeless
  edit pipeless sources.md "- Riley: should a cancelled order give the fee back? Nobody knew yet." "- Riley: should a cancelled order give the fee back? Nobody knew yet.

Decision | Status
--- | ---
P-03 | approved
"
  changes pipeless
  run pipeless "0" "a line with \"|\" that isn't a table row starting with \"|\""

  echo "== 44. A valid note using double-backtick inline code =="
  echo "Markdown inline code may use \`\` as its delimiter; a \"|\" inside it is text, not a table."
  copy double-tick
  edit double-tick sources.md "Attendees: Avery Lane, Jordan Pike, Riley Chen." 'Attendees: Avery Lane, Jordan Pike, Riley Chen. (Order codes look like ``A|B``.)'
  changes double-tick
  run double-tick "" ""

  echo "== 45. An escaped backtick used to hide a qualifier in a comment =="
  echo "A reader sees the comment as hidden; the escaped backtick must not make the checker treat it as code."
  copy escaped-tick
  edit escaped-tick sources.md "- $FEE" "- $FEE \\\`<!-- only for staff -->\`"
  changes escaped-tick
  run escaped-tick "0 2" "an escaped backtick"

  echo "== 46. The log's introduction naming an entry =="
  echo "A sentence above the list saying P-03 is approved: entries are named only in the list and the entries."
  copy intro-claim
  edit intro-claim log.md "## Current decisions" "P-03, the fee waiver, is approved.

## Current decisions"
  changes intro-claim
  run intro-claim "0" "names an entry above the Current decisions list"

  echo "== 47. The introduction naming an entry in disguise =="
  echo "\"P\\-03\" and \"P-**03**\" both display as P-03; the check reads the text as displayed."
  copy disguised
  edit disguised log.md "## Current decisions" 'P\-03, the fee waiver, is approved; so is P-**03**.

## Current decisions'
  changes disguised
  run disguised "0" "names an entry above the Current decisions list"

  AFTER=$(fingerprint)
  echo "== The real files were only read =="
  echo "SHA-256 of log.md, rules.md and sources.md, before: $BEFORE"
  echo "and after:                                         $AFTER"
  if [ "$BEFORE" = "$AFTER" ]; then echo "identical"; else echo "THE REAL FILES CHANGED"; FAIL=1; fi
  echo
  echo "== For the reader of this log alone: what was checked against =="
  echo "SHA-256 of participant/tools/decision-check.mjs: $(sha "$CHECK")"
  echo "SHA-256 of participant/context/decisions/sources.md: $(sha "$REAL/sources.md")"
  echo "The full text of participant/context/decisions/sources.md, the written records every approval"
  echo "above is checked against:"
  echo "----- sources.md -----"
  cat "$REAL/sources.md"
  echo "----- end of sources.md -----"
} > "$OUT" 2>&1

if grep -qF -- "$T" "$OUT"; then
  # Not shown: it holds this computer's temp folder name.
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
  const fs = require("fs"), [src, dir] = process.argv.slice(1);
  const tmp = `${dir}/.log-check.txt.${process.pid}.new`;
  fs.copyFileSync(src, tmp, fs.constants.COPYFILE_EXCL);
  try { fs.renameSync(tmp, `${dir}/log-check.txt`); } catch (e) { fs.unlinkSync(tmp); throw e; }
' "$OUT" "$LOGS" || { echo "Couldn't put log-check.txt in place."; cleanup; exit 2; }
cleanup
echo "Written: log-check.txt"

