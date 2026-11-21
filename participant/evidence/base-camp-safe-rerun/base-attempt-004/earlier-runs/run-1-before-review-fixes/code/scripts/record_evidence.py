#!/usr/bin/env python3
"""Record the evidence runs for the quest, in one go, without touching the store between runs.

Run from the attempt folder:  python3 -B scripts/record_evidence.py

It refuses to start if work/ already exists, so an earlier store is never
reused or wiped by this script. The only thing it does to a store between two
commands is read it (to fingerprint it and to copy a snapshot). The fingerprints
in each log are taken by this script from the file on disk, separately from the
ones the workflow prints.

Paths are relative to the attempt folder, so no home folder name is recorded.
"""
import datetime
import hashlib
import os
import shutil
import subprocess
import sys

ATTEMPT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ATTEMPT, "tests"))
import store_oracle  # noqa: E402  (the independent store reader the tests use)


def fingerprint(path):
    if not os.path.exists(path):
        return "absent"
    with open(path, "rb") as f:
        data = f.read()
    return "sha256 %s (%d bytes)" % (hashlib.sha256(data).hexdigest(), len(data))


def record(log, input_name, store, env=None, note=None):
    cmd = ["python3", "-B", "scripts/rerun.py", "--input", "scripts/sample/" + input_name, "--store", store]
    shown = " ".join(("%s=%s " % kv for kv in (env or {}).items())) + " ".join(cmd)
    before = fingerprint(store)
    proc = subprocess.run([sys.executable] + cmd[1:], capture_output=True, text=True,
                          env=dict(os.environ, **(env or {})), cwd=ATTEMPT)
    lines = ["$ " + shown,
             "recorded (UTC): " + datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")]
    if note:
        lines.append("note: " + note)
    lines += ["store file before this command, read by the recorder: " + before,
              "--- output (stdout, then stderr) ---",
              proc.stdout.rstrip("\n"), proc.stderr.rstrip("\n"),
              "--- end of output ---",
              "exit code: %d" % proc.returncode,
              "store file after this command, read by the recorder: " + fingerprint(store), ""]
    with open(os.path.join(ATTEMPT, "logs", log), "a", encoding="utf-8") as f:
        f.write("\n".join(l for l in lines if l is not None))
    print("recorded logs/%s (exit %d)" % (log, proc.returncode))
    return proc.returncode


def read(path):
    with open(path, "rb") as f:
        return f.read()


def main():
    os.chdir(ATTEMPT)
    if os.path.exists("work"):
        print("work/ already exists. Move it away by hand first; this script will not reuse or delete a store.")
        return 1
    os.makedirs("work")
    os.makedirs("store-snapshots", exist_ok=True)
    for name in ("first-run.txt", "second-run.txt", "changed-input.txt", "interrupted-run.txt",
                 "collision-run.txt", "store-check.txt"):
        if os.path.exists(os.path.join("logs", name)):
            print("logs/%s already exists. Move it away by hand first." % name)
            return 1

    main_store = "work/store.json"
    record("first-run.txt", "items.json", main_store)
    shutil.copy(main_store, "store-snapshots/1-after-first-run.json")
    record("second-run.txt", "items.json", main_store)
    shutil.copy(main_store, "store-snapshots/2-after-second-run.json")
    record("changed-input.txt", "items-changed.json", main_store)
    shutil.copy(main_store, "store-snapshots/3-after-changed-input.json")

    other = "work/store-interrupted.json"
    record("interrupted-run.txt", "items.json", other, env={"RERUN_SIM_CRASH": "after-write:7"},
           note="separate store. The kill is simulated: the workflow ends itself abruptly "
                "(os._exit, status 137) after its 7th store write.")
    shutil.copy(other, "store-snapshots/4-after-interrupted-run.json")
    record("interrupted-run.txt", "items.json", other, note="the rerun, same store, same input, no kill.")
    shutil.copy(other, "store-snapshots/5-after-rerun-of-interrupted.json")

    record("collision-run.txt", "items-collision.json", "work/store-collision.json",
           note="separate store. The input has two different items that share one ID (positions 3 and 11) "
                "and one item with no ID (position 12).")
    shutil.copy("work/store-collision.json", "store-snapshots/6-after-collision-run.json")

    # What the store files themselves show, worked out without the workflow's reports.
    snap = lambda n: read(os.path.join("store-snapshots", n))
    s1, s2, s3 = snap("1-after-first-run.json"), snap("2-after-second-run.json"), snap("3-after-changed-input.json")
    s4, s5, s6 = (snap("4-after-interrupted-run.json"), snap("5-after-rerun-of-interrupted.json"),
                  snap("6-after-collision-run.json"))
    out = ["Store snapshots compared by tests/store_oracle.py (it does not import the workflow).", ""]

    def show(title, before, after):
        d = store_oracle.diff(before, after)
        out.append(title)
        out.append("  records: %d -> %d" % (len(store_oracle.records_by_key(before)), len(store_oracle.records_by_key(after))))
        for part in ("created", "updated", "removed"):
            out.append("  %s (%d): %s" % (part, len(d[part]), ", ".join(d[part]) or "none"))
        out.append("  unchanged: %d" % len(d["unchanged"]))
        out.append("  files byte-for-byte identical: %s" % ("yes" if before == after else "no"))
        out.append("")

    show("empty store -> after first run", None, s1)
    show("after first run -> after second run", s1, s2)
    show("after second run -> after changed-input run", s2, s3)
    show("empty store -> after interrupted run", None, s4)
    show("after interrupted run -> after its rerun", s4, s5)
    show("after first run (uninterrupted) -> after rerun of the interrupted run (two different stores)", s1, s5)
    show("empty store -> after collision run", None, s6)
    r2, r3 = store_oracle.records_by_key(s2), store_oracle.records_by_key(s3)
    for key in store_oracle.diff(s2, s3)["updated"]:
        fields = [f for f in sorted(r3[key]) if r3[key][f] != r2[key][f]]
        out.append("changed-input run, %s: record_id %s -> %s; fields that differ: %s"
                   % (key, r2[key]["record_id"], r3[key]["record_id"], ", ".join(fields)))
    with open("logs/store-check.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    print("recorded logs/store-check.txt")
    return 0


if __name__ == "__main__":
    sys.exit(main())
