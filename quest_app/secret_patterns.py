"""Secret detection patterns, shared by repository hygiene and evidence scanning.

This module is deliberately pure: it holds the patterns and a matcher, and knows nothing
about files, evidence packages or the repository. `tools/secret_scan.py` uses it to keep
secrets out of the repository; the evidence workspace uses it to keep secrets out of a
submission, and the validator runner uses it to redact captured output.

Detection here is a safety net, not a guarantee. A pattern list cannot recognize every
secret, so the surrounding policy — credentials come from the environment or an
authenticated CLI, never from content — is what actually protects the participant.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final

REDACTION_PLACEHOLDER: Final = "[REDACTED]"


@dataclass(frozen=True, slots=True)
class SecretPattern:
    """One named detector.

    `regex` must place the sensitive span in group 1 when only part of the match is the
    secret, so redaction can keep the surrounding context readable.
    """

    id: str
    description: str
    regex: re.Pattern[str]


@dataclass(frozen=True, slots=True)
class SecretMatch:
    pattern_id: str
    description: str
    line: int
    column: int
    excerpt: str


def _c(pattern: str, *, case_sensitive: bool = False) -> re.Pattern[str]:
    return re.compile(pattern, 0 if case_sensitive else re.IGNORECASE)


# Field names whose value is a credential. Deliberately broader than the obvious three:
# evidence packages and raw API responses are where this module does most of its work, and
# there the field is as likely to be `apiKey` in JSON or `token` in YAML as `password`.
_KEYWORDS = "|".join(
    (
        r"passw(?:or)?d",
        r"passphrase",
        r"secret",
        r"api[_-]?key",
        r"apikey",
        r"access[_-]?token",
        r"auth[_-]?token",
        r"client[_-]?secret",
        r"refresh[_-]?token",
        r"private[_-]?key",
        r"credential",
        r"token",
        r"bearer",
    )
)


# Ordered most specific first: a GitHub token should be reported as a GitHub token, not as
# a generic high-entropy assignment.
#
# Round 13 E11 dropped the leading `\b` from every fixed-prefix pattern so that a token
# glued directly to a preceding letter or digit (`nnnghp_…`, `xAKIA…`) would still match —
# `\b` requires a transition between a word and a non-word character, and every one of these
# prefixes starts with a letter, so nothing preceded it without one. Round 14 E1 found the
# other half of that trade was never checked: with no leading boundary at all and every
# pattern case-insensitive, `sk-[A-Za-z0-9_-]{20,}` matched the tail of "ta-SK-review-…" in
# an ordinary hyphenated slug, and `(?:sk|rk)_(?:live|test)_…` matched "network_TEST_…" in a
# log line — both real strings from evidence a participant is asked to submit (Trello card
# URLs, test names, branch names).
#
# The two constraints do not need the same answer for every prefix:
#
# * A **distinctive** prefix (`AKIA`/`ASIA`/…, `gh[pousr]_`, `glpat-`, `xox[abposr]-`,
#   `xapp-`, `AIza`, `sk-ant-`, `ATATT3`, `ATTA`, `github_pat_`, `ya29.`, `eyJ`) is long and
#   specific enough that it does not turn up inside ordinary words or identifiers, so it
#   keeps no leading boundary — the round 13 E11 cases stay caught.
# * A **short generic** prefix (`sk-`, `sk_`/`rk_live|test_`, `npm_`) is exactly the kind of
#   fragment that does turn up mid-word, so it requires `(?<![A-Za-z0-9])` before it *and*
#   at least one digit in the body — a real key of this shape has one; "review-onboarding-
#   checklist" and "test_connectivity" do not. A token of this kind glued to a preceding
#   letter is no longer detected; that trade is what this round makes.
#
# Every fixed-prefix pattern is also compiled case-sensitively now: a real prefix has a
# fixed case (`AKIA`, `sk-`, `ghp_`), so matching either case only bought false positives
# from ordinary uppercase text (`RISK-ASSESSMENT-…`). Keyword-driven patterns (an
# assignment, a bearer header, a URL scheme) stay case-insensitive, because the keyword
# itself — not a literal credential prefix — is what identifies them, and a keyword can
# legitimately appear in any case.
PATTERNS: Final[tuple[SecretPattern, ...]] = (
    SecretPattern(
        "private-key-block",
        "PEM private key block",
        _c(r"-----BEGIN [A-Z ]*PRIVATE KEY-----", case_sensitive=True),
    ),
    SecretPattern(
        "aws-access-key-id",
        "AWS access key id",
        _c(r"((?:AKIA|ASIA|AGPA|AIDA|AROA)[A-Z0-9]{16})\b", case_sensitive=True),
    ),
    SecretPattern(
        "aws-secret-key",
        "AWS secret access key assignment",
        _c(r"aws_secret_access_key\s*[=:]\s*['\"]?([A-Za-z0-9/+=]{40})"),
    ),
    SecretPattern(
        "github-token", "GitHub token", _c(r"(gh[pousr]_[A-Za-z0-9]{36,})\b", case_sensitive=True)
    ),
    SecretPattern(
        "github-fine-grained-token",
        "GitHub fine-grained personal access token",
        _c(r"(github_pat_[A-Za-z0-9_]{80,})\b", case_sensitive=True),
    ),
    SecretPattern(
        "gitlab-token",
        "GitLab personal access token",
        _c(r"(glpat-[A-Za-z0-9_-]{20,})\b", case_sensitive=True),
    ),
    SecretPattern(
        "slack-token",
        "Slack token",
        _c(r"(xox[abposr]-[A-Za-z0-9-]{10,})\b", case_sensitive=True),
    ),
    SecretPattern(
        "slack-app-token",
        "Slack app-level token",
        _c(r"(xapp-[A-Za-z0-9-]{10,})\b", case_sensitive=True),
    ),
    SecretPattern(
        "google-api-key", "Google API key", _c(r"(AIza[0-9A-Za-z_-]{35})\b", case_sensitive=True)
    ),
    SecretPattern(
        "google-oauth-token",
        "Google OAuth access token",
        _c(r"(ya29\.[A-Za-z0-9_-]{20,})\b", case_sensitive=True),
    ),
    SecretPattern(
        "anthropic-key",
        "Anthropic API key",
        _c(r"(sk-ant-[A-Za-z0-9_-]{20,})\b", case_sensitive=True),
    ),
    SecretPattern(
        "openai-key",
        "OpenAI API key",
        # A short generic prefix (see the comment above `PATTERNS`): blocked from matching
        # mid-word by the leading lookbehind, and required to contain a digit like a real
        # key does, so "review-onboarding-checklist" glued to a preceding "sk-" is not one.
        _c(
            r"(?<![A-Za-z0-9])(sk-(?=[A-Za-z0-9_-]*\d)[A-Za-z0-9_-]{20,})\b",
            case_sensitive=True,
        ),
    ),
    SecretPattern(
        "trello-token",
        "Trello API token",
        _c(r"(ATTA[A-Fa-f0-9]{60,})\b", case_sensitive=True),
    ),
    SecretPattern(
        "atlassian-token",
        "Atlassian API token",
        _c(r"(ATATT3[A-Za-z0-9_=-]{20,})\b", case_sensitive=True),
    ),
    SecretPattern(
        "jwt",
        "JSON Web Token",
        _c(
            r"(eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,})\b",
            case_sensitive=True,
        ),
    ),
    SecretPattern(
        "basic-auth-url",
        "Credentials embedded in a URL",
        _c(r"\b[a-z][a-z0-9+.-]*://[^/\s:@]+:([^/\s:@]{3,})@"),
    ),
    SecretPattern(
        "stripe-key",
        "Stripe secret key",
        # Short generic prefix: same lookbehind-plus-digit treatment as openai-key.
        _c(
            r"(?<![A-Za-z0-9])((?:sk|rk)_(?:live|test)_(?=[A-Za-z0-9]*\d)[A-Za-z0-9]{10,})\b",
            case_sensitive=True,
        ),
    ),
    SecretPattern(
        "npm-token",
        "npm access token",
        _c(
            r"(?<![A-Za-z0-9])(npm_(?=[A-Za-z0-9]*\d)[A-Za-z0-9]{20,})\b",
            case_sensitive=True,
        ),
    ),
    SecretPattern(
        "url-query-credential",
        "Credential in a URL query parameter",
        _c(r"[?&](?:key|token)=([A-Za-z0-9_-]{16,})"),
    ),
    SecretPattern(
        "bearer-header",
        "Bearer credential in a header",
        _c(r"authorization\s*:\s*bearer\s+([A-Za-z0-9._~+/=-]{12,})"),
    ),
    # Quoted assignment first, so a quoted value keeps its exact span even when it contains
    # characters the unquoted form would stop at.
    SecretPattern(
        "secret-assignment",
        "Secret-like assignment",
        _c(r"[\"']?(?:" + _KEYWORDS + r")[\"']?\s*[=:]\s*[\"']([^\"'\n]{8,})[\"']"),
    ),
    # Unquoted: `.env` lines, shell transcripts and YAML. Stops at whitespace and at the
    # punctuation that ends a value in JSON, YAML flow style or a shell command.
    SecretPattern(
        "secret-assignment-unquoted",
        "Secret-like assignment",
        _c(r"[\"']?(?:" + _KEYWORDS + r")[\"']?\s*[=:]\s*([^\s\"',;}\]]{8,})"),
    ),
)

# Values that look like secrets but are documentation. A finding is suppressed when the
# captured span is one of these, so that .env.example and the authoring guide stay clean.
PLACEHOLDERS: Final[frozenset[str]] = frozenset(
    {
        "changeme",
        "change-me",
        "your-token-here",
        "your_token_here",
        "example",
        "placeholder",
        "redacted",
        "xxxxxxxx",
        "your-api-key",
        "your_api_key",
        "replace-me",
        "notarealsecret",
        "dummy",
        "fake",
        "sample",
        "<token>",
        "test",
        REDACTION_PLACEHOLDER.lower(),
    }
)


def _is_placeholder(value: str) -> bool:
    lowered = value.strip().lower()
    if lowered in PLACEHOLDERS:
        return True
    # Templates are instructions to the reader, not values: shell and CI expansions
    # (`${VAR}`, `$(cmd)`), documentation placeholders (`<your-token>`), and the format
    # placeholders that appear wherever this scanner reads its own source or a template.
    if lowered.startswith(("<", "${", "$(", "{{")) or lowered.endswith(">"):
        return True
    # Parentheses mean source code, not a credential: `token=secrets.token_urlsafe(32)` and
    # `token = payload.get("token")` are both assignments whose value is a call. No real
    # token, key, JWT or base64 blob contains one.
    if "(" in lowered or ")" in lowered:
        return True
    # A short dotted identifier chain is an attribute path, not a secret. The length bounds
    # matter: without them this also matches a JWT, whose three base64 segments are exactly
    # a long dotted chain.
    if (
        len(lowered) <= 40
        and re.fullmatch(r"[a-z_][a-z0-9_]*(?:\.[a-z_][a-z0-9_]*)+", lowered)
        and all(len(segment) <= 20 for segment in lowered.split("."))
    ):
        return True
    # Any brace at all means a template fragment. Real credentials — tokens, keys, JWTs,
    # base64 — do not contain braces, so this costs no detection and removes a whole class
    # of false positive from source code, Jinja templates and CI configuration.
    if "{" in lowered or "}" in lowered:
        return True
    # A run of a single repeated character is a mask, not a secret.
    return len(set(lowered)) <= 2


def scan_text(text: str) -> list[SecretMatch]:
    """Every secret-like span in `text`, ordered by position.

    Overlapping matches from different patterns are reported once, by the first pattern in
    `PATTERNS` that claims the span, so the most specific name wins.
    """
    claimed: set[tuple[int, int]] = set()
    matches: list[SecretMatch] = []
    line_starts = [0]
    for index, char in enumerate(text):
        if char == "\n":
            line_starts.append(index + 1)

    def position(offset: int) -> tuple[int, int]:
        low, high = 0, len(line_starts) - 1
        while low < high:
            mid = (low + high + 1) // 2
            if line_starts[mid] <= offset:
                low = mid
            else:
                high = mid - 1
        return low + 1, offset - line_starts[low] + 1

    for pattern in PATTERNS:
        for match in pattern.regex.finditer(text):
            captured = match.group(1) if match.re.groups else match.group(0)
            if _is_placeholder(captured):
                continue
            span = match.span(1) if match.re.groups else match.span(0)
            if any(span[0] < end and start < span[1] for start, end in claimed):
                continue
            claimed.add(span)
            line, column = position(span[0])
            matches.append(
                SecretMatch(
                    pattern_id=pattern.id,
                    description=pattern.description,
                    line=line,
                    column=column,
                    excerpt=_excerpt(captured),
                )
            )
    return sorted(matches, key=lambda m: (m.line, m.column))


def _excerpt(value: str) -> str:
    """Enough to tell two findings apart, never enough to reconstruct either.

    Findings are printed in CI logs, which are themselves a place secrets leak from. The
    first pass printed four leading and two trailing characters plus the exact length; for a
    short token that is most of it. Only a short leading fragment survives, and only when the
    value is long enough for a fragment to be meaningless on its own.
    """
    if len(value) < 12:
        return f"{len(value)} chars"
    return f"{value[:3]}… ({len(value)} chars)"


def redact_text(text: str) -> tuple[str, bool]:
    """`text` with every detected secret replaced. Returns the text and whether anything changed."""
    spans: list[tuple[int, int]] = []
    for pattern in PATTERNS:
        for match in pattern.regex.finditer(text):
            captured = match.group(1) if match.re.groups else match.group(0)
            if _is_placeholder(captured):
                continue
            spans.append(match.span(1) if match.re.groups else match.span(0))
    if not spans:
        return text, False
    merged: list[tuple[int, int]] = []
    for start, end in sorted(spans):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    out: list[str] = []
    cursor = 0
    for start, end in merged:
        out.append(text[cursor:start])
        out.append(REDACTION_PLACEHOLDER)
        cursor = end
    out.append(text[cursor:])
    return "".join(out), True
