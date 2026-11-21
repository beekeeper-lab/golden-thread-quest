"""Tests for the safe-rerun workflow, written from the quest's acceptance criteria.

Criteria (quest base-camp-safe-rerun, version 1):
  C1 every item has a key that stays the same across runs
  C2 the key does not depend on a title, a filename or the run time
  C3 a second run on identical input creates and changes nothing
  C4 a changed item is updated in place, not added again
  C5 each run reports what it created, updated and skipped
  C6 the result of the second run equals the result of the first

The workflow is run as a separate program, the way a person would run it. The
tests never import it. Expected keys are written out by hand below, and what a
run did to the store is worked out by tests/store_oracle.py from the store file.

Run:  python3 -B -m unittest discover -s tests -v     (from the attempt folder)
"""
import copy
import fcntl
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import store_oracle  # noqa: E402

SCRIPT = os.environ.get("RERUN_SCRIPT", os.path.join(HERE, "..", "scripts", "rerun.py"))
SAMPLE_DIR = os.path.join(HERE, "..", "scripts", "sample")

# Written by hand from the key rule: source name, a colon, the source's own ID,
# lower case, no surrounding spaces. Not computed by the code under test.
EXPECTED_KEYS = [
    "intake:req-0001", "intake:req-0002", "intake:req-0003", "intake:req-0004",
    "intake:req-0005", "intake:req-0006", "intake:req-0007", "intake:req-0008",
    "intake:req-0009", "intake:req-0010",
]

LINE = re.compile(r"^(created|updated|skipped|refused)\s+(.*)$")
SUMMARY = re.compile(r"^summary: created=(\d+) updated=(\d+) skipped=(\d+) refused=(\d+)$", re.M)
STORE_LINE = re.compile(
    r"^store: records_before=(\d+) records_after=(\d+) untouched_not_in_input=(\d+) "
    r"sha256_before=(\S+) sha256_after=(\S+)$", re.M)

# A clock about 400 days ahead, loaded into the workflow's Python before it starts.
FAKE_CLOCK = '''
import time, datetime
_SHIFT = 400 * 24 * 3600
_t, _tns = time.time, time.time_ns
time.time = lambda: _t() + _SHIFT
time.time_ns = lambda: _tns() + _SHIFT * 10**9
_lt, _gt = time.localtime, time.gmtime
time.localtime = lambda s=None: _lt(time.time() if s is None else s)
time.gmtime = lambda s=None: _gt(time.time() if s is None else s)
_sf = time.strftime
time.strftime = lambda f, t=None: _sf(f, time.localtime() if t is None else t)
_real = datetime.datetime
class _Shifted(_real):
    @classmethod
    def now(cls, tz=None):
        return _real.now(tz) + datetime.timedelta(seconds=_SHIFT)
    @classmethod
    def utcnow(cls):
        return _real.utcnow() + datetime.timedelta(seconds=_SHIFT)
    @classmethod
    def today(cls):
        return _real.today() + datetime.timedelta(seconds=_SHIFT)
datetime.datetime = _Shifted
_rd = datetime.date
class _ShiftedDate(_rd):
    @classmethod
    def today(cls):
        return (_real.now() + datetime.timedelta(seconds=_SHIFT)).date()
datetime.date = _ShiftedDate
'''


def sample():
    with open(os.path.join(SAMPLE_DIR, "items.json"), encoding="utf-8") as f:
        return json.load(f)


def read_bytes(path):
    if not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        return f.read()


def sha(data):
    return "absent" if data is None else hashlib.sha256(data).hexdigest()


