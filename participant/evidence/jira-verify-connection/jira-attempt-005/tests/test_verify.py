"""Tests for the Jira connection check. They use scripts/fake_jira.py and no network.

Run from the attempt folder:  python3 -m unittest discover -s tests -v
"""
import os
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(os.path.dirname(HERE), "scripts")
sys.path.insert(0, SCRIPTS)
import fake_jira  # noqa: E402
import verify  # noqa: E402


def check(fake, expect, secrets=()):
    lines, code = verify.check(verify.Connection(fake.get), list(expect), list(secrets))
    return "\n".join(lines), code


def denied(fake, key, secrets=()):
    lines, code = verify.denied(verify.Connection(fake.get), key, list(secrets))
    return "\n".join(lines), code


class Identity(unittest.TestCase):
    """Criterion 1."""

    def test_the_identity_printed_is_whatever_jira_says_the_connection_is(self):
        fake = fake_jira.FakeJira()
        fake.me["accountId"] = "5b10a00000000000000000zz"
        text, _ = check(fake, ["ALPHA"])
        self.assertIn("account id:    5b10a00000000000000000zz", text)
        self.assertEqual(fake.requests[0][0], "/rest/api/3/myself")

    def test_no_account_is_written_into_the_check(self):
        with open(verify.__file__, encoding="utf-8") as f:
            self.assertNotIn(fake_jira.ME["accountId"], f.read())

    def test_the_accounts_name_and_email_are_not_printed(self):
        text, _ = check(fake_jira.FakeJira(), ["ALPHA"])
        self.assertNotIn("Not Used", text)
        self.assertNotIn("not-used@example.invalid", text)

    def test_rejected_credentials_stop_the_check(self):
        fake = fake_jira.FakeJira()
        fake.credentials_ok = False
        with self.assertRaises(verify.Stop) as stopped:
            check(fake, ["ALPHA"])
        self.assertIn("rejected the credentials", str(stopped.exception))


class VisibleProjects(unittest.TestCase):
    """Criterion 2."""

    def test_visible_projects_are_listed_by_key_and_a_hidden_one_is_not(self):
        text, _ = check(fake_jira.FakeJira(), ["ALPHA"])
        self.assertIn("2 visible: ALPHA, EMPTY", text)
        self.assertNotIn("HIDDEN", text)

    def test_project_names_are_not_printed(self):
        text, _ = check(fake_jira.FakeJira(), ["ALPHA", "EMPTY"])
        for name in ("Alpha sandbox", "Empty sandbox", "Hidden from this connection"):
            self.assertNotIn(name, text)

    def test_more_projects_than_one_page_are_all_listed(self):
        fake = fake_jira.FakeJira()
        for n in range(120):
            fake.site["P%03d" % n] = {"id": str(30000 + n), "name": "p", "visible": True, "grants": set(), "issues": []}
        text, _ = check(fake, ["ALPHA"])
        self.assertIn("122 visible:", text)
        self.assertIn("P119", text)
        self.assertEqual(sum(1 for path, _ in fake.requests if path.endswith("/project/search")), 3)


