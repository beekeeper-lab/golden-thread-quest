#!/usr/bin/env python3
"""More recorded runs, made some time after scripts/record_evidence.py, on the stores it left in work/.

1. later-run.txt: the last input again (items-retitled.json) against work/store.json. The store has not
   been touched since the retitled run. Expected from the quest: nothing created, nothing changed.
2. source-change-run.txt: the same items with the source name changed to intake-v2, against a copy of
   that store (a copy, so that a failure could not spoil the main store). Expected: refused, nothing
   created. Then with --new-source: still refused, because the items are the same as the intake ones.
   Then with both flags, to show what a person can still allow on purpose.
3. relabel-run.txt: another copy of the store. A second source (billing, three items of its own) is
   added with --new-source. Then the intake items arrive labelled billing. Expected: refused, nothing
   created, although billing is a source name the store knows.

Run from the attempt folder:  python3 -B scripts/record_later_runs.py
"""
import os
import shutil
import sys

from record_evidence import ATTEMPT, fingerprint, record


def main():
    os.chdir(ATTEMPT)
    for name in ("later-run.txt", "source-change-run.txt", "relabel-run.txt"):
        if os.path.exists(os.path.join("logs", name)):
            print("logs/%s already exists. Move it away by hand first." % name)
            return 1
    for name in ("work/store-source-change.json", "work/store-relabel.json"):
        if os.path.exists(name):
            print("%s already exists. Move it away by hand first." % name)
            return 1
    if fingerprint("work/store.json") != fingerprint("store-snapshots/3b-after-retitled-run.json"):
        print("work/store.json is not the store the retitled run left. Stopping.")
        return 1

    record("later-run.txt", "items-retitled.json", "work/store.json",
           note="made later than the first recording (compare the 'recorded' lines), same store, same input "
                "as logs/retitled-run.txt, with the workflow as it is now.")
    shutil.copy("work/store.json", "store-snapshots/7-after-later-run.json")

    copy = "work/store-source-change.json"
    shutil.copy("work/store.json", copy)
    record("source-change-run.txt", "items-source-renamed.json", copy,
           note="a copy of the main store. The input is items-retitled.json with the source name changed "
                "from intake to intake-v2.")
    record("source-change-run.txt", "items-source-renamed.json", copy, extra=["--new-source"],
           note="the same with --new-source. Still refused: the items match the intake records.")
    record("source-change-run.txt", "items-source-renamed.json", copy,
           extra=["--new-source", "--same-item-other-source-ok"],
           note="the same with both flags, to show what a person can still allow on purpose: the ten items "
                "are created under the new name, beside the ten that were there.")
    shutil.copy(copy, "store-snapshots/8-after-both-flags.json")

    copy = "work/store-relabel.json"
    shutil.copy("work/store.json", copy)
    record("relabel-run.txt", "items-billing.json", copy, extra=["--new-source"],
           note="another copy of the main store. A second source, billing, with three items of its own, "
                "is added on purpose.")
    shutil.copy(copy, "store-snapshots/9-two-sources.json")
    record("relabel-run.txt", "items-relabelled-billing.json", copy,
           note="the ten intake items arrive labelled billing, a source name this store knows.")
    shutil.copy(copy, "store-snapshots/10-after-relabel-run.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
