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
from quest_app.secret_patterns import PATTERNS, REDACTION_PLACEHOLDER, redact_text, scan_text

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
    credential = base64.b64encode(JIRA_BASIC_CREDENTIAL).decode()  # secret-scan: allow
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


# Round 16 E1/E2: a unit whose repetition stresses each pattern's own worst case — mostly
# just the pattern's fixed prefix, which is where an unbounded lookahead or an unbounded
# quantifier ahead of a literal a pathological input never supplies does its damage.
#
# A list of pairs, not a `{"id": "unit"}` dict literal: several pattern ids end in a real
# keyword this module detects (`...-credential`, `...-secret-key`), and a dict literal's
# `"key": "value"` is exactly the assignment shape those keywords look for — with the
# quoted secret-assignment pattern, this file's own source became a finding. A tuple has no
# `[=:]` directly after the id, so it is not.
_PATTERN_ADVERSARIAL_UNITS: dict[str, str] = dict(  # noqa: C406 - a `{"id": "unit"}` dict literal
    # here is exactly the assignment shape the comment above explains avoiding.
    [
        ("private-key-block", "-----BEGIN OPAQUE "),
        ("aws-access-key-id", "AKIAZ"),
        ("aws-secret-key", "aws_secret_access_key=Z"),
        ("github-token", "ghp_Z"),
        ("github-fine-grained-token", "github_pat_Z"),
        ("gitlab-token", "glpat-Z"),
        ("slack-token", "xoxb-Z"),
        ("slack-app-token", "xapp-Z"),
        ("google-api-key", "AIzaZ"),
        ("google-oauth-token", "ya29.Z"),
        ("anthropic-key", "sk-ant-Z"),
        ("openai-key", "sk-"),
        ("trello-token", "ATTAZ"),
        ("atlassian-token", "ATATT3Z"),
        ("jwt", "eyJZ"),
        ("basic-auth-url", "a://Z"),
        ("stripe-key", "sk_live_"),
        ("npm-token", "npm_"),
        ("url-query-credential", "?key=Z"),
        ("bearer-header", "authorization: bearer Z"),
        ("basic-auth-header", "authorization: basic Z"),
        ("curl-user-credential", "curl -u Z "),
        ("xml-element-credential", "<password>Z"),
        ("yaml-block-scalar-credential", "password: >-\nZ\n"),
        ("secret-assignment", 'password="Z'),
        ("secret-assignment-unquoted", "password=Z"),
    ]
)


