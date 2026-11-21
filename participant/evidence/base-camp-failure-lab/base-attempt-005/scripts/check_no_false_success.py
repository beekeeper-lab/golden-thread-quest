#!/usr/bin/env python3
"""Records logs/no-false-success.txt for the base-camp-failure-lab quest.

Looks at the files the recorded runs left in work/ and checks that no run
that failed left a result that reads as complete.

It does not ask sync.py what happened. It opens each saved file itself and
compares it with what it knows the fake service holds: 100 stories,
STORY-001 to STORY-100.

For a run that should have failed or been incomplete, all of these must hold:
  - work/<run>.json (the name a complete result gets) does not exist
  - work/<run>.json.INCOMPLETE.json exists
  - inside, "status" is "incomplete" and "reason" is not empty
  - it holds fewer than 100 stories
  - no work/<run>.json.EARLIER.json, unless an earlier run had saved a
    complete file under the same name; then that file must be there,
    renamed, still holding all 100
For a run that should have completed:
  - work/<run>.json exists and says "status": "complete"
  - it holds exactly the 100 stories, each once
  - no INCOMPLETE file sits beside it
Then every file in work/ is swept once more: any file that says "complete"
must hold all 100 stories, whatever its name, and must be either a run that
should have completed or an EARLIER file.

Run from the attempt folder, after record_evidence.py:
    python3 scripts/check_no_false_success.py
Exit code 0 if every check passed, 1 if any failed.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ATTEMPT = os.path.dirname(HERE)
TRUTH = {"STORY-%03d" % n for n in range(1, 101)}

# run name -> should it have ended complete?
RUNS = [
    ("0-healthy", True),
    ("1a-timeout-lasting", False),
    ("1b-timeout-recovers", True),
    ("2-partial", False),
    ("3a-rate-limit-recovers", True),
    ("3b-rate-limit-lasting", False),
    ("3c-rate-limit-too-long", False),
    ("4a-malformed-answer", False),
    ("4b-malformed-item", False),
    ("5-failure-after-earlier-success", False),
]
# Runs where a complete file from an earlier run was already at the output name.
HAD_EARLIER = {"5-failure-after-earlier-success"}


COMPLETE_RUNS = {name for name, should_complete in RUNS if should_complete}


def describe(path):
    """Open a saved file and say what is really in it."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    ids = [item.get("id") for item in data["items"]]
    return {
        "status": data.get("status"),
        "reason": data.get("reason"),
        "count": len(ids),
        "all_100_once": len(ids) == 100 and set(ids) == TRUTH,
        "only_real_ids": all(i in TRUTH for i in ids) and len(set(ids)) == len(ids),
    }


def main():
    os.chdir(ATTEMPT)
    lines = []
    failed = []

    def out(text=""):
        lines.append(text)

    def check(label, ok):
        out("  %-4s %s" % ("ok" if ok else "FAIL", label))
        if not ok:
            failed.append(label)

    out("No false success: base-camp-failure-lab, attempt base-attempt-005")
    out("Recorded by scripts/check_no_false_success.py")
    out("")
    out("Checks the files left in work/ by the runs in logs/failure-runs.txt.")
    out("The checker opens each file itself and compares it with the 100 stories")
    out("the fake service holds (STORY-001 to STORY-100).")

    for name, should_complete in RUNS:
        named = "work/%s.json" % name
        marked = named + ".INCOMPLETE.json"
        out("")
        out("RUN %s   (should end %s)" % (name, "complete" if should_complete else "failed or incomplete"))
        if should_complete:
            check("%s exists" % named, os.path.exists(named))
            check("no INCOMPLETE file beside it", not os.path.exists(marked))
            if os.path.exists(named):
                d = describe(named)
                check('it says "status": "complete"', d["status"] == "complete")
                check("it holds all 100 stories, each once (found %d)" % d["count"], d["all_100_once"])
        else:
            check("%s does not exist" % named, not os.path.exists(named))
            check("%s exists" % marked, os.path.exists(marked))
            if os.path.exists(marked):
                d = describe(marked)
                check('it says "status": "incomplete"', d["status"] == "incomplete")
                check("it gives a reason: %s" % d["reason"], bool(d["reason"]))
                check("it holds fewer than 100 stories (found %d)" % d["count"], d["count"] < 100)
                check("every story in it is a real one, none twice, none made up", d["only_real_ids"])
            earlier = named + ".EARLIER.json"
            if name in HAD_EARLIER:
                check("%s exists (the earlier run's file, renamed)" % earlier, os.path.exists(earlier))
                if os.path.exists(earlier):
                    check("it still holds all 100 stories, unchanged", describe(earlier)["all_100_once"])
            else:
                check("no EARLIER file (there was no earlier run)", not os.path.exists(earlier))

    out("")
    out("SWEEP of every file in work/")
    names = sorted(os.listdir("work"))
    for name in names:
        d = describe(os.path.join("work", name))
        says_complete = d["status"] == "complete"
        out("  %-48s says %-10s holds %3d" % (name, d["status"], d["count"]))
        if says_complete and not d["all_100_once"]:
            failed.append("%s says complete but does not hold all 100" % name)
            out("  FAIL the file above says complete but does not hold all 100")
        if says_complete and not name.endswith(".EARLIER.json") and name[:-len(".json")] not in COMPLETE_RUNS:
            failed.append("%s says complete under the name of a run that failed" % name)
            out("  FAIL the file above says complete under the name of a run that failed")
        if not says_complete and not name.endswith(".INCOMPLETE.json"):
            failed.append("%s is not complete but its name does not say so" % name)
            out("  FAIL the file above is not complete but its name does not say so")
    expected = len(RUNS) + len(HAD_EARLIER)
    check("%d files swept, expected %d (one per run, and one EARLIER file)" % (len(names), expected),
          len(names) == expected)

    out("")
    if failed:
        out("RESULT: %d CHECK(S) FAILED" % len(failed))
        for label in failed:
            out("  - " + label)
    else:
        out("RESULT: ALL CHECKS PASSED. No failed run left a result that reads as complete.")

    text = "\n".join(lines) + "\n"
    with open(os.path.join("logs", "no-false-success.txt"), "w", encoding="utf-8") as f:
        f.write(text)
    sys.stdout.write(text)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