class Result:
    def __init__(self, proc):
        self.rc = proc.returncode
        self.out = proc.stdout
        self.err = proc.stderr
        self.text = proc.stdout + proc.stderr
        self.lines = [m.groups() for m in map(LINE.match, proc.stdout.splitlines()) if m]
        m = SUMMARY.search(proc.stdout)
        self.summary = None if not m else dict(zip(
            ("created", "updated", "skipped", "refused"), map(int, m.groups())))
        s = STORE_LINE.search(proc.stdout)
        self.store = None if not s else {
            "records_before": int(s.group(1)), "records_after": int(s.group(2)),
            "untouched": int(s.group(3)), "sha_before": s.group(4), "sha_after": s.group(5)}

    def verbs_for(self, key):
        return [verb for verb, rest in self.lines if rest.split()[0] == key]


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="rerun-test-")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.store = os.path.join(self.tmp, "store.json")
        self._n = 0

    def write_input(self, doc, name=None, subdir=None):
        self._n += 1
        folder = self.tmp if subdir is None else os.path.join(self.tmp, subdir)
        os.makedirs(folder, exist_ok=True)
        path = os.path.join(folder, name or "input-%d.json" % self._n)
        with open(path, "w", encoding="utf-8") as f:
            if isinstance(doc, str):
                f.write(doc)
            else:
                json.dump(doc, f)
        return path

    def run_wf(self, doc_or_path, env=None, store=None):
        path = doc_or_path if isinstance(doc_or_path, str) and os.path.exists(doc_or_path) \
            else self.write_input(doc_or_path)
        full_env = dict(os.environ)
        full_env.pop("RERUN_SIM_CRASH", None)
        full_env.update(env or {})
        proc = subprocess.run(
            [sys.executable, "-B", SCRIPT, "--input", path, "--store", store or self.store],
            capture_output=True, text=True, env=full_env, timeout=60)
        return Result(proc)

    def run_checked(self, doc, **kw):
        """Run and check the report against the store, read independently."""
        before = read_bytes(kw.get("store") or self.store)
        res = self.run_wf(doc, **kw)
        after = read_bytes(kw.get("store") or self.store)
        self.assert_report_matches_store(res, before, after)
        return res, before, after

    def assert_report_matches_store(self, res, before, after):
        self.assertIsNotNone(res.summary, "no summary line in:\n" + res.text)
        self.assertIsNotNone(res.store, "no store line in:\n" + res.text)
        d = store_oracle.diff(before, after)
        self.assertEqual(d["removed"], [], "a run removed records")
        self.assertEqual(res.summary["created"], len(d["created"]), res.text)
        self.assertEqual(res.summary["updated"], len(d["updated"]), res.text)
        created_lines = sorted(r.split()[0] for v, r in res.lines if v == "created")
        updated_lines = sorted(r.split()[0] for v, r in res.lines if v == "updated")
        self.assertEqual(created_lines, d["created"])
        self.assertEqual(updated_lines, d["updated"])
        self.assertEqual(res.store["records_before"], len(store_oracle.records_by_key(before)))
        self.assertEqual(res.store["records_after"], len(store_oracle.records_by_key(after)))
        self.assertEqual(res.store["sha_before"], sha(before))
        self.assertEqual(res.store["sha_after"], sha(after))
        for verb in ("created", "updated", "skipped", "refused"):
            self.assertEqual(res.summary[verb], sum(1 for v, _ in res.lines if v == verb),
                             "summary count for %s differs from its lines" % verb)

    def first_run(self):
        res, before, after = self.run_checked(sample())
        self.assertEqual(res.rc, 0, res.text)
        return res, after


class FirstRun(Base):
    def test_first_run_creates_ten_records_with_expected_keys(self):  # C1, C5
        res, after = self.first_run()
        self.assertEqual(res.summary, {"created": 10, "updated": 0, "skipped": 0, "refused": 0})
        self.assertEqual(sorted(store_oracle.records_by_key(after)), EXPECTED_KEYS)
        for key in EXPECTED_KEYS:
            self.assertEqual(res.verbs_for(key), ["created"])

    def test_each_record_has_its_own_record_id(self):  # C1
        _, after = self.first_run()
        ids = [r["record_id"] for r in store_oracle.records_by_key(after).values()]
        self.assertEqual(len(set(ids)), 10)

    def test_store_keeps_item_content(self):
        _, after = self.first_run()
        recs = store_oracle.records_by_key(after)
        for key, item in zip(EXPECTED_KEYS, sample()["items"]):
            self.assertEqual(recs[key]["title"], item["title"])
            self.assertEqual(recs[key]["body"], item["body"])

    def test_counts_add_up_to_input_items(self):  # C5
        res, _ = self.first_run()
        self.assertEqual(sum(res.summary.values()), 10)
        self.assertEqual(len(res.lines), 10)


