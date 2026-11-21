#!/usr/bin/env python3
"""Safe-rerun workflow for the base-camp-safe-rerun quest.

Reads a JSON file of work items and puts them into a simulated system, which is
one local JSON file (the "store"). No network, no real system.

For each item it works out a key from the source system's name and the ID that
system gave the item, looks the key up in the store, and then:

  created   no record has this key, so one is added
  updated   a record has this key and its title or body differs, so that
            record is changed in place
  skipped   a record has this key and the same title and body
  refused   the item has no usable ID, or shares its key with a different
            item in the same input; nothing is written for it

Output names keys, record IDs, positions and field names. It never prints a
title or a body.

Exit codes:
  0  ran to the end, nothing refused
  2  ran to the end, at least one item refused
  1  "run refused": bad input file, damaged store, or another run holds the
     store. This is decided before the first write, so the store is unchanged.
     Or "run stopped": something failed part-way (for example the disk could
     not be written). Items already reported above that line were written.
     Run it again once the cause is fixed.
A lock file (STORE.lock) is created beside the store on every run.

A run whose source name the store has no records from is refused when the
store already holds records, because the usual cause is the same system
exported under a new name, which would create every item again. If the source
really is new, say so with --new-source.

A run is also refused if an item it would create has the same ID, title and
body as a record under another source name, because that is what the same
item exported under the wrong name looks like. If two sources really do hold
the same item, say so with --same-item-other-source-ok.

Usage: rerun.py --input ITEMS.json --store STORE.json [--new-source] [--same-item-other-source-ok]
"""
import argparse
import fcntl
import hashlib
import json
import os
import re
import sys

EXIT_OK, EXIT_RUN_REFUSED, EXIT_ITEMS_REFUSED = 0, 1, 2

# A source name and an ID may hold only these characters, and must start with a
# letter or digit. Only the plain letters a to z count as letters, so no Unicode
# rule can fold two different IDs onto one key. A colon is not allowed, so
# "source:id" can be split in one way only.
SOURCE_RE = re.compile(r"\A[A-Za-z0-9][A-Za-z0-9_-]*\Z")
ID_RE = re.compile(r"\A[A-Za-z0-9][A-Za-z0-9._-]*\Z")
KEY_RE = re.compile(r"\A[a-z0-9][a-z0-9_-]*:[a-z0-9][a-z0-9._-]*\Z")
RECORD_ID_RE = re.compile(r"\ASIM-([0-9]{4,})\Z")
MAX_ID_LENGTH = 100
CONTENT_FIELDS = ("title", "body")


class RunRefused(Exception):
    """The whole run stops before anything is written."""


def tidy_source(source):
    if not isinstance(source, str) or not SOURCE_RE.match(source.strip()) or len(source.strip()) > MAX_ID_LENGTH:
        raise RunRefused("the input's source name is missing, too long, or is not made of "
                         "the letters a to z, digits, dash and underscore")
    return source.strip().lower()


def make_key(source, source_id):
    """Key = source name + ":" + source ID, each with outer spaces removed and A-Z lower-cased.

    Raises ValueError with a reason. The reason never contains the ID itself.
    """
    if not isinstance(source_id, str) or not source_id.strip():
        raise ValueError("no usable source_id")
    sid = source_id.strip()
    if len(sid) > MAX_ID_LENGTH:
        raise ValueError("source_id is longer than %d characters" % MAX_ID_LENGTH)
    if not ID_RE.match(sid):
        raise ValueError("source_id must start with a letter or digit and hold only "
                         "the letters a to z, digits, dot, dash and underscore")
    return source + ":" + sid.lower()


def saveable(text):
    """True if the text can be written to the store file (UTF-8)."""
    try:
        text.encode("utf-8")
        return True
    except UnicodeError:
        return False


def no_repeated_names(pairs):
    """For reading JSON: a field name given twice is an error, not "the last one wins"."""
    names = [name for name, _ in pairs]
    if len(set(names)) != len(names):
        raise ValueError("a field name is repeated")
    return dict(pairs)


# ---------------------------------------------------------------- the simulated system

