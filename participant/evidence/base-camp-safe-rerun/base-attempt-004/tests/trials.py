"""Real-kill and many-at-once trials against scripts/rerun.py.

Unlike the unit tests, the kill here is a real SIGKILL sent from outside at a random moment,
with no help from the workflow's test hook. Everything happens in a temporary folder.

Expected results come from the quest, not from the code:
  - after any kill the store is readable and holds no key twice
  - once a run is allowed to finish, the store is byte-for-byte what one uninterrupted run gives
  - several runs started at once leave that same store, and no record is doubled

Run:  python3 -B tests/trials.py      (from the attempt folder; about a minute)
"""
import json
import os
import random
import shutil
import signal
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import store_oracle  # noqa: E402

SCRIPT = os.environ.get("RERUN_SCRIPT", os.path.join(HERE, "..", "scripts", "rerun.py"))
ITEMS, KILL_TRIALS, KILLS_PER_TRIAL, PARALLEL_TRIALS, PARALLEL_RUNS = 600, 6, 4, 3, 8
SEED = 20261117


def read(path):
    if not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        return f.read()


def cmd(inp, store):
    return [sys.executable, "-B", SCRIPT, "--input", inp, "--store", store]


def main():
    rng = random.Random(SEED)
    tmp = tempfile.mkdtemp(prefix="rerun-trials-")
    problems = []
    try:
        inp = os.path.join(tmp, "items.json")
        with open(inp, "w") as f:
            json.dump({"source": "trial", "items": [
                {"source_id": "T-%04d" % i, "title": "trial item %d" % i, "body": "made-up body %d" % i}
                for i in range(1, ITEMS + 1)]}, f)
        clean_store = os.path.join(tmp, "clean.json")
        started = time.time()
        proc = subprocess.run(cmd(inp, clean_store), capture_output=True, text=True)
        clean_seconds = time.time() - started
        clean = read(clean_store)
        print("input: %d made-up items. random seed %d." % (ITEMS, SEED))
        print("uninterrupted run: exit %d, %d records, %.2f seconds" % (
            proc.returncode, len(store_oracle.records_by_key(clean)), clean_seconds))
        if proc.returncode != 0 or len(store_oracle.records_by_key(clean)) != ITEMS:
            print("STOP: the uninterrupted run did not give %d records" % ITEMS)
            return 1

        print("")
        print("REAL KILL: %d trials, up to %d SIGKILLs each at random moments, then one run left to finish" % (
            KILL_TRIALS, KILLS_PER_TRIAL))
        landed_total = 0
        for trial in range(1, KILL_TRIALS + 1):
            store = os.path.join(tmp, "kill-%d.json" % trial)
            notes = []
            for _ in range(KILLS_PER_TRIAL):
                delay = rng.uniform(0.05, max(0.1, clean_seconds * 0.6))
                p = subprocess.Popen(cmd(inp, store), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                time.sleep(delay)
                still_running = p.poll() is None
                if still_running:
                    p.send_signal(signal.SIGKILL)
                p.wait()
                data = read(store)
                try:
                    count = len(store_oracle.records_by_key(data))
                except Exception as error:  # unreadable store or a key twice
                    problems.append("trial %d: store not usable after a kill (%s)" % (trial, type(error).__name__))
                    count = -1
                landed = still_running and p.returncode == -signal.SIGKILL
                landed_total += landed
                notes.append("%s at %.2fs -> %d records" % ("killed" if landed else "finished before the kill", delay, count))
            final = subprocess.run(cmd(inp, store), capture_output=True, text=True)
            same = read(store) == clean
            leftovers = [n for n in os.listdir(tmp) if n.startswith("kill-%d.json" % trial)
                         and n not in ("kill-%d.json" % trial, "kill-%d.json.lock" % trial)]
            if final.returncode != 0:
                problems.append("trial %d: the finishing run exited %d" % (trial, final.returncode))
            if not same:
                problems.append("trial %d: final store differs from the uninterrupted run's store" % trial)
            if leftovers:
                problems.append("trial %d: left-over files %s" % (trial, leftovers))
            summary = [l for l in final.stdout.splitlines() if l.startswith("summary:")]
            print("trial %d: %s" % (trial, "; ".join(notes)))
            print("         finishing run: exit %d, %s; store identical to uninterrupted run: %s; left-over files: %d" % (
                final.returncode, summary[0] if summary else "no summary", "yes" if same else "NO", len(leftovers)))
        print("kills that landed while the workflow was running: %d of %d" % (landed_total, KILL_TRIALS * KILLS_PER_TRIAL))
        if landed_total < KILL_TRIALS:
            problems.append("too few kills landed mid-run for this to mean much")

        print("")
        print("MANY AT ONCE: %d trials, %d runs started together on one empty store" % (PARALLEL_TRIALS, PARALLEL_RUNS))
        for trial in range(1, PARALLEL_TRIALS + 1):
            store = os.path.join(tmp, "par-%d.json" % trial)
            procs = [subprocess.Popen(cmd(inp, store), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                     for _ in range(PARALLEL_RUNS)]
            results = [(p.communicate(), p.returncode) for p in procs]
            ok = sum(1 for _, rc in results if rc == 0)
            locked = sum(1 for (out, err), rc in results if rc == 1 and "another run is using this store" in err)
            other = PARALLEL_RUNS - ok - locked
            created = sum(int(l.split("created=")[1].split()[0]) for (out, _), rc in results if rc == 0
                          for l in out.splitlines() if l.startswith("summary:"))
            same = read(store) == clean
            if other:
                problems.append("parallel trial %d: %d runs ended in some other way" % (trial, other))
            if not same:
                problems.append("parallel trial %d: store differs from the uninterrupted run's store" % trial)
            if created != ITEMS:
                problems.append("parallel trial %d: runs reported %d created in total, expected %d" % (trial, created, ITEMS))
            print("trial %d: %d ran (exit 0), %d refused because another run held the store (exit 1), %d other; "
                  "created in total: %d; store identical to uninterrupted run: %s" % (
                      trial, ok, locked, other, created, "yes" if same else "NO"))

        print("")
        print("problems: %s" % ("none" if not problems else ""))
        for line in problems:
            print("  - " + line)
        return 1 if problems else 0
    finally:
        shutil.rmtree(tmp, True)


if __name__ == "__main__":
    sys.exit(main())
