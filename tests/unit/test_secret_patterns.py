"""The secret scanner must find real secrets and stay quiet about documentation."""

from __future__ import annotations

import pytest
from quest_app.secret_patterns import REDACTION_PLACEHOLDER, redact_text, scan_text

DETECTED = [
    ("github-token", 'token = "ghp_abcdefghijklmnopqrstuvwxyz0123456789"'),
    ("aws-access-key-id", "AKIAIOSFODNN7EXAMPLX"),
    ("private-key-block", "-----BEGIN RSA PRIVATE KEY-----"),
    ("slack-token", "xoxb-1234567890-abcdefghijkl"),
    ("google-api-key", "AIzaSyA1234567890abcdefghijklmnopqrstuv"),
    ("anthropic-key", "sk-ant-api03-aaaaaaaaaaaaaaaaaaaaaaaa"),
    ("gitlab-token", "glpat-abcdefghij1234567890"),
    (
        "jwt",
        "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dBjftJeZ4CVPmB92K27uhbUJU1p1r_wW1gFWFOEjXk",
    ),
    ("basic-auth-url", "https://svc:hunter2hunter2@example.com/api"),
    ("generic-assignment", 'client_secret: "s3cr3t-value-long-enough"'),
]

IGNORED = [
    "GTQ_SERVICE_HOST=127.0.0.1",
    "# JIRA_BASE_URL=https://example.atlassian.net",
    'password = "changeme"',
    'api_key: "<your-api-key>"',
    'token = "${GITHUB_TOKEN}"',
    'secret = "xxxxxxxxxxxx"',
    f'token = "{REDACTION_PLACEHOLDER}"',
]


@pytest.mark.parametrize(("pattern_id", "text"), DETECTED, ids=[p for p, _ in DETECTED])
def test_detects_secret(pattern_id: str, text: str) -> None:
    matches = scan_text(text)
    assert matches, f"expected {pattern_id} to be detected in {text!r}"
    assert matches[0].pattern_id == pattern_id


@pytest.mark.parametrize("text", IGNORED)
def test_ignores_documentation(text: str) -> None:
    assert scan_text(text) == []


def test_excerpt_never_reveals_the_secret() -> None:
    secret = "ghp_abcdefghijklmnopqrstuvwxyz0123456789"
    (match,) = scan_text(f"token = {secret}")
    assert secret not in match.excerpt
    assert match.excerpt.startswith("ghp_")


def test_reports_line_and_column() -> None:
    text = "first line\nsecond line\ntoken = ghp_abcdefghijklmnopqrstuvwxyz0123456789\n"
    (match,) = scan_text(text)
    assert match.line == 3
    assert match.column == 9


def test_overlapping_patterns_report_the_most_specific_name() -> None:
    # A GitHub token inside a secret-like assignment matches two patterns.
    (match,) = scan_text('api_key = "ghp_abcdefghijklmnopqrstuvwxyz0123456789"')
    assert match.pattern_id == "github-token"


def test_redaction_removes_the_value_and_keeps_context() -> None:
    redacted, changed = redact_text("token = ghp_abcdefghijklmnopqrstuvwxyz0123456789 end")
    assert changed
    assert "ghp_abcdefghijklmnopqrstuvwxyz0123456789" not in redacted
    assert redacted == f"token = {REDACTION_PLACEHOLDER} end"


def test_redaction_of_clean_text_changes_nothing() -> None:
    text = "GTQ_SERVICE_PORT=8765\n"
    assert redact_text(text) == (text, False)
