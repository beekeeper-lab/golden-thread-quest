"""Independent reading of the simulated store, used by the tests.

This file does not import the workflow. It reads two store files (before and
after a run) as plain JSON and works out, by key, what was created, updated,
removed or left alone. The tests compare this with what the workflow reported.
"""
import json


def records_by_key(store_bytes):
    """Return {key: record}. An absent store (None) is an empty store."""
    if store_bytes is None:
        return {}
    doc = json.loads(store_bytes.decode("utf-8"))
    out = {}
    for rec in doc["records"]:
        if rec["key"] in out:
            raise AssertionError("duplicate key in store: " + rec["key"])
        out[rec["key"]] = rec
    return out


def diff(before_bytes, after_bytes):
    before = records_by_key(before_bytes)
    after = records_by_key(after_bytes)
    created = sorted(k for k in after if k not in before)
    removed = sorted(k for k in before if k not in after)
    updated = sorted(k for k in after if k in before and after[k] != before[k])
    unchanged = sorted(k for k in after if k in before and after[k] == before[k])
    return {"created": created, "updated": updated, "removed": removed, "unchanged": unchanged}
