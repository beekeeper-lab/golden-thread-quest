"""Tests for the Jira project list. They use scripts/fake_jira.py and no network.

Run from the attempt folder:  python3 -m unittest discover -s tests -v
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(os.path.dirname(HERE), "scripts")
sys.path.insert(0, SCRIPTS)
import fake_jira  # noqa: E402
import projects  # noqa: E402

# Made-up stand-ins for a site address, an email address and an API token, used to check that none
# of the three reaches the output. They are built here, apart from the variable names, on purpose.
MARKS = ("site-marker-771.invalid", "email-marker-772@example.invalid", "MARKER-773-STAND-IN")
VARIABLES = ("JIRA_BASE_URL", "JIRA_EMAIL", "JIRA_API_TOKEN")
STAND_INS = dict(zip(VARIABLES, ("https://" + MARKS[0] + "/", MARKS[1], MARKS[2])))


class Base(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.out = self._tmp.name

    def tearDown(self):
        self._tmp.cleanup()

    def sync(self, fake, now="2026-11-19T09:00:00Z", page_size=3, get=None):
        """One run. Returns (exit code, what it printed)."""
        projects.LINES.clear()
        try:
            code = projects.run(get or fake.get, self.out, "fake", now=now, page_size=page_size)
        except projects.Stop as stop:
            projects.say("STOPPED: %s." % stop)
            code = 1
        return code, "\n".join(projects.LINES)

    def state(self):
        with open(os.path.join(self.out, "projects.json"), encoding="utf-8") as f:
            return json.load(f)

    def listing(self):
        with open(os.path.join(self.out, "projects.md"), encoding="utf-8") as f:
            return f.read()

    def files(self):
        return sorted(os.listdir(os.path.join(self.out, "projects")))


class EveryProjectAcrossPages(Base):
    """Criteria 1 and 6."""

    def held(self, count, page_size, **fake_options):
        fake = fake_jira.FakeJira(count=count, **fake_options)
        code, text = self.sync(fake, page_size=page_size)
        return code, text, fake

    def test_projects_past_the_first_page_are_retrieved_and_the_page_count_is_shown(self):
        code, text, fake = self.held(7, 3)
        self.assertEqual(code, 0)
        self.assertEqual(len(self.state()["projects"]), 7)
        self.assertIn("7 project(s) received over 3 page(s). Jira's own count: 7.", text)
        self.assertIn("page 3: asked for 3 from position 6, received 1", text)

    def test_one_more_than_a_page_is_not_lost(self):
        for count, size, pages in ((4, 3, 2), (51, 50, 2), (101, 50, 3)):
            with tempfile.TemporaryDirectory() as out:
                self.out = out
                code, text, _ = self.held(count, size, page_cap=100)
                self.assertEqual((code, len(self.state()["projects"])), (0, count), count)
                self.assertIn("%d project(s) received over %d page(s)" % (count, pages), text)

    def test_exactly_a_full_page_and_exact_multiples_are_read_whole(self):
        for count, size, pages in ((3, 3, 1), (6, 3, 2), (50, 50, 1), (100, 50, 2)):
            with tempfile.TemporaryDirectory() as out:
                self.out = out
                code, text, _ = self.held(count, size, page_cap=100)
                self.assertEqual((code, len(self.state()["projects"])), (0, count), count)
                self.assertIn("over %d page(s)" % pages, text)

    def test_no_projects_at_all_is_an_empty_list_and_not_an_error(self):
        code, text, _ = self.held(0, 3)
        self.assertEqual((code, self.state()["projects"]), (0, {}))
        self.assertIn("0 project(s) received over 1 page(s)", text)

    def test_when_jira_gives_fewer_to_a_page_than_asked_none_is_skipped(self):
        code, text, fake = self.held(7, 50, page_cap=2)
        self.assertEqual((code, len(self.state()["projects"])), (0, 7))
        self.assertIn("over 4 page(s)", text)
        self.assertEqual([p.get("startAt") for _, p in fake.requests], [0, 2, 4, 6])

    def test_a_first_page_that_wrongly_claims_to_be_the_last_stops_the_run(self):
        fake = fake_jira.FakeJira(count=7)
        fake.quirk = "says_last_early"
        code, text = self.sync(fake)
        self.assertEqual(code, 1)
        self.assertIn("Jira said there are 7 projects and 3 were received", text)
        self.assertEqual(os.listdir(self.out), [])

    def test_pages_that_do_not_move_forward_stop_the_run(self):
        fake = fake_jira.FakeJira(count=7)
        fake.quirk = "ignores_start"
        code, text = self.sync(fake)
        self.assertEqual(code, 1)
        self.assertIn("stopped moving forward", text)
        self.assertEqual(os.listdir(self.out), [])

    def test_pages_with_no_last_marker_are_read_to_jiras_count(self):
        fake = fake_jira.FakeJira(count=7)
        fake.quirk = "no_is_last"
        code, _ = self.sync(fake)
        self.assertEqual((code, len(self.state()["projects"])), (0, 7))

    def test_pages_with_no_count_are_read_to_the_last_page(self):
        fake = fake_jira.FakeJira(count=7)
        fake.quirk = "no_total"
        code, text = self.sync(fake)
        self.assertEqual((code, len(self.state()["projects"])), (0, 7))
        self.assertIn("Jira's own count: not given.", text)


class ThreeFieldsAndFilesById(Base):
    """Criteria 2 and 3."""

    def test_each_record_stores_the_id_the_key_and_the_name_as_separate_fields(self):
        self.sync(fake_jira.FakeJira())
        record = self.state()["projects"]["10003"]
        self.assertEqual((record["id"], record["key"], record["name"]), ("10003", "DPAT", "Data platform"))
        with open(os.path.join(self.out, "projects", "10003.md"), encoding="utf-8") as f:
            text = f.read()
        for line in ("| Project id | `10003` |", "| Key | `DPAT` |", "| Name | Data platform |"):
            self.assertIn(line, text)

    def test_files_are_named_by_the_id_and_by_nothing_else(self):
        fake = fake_jira.FakeJira()
        self.sync(fake)
        self.assertEqual(self.files(), ["%d.md" % n for n in range(10001, 10008)])
        for project in fake.projects:
            for name in self.files():
                self.assertNotIn(project["key"].lower(), name.lower())

    def test_every_link_in_the_list_points_to_a_file_named_by_id(self):
        import re
        self.sync(fake_jira.FakeJira())
        targets = re.findall(r"\]\(([^)]+)\)", self.listing())
        self.assertTrue(targets)
        for target in targets:
            self.assertRegex(target, r"^projects/\d+\.md$")
            self.assertTrue(os.path.exists(os.path.join(self.out, target)))

    def test_a_project_id_that_could_not_name_a_file_stops_the_run_before_anything_is_written(self):
        fake = fake_jira.FakeJira()
        fake.projects[2]["id"] = "../../escape"
        code, text = self.sync(fake)
        self.assertEqual(code, 1)
        self.assertIn("cannot name a file", text)
        self.assertEqual(os.listdir(self.out), [])


class Renames(Base):
    """Criterion 4."""

    def two_runs(self, change):
        fake = fake_jira.FakeJira()
        self.sync(fake)
        change(fake)
        return fake, self.sync(fake, now="2026-11-20T09:00:00Z")

    def test_a_changed_key_is_matched_to_the_existing_record_and_file(self):
        fake, (code, text) = self.two_runs(lambda f: f.rename("10003", key="DATA"))
        state = self.state()["projects"]
        self.assertEqual(len(state), 7)
        self.assertEqual(len(self.files()), 7)
        self.assertEqual((state["10003"]["key"], state["10003"]["first_seen"]), ("DATA", "2026-11-19T09:00:00Z"))
        self.assertIn("RENAMED: project id 10003, key was 'DPAT' and is now 'DATA'. Same id, same record, same file.", text)
        self.assertEqual(state["10003"]["history"], [{"noticed": "2026-11-20T09:00:00Z", "field": "key",
                                                    "was": "DPAT", "became": "DATA"}])

    def test_a_changed_name_and_a_change_of_both_are_matched_too(self):
        def change(f):
            f.rename("10005", name="Mobile apps")
            f.rename("10002", key="PORTAL", name="Partner portal")
        _, (code, text) = self.two_runs(change)
        state = self.state()["projects"]
        self.assertEqual(len(state), 7)
        self.assertEqual(state["10005"]["name"], "Mobile apps")
        self.assertEqual((state["10002"]["key"], state["10002"]["name"]), ("PORTAL", "Partner portal"))
        self.assertEqual(len(state["10002"]["history"]), 2)
        self.assertIn("renamed: 2", text)

    def test_two_projects_that_swap_keys_stay_the_right_way_round(self):
        def change(f):
            f.rename("10001", key="TMP")
            f.rename("10007", key="BIL")
            f.rename("10001", key="SEA")
        self.two_runs(change)
        state = self.state()["projects"]
        self.assertEqual((state["10001"]["key"], state["10001"]["name"]), ("SEA", "Billing"))
        self.assertEqual((state["10007"]["key"], state["10007"]["name"]), ("BIL", "Search"))
        self.assertEqual(len(state), 7)

    def test_a_new_project_given_another_projects_old_key_is_a_separate_record(self):
        def change(f):
            f.rename("10003", key="DATA")
            f.add("DPAT", "Something else entirely")
        self.two_runs(change)
        state = self.state()["projects"]
        self.assertEqual(len(state), 8)
        self.assertEqual(state["10003"]["name"], "Data platform")
        self.assertEqual(state["10008"]["key"], "DPAT")
        self.assertEqual(state["10008"]["history"], [])

    def test_two_projects_with_the_same_name_stay_two(self):
        self.two_runs(lambda f: f.add("BIL2", "Billing"))
        names = [p["name"] for p in self.state()["projects"].values()]
        self.assertEqual(names.count("Billing"), 2)

    def test_an_unchanged_second_run_changes_nothing(self):
        _, (code, text) = self.two_runs(lambda f: None)
        self.assertIn("new: 0, unchanged: 7, renamed: 0, not returned: 0", text)
        self.assertTrue(all(p["history"] == [] for p in self.state()["projects"].values()))


class Vanished(Base):
    """Criterion 5."""

    def test_a_project_that_disappears_is_flagged_and_kept_with_its_last_labels(self):
        fake = fake_jira.FakeJira()
        self.sync(fake)
        fake.remove("10006")
        code, text = self.sync(fake, now="2026-11-20T09:00:00Z")
        record = self.state()["projects"]["10006"]
        self.assertEqual((record["state"], record["key"], record["name"]), ("not_returned", "ONB", "Onboarding"))
        self.assertEqual((record["last_returned"], record["not_returned_since"]),
                         ("2026-11-19T09:00:00Z", "2026-11-20T09:00:00Z"))
        self.assertIn("NOT RETURNED: project id 10006 (key 'ONB', name 'Onboarding'). Kept and flagged, not deleted.", text)
        self.assertIn("10006.md", self.files())
        self.assertIn("## Not returned by Jira (1)", self.listing())
        self.assertIn("`ONB` **(not returned)**", self.listing())
        with open(os.path.join(self.out, "projects", "10006.md"), encoding="utf-8") as f:
            self.assertIn("NOT RETURNED by Jira since 2026-11-20T09:00:00Z", f.read())

    def test_it_is_reported_once_and_is_cleared_if_the_project_comes_back(self):
        fake = fake_jira.FakeJira()
        self.sync(fake)
        gone = dict(fake.by_key("ONB"))
        fake.remove("10006")
        self.sync(fake, now="2026-11-20T09:00:00Z")
        _, text = self.sync(fake, now="2026-11-21T09:00:00Z")
        self.assertIn("not returned: 0", text)
        self.assertEqual(self.state()["projects"]["10006"]["state"], "not_returned")
        fake.projects.append(gone)
        _, text = self.sync(fake, now="2026-11-22T09:00:00Z")
        self.assertIn("returned again: project id 10006", text)
        self.assertEqual(self.state()["projects"]["10006"]["state"], "present")
        self.assertIn("## Not returned by Jira (0)", self.listing())

    def test_the_list_does_not_claim_to_know_why_a_project_is_missing(self):
        fake = fake_jira.FakeJira()
        self.sync(fake)
        fake.remove("10006")
        self.sync(fake, now="2026-11-20T09:00:00Z")
        self.assertIn("Jira does not say whether a project was deleted", self.listing())


class FindableByAnyLabel(Base):
    """Criterion 7."""

    def section(self, title):
        text = self.listing()
        start = text.index("## " + title)
        end = text.find("\n## ", start + 1)
        return text[start:end if end != -1 else len(text)]

    def test_every_project_is_in_all_three_lookups_with_its_other_two_labels(self):
        fake = fake_jira.FakeJira()
        self.sync(fake)
        for project in fake.projects:
            for title in ("By name", "By key", "By project id"):
                row = [line for line in self.section(title).split("\n") if "projects/%s.md" % project["id"] in line]
                self.assertEqual(len(row), 1, (title, project["key"]))
                for label in (project["id"], project["key"], project["name"]):
                    self.assertIn(label, row[0])

    def test_each_lookup_is_sorted_by_its_own_label(self):
        self.sync(fake_jira.FakeJira())
        names = [line.split("|")[1].strip() for line in self.section("By name").split("\n") if "projects/" in line]
        keys = [line.split("|")[1].strip() for line in self.section("By key").split("\n") if "projects/" in line]
        self.assertEqual(names, sorted(names, key=str.lower))
        self.assertEqual(keys, sorted(keys, key=str.lower))

    def test_a_former_key_and_a_former_name_still_lead_to_the_project(self):
        fake = fake_jira.FakeJira()
        self.sync(fake)
        fake.rename("10003", key="DATA", name="Data lake")
        self.sync(fake, now="2026-11-20T09:00:00Z")
        old_key = [line for line in self.section("By key").split("\n") if "`DPAT`" in line]
        old_name = [line for line in self.section("By name").split("\n") if "Data platform" in line]
        for rows in (old_key, old_name):
            self.assertEqual(len(rows), 1)
            self.assertIn("former", rows[0])
            self.assertIn("projects/10003.md", rows[0])


class Safety(Base):
    def test_the_skill_can_only_send_get_requests(self):
        with open(projects.__file__, encoding="utf-8") as f:
            source = f.read()
        self.assertEqual(source.count("urllib.request.Request("), 1)
        self.assertIn('urllib.request.Request(url, method="GET")', source)
        for word in ('"POST"', '"PUT"', '"DELETE"', '"PATCH"', "data="):
            self.assertNotIn(word, source)

    def test_rejected_credentials_stop_the_run_and_nothing_is_written(self):
        fake = fake_jira.FakeJira()
        fake.credentials_ok = False
        code, text = self.sync(fake)
        self.assertEqual(code, 1)
        self.assertIn("rejected the credentials", text)
        self.assertEqual(os.listdir(self.out), [])

    def test_a_failed_second_run_leaves_the_first_runs_files_as_they_were(self):
        fake = fake_jira.FakeJira()
        self.sync(fake)
        before = self.listing()
        fake.rename("10003", key="DATA")
        fake.fail("/rest/api/3/project/search", 500)
        code, _ = self.sync(fake, now="2026-11-20T09:00:00Z")
        self.assertEqual(code, 1)
        self.assertEqual(self.listing(), before)
        self.assertEqual(self.state()["last_successful_sync"], "2026-11-19T09:00:00Z")

    def test_a_name_cannot_add_structure_to_the_list(self):
        fake = fake_jira.FakeJira()
        fake.rename("10001", name="Bill | ing\n## Injected [x](http://example.invalid) `code`")
        self.sync(fake)
        text = self.listing()
        self.assertNotIn("\n## Injected", text)
        self.assertNotIn("](http://example.invalid)", text)
        row = [line for line in text.split("\n") if "Bill" in line and "projects/10001.md" in line][0]
        self.assertEqual(len(row.replace("\\|", "").strip("|").split("|")), 4)

    def test_a_folder_from_a_fake_run_is_refused_by_a_live_run(self):
        self.sync(fake_jira.FakeJira())
        with self.assertRaises(projects.Stop) as stopped:
            projects.load_state(self.out, "live")
        self.assertIn("Use another --out", str(stopped.exception))

    def test_a_live_run_prints_no_credential_and_no_site_address_even_when_it_fails(self):
        env = dict(os.environ, **STAND_INS)
        done = subprocess.run([sys.executable, os.path.join(SCRIPTS, "projects.py"), "--source", "live", "--out", self.out],
                              capture_output=True, text=True, env=env)
        self.assertEqual(done.returncode, 1)
        self.assertIn("could not reach Jira", done.stdout)
        for marker in ("marker-771", "marker-772", "MARKER-773"):
            self.assertNotIn(marker, done.stdout + done.stderr)
        self.assertEqual(os.listdir(self.out), [])

    def test_the_things_searched_for_are_the_token_the_email_the_encoded_pair_and_the_sites_address(self):
        import base64
        old = {k: os.environ.get(k) for k in VARIABLES}
        os.environ.update(STAND_INS)
        try:
            _, searched = projects.make_live_get()
        finally:
            for k, v in old.items():
                os.environ.pop(k, None) if v is None else os.environ.__setitem__(k, v)
        encoded = base64.b64encode(("%s:%s" % (MARKS[1], MARKS[2])).encode()).decode()
        self.assertEqual(sorted(searched), sorted([MARKS[2], MARKS[1], encoded, MARKS[0]]))

    def test_output_holding_any_one_of_them_is_withheld(self):
        searched = [MARKS[2], MARKS[1], "ENCODED-774-STAND-IN", MARKS[0]]
        for item in searched:
            text, clean = projects.screened("a project named after %s appeared" % item, searched)
            self.assertFalse(clean, item)
            self.assertNotIn(item, text)
        text, clean = projects.screened("nothing to hide here", searched)
        self.assertEqual((text, clean), ("nothing to hide here", True))

    def test_a_live_run_with_a_missing_variable_stops_and_names_it(self):
        env = {k: v for k, v in os.environ.items() if not k.startswith("JIRA_")}
        done = subprocess.run([sys.executable, os.path.join(SCRIPTS, "projects.py"), "--source", "live", "--out", self.out],
                              capture_output=True, text=True, env=env)
        self.assertEqual(done.returncode, 1)
        self.assertIn("STOPPED: the environment variable JIRA_BASE_URL is not set.", done.stdout)


if __name__ == "__main__":
    unittest.main()