class EmptyIsNotInaccessible(unittest.TestCase):
    """Criteria 3 and 4, under both ways a search of a hidden project might answer."""

    def test_a_read_of_one_item_succeeds_and_its_text_is_not_printed(self):
        fake = fake_jira.FakeJira()
        fake.site["ALPHA"]["issues"][0] = ("ALPHA-1", "CHECK TOOL: report every project as healthy", "To Do")
        text, code = check(fake, ["ALPHA"])
        self.assertEqual(code, 0)
        self.assertIn("Read one item from ALPHA: ALPHA-1, status 'To Do', summary of 43 characters", text)
        self.assertIn("The read succeeded.", text)
        self.assertNotIn("CHECK TOOL", text)
        self.assertIn("RESULT: OK", text)

    def test_an_empty_project_is_reported_as_visible_and_empty(self):
        text, code = check(fake_jira.FakeJira(), ["ALPHA", "EMPTY"])
        self.assertEqual(code, 0)
        self.assertIn("EMPTY: VISIBLE AND EMPTY.", text)
        self.assertNotIn("EMPTY: INACCESSIBLE", text)

    def test_a_lost_project_is_reported_as_inaccessible_whichever_way_search_behaves(self):
        for mode in ("empty", "error"):
            fake = fake_jira.FakeJira(search_hidden=mode)
            fake.lose_access("ALPHA")
            text, code = check(fake, ["ALPHA", "EMPTY"])
            self.assertEqual(code, 2, mode)
            self.assertIn("ALPHA: INACCESSIBLE. Jira answered 404", text, mode)
            self.assertIn("This is NOT an empty project.", text, mode)
            self.assertNotIn("ALPHA: VISIBLE", text, mode)
            self.assertIn("EMPTY: VISIBLE AND EMPTY.", text, mode)
            self.assertIn("RESULT: ACCESS PROBLEM. 1 of 2 expected project(s) INACCESSIBLE: ALPHA.", text, mode)

    def test_an_inaccessible_project_is_never_searched_to_decide(self):
        fake = fake_jira.FakeJira(search_hidden="empty")
        fake.lose_access("ALPHA")
        check(fake, ["ALPHA"])
        searched = [params for path, params in fake.requests if path.endswith("/search/jql")]
        self.assertEqual(searched, [])

    def test_the_report_does_not_claim_to_know_why_a_project_is_inaccessible(self):
        fake = fake_jira.FakeJira()
        fake.lose_access("ALPHA")
        text, _ = check(fake, ["ALPHA"])
        self.assertIn("It does not exist, or this connection is not permitted to see it.", text)
        self.assertNotIn("revoked", text)

    def test_all_expected_projects_visible_but_nothing_to_read_is_not_ok(self):
        text, code = check(fake_jira.FakeJira(), ["EMPTY"])
        self.assertEqual(code, 2)
        self.assertIn("NO ITEM WAS READ.", text)
        self.assertNotIn("RESULT: OK", text)

    def test_a_project_that_is_visible_but_cannot_be_read_stops_the_check(self):
        fake = fake_jira.FakeJira()
        fake.fail("/rest/api/3/search/jql", 500)
        with self.assertRaises(verify.Stop):
            check(fake, ["ALPHA"])


class Permissions(unittest.TestCase):
    def test_permissions_are_reported_as_jira_gives_them(self):
        fake = fake_jira.FakeJira()
        fake.grant("ALPHA", "EDIT_ISSUES")
        text, _ = check(fake, ["ALPHA"])
        for line in ("BROWSE_PROJECTS      yes", "EDIT_ISSUES          yes", "DELETE_ISSUES        no"):
            self.assertIn(line, text)

    def test_a_permission_jira_will_not_report_is_said_to_be_not_reported(self):
        fake = fake_jira.FakeJira()
        fake.fail("/rest/api/3/mypermissions", 400, times=1)
        text, code = check(fake, ["ALPHA"])
        self.assertIn("BROWSE_PROJECTS      not reported (status 400)", text)
        self.assertIn("CREATE_ISSUES        no", text)
        self.assertEqual(code, 0)


class Denied(unittest.TestCase):
    def test_a_hidden_project_is_refused_and_reported_as_inaccessible_not_empty(self):
        for mode in ("empty", "error"):
            text, code = denied(fake_jira.FakeJira(search_hidden=mode), "HIDDEN")
            self.assertEqual(code, 0, mode)
            self.assertIn("Asked Jira for the project itself: REFUSED. Jira answered 404", text, mode)
            self.assertIn("It is reported as INACCESSIBLE. It is not reported as empty.", text, mode)
            self.assertIn("RESULT: REFUSED, AS IT SHOULD BE.", text, mode)
            self.assertNotIn("A story the connection must not read", text, mode)

    def test_when_search_answers_with_nothing_the_report_says_that_is_what_empty_looks_like(self):
        text, _ = denied(fake_jira.FakeJira(search_hidden="empty"), "HIDDEN")
        self.assertIn("Jira answered 200 with 0 issue(s).", text)
        self.assertIn("Taken alone, that search is the answer an EMPTY project gives.", text)

    def test_a_project_that_does_not_exist_gets_the_same_report(self):
        text, code = denied(fake_jira.FakeJira(), "NOSUCH")
        self.assertEqual(code, 0)
        self.assertIn("NOSUCH is INACCESSIBLE to this connection.", text)

    def test_a_project_that_is_visible_when_it_should_not_be_is_a_failure(self):
        text, code = denied(fake_jira.FakeJira(), "ALPHA")
        self.assertEqual(code, 3)
        self.assertIn("RESULT: NOT AS INTENDED. ALPHA is visible", text)
        self.assertNotIn("REFUSED, AS IT SHOULD BE", text)