@pytest.mark.parametrize("pattern", PATTERNS, ids=[p.id for p in PATTERNS])
def test_every_pattern_scales_near_linearly_on_adversarial_input(pattern) -> None:  # type: ignore[no-untyped-def]
    """Round 16 E1: `openai-key`'s digit lookahead was unbounded and shared its character
    class with its own prefix, so a run of nothing but `sk-` never gave the lookahead a
    character to stop on — every occurrence re-scanned to the end of the string, quadratic
    (80 KB took 6.3s; a 2 MB file never finished under the locks this runs inside of).

    A fixed wall-clock bound on one input size is hardware-dependent (round 16 F3 found
    exactly that for a related pattern): timing at `n` and `4n` and requiring the ratio stay
    well under the `16x` a quadratic algorithm would show is robust to how fast the machine
    happens to be, and is run here for every pattern, not just the one round 16 found.
    """
    unit = _PATTERN_ADVERSARIAL_UNITS[pattern.id]
    small = unit * max(1, 250_000 // len(unit))
    large = small * 4
    started = time.monotonic()
    pattern.regex.findall(small)
    small_elapsed = max(time.monotonic() - started, 1e-6)
    started = time.monotonic()
    pattern.regex.findall(large)
    large_elapsed = time.monotonic() - started
    ratio = large_elapsed / small_elapsed
    assert ratio < 8, (
        f"{pattern.id}: 4x the input took {ratio:.1f}x as long "
        f"({small_elapsed:.3f}s -> {large_elapsed:.3f}s), expected near-linear scaling"
    )


def test_scan_text_stays_fast_with_many_distinct_non_overlapping_matches() -> None:
    """Round 16 E2: `scan_text`'s overlap check used to scan every earlier claim for every
    new match, which is O(matches^2) in the match count — 95k distinct AWS keys in a 2 MB
    file took 497s even though the AWS pattern itself is linear. Timing at `n` and `4n`
    keeps this robust to machine speed, the same way the per-pattern test above is: a
    quadratic bookkeeping cost would show roughly 16x for 4x the matches, not the well-under
    8x this asserts.
    """

    def matches(count: int) -> str:
        return "".join(f"AKIA{i:016d}\n" for i in range(count))

    small = matches(5_000)
    large = matches(20_000)
    started = time.monotonic()
    scan_text(small)
    small_elapsed = max(time.monotonic() - started, 1e-6)
    started = time.monotonic()
    scan_text(large)
    large_elapsed = time.monotonic() - started
    ratio = large_elapsed / small_elapsed
    assert ratio < 8, (
        f"4x the matches took {ratio:.1f}x as long "
        f"({small_elapsed:.3f}s -> {large_elapsed:.3f}s), expected near-linear scaling"
    )


# Round 16 E4: the bracket alternative used to stop at the closing `]`, so a placeholder
# glued to a real value (`[Pr0d]Sup3rS3cretValue`) captured only the bracket — a finding,
# but the wrong span — and redacting it left the real value in clear text, scanning clean.
def test_a_placeholder_glued_to_a_real_value_is_detected() -> None:
    (match,) = scan_text("password=[Pr0d]Sup3rS3cretValue")  # secret-scan: allow
    assert match.pattern_id == "secret-assignment-unquoted"


def test_redacting_a_placeholder_glued_to_a_real_value_covers_the_whole_value() -> None:
    redacted, changed = redact_text("password=[Pr0d]Sup3rS3cretValue")  # secret-scan: allow
    assert changed
    assert "Sup3rS3cretValue" not in redacted
    assert scan_text(redacted) == [], "the redaction itself must not still be a finding"


def test_a_real_value_glued_after_this_applications_own_placeholder_is_detected() -> None:
    (match,) = scan_text(f"password={REDACTION_PLACEHOLDER}realvalue9")  # secret-scan: allow
    assert match.pattern_id == "secret-assignment-unquoted"


# Round 16 E5: `${VAR:-default}`/`${VAR-default}` is a shell or compose *default*, which is
# a real value the moment the variable is unset — not a placeholder, which only a value
# entirely `${VAR}` (optionally `${VAR:?message}`) is.
@pytest.mark.parametrize(
    "text",
    [
        "DB_PASSWORD=${DB_PASSWORD:-Sup3rS3cretValue9}",  # secret-scan: allow
        "POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-Sup3rS3cretValue9}",  # secret-scan: allow
        "DB_PASSWORD=${DB_PASSWORD-Sup3rS3cretValue9}",  # secret-scan: allow
    ],
)
def test_a_shell_or_compose_default_value_is_detected(text: str) -> None:
    matches = scan_text(text)
    assert matches, f"expected {text!r} to be detected"
    assert matches[0].pattern_id == "secret-assignment-unquoted"


@pytest.mark.parametrize(
    "text",
    [
        "DB_PASSWORD=${DB_PASSWORD}",
        "DB_PASSWORD=${DB_PASSWORD:?must be set}",
    ],
)
def test_a_bare_shell_expansion_with_no_default_stays_a_placeholder(text: str) -> None:
    assert scan_text(text) == []


# Round 16 E6: round 15 E12 excused ANY unquoted value containing a paren or brace
# anywhere, so an ordinary `.env` password that happens to contain one was never detected.
@pytest.mark.parametrize(
    "text",
    [
        "DB_PASSWORD=Tr0ub4dor(3)xyz",  # secret-scan: allow
        # The value class stops at an unescaped `}` (so a JSON object's own closing brace
        # is never swallowed into a value); the credential must have 8 characters ahead of
        # the brace to still meet the pattern's own minimum length, same as any other value.
        "API_KEY=k8s-secret{X}9aQ2vLm7",  # secret-scan: allow
    ],
)
def test_an_unquoted_password_containing_a_paren_or_brace_is_detected(text: str) -> None:
    matches = scan_text(text)
    assert matches, f"expected {text!r} to be detected"
    assert matches[0].pattern_id == "secret-assignment-unquoted"


# Round 16 E7: before this, ANY short dotted-segment chain was exempted as an attribute
# path, so a dotted passphrase read exactly like one and was never reported.
@pytest.mark.parametrize(
    "text",
    [
        "password: correct.horse.battery.staple",  # secret-scan: allow
        "password=Welcome.To.Acme",  # secret-scan: allow
    ],
)
def test_a_dotted_passphrase_is_detected(text: str) -> None:
    matches = scan_text(text)
    assert matches, f"expected {text!r} to be detected"
    assert matches[0].pattern_id == "secret-assignment-unquoted"


@pytest.mark.parametrize(
    "text",
    [
        "token = self.config",
        "secret = os.environ",
    ],
)
def test_a_known_code_shape_dotted_attribute_path_stays_exempted(text: str) -> None:
    assert scan_text(text) == []


# Round 16 E11: scan-coverage gaps that are cheap to close without a new false positive on
# this repository's own source or the realistic-evidence corpus above.
def test_an_xml_element_credential_is_detected() -> None:
    (match,) = scan_text("<password>Sup3rS3cretValue9</password>")  # secret-scan: allow
    assert match.pattern_id == "xml-element-credential"


def test_a_yaml_block_scalar_credential_is_detected() -> None:
    (match,) = scan_text("password: >-\n  Sup3rS3cretValue9\n")  # secret-scan: allow
    assert match.pattern_id == "yaml-block-scalar-credential"


def test_a_curl_dash_u_credential_is_detected() -> None:
    transcript = (
        "curl -u me@example.com:abcdEFGH1234abcdEFGH1234 "  # secret-scan: allow
        "https://example.atlassian.net"
    )
    (match,) = scan_text(transcript)
    assert match.pattern_id == "curl-user-credential"


def test_a_docker_uid_gid_flag_is_not_a_curl_user_false_positive() -> None:
    """`docker run -u 1000:1000` takes a colon-separated argument too, but it is not curl
    and it is not a credential."""
    assert scan_text("docker run -u 1000:1000 image") == []


@pytest.mark.parametrize(
    "text",
    [
        "DB_PASS=Sup3rS3cretValue9",  # secret-scan: allow
        "PWD=Sup3rS3cretValue9",  # secret-scan: allow
    ],
)
def test_db_pass_and_pwd_keywords_are_detected(text: str) -> None:
    matches = scan_text(text)
    assert matches, f"expected {text!r} to be detected"
    assert matches[0].pattern_id == "secret-assignment-unquoted"


def test_bare_pass_stays_ordinary_vocabulary_not_a_keyword() -> None:
    """This repository's own test-result vocabulary (`vendor/axe.min.js`'s
    `messages:{pass:"..."}`) and English's "bypass" both use `pass` with no underscore
    before it; only the `DB_PASS`-style compound is a credential field name."""
    assert scan_text('"pass": "Every required check passed."') == []
    assert scan_text("bypass=true") == []


@pytest.mark.parametrize(
    "text",
    [
        'password: "<Sup3rS3cretValue9"',  # secret-scan: allow
        "password=Sup3rS3cretValue9>",  # secret-scan: allow
    ],
)
def test_a_lone_angle_bracket_no_longer_makes_a_value_a_template(text: str) -> None:
    matches = scan_text(text)
    assert matches, f"expected {text!r} to be detected"


def test_a_matched_angle_bracket_pair_is_still_a_template() -> None:
    assert scan_text('api_key: "<your-api-key>"') == []


# Round 16 F3: the JWT header segment's own bound (`{10,512}`) is what keeps a 2 MB
# adversarial `eyJ`-repeated file fast; mutating it back to `{10,4096}` (the shape a code
# comment says once took 5 to 9 seconds in CI) passed the wall-clock adversarial test on
# both machines that mutation-tested it, since it is fast enough on modern hardware to hide
# under any bound generous enough not to flake on a slow one. Pinning the literal bound in
# the compiled pattern's own source, and a header that is exactly one character past it,
# catches the regression independent of how fast the machine is.
def test_the_jwt_header_segment_bound_is_pinned() -> None:
    jwt_pattern = next(p for p in PATTERNS if p.id == "jwt")
    assert "{10,512}" in jwt_pattern.regex.pattern

    payload = "eyJhbGciOiJIUzI1NiJ9"
    signature = "dBjftJeZ4CVPmB92K27uhbUJU1p"

    within_bound = "eyJ" + "a" * 500 + "." + payload + "." + signature
    (match,) = scan_text(within_bound)
    assert match.pattern_id == "jwt"

    past_bound = "eyJ" + "a" * 513 + "." + payload + "." + signature
    assert not any(m.pattern_id == "jwt" for m in scan_text(past_bound))


# Round 17 E1: every assignment pattern required the operator immediately after the keyword,
# so a keyword followed by any identifier suffix — the ordinary way a config names a second
# credential of the same kind — was never matched.
@pytest.mark.parametrize(
    "text",
    [
        "SECRET_KEY=Sup3rS3cretValue9xyz",  # secret-scan: allow
        '"secret_key": "Sup3rS3cretValue9xyz"',  # secret-scan: allow
        '"secretKey": "Sup3rS3cretValue9xyz"',  # secret-scan: allow
        "JWT_SECRET_KEY=Sup3rS3cretValue9xyz",  # secret-scan: allow
        "SECRET_KEY_BASE=Sup3rS3cretValue9xyz",  # secret-scan: allow
        "ENCRYPTION_KEY=Sup3rS3cretValue9xyz",  # secret-scan: allow
        "signing_key: Sup3rS3cretValue9xyz",  # secret-scan: allow
        "DB_PASSWORD_PROD=Sup3rS3cretValue9",  # secret-scan: allow
        "TRELLO_TOKEN_PROD=Sup3rS3cretValue9",  # secret-scan: allow
        "JIRA_API_TOKEN_2=Sup3rS3cretValue9",  # secret-scan: allow
        "DB_PASS_PROD=Sup3rS3cretValue9",  # secret-scan: allow
        '"dbPass": "Sup3rS3cretValue9"',  # secret-scan: allow
        "AccountKey=Sup3rS3cretValue9xyzAbCdEf==",  # secret-scan: allow
    ],
)
def test_a_keyword_with_an_identifier_suffix_is_detected(text: str) -> None:
    matches = scan_text(text)
    assert matches, f"expected {text!r} to be detected"
    assert matches[0].pattern_id in {"secret-assignment", "secret-assignment-unquoted"}
    redacted, _ = redact_text(text)
    assert "Sup3rS3cretValue9" not in redacted


@pytest.mark.parametrize(
    "text",
    [
        # A suffixed name's value never starts on the next line: that is a class body or a
        # docstring, not a value.
        "class SecretMatch:\n    pattern_id: str\n",
        'class SecretPattern:\n    """One named detector.\n',
        # Keyword-named code this repository's own source contains.
        "TOKEN_PLACEHOLDER = REQUEST_TOKEN_PLACEHOLDER",
        '{"total_tokens": total_tokens,',
        'print(f"Total tokens:   {total_tokens:,}")',
        "tokenList:function(){return Sp},uniqueArray",
        # Bare `pass` and camelCase `Pass` after an arbitrary word stay ordinary vocabulary.
        "bypass=truetruetrue",
        "onPass=handlePassEvent",
    ],
)
def test_suffixed_keyword_code_shapes_are_not_false_positives(text: str) -> None:
    assert scan_text(text) == []


def test_a_bare_keyword_value_on_the_next_line_is_still_detected() -> None:
    """A YAML plain scalar may start on the line after its key; only a suffixed name gives
    that up."""
    assert scan_text("password:\n  Sup3rS3cretValue9\n")  # secret-scan: allow


# Round 17 E9: `PWD`/`OLDPWD` are the shell's own working-directory variables, printed by
# every `env`/`printenv` transcript; a path value there is not a password.
@pytest.mark.parametrize(
    "text",
    [
        "PWD=/home/gregg/workspace/quest",
        "OLDPWD=/home/gregg",
        '"PWD": "/home/gregg/workspace/quest"',
        "PWD=~/workspace/quest",
        "SHELL=/bin/bash\nPWD=/home/gregg/quest\nOLDPWD=/home/gregg\n",  # secret-scan: allow
    ],
)
def test_the_shells_working_directory_variables_are_not_findings(text: str) -> None:
    assert scan_text(text) == []


@pytest.mark.parametrize(
    "text",
    [
        "DB_PWD=Sup3rS3cretValue9",  # secret-scan: allow
        "pwd: Sup3rS3cretValue9",  # secret-scan: allow
        "OLDPWD=Sup3rS3cretValue9",  # secret-scan: allow
        "DB_PWD=/Sup3rS3cretValue9",  # secret-scan: allow
    ],
)
def test_a_pwd_holding_something_other_than_a_path_is_still_detected(text: str) -> None:
    assert scan_text(text), f"expected {text!r} to be detected"


# Round 17 E3 (and the curriculum lens's C1, the same defect): a bracket of fewer than three
# characters glued to a real value was never matched, and a `]` after the bracket ended the
# capture, so a real value after it was left out of both the scan and the redaction.
@pytest.mark.parametrize(
    "text",
    [
        "password=[X]Sup3rS3cretValue9",  # secret-scan: allow
        "password=[ab]Sup3rS3cretValue9",  # secret-scan: allow
        "password=[]Sup3rS3cretValue9",  # secret-scan: allow
        "db_password=[Q]Tr0ub4dor3HunterRealSecret9",  # secret-scan: allow
        "password=[REDACTED]]Sup3rS3cretValue9",  # secret-scan: allow
        "password=[abc]]Sup3rS3cretValue9",  # secret-scan: allow
        "password=[Sup3r]S3cret]Value9",  # secret-scan: allow
    ],
)
def test_a_bracket_glued_to_a_real_value_is_detected_and_fully_redacted(text: str) -> None:
    matches = scan_text(text)
    assert matches, f"expected {text!r} to be detected"
    assert matches[0].pattern_id == "secret-assignment-unquoted"
    redacted, changed = redact_text(text)
    assert changed
    assert redacted.endswith(f"={REDACTION_PLACEHOLDER}"), redacted
    assert scan_text(redacted) == [], "the redaction itself must not still be a finding"


def test_a_redaction_followed_by_a_stray_bracket_is_a_fixed_point() -> None:
    redacted, _ = redact_text("password=Sup3rS3cretValue9]")  # secret-scan: allow
    assert redacted == f"password={REDACTION_PLACEHOLDER}]"
    assert scan_text(redacted) == []
    assert redact_text(redacted) == (redacted, False)


# Round 17 E4: a real value glued after a template was excused along with the template —
# unquoted because the value class stopped at the expansion's `}`, quoted because a value
# only had to *start* with `$(` or `{{`.
@pytest.mark.parametrize(
    "text",
    [
        "DB_PASSWORD=${DB_PASSWORD}Sup3rS3cretValue9",  # secret-scan: allow
        "api_key=${API_KEY}Sup3rS3cretValue9",  # secret-scan: allow
        "DB_PASSWORD=${DB_PASSWORD:?unset}Sup3rS3cretValue9",  # secret-scan: allow
        'PASSWORD="$(true)Sup3rS3cretValue9"',  # secret-scan: allow
        'password: "{{ vault_pw }}Sup3rS3cretValue9"',  # secret-scan: allow
        "password: {{vault_pw}}Sup3rS3cretValue9",  # secret-scan: allow
    ],
)
def test_a_real_value_glued_after_a_template_is_detected(text: str) -> None:
    assert scan_text(text), f"expected {text!r} to be detected"
    redacted, _ = redact_text(text)
    assert "Sup3rS3cretValue9" not in redacted
    assert scan_text(redacted) == []


@pytest.mark.parametrize(
    "text",
    [
        "token=$(gh auth token)",
        'token = "$(gh auth token)"',
        "password: {{ vault_pw }}",
        "password: {{vault_pw}}",
    ],
)
def test_a_value_that_is_entirely_a_template_stays_a_placeholder(text: str) -> None:
    assert scan_text(text) == []


# Round 17 E17: a `,`/`;` glued inside an unquoted value cut it short — half the value was
# left in clear text by the redaction, or, with too few characters before the cut, the
# whole value was never matched.
@pytest.mark.parametrize(
    "text",
    [
        "password=Sup3rS3cr;etValue9",  # secret-scan: allow
        "password=ab,Sup3rS3cretValue9",  # secret-scan: allow
        "password=Sup3r,S3cret;Value9 next",  # secret-scan: allow
    ],
)
def test_a_value_glued_across_a_comma_or_semicolon_is_redacted_whole(text: str) -> None:
    assert scan_text(text), f"expected {text!r} to be detected"
    redacted, _ = redact_text(text)
    assert "etValue9" not in redacted and "Value9" not in redacted, redacted
    assert scan_text(redacted) == []


@pytest.mark.parametrize(
    "text",
    [
        "f(token=token,user=user)",
        "{password:e,next:t}",
        '"password":null,"x":1',
        "token=secrets.token_urlsafe(32),",
        "password=ab,cd,efgh=1",
    ],
)
def test_code_after_a_comma_is_not_glued_into_a_value(text: str) -> None:
    assert scan_text(text) == []


def test_a_separator_followed_by_a_space_still_ends_the_value() -> None:
    redacted, _ = redact_text("password=Sup3rS3cretValue9, user=bob")  # secret-scan: allow
    assert redacted == f"password={REDACTION_PLACEHOLDER}, user=bob"


# Round 17 E5: the call/subscript exemption matched only the lowered shape, so a password
# that merely ended like a call, a subscript, a bare closing or a format placeholder was
# excused along with real code.
@pytest.mark.parametrize(
    "text",
    [
        "password=Tr0ub4dor(3)",  # secret-scan: allow
        "password=Summer2024(!)",  # secret-scan: allow
        "DB_PASS=Sup3rS3cr3t)",  # secret-scan: allow
        "password=MyP4ssw0rd(",  # secret-scan: allow
        "password={Sup3rS3cretValue9}",  # secret-scan: allow
        "password=abc[Sup3rS3cretValue9",  # secret-scan: allow
        'password = "{Sup3rS3cretValue9}"',  # secret-scan: allow
    ],
)
def test_a_password_shaped_like_the_end_of_a_call_is_detected(text: str) -> None:
    assert scan_text(text), f"expected {text!r} to be detected"
    redacted, _ = redact_text(text)
    assert "S3cr" not in redacted and "0ub4" not in redacted and "P4ss" not in redacted
    assert "Summer2024" not in redacted


@pytest.mark.parametrize(
    "text",
    [
        "token = parts[-1]",
        'token = os.environ["GITHUB_TOKEN"]',
        "client = OpenAI(api_key=api_key)",
        "token = base64.b64encode(raw)",
    ],
)
def test_real_code_shapes_stay_exempted(text: str) -> None:
    assert scan_text(text) == []


# Round 17 C2: the plain unquoted run stopped at every `}`, so with fewer than eight
# characters before the brace nothing matched at all and the real secret after it was never
# looked at.
def test_a_brace_glued_inside_an_unquoted_value_does_not_hide_it() -> None:
    text = "api_key=k8s{Q}9aQ2vLm7RealSecret"  # secret-scan: allow
    (match,) = scan_text(text)
    assert match.pattern_id == "secret-assignment-unquoted"
    assert redact_text(text)[0] == f"api_key={REDACTION_PLACEHOLDER}"


# Round 17 E6: only the root of a dotted chain was checked, so a passphrase that merely
# started with a code-root name read as an attribute path.
@pytest.mark.parametrize(
    "text",
    [
        "password=context.is.king2024",  # secret-scan: allow
        "password=settings.Sup3r.Secret9",  # secret-scan: allow
        "password=config.a.b.c.d",  # secret-scan: allow
    ],
)
def test_a_passphrase_starting_with_a_code_root_is_detected(text: str) -> None:
    assert scan_text(text), f"expected {text!r} to be detected"


@pytest.mark.parametrize(
    "text",
    ["password = settings.DB_PASSWORD", "token = self.config.github_token", "secret = os.environ"],
)
def test_a_real_attribute_path_from_a_code_root_stays_exempted(text: str) -> None:
    assert scan_text(text) == []
