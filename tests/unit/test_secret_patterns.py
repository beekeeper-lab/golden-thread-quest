"""The secret scanner must find real secrets and stay quiet about documentation.

Every credential-shaped literal is a module constant on its own line carrying
`# secret-scan: allow`, which is how `tools/secret_scan.py` lets its own fixtures live in
the repository. Keeping them on single lines matters: the pragma is per line, and a
formatter that wraps a long literal would otherwise move the value off its own pragma.

The pragma is honoured by the repository scanner only. `scan_text` knows nothing about it,
so the detectors under test here are the real ones.
"""

from __future__ import annotations

import base64
import time

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


# Round 15 E1: `redact_text`'s own output must never be a fresh finding. The unquoted
# value class used to stop at a closing `]`, so `TOKEN=[REDACTED]` redacted to a value
# missing its own bracket, which `_is_placeholder` did not recognize as the marker it is —
# a participant who redacted with this application's own placeholder was refused for a
# secret that was never there.
@pytest.mark.parametrize(
    ("pattern_id", "text"), DETECTED, ids=[f"{i:02d}-{p}" for i, (p, _) in enumerate(DETECTED)]
)
def test_redaction_is_a_fixed_point_of_the_scan(pattern_id: str, text: str) -> None:
    redacted, changed = redact_text(text)
    assert changed, f"expected {pattern_id} to redact {text!r}"
    assert scan_text(redacted) == [], f"redacting {text!r} left something the scan still flags"


def test_this_applications_own_redaction_marker_is_never_a_finding() -> None:
    assert scan_text(f"JIRA_API_TOKEN={REDACTION_PLACEHOLDER}") == []
    assert scan_text(f"password: {REDACTION_PLACEHOLDER}") == []
    assert scan_text(f"?key={REDACTION_PLACEHOLDER}&token={REDACTION_PLACEHOLDER}") == []


def test_a_gh_cli_masked_token_is_not_a_finding() -> None:
    """`gh auth status` prints exactly this shape: a real prefix, then all mask characters."""
    assert scan_text("  - Token: gho_************************************") == []
    assert scan_text("Token: xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx") == []


# Round 15 E2: Jira Cloud's documented script authentication is HTTP Basic with
# `email:api_token`; a `curl -v` transcript — the exact command-record proof the Jira,
# Trello and GitHub quests ask for — shows the header verbatim, and base64 hid the
# `ATATT3…` prefix from every other pattern.
JIRA_BASIC_CREDENTIAL = (
    b"gregg@example.com:ATATT3xFfGF0T4n2pqrANotherLongJiraToken"  # secret-scan: allow
)


def test_a_basic_auth_header_in_a_curl_v_transcript_is_detected() -> None:
    credential = base64.b64encode(JIRA_BASIC_CREDENTIAL).decode()
    transcript = (
        "* Connected to example.atlassian.net (203.0.113.9) port 443\n"
        f"> Authorization: Basic {credential}\n"  # secret-scan: allow
        "> User-Agent: curl/8.4.0\n"
        "< HTTP/1.1 200 OK\n"
    )
    (match,) = scan_text(transcript)
    assert match.pattern_id == "basic-auth-header"


def test_a_proxy_authorization_basic_header_is_detected() -> None:
    credential = base64.b64encode(b"user:hunter2hunter2longenough").decode()  # secret-scan: allow
    (match,) = scan_text(f"Proxy-Authorization: Basic {credential}")  # secret-scan: allow
    assert match.pattern_id == "basic-auth-header"


def test_an_authorization_token_scheme_header_is_detected() -> None:
    """GitHub's and Django REST Framework's APIs both accept this scheme."""
    (match,) = scan_text(f"Authorization: token {GITHUB}")  # secret-scan: allow
    assert match.pattern_id == "github-token"
    forty_hex = "0123456789abcdef0123456789abcdef01234567"  # secret-scan: allow
    (match,) = scan_text(f"Authorization: token {forty_hex}")  # secret-scan: allow
    assert match.pattern_id == "basic-auth-header"


