"""The secret scanner must find real secrets and stay quiet about documentation.

Every credential-shaped literal is a module constant on its own line carrying
`# secret-scan: allow`, which is how `tools/secret_scan.py` lets its own fixtures live in
the repository. Keeping them on single lines matters: the pragma is per line, and a
formatter that wraps a long literal would otherwise move the value off its own pragma.

The pragma is honoured by the repository scanner only. `scan_text` knows nothing about it,
so the detectors under test here are the real ones.
"""

from __future__ import annotations

import pytest
from quest_app.secret_patterns import REDACTION_PLACEHOLDER, redact_text, scan_text

GITHUB = "ghp_abcdefghijklmnopqrstuvwxyz0123456789"  # secret-scan: allow
AWS = "AKIAIOSFODNN7EXAMPLX"  # secret-scan: allow
PEM = "-----BEGIN RSA PRIVATE KEY-----"  # secret-scan: allow
SLACK = "xoxb-1234567890-abcdefghijkl"  # secret-scan: allow
GOOGLE = "AIzaSyA1234567890abcdefghijklmnopqrstuv"  # secret-scan: allow
ANTHROPIC = "sk-ant-api03-aaaaaaaaaaaaaaaaaaaaaaaa"  # secret-scan: allow
GITLAB = "glpat-abcdefghij1234567890"  # secret-scan: allow
STRIPE = "sk_live_51H8xQzAbCdEfGhIjKlMnOpQr"  # secret-scan: allow
NPM = "npm_abcdefghijklmnopqrstuvwxyz0123456789"  # secret-scan: allow
JWT = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjMifQ.dBjftJeZ4CVPmB92K27uhbUJU1p"  # secret-scan: allow
URL_PASSWORD = "hunter2hunter2"  # secret-scan: allow
BEARER = "abc123def456ghi789jkl"  # secret-scan: allow
CLIENT_SECRET = "s3cr3t-value-long-enough"  # secret-scan: allow
API_KEY = "AbCdEfGhIjKlMnOpQrSt"  # secret-scan: allow
ENV_TOKEN = "s0mereallyLongSecretValue123"  # secret-scan: allow
YAML_PASSWORD = "hunter2hunter2"  # secret-scan: allow

DETECTED: list[tuple[str, str]] = [
    ("github-token", f"token = {GITHUB}"),
    ("aws-access-key-id", AWS),
    ("private-key-block", PEM),
    ("slack-token", SLACK),
    ("google-api-key", GOOGLE),
    ("anthropic-key", ANTHROPIC),
    ("gitlab-token", GITLAB),
    ("stripe-key", f"stripe_key = {STRIPE}"),
    ("npm-token", f"npm_token={NPM}"),
    ("jwt", JWT),
    ("basic-auth-url", f"https://svc:{URL_PASSWORD}@example.com/api"),
    ("bearer-header", f"Authorization: Bearer {BEARER}"),
    ("secret-assignment", f'client_secret: "{CLIENT_SECRET}"'),
    ("secret-assignment", f'{{"apiKey": "{API_KEY}"}}'),
    ("secret-assignment-unquoted", f"JIRA_API_TOKEN={ENV_TOKEN}"),
    ("secret-assignment-unquoted", f"password: {YAML_PASSWORD}"),
]

# Documentation, templates and masks. A scanner that stops on these is a scanner people
# route around, which is worse than one that misses an exotic format.
IGNORED = [
    "GTQ_SERVICE_HOST=127.0.0.1",
    "GTQ_SERVICE_PORT=8765",
    "# JIRA_BASE_URL=https://example.atlassian.net",
    'password = "changeme"',
    'api_key: "<your-api-key>"',
    'token = "${GITHUB_TOKEN}"',
    'secret = "{{ secret_value }}"',
    'secret = "xxxxxxxxxxxx"',
    f'token = "{REDACTION_PLACEHOLDER}"',
]


@pytest.mark.parametrize(
    ("pattern_id", "text"), DETECTED, ids=[f"{i:02d}-{p}" for i, (p, _) in enumerate(DETECTED)]
)
def test_detects_secret(pattern_id: str, text: str) -> None:
    matches = scan_text(text)
    assert matches, f"expected {pattern_id} to be detected"
    assert matches[0].pattern_id == pattern_id