def file_sha(path):
    if not os.path.exists(path):
        return "absent"
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def load_store(path):
    if not os.path.exists(path):
        return {"next_record_number": 1, "records": []}
    try:
        with open(path, encoding="utf-8") as f:
            store = json.load(f, object_pairs_hook=no_repeated_names)
    except (OSError, ValueError, RecursionError):
        raise RunRefused("the store file cannot be read as JSON, or repeats a field name; it was left as it is")
    ok = (isinstance(store, dict) and isinstance(store.get("records"), list)
          and isinstance(store.get("next_record_number"), int)
          and not isinstance(store.get("next_record_number"), bool))
    if ok:
        for rec in store["records"]:
            if not (isinstance(rec, dict) and isinstance(rec.get("key"), str) and KEY_RE.match(rec["key"])
                    and isinstance(rec.get("record_id"), str) and RECORD_ID_RE.match(rec["record_id"])
                    and isinstance(rec.get("revision"), int) and not isinstance(rec.get("revision"), bool)
                    and rec["revision"] >= 1
                    and all(isinstance(rec.get(f), str) and saveable(rec[f]) for f in CONTENT_FIELDS)):
                ok = False
                break
    if not ok:
        raise RunRefused("the store file does not have the expected shape; it was left as it is")
    keys = [rec["key"] for rec in store["records"]]
    if len(set(keys)) != len(keys):
        raise RunRefused("the store already holds two records with one key; it was left as it is")
    record_ids = [rec["record_id"] for rec in store["records"]]
    if len(set(record_ids)) != len(record_ids):
        raise RunRefused("the store holds two records with one record ID; it was left as it is")
    highest = max([int(RECORD_ID_RE.match(r).group(1)) for r in record_ids] or [0])
    if store["next_record_number"] <= highest:
        raise RunRefused("the store's next record number is not above its highest record ID; it was left as it is")
    return store