class SecondRun(Base):
    def test_second_run_changes_nothing(self):  # C3, C6
        _, after1 = self.first_run()
        stat1 = os.stat(self.store)
        res, before, after2 = self.run_checked(sample())
        stat2 = os.stat(self.store)
        self.assertEqual(res.rc, 0, res.text)
        self.assertEqual(after2, after1, "store bytes differ after the second run")
        self.assertEqual(stat2.st_ino, stat1.st_ino, "store file was replaced")
        self.assertEqual(stat2.st_mtime_ns, stat1.st_mtime_ns, "store file was rewritten")
        self.assertEqual(res.summary, {"created": 0, "updated": 0, "skipped": 10, "refused": 0})
        for key in EXPECTED_KEYS:
            self.assertEqual(res.verbs_for(key), ["skipped"])

    def test_skip_lines_say_why(self):  # C5, outcome "report what was skipped and why"
        self.first_run()
        res = self.run_wf(sample())
        for verb, rest in res.lines:
            self.assertEqual(verb, "skipped")
            self.assertRegex(rest, r"\(.+\)$", "a skip line gives no reason: " + rest)

    def test_five_runs_leave_the_first_result(self):  # C3, C6
        _, after1 = self.first_run()
        for _ in range(4):
            res = self.run_wf(sample())
            self.assertEqual(res.rc, 0)
            self.assertEqual(read_bytes(self.store), after1)

    def test_report_fingerprints_link_the_runs(self):  # C6
        res1, _ = self.first_run()
        res2 = self.run_wf(sample())
        self.assertEqual(res1.store["sha_before"], "absent")
        self.assertEqual(res2.store["sha_before"], res1.store["sha_after"])
        self.assertEqual(res2.store["sha_after"], res1.store["sha_after"])


class KeyDoesNotDependOn(Base):
    def test_filename_or_folder(self):  # C2
        _, after1 = self.first_run()
        path = self.write_input(sample(), name="renamed export (final) v2.json", subdir="another/place")
        res = self.run_wf(path)
        self.assertEqual(res.summary, {"created": 0, "updated": 0, "skipped": 10, "refused": 0})
        self.assertEqual(read_bytes(self.store), after1)

    def test_order_of_items(self):  # C1
        _, after1 = self.first_run()
        doc = sample()
        doc["items"].reverse()
        res = self.run_wf(doc)
        self.assertEqual(res.summary, {"created": 0, "updated": 0, "skipped": 10, "refused": 0})
        self.assertEqual(read_bytes(self.store), after1)

    def test_title(self):  # C2, C4
        _, after1 = self.first_run()
        doc = sample()
        doc["items"][1]["title"] = "Order printer paper and toner"
        res, before, after = self.run_checked(doc)
        d = store_oracle.diff(before, after)
        self.assertEqual(d["created"], [])
        self.assertEqual(d["updated"], ["intake:req-0002"])
        self.assertEqual(len(d["unchanged"]), 9)
        old = store_oracle.records_by_key(before)["intake:req-0002"]
        new = store_oracle.records_by_key(after)["intake:req-0002"]
        self.assertEqual(new["record_id"], old["record_id"])
        self.assertEqual(new["title"], "Order printer paper and toner")

    def test_run_time(self):  # C2
        _, after1 = self.first_run()
        clock = os.path.join(self.tmp, "clock")
        os.makedirs(clock)
        with open(os.path.join(clock, "sitecustomize.py"), "w") as f:
            f.write(FAKE_CLOCK)
        probe = subprocess.run(
            [sys.executable, "-B", "-c", "import time, datetime; print(time.time()); "
             "print(datetime.datetime.now().timestamp()); print(time.strftime('%Y'))"],
            capture_output=True, text=True, env=dict(os.environ, PYTHONPATH=clock))
        import time
        shifted = [float(x) for x in probe.stdout.split()[:2]]
        for value in shifted:
            self.assertGreater(value, time.time() + 399 * 24 * 3600, "the fake clock is not in effect")
        res = self.run_wf(sample(), env={"PYTHONPATH": clock})
        self.assertEqual(res.rc, 0, res.text)
        self.assertEqual(res.summary, {"created": 0, "updated": 0, "skipped": 10, "refused": 0})
        self.assertEqual(read_bytes(self.store), after1)

    def test_spelling_of_the_id(self):  # C1: case and surrounding spaces
        _, after1 = self.first_run()
        doc = sample()
        doc["items"][6]["source_id"] = "  req-0007 "
        doc["source"] = " Intake "
        res = self.run_wf(doc)
        self.assertEqual(res.summary, {"created": 0, "updated": 0, "skipped": 10, "refused": 0})
        self.assertEqual(read_bytes(self.store), after1)