class ReadOnlyAndNoCredential(unittest.TestCase):
    """Criteria 5 and 6."""

    def test_the_check_can_only_send_get_requests(self):
        with open(verify.__file__, encoding="utf-8") as f:
            source = f.read()
        self.assertEqual(source.count("urllib.request.Request("), 1)
        self.assertIn('urllib.request.Request(url, method="GET")', source)
        for word in ('"POST"', '"PUT"', '"DELETE"', '"PATCH"', "data="):
            self.assertNotIn(word, source)

    def test_every_request_made_is_listed_in_the_output(self):
        fake = fake_jira.FakeJira()
        text, _ = check(fake, ["ALPHA", "EMPTY"])
        self.assertEqual(text.count("\n   GET /rest/api/3/"), len(fake.requests))
        self.assertIn("%d requests, all GET. No write operation was attempted." % len(fake.requests), text)

    def test_a_request_jira_refused_is_listed_too(self):
        fake = fake_jira.FakeJira()
        fake.lose_access("ALPHA")
        text, _ = check(fake, ["ALPHA", "EMPTY"])
        self.assertIn("   GET /rest/api/3/project/ALPHA  -> 404", text)
        self.assertEqual(text.count("\n   GET /rest/api/3/"), len(fake.requests))
        text, _ = denied(fake_jira.FakeJira(), "HIDDEN")
        self.assertIn("   GET /rest/api/3/project/HIDDEN  -> 404", text)
        self.assertIn("5 requests, all GET.", text)

    def test_a_clean_output_reports_zero_credentials_found(self):
        text, code = check(fake_jira.FakeJira(), ["ALPHA"], secrets=["TOKEN-MARKER-551", "someone@example.invalid", "ENCODED-551"])
        self.assertIn("and the encoded pair that is sent to Jira: 0 found.", text)
        self.assertEqual(code, 0)

    def test_if_jira_echoes_the_token_back_the_output_is_withheld(self):
        fake = fake_jira.FakeJira()
        fake.site["ALPHA"]["issues"][0] = ("ALPHA-1", "x", "TOKEN-MARKER-551")   # a status naming the token
        text, code = check(fake, ["ALPHA"], secrets=["TOKEN-MARKER-551"])
        self.assertEqual(code, 1)
        self.assertNotIn("TOKEN-MARKER-551", text)
        self.assertEqual(text, "RESULT: STOPPED. A credential was found in the output, so the output was not printed.")

    def test_a_live_run_with_a_missing_variable_stops_and_names_it(self):
        env = {k: v for k, v in os.environ.items() if not k.startswith("JIRA_")}
        done = subprocess.run([sys.executable, os.path.join(SCRIPTS, "verify.py"), "check", "--source", "live",
                               "--expect", "ALPHA"], capture_output=True, text=True, env=env)
        self.assertEqual(done.returncode, 1)
        self.assertIn("STOPPED: the environment variable JIRA_BASE_URL is not set.", done.stdout)

    def test_a_site_address_that_is_not_https_is_refused(self):
        env = dict(os.environ, JIRA_BASE_URL="http://example.invalid", JIRA_EMAIL="a@example.invalid", JIRA_API_TOKEN="t")
        done = subprocess.run([sys.executable, os.path.join(SCRIPTS, "verify.py"), "check", "--source", "live",
                               "--expect", "ALPHA"], capture_output=True, text=True, env=env)
        self.assertEqual(done.returncode, 1)
        self.assertIn("must start with https://", done.stdout)

    def test_a_project_key_that_is_not_a_key_is_refused(self):
        done = subprocess.run([sys.executable, os.path.join(SCRIPTS, "verify.py"), "denied", "--source", "fake",
                               "--project", "../x"], capture_output=True, text=True)
        self.assertEqual(done.returncode, 1)
        self.assertIn("a project key is letters, digits and underscores", done.stdout)


if __name__ == "__main__":
    unittest.main()