def save_store(path, store, crash):
    """Write the whole store to a side file, then swap it in, so a kill leaves the old or the new store."""
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(json.dumps(store, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
        f.flush()
        os.fsync(f.fileno())
    crash.maybe("mid-write")
    os.replace(tmp, path)
    crash.maybe("after-write")


class SimulatedKill:
    """Test hook. RERUN_SIM_CRASH=after-write:7 ends the process abruptly after the 7th
    store write; mid-write:8 ends it during the 8th, before the new store is swapped in.
    The process exits with status 137 and runs no clean-up, like a kill would."""

    def __init__(self):
        spec = os.environ.get("RERUN_SIM_CRASH", "")
        self.point, self.at = None, 0
        if spec:
            point, _, number = spec.partition(":")
            if point not in ("after-write", "mid-write") or not number.isdigit():
                raise RunRefused("RERUN_SIM_CRASH is not understood")
            self.point, self.at = point, int(number)
        self.count = {"after-write": 0, "mid-write": 0}

    def maybe(self, point):
        self.count[point] += 1
        if point == self.point and self.count[point] == self.at:
            sys.stdout.flush()
            sys.stderr.flush()
            os._exit(137)


# ---------------------------------------------------------------- the workflow

def load_input(path):
    try:
        with open(path, encoding="utf-8") as f:
            doc = json.load(f, object_pairs_hook=no_repeated_names)
    except (OSError, ValueError, RecursionError):
        raise RunRefused("the input file cannot be read as JSON, or repeats a field name")
    if not isinstance(doc, dict) or not isinstance(doc.get("items"), list):
        raise RunRefused("the input file needs a source name and a list of items")
    return tidy_source(doc.get("source")), doc["items"]


def plan(source, items):
    """Decide, before any write, which items may be processed.

    Returns one entry per input position: (position, key or None, item, refusal or None, repeat_of or None).
    """
    entries = []
    by_key = {}
    for position, item in enumerate(items, 1):
        if not isinstance(item, dict):
            entries.append([position, None, None, "item is not a set of fields", None])
            continue
        try:
            key = make_key(source, item.get("source_id"))
        except ValueError as reason:
            entries.append([position, None, None, str(reason), None])
            continue
        by_key.setdefault(key, []).append(len(entries))
        if not all(isinstance(item.get(f), str) for f in CONTENT_FIELDS):
            entries.append([position, key, None, "title or body is missing or is not text", None])
        elif not all(saveable(item[f]) for f in CONTENT_FIELDS):
            entries.append([position, key, None, "title or body holds text that cannot be saved", None])
        else:
            entries.append([position, key, item, None, None])

    for key, indexes in by_key.items():
        if len(indexes) < 2:
            continue
        positions = [entries[i][0] for i in indexes]
        usable = [i for i in indexes if entries[i][2] is not None]
        contents = {tuple(entries[i][2][f] for f in CONTENT_FIELDS) for i in usable}
        if len(usable) == len(indexes) and len(contents) == 1:
            for i in indexes[1:]:
                entries[i][4] = positions[0]
        else:
            # Any difference among items that claim one key, or an unusable item among them,
            # means nobody can say which one is right. None of them is written.
            for i in usable:
                others = ", ".join(str(p) for p in positions if p != entries[i][0])
                entries[i][3] = ("same key as position %s, different content; "
                                 "nothing written for this key" % others)
    return entries


def run(input_path, store_path, allow_new_source=False, allow_twins=False):
    crash = SimulatedKill()
    source, items = load_input(input_path)
    store = load_store(store_path)
    known_sources = sorted({rec["key"].split(":")[0] for rec in store["records"]})
    if known_sources and source not in known_sources and not allow_new_source:
        raise RunRefused("the store has no records from source '%s' (it has: %s). If this is the same system "
                         "under a new name, correct the name in the input. If it is a new source, run again "
                         "with --new-source. Nothing was written." % (source, ", ".join(known_sources)))
    sha_before = file_sha(store_path)
    records_before = len(store["records"])
    by_key = {rec["key"]: rec for rec in store["records"]}
    entries = plan(source, items)

    if not allow_twins:
        # An item about to be created that already exists, ID, title and body, under another
        # source name is most likely the same item exported under the wrong name.
        elsewhere = {}
        for rec in store["records"]:
            rec_source, _, rec_id = rec["key"].partition(":")
            if rec_source != source:
                elsewhere.setdefault(rec_id, []).append(rec)
        twins = []
        for position, key, item, refusal, repeat_of in entries:
            if refusal or key in by_key:
                continue
            for rec in elsewhere.get(key.partition(":")[2], []):
                if all(rec[f] == item[f] for f in CONTENT_FIELDS):
                    twins.append((key, rec["key"]))
        if twins:
            raise RunRefused("%d item(s) this run would create have the same ID, title and body as a record under "
                             "another source name (first: %s is the same as %s). If the source name in the input "
                             "is wrong, correct it. If two sources really hold the same item, run again with "
                             "--same-item-other-source-ok. Nothing was written."
                             % (len(twins), twins[0][0], twins[0][1]))

    print("run: source=%s input_items=%d" % (source, len(items)))
    counts = {"created": 0, "updated": 0, "skipped": 0, "refused": 0}
    seen_keys = set()

    def say(verb, text):
        counts[verb] += 1
        print("%-8s %s" % (verb, text), flush=True)

    for position, key, item, refusal, repeat_of in entries:
        if refusal:
            say("refused", "%s at position %d (%s)" % (key, position, refusal) if key
                else "position %d (%s)" % (position, refusal))
            if key:
                seen_keys.add(key)
            continue
        seen_keys.add(key)
        if repeat_of:
            say("skipped", "%s at position %d (repeat of position %d in this input, same content)"
                % (key, position, repeat_of))
            continue
        rec = by_key.get(key)
        if rec is None:
            rec = {"key": key, "record_id": "SIM-%04d" % store["next_record_number"], "revision": 1}
            for field in CONTENT_FIELDS:
                rec[field] = item[field]
            store["next_record_number"] += 1
            store["records"].append(rec)
            by_key[key] = rec
            save_store(store_path, store, crash)
            say("created", "%s -> %s" % (key, rec["record_id"]))
            continue
        changed = [f for f in CONTENT_FIELDS if rec[f] != item[f]]
        if not changed:
            say("skipped", "%s = %s (already present, content unchanged)" % (key, rec["record_id"]))
            continue
        for field in changed:
            rec[field] = item[field]
        rec["revision"] += 1
        save_store(store_path, store, crash)
        say("updated", "%s = %s (changed: %s; revision %d -> %d)"
            % (key, rec["record_id"], ", ".join(changed), rec["revision"] - 1, rec["revision"]))

    untouched = sum(1 for k in by_key if k not in seen_keys)
    print("summary: created=%(created)d updated=%(updated)d skipped=%(skipped)d refused=%(refused)d" % counts)
    print("store: records_before=%d records_after=%d untouched_not_in_input=%d sha256_before=%s sha256_after=%s"
          % (records_before, len(store["records"]), untouched, sha_before, file_sha(store_path)))
    return EXIT_ITEMS_REFUSED if counts["refused"] else EXIT_OK


def main(argv=None):
    parser = argparse.ArgumentParser(description="Put work items into the simulated system; safe to run again.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--store", required=True)
    parser.add_argument("--new-source", action="store_true",
                        help="allow a source name the store has no records from yet")
    parser.add_argument("--same-item-other-source-ok", action="store_true",
                        help="allow creating an item that matches a record under another source name")
    args = parser.parse_args(argv)
    args.store = os.path.realpath(args.store)  # a link to a store means the store itself
    try:
        lock = open(args.store + ".lock", "a")
    except OSError:
        print("run refused: the store's folder cannot be written", file=sys.stderr)
        return EXIT_RUN_REFUSED
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        print("run refused: another run is using this store", file=sys.stderr)
        return EXIT_RUN_REFUSED
    try:
        tmp = args.store + ".tmp"
        if os.path.exists(tmp):
            os.remove(tmp)  # half-written side file from a killed run; the store itself is whole
        return run(args.input, args.store, args.new_source, args.same_item_other_source_ok)
    except RunRefused as reason:
        print("run refused: %s" % reason, file=sys.stderr)
        return EXIT_RUN_REFUSED
    except Exception as error:  # the message may hold item text, so only its kind is printed
        sys.stdout.flush()
        print("run stopped: unexpected %s. Items reported above this line were written; "
              "nothing after them was. Run again once the cause is fixed." % type(error).__name__,
              file=sys.stderr)
        return EXIT_RUN_REFUSED
    finally:
        lock.close()


if __name__ == "__main__":
    sys.exit(main())
