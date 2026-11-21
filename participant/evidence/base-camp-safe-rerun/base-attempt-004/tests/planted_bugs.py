"""Plant one bug at a time in a copy of scripts/rerun.py and run the tests against the copy.

A bug is "caught" when at least one test fails, "SURVIVED" when the tests still pass.
The real script is never modified. A control run on an unmodified copy must pass,
otherwise the result means nothing.

Run:  python3 -B tests/planted_bugs.py      (from the attempt folder)
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "..", "scripts", "rerun.py")

KEY_LINE = 'key = make_key(source, item.get("source_id"))'
LOAD_LINE = "source, items = load_input(input_path)"

# (name, what the bug does, text to find, text to put in its place)
BUGS = [
    ("key-from-title", "key built from the title",
     KEY_LINE, 'key = make_key(source, re.sub(r"[^a-z0-9]+", "-", tidy(str(item.get("title")))).strip("-"))'),
    ("key-from-filename", "input filename mixed into the key",
     LOAD_LINE, LOAD_LINE + '; source += "-" + re.sub(r"[^a-z0-9]+", "-", os.path.basename(input_path).casefold()).strip("-")'),
    ("key-from-folder", "input folder name mixed into the key",
     LOAD_LINE, LOAD_LINE + '; source += "-" + re.sub(r"[^a-z0-9]+", "-", os.path.basename(os.path.dirname(os.path.abspath(input_path))).casefold()).strip("-")[:6]'),
    ("key-from-position", "key built from the item's place in the file",
     KEY_LINE, 'key = make_key(source, "item-%d" % position)'),
    ("key-has-run-second", "run time (seconds) mixed into the key",
     LOAD_LINE, LOAD_LINE + '; source += "-%d" % __import__("time").time()'),
    ("key-has-run-year-time", "run year (time.strftime) mixed into the key",
     LOAD_LINE, LOAD_LINE + '; source += "-" + __import__("time").strftime("%Y")'),
    ("key-has-run-date-datetime", "run date (datetime.now) mixed into the key",
     LOAD_LINE, LOAD_LINE + '; source += "-" + __import__("datetime").datetime.now().strftime("%Y%m%d")'),
    ("key-has-run-date-today", "run date (date.today) mixed into the key",
     LOAD_LINE, LOAD_LINE + '; source += "-" + __import__("datetime").date.today().strftime("%Y%m%d")'),
    ("lookup-depends-on-year", "keys look right, but existing records are only recognised in the year 2026",
     "rec = by_key.get(key)", 'rec = by_key.get(key) if __import__("time").strftime("%Y") == "2026" else None'),
    ("always-create", "no lookup before creating",
     "rec = by_key.get(key)", "rec = None"),
    ("changed-item-appended", "a changed item is added as a new record",
     "rec = by_key.get(key)",
     "rec = by_key.get(key)\n        if rec is not None and any(rec[f] != item[f] for f in CONTENT_FIELDS): rec = None"),
    ("unchanged-item-rewritten", "an unchanged item is updated anyway",
     "if not changed:", "if False:"),
    ("unchanged-store-rewritten", "the store file is rewritten with the same content on a skip",
     'if not changed:\n            say("skipped"', 'if not changed:\n            save_store(store_path, store, crash)\n            say("skipped"'),
    ("body-change-missed", "only the title is compared, so a body change is skipped",
     "changed = [f for f in CONTENT_FIELDS if rec[f] != item[f]]", 'changed = [f for f in ("title",) if rec[f] != item[f]]'),
    ("update-gets-new-record-id", "an update gives the record a new record ID",
     'rec["revision"] += 1', 'rec["revision"] += 1; rec["record_id"] = "SIM-%04d" % store["next_record_number"]; store["next_record_number"] += 1'),
    ("skipped-count-wrong", "skipped count is doubled",
     "counts[verb] += 1", 'counts[verb] += 2 if verb == "skipped" else 1'),
    ("created-count-off-by-one", "created count starts at one",
     'counts = {"created": 0,', 'counts = {"created": 1,'),
    ("update-reported-as-skip", "an update is reported as a skip",
     'say("updated", "%s = %s (changed: %s; revision %d -> %d)"', 'say("skipped", "%s = %s (changed: %s; revision %d -> %d)"'),
    ("skip-reason-missing", "skip lines give no reason",
     '"%s = %s (already present, content unchanged)"', '"%s = %s"'),
    ("update-fields-missing", "update lines name the wrong field",
     '", ".join(changed)', '"title"'),
    ("untouched-count-wrong", "count of records not in the input is inverted",
     "if k not in seen_keys", "if k in seen_keys"),
    ("sha-before-wrong", "the report's fingerprint of the store before the run is made up",
     "sha_before = file_sha(store_path)", 'sha_before = "absent"'),
    ("body-in-log-on-create", "body text printed when a record is created",
     'say("created", "%s -> %s" % (key, rec["record_id"]))', 'say("created", "%s -> %s %s" % (key, rec["record_id"], item["body"]))'),
    ("title-in-log-on-update", "old title printed when a record is updated",
     'for field in changed:\n            rec[field] = item[field]', 'print("was:", rec["title"])\n        for field in changed:\n            rec[field] = item[field]'),
    ("body-in-log-on-refusal", "body text printed when an item is refused",
     'entries[i][3] = ("same key as position %s, different content; "', 'entries[i][3] = (entries[i][2]["body"] + " same key as position %s, different content; "'),
    ("raw-id-echoed", "a refused ID is printed as it arrived",
     'raise ValueError("source_id must start with a letter or digit and hold only "\n                         "the letters a to z, digits, dot, dash and underscore")',
     'raise ValueError("source_id has other characters: " + source_id)'),
    ("case-not-folded", "upper and lower case IDs are different keys",
     'return source + ":" + sid.lower()', 'return source + ":" + sid'),
    ("spaces-not-trimmed", "surrounding spaces are kept in IDs",
     "sid = source_id.strip()", "sid = source_id"),
    ("id-pattern-not-checked", "any characters are allowed in an ID",
     "if not ID_RE.match(sid):", "if False:"),
    ("source-pattern-not-checked", "any characters are allowed in a source name",
     "if not isinstance(source, str) or not SOURCE_RE.match(source.strip()) or len(source.strip()) > MAX_ID_LENGTH:",
     "if not isinstance(source, str):"),
    ("missing-id-gets-invented-key", "an item without an ID gets a made-up key",
     'raise ValueError("no usable source_id")', 'return source + ":unknown"'),
    ("number-id-accepted", "a number is accepted as an ID",
     "if not isinstance(source_id, str) or not source_id.strip():",
     "source_id = str(source_id)\n    if not source_id.strip() or source_id == 'None':"),
    ("collision-first-wins", "of two different items with one key, the first is kept",
     "if len(usable) == len(indexes) and len(contents) == 1:", "if len(usable) == len(indexes):"),
    ("collision-not-detected", "two different items with one key are both processed",
     "if len(indexes) < 2:", "if True:"),
    ("non-text-content-accepted", "an item whose title is not text is processed",
     "if not all(isinstance(item.get(f), str) for f in CONTENT_FIELDS):", "if False:"),
    # ---- added after the independent review
    ("ids-merged-dots-dropped", "dots are dropped from IDs, so a.b and ab share a key",
     'return source + ":" + sid.lower()', 'return source + ":" + sid.lower().replace(".", "")'),
    ("ids-merged-underscore-dash", "underscore is turned into dash in IDs",
     'return source + ":" + sid.lower()', 'return source + ":" + sid.lower().replace("_", "-")'),
    ("ids-merged-cut-to-12", "IDs are cut to 12 characters",
     'return source + ":" + sid.lower()', 'return source + ":" + sid.lower()[:12]'),
    ("ids-merged-cut-to-60", "IDs are cut to 60 characters",
     'return source + ":" + sid.lower()', 'return source + ":" + sid.lower()[:60]'),
    ("ids-merged-zeros-collapsed", "runs of zeros in IDs are collapsed",
     'return source + ":" + sid.lower()', 'return source + ":" + re.sub("0+", "0", sid.lower())'),
    ("ids-merged-leading-zeros", "leading zeros in numbers are dropped",
     'return source + ":" + sid.lower()', 'return source + ":" + re.sub(r"(?<![0-9])0+(?=[0-9])", "", sid.lower())'),
    ("ids-merged-unicode-folding", "Unicode folding (NFKC and casefold) merges look-alike IDs",
     "sid = source_id.strip()", 'sid = __import__("unicodedata").normalize("NFKC", source_id).strip().casefold()'),
    ("ids-unicode-letters-allowed", "letters outside a to z are allowed in IDs",
     'ID_RE = re.compile(r"\\A[A-Za-z0-9][A-Za-z0-9._-]*\\Z")', 'ID_RE = re.compile(r"\\A\\w[\\w.-]*\\Z")'),
    ("id-length-not-checked", "an ID of any length is accepted",
     "if len(sid) > MAX_ID_LENGTH:", "if False:"),
    ("collision-compares-body-only", "two items with one key and one body but different titles count as a repeat",
     "contents = {tuple(entries[i][2][f] for f in CONTENT_FIELDS) for i in usable}",
     'contents = {entries[i][2]["body"] for i in usable}'),
    ("collision-checks-first-pair-only", "of three items with one key, only the first two are compared",
     "contents = {tuple(entries[i][2][f] for f in CONTENT_FIELDS) for i in usable}",
     "contents = {tuple(entries[i][2][f] for f in CONTENT_FIELDS) for i in usable[:2]}"),
    ("collision-ignores-unusable-twin", "an unusable item does not count as a rival for its key",
     "if len(usable) == len(indexes) and len(contents) == 1:", "if len(contents) == 1:"),
    ("revision-not-raised", "an update does not raise the revision",
     'rec["revision"] += 1', "pass"),
    ("unsaveable-text-not-checked", "text that cannot be saved is not refused, so the run fails part-way",
     "elif not all(saveable(item[f]) for f in CONTENT_FIELDS):", "elif False:"),
    ("refused-keys-counted-absent", "refused keys are counted as not in the input",
     "            if key:\n                seen_keys.add(key)\n", ""),
    ("run-refused-echoes-source", "a refused run prints the source name as it arrived",
     'raise RunRefused("the input\'s source name is missing, too long, or is not made of "',
     'raise RunRefused(str(source) + ": the input\'s source name is missing, too long, or is not made of "'),
    ("run-stopped-prints-error-text", "an unexpected failure prints the error's own text",
     "type(error).__name__,", "error,"),
    ("unexpected-failure-not-caught", "an unexpected failure ends in a traceback",
     "except Exception as error:", "except ZeroDivisionError as error:"),
    ("deep-input-crashes", "a very deeply nested input ends in a traceback",
     'except (OSError, ValueError, RecursionError):\n        raise RunRefused("the input file cannot be read as JSON, or repeats a field name")',
     'except (OSError, ValueError):\n        raise RunRefused("the input file cannot be read as JSON, or repeats a field name")'),
    ("repeated-field-names-accepted", "a field name given twice in the input is accepted (last one wins)",
     "doc = json.load(f, object_pairs_hook=no_repeated_names)", "doc = json.load(f)"),
    ("store-record-id-clash-not-checked", "a store with two records sharing a record ID is used anyway",
     "if len(set(record_ids)) != len(record_ids):", "if False:"),
    ("store-next-number-not-checked", "a store whose next record number was set back is used anyway",
     'if store["next_record_number"] <= highest:', "if False:"),
    ("store-key-pattern-not-checked", "a store record with a key of the wrong form is used anyway",
     'isinstance(rec.get("key"), str) and KEY_RE.match(rec["key"])', 'isinstance(rec.get("key"), str)'),
    ("store-record-id-pattern-not-checked", "a store record with an odd record ID is used anyway",
     'isinstance(rec.get("record_id"), str) and RECORD_ID_RE.match(rec["record_id"])',
     'isinstance(rec.get("record_id"), str)'),
    ("store-revision-not-checked", "a store record with a revision of true or zero is used anyway",
     'and isinstance(rec.get("revision"), int) and not isinstance(rec.get("revision"), bool)\n                    and rec["revision"] >= 1',
     'and isinstance(rec.get("revision"), int)'),
    # ---- added with the source-name guard
    ("source-guard-removed", "an unknown source name is accepted without being asked for",
     "if known_sources and source not in known_sources and not allow_new_source:", "if False:"),
    ("source-guard-ignores-flag", "a new source is refused even when asked for",
     "if known_sources and source not in known_sources and not allow_new_source:",
     "if known_sources and source not in known_sources:"),
    ("source-guard-blocks-first-use", "a store with no records refuses its first source",
     "if known_sources and source not in known_sources and not allow_new_source:",
     "if source not in known_sources and not allow_new_source:"),
    ("source-guard-prefix-match", "a source name that starts like a known one counts as known",
     "if known_sources and source not in known_sources and not allow_new_source:",
     "if known_sources and not any(k.startswith(source) or source.startswith(k) for k in known_sources) and not allow_new_source:"),
    ("source-guard-flag-always-on", "the new-source flag is treated as always given",
     "return run(args.input, args.store, args.new_source,", "return run(args.input, args.store, True,"),
    ("source-guard-no-hint", "the refusal does not say how to allow a new source",
     "with --new-source. Nothing was written.", "Nothing was written."),
    # ---- added after the second review
    ("twin-guard-removed", "items relabelled to another known source are created again",
     "    if not allow_twins:\n        # An item about to be created", "    if False:\n        # An item about to be created"),
    ("twin-guard-ignores-flag", "matching items under another source are refused even when asked for",
     "    if not allow_twins:\n        # An item about to be created", "    if True:\n        # An item about to be created"),
    ("twin-guard-flag-always-on", "the same-item flag is treated as always given",
     "args.new_source, args.same_item_other_source_ok)", "args.new_source, True)"),
    ("twin-guard-matches-id-only", "any shared ID under another source stops the run, whatever the content",
     "                if all(rec[f] == item[f] for f in CONTENT_FIELDS):\n                    twins.append(", "                if True:\n                    twins.append("),
    ("twin-guard-matches-content-only", "any shared title and body under another source stops the run, whatever the ID",
     'for rec in elsewhere.get(key.partition(":")[2], []):', "for rec in [r for rs in elsewhere.values() for r in rs]:"),
    ("twin-guard-needs-all-items", "the run is stopped only when every item matches",
     "        if twins:\n", "        if twins and len(twins) == len(entries):\n"),
    # "twin-guard-checks-own-source" was planted once and removed: it changes nothing the workflow does, because
    # an item whose key is already in the store is never a candidate for the check. See planted-bugs-round-6-first-pass.txt.
    ("twin-guard-prints-content", "the refusal prints the matching item's title",
     "% (len(twins), twins[0][0], twins[0][1]))", '% (len(twins), twins[0][0], twins[0][1]) + " " + store["records"][0]["title"])'),
    ("twin-guard-no-hint", "the refusal does not say how to allow it",
     "--same-item-other-source-ok. Nothing was written.", "the right option. Nothing was written."),
    ("store-repeated-field-names-accepted", "a store file that gives a field name twice is used (last one wins)",
     "store = json.load(f, object_pairs_hook=no_repeated_names)", "store = json.load(f)"),
    ("link-not-followed", "a store given as a link is replaced by a file, and the real store is not updated",
     "args.store = os.path.realpath(args.store)", "pass"),
    ("refusal-exit-code-zero", "a run with refused items exits 0",
     'return EXIT_ITEMS_REFUSED if counts["refused"] else EXIT_OK', "return EXIT_OK"),
    ("store-reset-at-start", "the store is emptied at the start of each run",
     "store = load_store(store_path)", 'store = {"next_record_number": 1, "records": []}'),
    ("records-not-in-input-deleted", "records missing from the input are deleted",
     "untouched = sum(", 'store["records"] = [r for r in store["records"] if r["key"] in seen_keys]; save_store(store_path, store, crash)\n    untouched = sum('),
    ("damaged-store-overwritten", "an unreadable store is treated as empty and overwritten",
     'raise RunRefused("the store file cannot be read as JSON, or repeats a field name; it was left as it is")', 'return {"next_record_number": 1, "records": []}'),
    ("store-shape-not-checked", "a store with the wrong shape is used anyway",
     "if not ok:", "if False:"),
    ("store-duplicates-not-checked", "a store that already has two records with one key is used anyway",
     "if len(set(keys)) != len(keys):", "if False:"),
    ("lock-ignored", "two runs may use one store at the same time",
     "fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)", "pass"),
    ("write-not-atomic", "the store is written in place, not swapped in",
     'tmp = path + ".tmp"', "tmp = path"),
    ("stale-side-file-kept", "a half-written side file from a killed run is not cleared",
     "os.remove(tmp)  #", "pass  #"),
    ("save-once-at-end", "the store is saved once at the end of the run, not after each item",
     None, None),
]


def apply(source, name, old, new):
    if name == "save-once-at-end":
        out = source.replace("            save_store(store_path, store, crash)\n", "            crash.maybe('after-write')\n")
        out = out.replace("    untouched = sum(", "    save_store(store_path, store, crash)\n    untouched = sum(")
        assert out != source
        return out
    assert source.count(old) == 1, "%s: text found %d times, expected once" % (name, source.count(old))
    return source.replace(old, new)


def run_tests(script):
    proc = subprocess.run([sys.executable, "-B", "-m", "unittest", "discover", "-s", HERE],
                          capture_output=True, text=True, env=dict(os.environ, RERUN_SCRIPT=script))
    failed = sorted(set(re.findall(r"^(?:FAIL|ERROR): (\w+)", proc.stderr, re.M)))
    ran = re.search(r"^Ran (\d+) tests", proc.stderr, re.M)
    return proc.returncode, failed, int(ran.group(1)) if ran else 0


def main():
    only = set(sys.argv[1:])
    with open(SCRIPT, encoding="utf-8") as f:
        source = f.read()
    tmp = tempfile.mkdtemp(prefix="planted-")
    try:
        copy = os.path.join(tmp, "rerun.py")
        shutil.copy(SCRIPT, copy)
        rc, failed, ran = run_tests(copy)
        print("control  unmodified copy: %d tests ran, %d failed" % (ran, len(failed)))
        if rc != 0 or ran == 0:
            print("STOP: the control run did not pass, so the results below would mean nothing")
            return 1
        caught = survived = 0
        for name, what, old, new in BUGS:
            if only and name not in only:
                continue
            with open(copy, "w", encoding="utf-8") as f:
                f.write(apply(source, name, old, new))
            rc, failed, ran = run_tests(copy)
            if failed:
                caught += 1
                shown = ", ".join(failed[:3]) + (" and %d more" % (len(failed) - 3) if len(failed) > 3 else "")
                print("caught   %-30s %s -> %d test(s) failed: %s" % (name, what, len(failed), shown))
            else:
                survived += 1
                print("SURVIVED %-30s %s -> all %d tests passed" % (name, what, ran))
        print("total: %d planted, %d caught, %d survived" % (caught + survived, caught, survived))
        return 1 if survived else 0
    finally:
        shutil.rmtree(tmp, True)


if __name__ == "__main__":
    sys.exit(main())