class ChangedItem(Base):
    def changed_doc(self):
        with open(os.path.join(SAMPLE_DIR, "items-changed.json"), encoding="utf-8") as f:
            return json.load(f)

    def test_sample_changed_file_differs_in_exactly_one_item(self):
        a, b = sample(), self.changed_doc()
        self.assertEqual(a["source"], b["source"])
        self.assertEqual(len(a["items"]), 10)
        self.assertEqual(len(b["items"]), 10)
        differing = [i for i in range(10) if a["items"][i] != b["items"][i]]
        self.assertEqual(differing, [3])
        self.assertEqual(a["items"][3]["source_id"], b["items"][3]["source_id"])

    def test_changed_body_updates_in_place(self):  # C4, C5
        self.first_run()
        res, before, after = self.run_checked(self.changed_doc())
        self.assertEqual(res.rc, 0, res.text)
        self.assertEqual(res.summary, {"created": 0, "updated": 1, "skipped": 9, "refused": 0})
        d = store_oracle.diff(before, after)
        self.assertEqual(d["updated"], ["intake:req-0004"])
        self.assertEqual(len(d["unchanged"]), 9)
        self.assertEqual(len(store_oracle.records_by_key(after)), 10)
        old = store_oracle.records_by_key(before)["intake:req-0004"]
        new = store_oracle.records_by_key(after)["intake:req-0004"]
        self.assertEqual(new["record_id"], old["record_id"])
        self.assertEqual(new["body"], self.changed_doc()["items"][3]["body"])
        self.assertEqual(new["title"], old["title"])
        self.assertEqual(res.verbs_for("intake:req-0004"), ["updated"])

    def test_update_line_names_changed_fields(self):  # C5
        self.first_run()
        res = self.run_wf(self.changed_doc())
        rest = [r for v, r in res.lines if v == "updated"][0]
        self.assertIn("body", rest)
        self.assertNotIn("title", rest)

    def test_rerun_of_changed_input_changes_nothing(self):  # C3 after an update
        self.first_run()
        self.run_wf(self.changed_doc())
        after_update = read_bytes(self.store)
        res, _, after = self.run_checked(self.changed_doc())
        self.assertEqual(res.summary, {"created": 0, "updated": 0, "skipped": 10, "refused": 0})
        self.assertEqual(after, after_update)

    def test_mixed_run_counts_match_store(self):  # C5
        self.first_run()
        doc = sample()
        doc["items"] = doc["items"][:5]
        doc["items"][0]["title"] = "Replace hallway light fitting and switch"
        doc["items"][4]["body"] = "Twelve people now."
        doc["items"].append({"source_id": "REQ-0011", "title": "New one", "body": "b11"})
        doc["items"].append({"source_id": "REQ-0012", "title": "New two", "body": "b12"})
        res, before, after = self.run_checked(doc)
        self.assertEqual(res.summary, {"created": 2, "updated": 2, "skipped": 3, "refused": 0})
        d = store_oracle.diff(before, after)
        self.assertEqual(d["created"], ["intake:req-0011", "intake:req-0012"])
        self.assertEqual(d["updated"], ["intake:req-0001", "intake:req-0005"])
        self.assertEqual(len(d["unchanged"]), 8)
        self.assertEqual(res.store["untouched"], 5)

    def test_records_missing_from_input_are_left_alone(self):
        self.first_run()
        doc = sample()
        doc["items"] = doc["items"][:2]
        res, before, after = self.run_checked(doc)
        self.assertEqual(after, before)