@pytest.mark.parametrize("text", IGNORED)
def test_ignores_documentation(text: str) -> None:
    assert scan_text(text) == []


def test_excerpt_reveals_no_usable_fragment() -> None:
    """A finding is printed into CI logs, so it must not carry the value it found."""
    (match,) = scan_text(f"token = {GITHUB}")
    assert match.excerpt == f"{GITHUB[:3]}… ({len(GITHUB)} chars)"
    assert GITHUB[3:] not in match.excerpt


def test_short_value_excerpt_shows_no_characters_at_all() -> None:
    (match,) = scan_text("password: shortish")  # secret-scan: allow
    assert match.excerpt == "8 chars"


def test_reports_line_and_column() -> None:
    (match,) = scan_text(f"first line\nsecond line\ntoken = {GITHUB}\n")
    assert match.line == 3
    assert match.column == 9


def test_overlapping_patterns_report_the_most_specific_name() -> None:
    (match,) = scan_text(f'api_key = "{GITHUB}"')
    assert match.pattern_id == "github-token"


@pytest.mark.parametrize(
    ("pattern_id", "text"),
    [
        ("github-token", f"nnn{GITHUB}"),
        ("aws-access-key-id", f"x{AWS}"),
        ("gitlab-token", f"id{GITLAB}"),
        ("slack-token", f"key{SLACK}"),
        ("google-api-key", f"k{GOOGLE}"),
        ("anthropic-key", f"v{ANTHROPIC}"),
        ("npm-token", f"a{NPM}"),
        ("stripe-key", f"z{STRIPE}"),
        ("jwt", f"q{JWT}"),
    ],
)
def test_a_token_directly_preceded_by_a_letter_is_still_detected(
    pattern_id: str, text: str
) -> None:
    """Round 13 E11: the leading `\\b` these patterns used to require meant a token with no
    separator before it — `nnnghp_…`, `xAKIA…` — was invisible to the scan and to
    redaction. The literal prefixes are specific enough that dropping the leading boundary
    does not need one."""
    matches = scan_text(text)
    assert matches, f"expected {pattern_id} to be detected in {text!r}"
    assert matches[0].pattern_id == pattern_id


def test_redaction_still_removes_a_token_with_no_separator_before_it() -> None:
    redacted, changed = redact_text(f"nnn{GITHUB} end")
    assert changed
    assert GITHUB not in redacted
    assert redacted == f"nnn{REDACTION_PLACEHOLDER} end"


@pytest.mark.parametrize(
    "text",
    [
        "This week's task-force meeting covers the desktop rollout schedule.",
        "The risk-taking assessment for this quarter is still in draft form.",
    ],
)
def test_ordinary_prose_with_a_hyphenated_word_is_not_a_false_positive(text: str) -> None:
    """Dropping the leading boundary must not turn common hyphenated English into a finding."""
    assert scan_text(text) == []


def test_anthropic_key_is_not_reported_as_an_openai_key() -> None:
    """`sk-` is a prefix of `sk-ant-`; ordering in PATTERNS is what keeps the name right."""
    (match,) = scan_text(ANTHROPIC)
    assert match.pattern_id == "anthropic-key"


def test_redaction_removes_the_value_and_keeps_context() -> None:
    redacted, changed = redact_text(f"token = {GITHUB} end")
    assert changed
    assert GITHUB not in redacted
    assert redacted == f"token = {REDACTION_PLACEHOLDER} end"


def test_redaction_of_clean_text_changes_nothing() -> None:
    text = "GTQ_SERVICE_PORT=8765\n"
    assert redact_text(text) == (text, False)


def test_redaction_handles_several_secrets_on_one_line() -> None:
    redacted, changed = redact_text(f"a={GITHUB} b={AWS}")
    assert changed
    assert redacted.count(REDACTION_PLACEHOLDER) == 2
    assert GITHUB not in redacted
    assert AWS not in redacted