# Round 15 E5: `basic-auth-url` and `jwt` used unbounded quantifiers ahead of a literal that
# a pathological input never supplies, which is quadratic — every starting offset rescans
# the rest of the text. A 120 KB adversarial file took 36s; 2 MB would take hours, all under
# the store, generated and service locks `redact_text`/`scan_text` run inside of.
@pytest.mark.parametrize("unit", ["a.", "a-", "eyJ"])
def test_scan_text_stays_fast_on_a_two_megabyte_adversarial_file(unit: str) -> None:
    text = unit * (2_000_000 // len(unit))
    started = time.monotonic()
    scan_text(text)
    elapsed = time.monotonic() - started
    assert elapsed < 5, f"{unit!r} * ~2MB took {elapsed:.2f}s, expected well under 5s"


# Round 15 E12: the OpenPGP armor marker is "...PRIVATE KEY BLOCK-----", not
# "...PRIVATE KEY-----" like an RSA or OpenSSH block.
def test_a_pgp_private_key_block_is_detected() -> None:
    pgp_marker = "-----BEGIN PGP PRIVATE KEY BLOCK-----"  # secret-scan: allow
    (match,) = scan_text(pgp_marker)
    assert match.pattern_id == "private-key-block"


# Round 15 E12: a bare paren or brace anywhere in a value used to mark it a placeholder
# outright, which dropped real passwords that happen to contain one.
PASSWORD_WITH_PAREN = "Tr0ub4dor(3)x"  # secret-scan: allow
PASSWORD_WITH_BRACE = "s3cr{t}Passw0rd"  # secret-scan: allow


@pytest.mark.parametrize(
    "text",
    [
        f'password: "{PASSWORD_WITH_PAREN}"',
        f'password = "{PASSWORD_WITH_BRACE}"',
    ],
)
def test_a_password_containing_a_paren_or_brace_is_still_detected(text: str) -> None:
    matches = scan_text(text)
    assert matches, f"expected {text!r} to be detected"
    assert matches[0].pattern_id == "secret-assignment"


@pytest.mark.parametrize(
    "text",
    [
        'secret = "{{ secret_value }}"',
        "note = (redacted)",
        "note = (see vault)",
    ],
)
def test_real_template_and_parenthetical_placeholders_stay_ignored(text: str) -> None:
    assert scan_text(text) == []


def test_a_source_code_call_expression_is_still_not_a_finding() -> None:
    """The unquoted pattern has no closing delimiter, so it captures straight into a real
    call expression — this module's own source among the files `tools/secret_scan.py`
    reads — whenever a keyword-named variable is assigned one."""
    assert scan_text('token = payload.get("token")') == []
    assert scan_text("token=secrets.token_urlsafe(32),") == []
    assert scan_text('api_key = load_api_key(config["provider"], project_root)') == []


# Round 15 E12: Jira's own pagination fields are named `nextPageToken`/`pageToken`; the
# keyword `token` has no left boundary of its own and used to match their tail, so the
# opaque continuation cursor the Jira quest asks participants to page through and document
# was flagged as a credential.
@pytest.mark.parametrize(
    "text",
    [
        '{"issues": [], "nextPageToken": "CAEaAggDIgQIARAB", "isLast": false}',
        '{"pageToken": "CAEaAggDIgQIARAB"}',
    ],
)
def test_jira_pagination_token_fields_are_not_false_positives(text: str) -> None:
    assert scan_text(text) == []


# Round 15 T1: every fixed-prefix pattern is compiled case-sensitively (`SECURITY-AND-
# PRIVACY.md` states this as a deliberate property), but nothing defended it — every
# `DETECTED` fixture above happens to already be written in the pattern's real case.
@pytest.mark.parametrize(
    ("pattern_id", "real_case", "wrong_case"),
    [
        ("aws-access-key-id", AWS, AWS.lower()),
        ("github-fine-grained-token", GITHUB_FINE, GITHUB_FINE.upper()),
        ("slack-app-token", SLACK_APP, SLACK_APP.upper()),
        ("google-oauth-token", GOOGLE_OAUTH, GOOGLE_OAUTH.upper()),
        ("trello-token", TRELLO, TRELLO.lower()),
    ],
)
def test_distinctive_prefixes_match_only_their_real_case(
    pattern_id: str, real_case: str, wrong_case: str
) -> None:
    (match,) = scan_text(real_case)
    assert match.pattern_id == pattern_id
    assert not any(m.pattern_id == pattern_id for m in scan_text(wrong_case)), (
        f"{pattern_id} matched a case it should have refused: {wrong_case!r}"
    )


# Round 15 T2: `url-query-credential`'s `token=` alternative had no fixture of its own —
# only `?key=` was ever exercised, so a regression that silently dropped `|token` would let
# a real credential in a query string pass the scan clean.
def test_url_query_credential_detects_the_token_parameter() -> None:
    (match,) = scan_text(f"GET /1/members/me/boards?token={QUERY_CREDENTIAL}")
    assert match.pattern_id == "url-query-credential"