class BadKeys(Base):
    def test_two_different_items_with_one_key_are_both_refused(self):
        doc = sample()
        doc["items"].append({"source_id": "REQ-0003", "title": "Other job", "body": "other body"})
        res, before, after = self.run_checked(doc)
        self.assertEqual(res.rc, 2, res.text)
        self.assertEqual(res.summary, {"created": 9, "updated": 0, "skipped": 0, "refused": 2})
        self.assertNotIn("intake:req-0003", store_oracle.records_by_key(after))
        self.assertEqual(res.verbs_for("intake:req-0003"), ["refused", "refused"])
        self.assertEqual(len(store_oracle.records_by_key(after)), 9)

    def test_collision_on_existing_record_leaves_it_untouched(self):
        _, after1 = self.first_run()
        doc = sample()
        doc["items"][2]["body"] = "version A"
        doc["items"].append({"source_id": "REQ-0003", "title": "Other job", "body": "version B"})
        res, before, after = self.run_checked(doc)
        self.assertEqual(res.rc, 2)
        self.assertEqual(after, after1)
        self.assertEqual(res.summary, {"created": 0, "updated": 0, "skipped": 9, "refused": 2})

    def test_near_duplicate_spelling_counts_as_the_same_key(self):
        doc = sample()
        doc["items"].append({"source_id": " req-0003 ", "title": "Other job", "body": "other body"})
        res, _, after = self.run_checked(doc)
        self.assertEqual(res.rc, 2)
        self.assertEqual(res.summary["refused"], 2)
        self.assertEqual(len(store_oracle.records_by_key(after)), 9)

    def test_refusal_lines_give_positions(self):
        doc = sample()
        doc["items"].append({"source_id": "REQ-0003", "title": "Other job", "body": "other body"})
        res = self.run_wf(doc)
        refused = [r for v, r in res.lines if v == "refused"]
        self.assertTrue(any("position 3" in r for r in refused), refused)
        self.assertTrue(any("position 11" in r for r in refused), refused)

    def test_identical_repeat_is_created_once(self):
        doc = sample()
        doc["items"].append(copy.deepcopy(doc["items"][4]))
        res, _, after = self.run_checked(doc)
        self.assertEqual(res.rc, 0, res.text)
        self.assertEqual(res.summary, {"created": 10, "updated": 0, "skipped": 1, "refused": 0})
        self.assertEqual(sorted(store_oracle.records_by_key(after)), EXPECTED_KEYS)

    def test_item_without_usable_id_is_refused_and_no_key_is_invented(self):
        for label, bad in [("absent", None), ("empty", ""), ("spaces", "   "),
                           ("null", "NULL-VALUE"), ("number", 7), ("list", ["REQ-1"])]:
            with self.subTest(label):
                store = os.path.join(self.tmp, "store-%s.json" % label)
                doc = sample()
                extra = {"title": "Water the plants", "body": "no id"}
                if label == "null":
                    extra["source_id"] = None
                elif bad is not None:
                    extra["source_id"] = bad
                doc["items"].insert(5, extra)
                before = read_bytes(store)
                res = self.run_wf(doc, store=store)
                after = read_bytes(store)
                self.assert_report_matches_store(res, before, after)
                self.assertEqual(res.rc, 2, res.text)
                self.assertEqual(res.summary, {"created": 10, "updated": 0, "skipped": 0, "refused": 1})
                self.assertEqual(sorted(store_oracle.records_by_key(after)), EXPECTED_KEYS)
                self.assertTrue(any(v == "refused" and "position 6" in r for v, r in res.lines), res.text)

    def test_id_with_line_break_or_colon_is_refused_and_not_echoed(self):
        for bad in ["REQ-1\ncreated intake:req-9999 -> SIM-9999", "a:b", "REQ 0001", "../x"]:
            with self.subTest(bad):
                store = os.path.join(self.tmp, "store-%d.json" % abs(hash(bad)))
                doc = sample()
                doc["items"].append({"source_id": bad, "title": "t", "body": "b"})
                res = self.run_wf(doc, store=store)
                self.assertEqual(res.rc, 2, res.text)
                self.assertEqual(res.summary, {"created": 10, "updated": 0, "skipped": 0, "refused": 1})
                self.assertEqual(len(res.lines), 11)
                self.assertNotIn("req-9999", res.text)
                self.assertEqual(sorted(store_oracle.records_by_key(read_bytes(store))), EXPECTED_KEYS)

    def test_item_with_non_text_content_is_refused(self):
        doc = sample()
        doc["items"].append({"source_id": "REQ-0011", "title": 5, "body": "b"})
        doc["items"].append("just a string")
        res, _, after = self.run_checked(doc)
        self.assertEqual(res.rc, 2)
        self.assertEqual(res.summary, {"created": 10, "updated": 0, "skipped": 0, "refused": 2})

    def test_source_name_that_could_blur_keys_stops_the_run(self):
        for bad in ["in:take", "", "two words", None]:
            with self.subTest(bad):
                doc = sample()
                doc["source"] = bad
                res = self.run_wf(doc)
                self.assertEqual(res.rc, 1, res.text)
                self.assertIsNone(read_bytes(self.store))

    def test_sample_collision_file(self):
        with open(os.path.join(SAMPLE_DIR, "items-collision.json"), encoding="utf-8") as f:
            doc = json.load(f)
        res, _, after = self.run_checked(doc)
        self.assertEqual(res.rc, 2)
        self.assertEqual(res.summary, {"created": 9, "updated": 0, "skipped": 0, "refused": 3})
        self.assertNotIn("intake:req-0003", store_oracle.records_by_key(after))


