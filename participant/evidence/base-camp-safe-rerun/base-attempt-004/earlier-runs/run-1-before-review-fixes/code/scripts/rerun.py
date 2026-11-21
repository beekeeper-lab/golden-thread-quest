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

Exit codes: 0 ran, nothing refused; 2 ran, at least one item refused;
1 the run was refused as a whole (bad input file, damaged store, or another
run holds the store) and nothing was written.

Usage: rerun.py --input ITEMS.json --store STORE.json
"""
import argparse
import fcntl
import hashlib
import json
import os
import re
import sys
import unicodedata

EXIT_OK, EXIT_RUN_REFUSED, EXIT_ITEMS_REFUSED = 0, 1, 2

# After tidying, a source name and an ID may hold only these characters. A
# colon is not among them, so "source:id" can be split in one way only.
SOURCE_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
CONTENT_FIELDS = ("title", "body")


class RunRefused(Exception):
    """The whole run stops before anything is written."""


def tidy(text):
    """Same text however it was typed: one Unicode form, no outer spaces, lower case."""
    return unicodedata.normalize("NFKC", text).strip().casefold()


def tidy_source(source):
    if not isinstance(source, str) or not SOURCE_RE.match(tidy(source)):
        raise RunRefused("the input's source name is missing or has characters "
                         "outside letters, digits, dash and underscore")
    return tidy(source)


def make_key(source, source_id):
    """Key = tidied source name + ":" + tidied source ID. Raises ValueError with a reason."""
    if not isinstance(source_id, str) or not tidy(source_id):
        raise ValueError("no usable source_id")
    sid = tidy(source_id)
    if not ID_RE.match(sid):
        raise ValueError("source_id has characters outside letters, digits, dot, dash and underscore")
    return source + ":" + sid


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
            store = json.load(f)
    except (OSError, ValueError):
        raise RunRefused("the store file cannot be read as JSON; it was left as it is")
    ok = (isinstance(store, dict) and isinstance(store.get("records"), list)
          and isinstance(store.get("next_record_number"), int)
          and not isinstance(store.get("next_record_number"), bool))
    if ok:
        for rec in store["records"]:
            if not (isinstance(rec, dict) and isinstance(rec.get("key"), str)
                    and isinstance(rec.get("record_id"), str)
                    and isinstance(rec.get("revision"), int)
                    and all(isinstance(rec.get(f), str) for f in CONTENT_FIELDS)):
                ok = False
                break
    if not ok:
        raise RunRefused("the store file does not have the expected shape; it was left as it is")
    keys = [rec["key"] for rec in store["records"]]
    if len(set(keys)) != len(keys):
        raise RunRefused("the store already holds two records with one key; it was left as it is")
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
            doc = json.load(f)
    except (OSError, ValueError):
        raise RunRefused("the input file cannot be read as JSON")
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
        if not all(isinstance(item.get(f), str) for f in CONTENT_FIELDS):
            entries.append([position, key, None, "title or body is missing or is not text", None])
            continue
        entries.append([position, key, item, None, None])
        by_key.setdefault(key, []).append(len(entries) - 1)

    for key, indexes in by_key.items():
        if len(indexes) < 2:
            continue
        contents = {tuple(entries[i][2][f] for f in CONTENT_FIELDS) for i in indexes}
        positions = [entries[i][0] for i in indexes]
        if len(contents) == 1:
            for i in indexes[1:]:
                entries[i][4] = positions[0]
        else:
            for i in indexes:
                others = ", ".join(str(p) for p in positions if p != entries[i][0])
                entries[i][3] = ("same key as position %s, different content; "
                                 "nothing written for this key" % others)
    return entries


def run(input_path, store_path):
    crash = SimulatedKill()
    source, items = load_input(input_path)
    store = load_store(store_path)
    sha_before = file_sha(store_path)
    records_before = len(store["records"])
    by_key = {rec["key"]: rec for rec in store["records"]}
    entries = plan(source, items)

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
    args = parser.parse_args(argv)
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
        return run(args.input, args.store)
    except RunRefused as reason:
        print("run refused: %s" % reason, file=sys.stderr)
        return EXIT_RUN_REFUSED
    finally:
        lock.close()


if __name__ == "__main__":
    sys.exit(main())
