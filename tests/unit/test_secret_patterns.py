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
OPENAI = "sk-abcdefghijklmnopqrstuvwxyz0123456789"  # secret-scan: allow
GITHUB_FINE = "github_pat_" + "AB01" * 20  # secret-scan: allow
TRELLO = "ATTA" + "a1b2c3d4" * 8 + "ABCD1234"  # secret-scan: allow
SLACK_APP = (
    "xapp-1-A0123456789-1234567890123-abcdef0123456789abcdef0123456789"  # secret-scan: allow
)
GOOGLE_OAUTH = "ya29.a0AfH6SMBx3n9QwErTyUiOpAsDfGhJkLzXcVbNm"  # secret-scan: allow
QUERY_CREDENTIAL = "0123456789abcdef0123456789abcdef"  # secret-scan: allow
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
    ("openai-key", f"token = {OPENAI}"),
    ("github-fine-grained-token", f"token = {GITHUB_FINE}"),
    ("trello-token", f"token = {TRELLO}"),
    ("slack-app-token", f"token = {SLACK_APP}"),
    ("google-oauth-token", f"token = {GOOGLE_OAUTH}"),
    ("url-query-credential", f"GET /1/members/me/boards?key={QUERY_CREDENTIAL}"),
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
        ("jwt", f"q{JWT}"),
    ],
)
def test_a_token_directly_preceded_by_a_letter_is_still_detected(
    pattern_id: str, text: str
) -> None:
    """Round 13 E11: the leading `\\b` these patterns used to require meant a token with no
    separator before it — `nnnghp_…`, `xAKIA…` — was invisible to the scan and to
    redaction. These prefixes are distinctive enough (round 14 E1) that they keep no
    leading boundary at all, so the E11 case stays caught."""
    matches = scan_text(text)
    assert matches, f"expected {pattern_id} to be detected in {text!r}"
    assert matches[0].pattern_id == pattern_id


@pytest.mark.parametrize(
    ("pattern_id", "text"),
    [
        ("npm-token", f"a{NPM}"),
        ("stripe-key", f"z{STRIPE}"),
        ("openai-key", f"a{OPENAI}"),
    ],
)
def test_a_short_generic_prefix_glued_to_a_letter_is_no_longer_detected(
    pattern_id: str, text: str
) -> None:
    """Round 14 E1: unlike the distinctive prefixes above, `npm_`, `sk_`/`rk_` and `sk-` are
    short enough to turn up mid-word (`network_test_connectivity` matched `stripe-key`,
    `task-review-…` matched `openai-key`). They now require a lookbehind that a token glued
    to a preceding letter fails, which is the trade this round makes: the round 13 E11 glued
    case is no longer caught for these three, in exchange for the false positives going
    away."""
    assert scan_text(text) == []


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


@pytest.mark.parametrize(
    "text",
    [
        # Round 14 E1: real evidence text the Trello, GitHub and Jira quests ask
        # participants to submit, all of which used to trip a fixed-prefix pattern.
        "https://trello.com/c/Xy12AbCd/48-task-review-onboarding-checklist",
        "Cloned https://github.com/acme/desk-booking-integration-service",
        "git switch -c feature/risk-assessment-dashboard-update",
        "See the ask-the-product-owner-first-guideline in the wiki.",
        'labels: ["whisk-migration-phase-two-2026"]',
        "tests/test_net.py::network_test_connectivity PASSED",
        "test('framework_test_bootstrapping', async () => {",
        "RISK-ASSESSMENT-FRAMEWORK-2026-Q3 approved",
        'class="mask-image-gradient-overlay-large"',
        "sha256:961a703db315b6da63e2a0e8f9cd3bc8db210f269a6451505236a78d84d250b3",
        "commit 3b9b7c2e1f8a9d0c4b5a6e7f8091a2b3c4d5e6f7",
        "id: 0b8f3c1e-6d2a-4f7b-9c3e-1a2b3c4d5e6f",
        "trace: test-results/example-task-login-flow-retry1/trace.zip",
    ],
)
def test_realistic_evidence_text_is_not_a_false_positive(text: str) -> None:
    """`scratchpad/r14-regex-battery.py`'s false-positive cases, kept as a regression suite."""
    assert scan_text(text) == []


@pytest.mark.parametrize(
    ("pattern_id", "prefix", "cs_body"),
    [
        ("openai-key", "sk-", "abcdefghijklmnopqrstuvwx"),
        ("stripe-key", "sk_live_", "abcdefghijklmn"),
        ("npm-token", "npm_", "abcdefghijklmnopqrstuvwx"),
    ],
)
def test_short_generic_prefix_without_a_digit_in_the_body_is_not_detected(
    pattern_id: str, prefix: str, cs_body: str
) -> None:
    """Round 14 E1: a real key of this shape always has a digit in it; a value that is only
    letters is the ordinary-word case these prefixes are prone to, not a credential.

    Written without a `token`/`key`/`secret` keyword nearby, so the generic
    secret-assignment scanner cannot claim the span first and mask what this is testing.
    """
    assert scan_text(f"see {prefix}{cs_body} in the log") == []


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