class Privacy(Base):
    def private_strings(self, docs):
        out = set()
        for doc in docs:
            for item in doc["items"]:
                if isinstance(item, dict):
                    for field in ("title", "body"):
                        if isinstance(item.get(field), str):
                            out.add(item[field])
                            out.update(w for w in item[field].split() if w.startswith("MARKER-"))
        return out

    def test_no_title_or_body_text_in_output(self):
        with open(os.path.join(SAMPLE_DIR, "items-changed.json"), encoding="utf-8") as f:
            changed = json.load(f)
        with open(os.path.join(SAMPLE_DIR, "items-collision.json"), encoding="utf-8") as f:
            collision = json.load(f)
        retitled = sample()
        retitled["items"][0]["title"] = "A brand new private title"
        private = self.private_strings([sample(), changed, collision, retitled])
        self.assertGreater(len(private), 30)
        outputs = []
        for doc in (sample(), sample(), changed, retitled, collision):
            outputs.append(self.run_wf(doc).text)
        crash = self.run_wf(sample(), env={"RERUN_SIM_CRASH": "after-write:2"},
                            store=os.path.join(self.tmp, "s2.json"))
        outputs.append(crash.text)
        for text in outputs:
            for secret in private:
                self.assertNotIn(secret, text)


class Interrupted(Base):
    def clean_store(self):
        clean = os.path.join(self.tmp, "clean.json")
        res = self.run_wf(sample(), store=clean)
        self.assertEqual(res.rc, 0)
        return read_bytes(clean)

    def test_killed_after_seven_then_rerun_completes(self):
        clean = self.clean_store()
        res = self.run_wf(sample(), env={"RERUN_SIM_CRASH": "after-write:7"})
        self.assertEqual(res.rc, 137, res.text)
        self.assertIsNone(res.summary, "a killed run must not print a summary")
        partial = read_bytes(self.store)
        self.assertEqual(sorted(store_oracle.records_by_key(partial)), EXPECTED_KEYS[:7])
        res2, before, after = self.run_checked(sample())
        self.assertEqual(res2.rc, 0, res2.text)
        self.assertEqual(res2.summary, {"created": 3, "updated": 0, "skipped": 7, "refused": 0})
        self.assertEqual(after, clean, "interrupted then rerun differs from one clean run")

    def test_killed_in_the_middle_of_a_write_then_rerun_completes(self):
        clean = self.clean_store()
        res = self.run_wf(sample(), env={"RERUN_SIM_CRASH": "mid-write:8"})
        self.assertEqual(res.rc, 137, res.text)
        partial = read_bytes(self.store)
        self.assertEqual(sorted(store_oracle.records_by_key(partial)), EXPECTED_KEYS[:7])
        res2, before, after = self.run_checked(sample())
        self.assertEqual(res2.rc, 0, res2.text)
        self.assertEqual(res2.summary, {"created": 3, "updated": 0, "skipped": 7, "refused": 0})
        self.assertEqual(after, clean)
        leftovers = [n for n in os.listdir(self.tmp) if n.startswith("store.json") and
                     n not in ("store.json", "store.json.lock")]
        self.assertEqual(leftovers, [], "half-written file left behind after the rerun")

    def test_half_written_file_is_cleared_even_when_the_rerun_writes_nothing(self):
        _, after1 = self.first_run()
        doc = sample()
        doc["items"][1]["body"] = "changed one"
        res = self.run_wf(doc, env={"RERUN_SIM_CRASH": "mid-write:1"})
        self.assertEqual(res.rc, 137)
        self.assertEqual(read_bytes(self.store), after1, "the kill came before the swap, so the store is the old one")
        res2 = self.run_wf(sample())
        self.assertEqual(res2.summary, {"created": 0, "updated": 0, "skipped": 10, "refused": 0})
        self.assertEqual(read_bytes(self.store), after1)
        leftovers = [n for n in os.listdir(self.tmp) if n.startswith("store.json") and
                     n not in ("store.json", "store.json.lock")]
        self.assertEqual(leftovers, [])

    def test_killed_during_first_write_leaves_no_store(self):
        res = self.run_wf(sample(), env={"RERUN_SIM_CRASH": "mid-write:1"})
        self.assertEqual(res.rc, 137)
        self.assertIsNone(read_bytes(self.store))
        res2 = self.run_wf(sample())
        self.assertEqual(res2.summary, {"created": 10, "updated": 0, "skipped": 0, "refused": 0})

    def test_killed_during_an_update_then_rerun(self):
        self.first_run()
        doc = sample()
        doc["items"][1]["body"] = "changed one"
        doc["items"][8]["body"] = "changed two"
        res = self.run_wf(doc, env={"RERUN_SIM_CRASH": "after-write:1"})
        self.assertEqual(res.rc, 137)
        res2, before, after = self.run_checked(doc)
        self.assertEqual(res2.summary, {"created": 0, "updated": 1, "skipped": 9, "refused": 0})
        recs = store_oracle.records_by_key(after)
        self.assertEqual(recs["intake:req-0002"]["body"], "changed one")
        self.assertEqual(recs["intake:req-0009"]["body"], "changed two")
        self.assertEqual(len(recs), 10)


class RefuseTheRun(Base):
    def test_damaged_store_is_never_overwritten(self):
        for label, content in [
            ("not json", "{ this is not json"),
            ("wrong shape", json.dumps({"records": "nope"})),
            ("empty file", ""),
            ("duplicate keys", json.dumps({"next_record_number": 3, "records": [
                {"key": "intake:req-0001", "record_id": "SIM-0001", "title": "a", "body": "b", "revision": 1},
                {"key": "intake:req-0001", "record_id": "SIM-0002", "title": "a", "body": "b", "revision": 1}]})),
            ("record without key", json.dumps({"next_record_number": 2, "records": [{"record_id": "SIM-0001"}]})),
            ("record with a number for a title", json.dumps({"next_record_number": 2, "records": [
                {"key": "intake:req-0001", "record_id": "SIM-0001", "title": 5, "body": "b", "revision": 1}]})),
        ]:
            with self.subTest(label):
                with open(self.store, "w") as f:
                    f.write(content)
                before = read_bytes(self.store)
                res = self.run_wf(sample())
                self.assertEqual(res.rc, 1, res.text)
                self.assertEqual(read_bytes(self.store), before)
                self.assertEqual([v for v, _ in res.lines if v in ("created", "updated")], [])
                self.assertIn("run refused", res.err)
                self.assertNotIn("Traceback", res.text, "the workflow crashed where it should have refused")

    def test_unreadable_input_writes_nothing(self):
        for label, content in [("not json", "nope"), ("a list", "[]"), ("no items", '{"source": "intake"}'),
                               ("items not a list", '{"source": "intake", "items": {}}')]:
            with self.subTest(label):
                path = self.write_input(content)
                res = self.run_wf(path)
                self.assertEqual(res.rc, 1, res.text)
                self.assertIsNone(read_bytes(self.store))

    def test_missing_input_file(self):
        proc = subprocess.run([sys.executable, "-B", SCRIPT, "--input", os.path.join(self.tmp, "nope.json"),
                               "--store", self.store], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 1)
        self.assertIsNone(read_bytes(self.store))

    def test_second_run_at_the_same_time_is_refused(self):
        self.first_run()
        before = read_bytes(self.store)
        with open(self.store + ".lock", "a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            doc = sample()
            doc["items"][0]["body"] = "changed while locked"
            res = self.run_wf(doc)
            self.assertEqual(res.rc, 1, res.text)
            self.assertEqual(read_bytes(self.store), before)
        res2 = self.run_wf(sample())
        self.assertEqual(res2.rc, 0, "lock was not released: " + res2.text)


if __name__ == "__main__":
    unittest.main()
