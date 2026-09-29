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
        # Round 15 E12: bare "token" has no left boundary of its own, so it used to match
        # the tail of a pagination field name — Jira's `nextPageToken`/`pageToken`, the exact
        # shape the Jira quest asks participants to page through and document — as if the
        # field name itself were an assignment keyword. Jira's own docs name that field
        # `nextPageToken` or `pageToken`; a real credential field is never called that, so
        # the lookbehind costs no detection.
        r"(?<!page)token",
        r"bearer",
        # Round 16 E11: `passw(?:or)?d` only ever matched "password"/"passwd" — `DB_PASS=`
        # and `PWD=` (the shell's own working-directory variable name, reused constantly as
        # a field name for "password") had no keyword of their own. A bare `pass` is not
        # safe to add on its own: this repository's own test-result vocabulary uses it
        # constantly as a plain field name (`"pass": "Every required check passed."`,
        # `messages:{pass:"..."}` in `vendor/axe.min.js`), and English has "bypass". Real
        # env-var-style names compound it behind an underscore instead (`DB_PASS`,
        # `ADMIN_PASS`), which none of those do, so the lookbehind requires one.
        #
        # Round 17 E1: the `\b` here stopped `DB_PASS_PROD` (an `_` is a word character, so
        # there is no boundary between `PASS` and `_PROD`) once a keyword could carry an
        # identifier suffix (see `_KEY` below); a following letter is what `\b` was keeping
        # out (`_passthrough`), so that is what the lookahead refuses now.
        r"(?<=_)pass(?![a-z])",
        # Round 17 E1: `"dbPass": "…"` (camelCase, no underscore) and PHP's `$dbpass` are
        # the other common spelling of the same compound. Only named credential-owner
        # prefixes qualify, never a bare letter before `pass`, so "bypass", "onPass",
        # "firstPass" and `messages:{pass:...}` stay ordinary vocabulary.
        r"(?:db|admin|user|root|smtp|mail|ftp|sql|redis|ldap)pass(?![a-z])",
        # Round 17 E9: `PWD` and `OLDPWD` are also the shell's own working-directory
        # variables, and every `env`/`printenv` transcript prints them — so a bare `pwd`
        # keyword made any such transcript a finding that blocked submission. A standalone
        # `PWD`/`OLDPWD` (nothing but a non-identifier character before it) whose value is a
        # filesystem path (`/…`, `~/…`, `C:\…`) is that variable, not a password; any other
        # value is still one, and a compound name (`DB_PWD`) is detected whatever its value.
        # The trade: a standalone `PWD=` holding a password that itself starts with `/` or
        # `~/` is read as a path.
        r"(?<![a-z0-9_])(?:old)?pwd(?![\"']?[ \t]*[=:][ \t]*[\"']?(?:/|~/|[a-z]:[\\/]))",
        r"(?<=[a-z0-9_])(?<!old)pwd",
        # Round 17 E1: a bare `key` is not safe as a keyword (`key: value` is every YAML
        # and JSON mapping ever written), so only the compounds that name a credential are
        # added: Django's and Rails' `SECRET_KEY`/`SECRET_KEY_BASE` (already reached through
        # `secret` plus a suffix), and the encryption, storage-account and signing keys.
        r"encryption[_-]?key",
        r"account[_-]?key",
        r"signing[_-]?key",
    )
)

# Round 17 E1: every assignment-shaped pattern used to require the `[=:]` (or closing tag,
# or quote) immediately after the keyword itself, so a keyword followed by anything at all
# before the operator was never matched: `SECRET_KEY=`, `"secret_key": "…"`, `"secretKey"`,
# `JWT_SECRET_KEY=`, `DB_PASSWORD_PROD=`, `JIRA_API_TOKEN_2=` — the ordinary way an env
# file or config names a second credential of the same kind. The keyword may now be
# followed by an identifier suffix (letters, digits, `_`, `-`) before whatever the pattern
# expects next. The suffix is bounded, so each keyword occurrence costs a constant amount
# of backtracking however long the identifier run after it is. The trade is a wider net:
# a field such as `password_file` or `secret_name` holding an 8-character value is now a
# finding too; none of this repository's own tracked files, and none of the negative
# fixtures (`nextPageToken`, `bypass`, `"pass": …`), has that shape.
#
# A suffixed name gives up one thing the bare keyword has: its operator may not be followed
# by a line break before the value. A bare `password:` followed by the value indented on
# the next line is a valid YAML plain scalar and stays detected; but a suffix is exactly
# what turns a Python class or loop header into that shape (`class SecretMatch:` followed by
# an indented `pattern_id: str`, `class SecretPattern:` followed by its docstring), and
# neither a class body nor a docstring is a value.
_KEY = r"(?:" + _KEYWORDS + r")[A-Za-z0-9_-]{0,40}"
_ASSIGNMENT_KEY = (
    r"[\"']?(?:" + _KEYWORDS + r")(?:[\"']?\s*[=:]\s*|[A-Za-z0-9_-]{1,40}[\"']?[ \t]*[=:][ \t]*)"
)


# The bracketed form of an unquoted value (see `secret-assignment-unquoted` below).
_UNQUOTED_BRACKET_VALUE = (
    r"\[(?:[^\]\n\s,\"']{3,80}|(?=[^\]\n\s,\"']{0,2}\][^\s\"',;}`]{5})[^\]\n\s,\"']{0,2})\]"
    r"(?:\]*[^\s\"',;}`\]])*"
)


# The plain form of an unquoted value: a run of value characters, which stops at whitespace
# and at the punctuation that ends a value in JSON, YAML flow style or a shell command.
#
# Round 17 E17: `,` and `;` are among those stops, so a password assigned as
# `Sup3rS3cr;etValue9` redacted to `[REDACTED];etValue9` — half the value left in clear
# text — and one assigned as `ab,Sup3rS3cretValue9` was never matched at all, the two
# characters before the comma being too few to be a finding. The rule now: a `,` or `;`
# glued between two runs of value characters is part of the value, as long as the run
# after it goes on to a real end of value (whitespace, a quote, a closing `}`/`]`, the end
# of the text, or another such separator) and contains none of `=`, `:`, `(`, `)`, `{`,
# `}`, `[`, `<`, `>`. That second condition is what keeps code out: after a comma, code
# continues with another key or argument (`f(token=token,user=user)`, minified
# `{password:e,next:t}`), which has one of those characters in it; a value continues with
# more of itself, which does not. A value whose first run is under eight characters
# (`ab,…`) counts only when the whole run, separators included, reaches eight and ends at
# a real end of value. Each tail run excludes its own separators and has to end on a
# terminator, so it cannot backtrack. The trade: a shell line with no space after a `;`
# (a password followed directly by `;echo done`) is now redacted through the command glued
# to it.
_UNQUOTED_PLAIN_TAIL = r"[,;][^\s\"',;}`\]=:(){}\[<>]+(?=[\s\"',;}`\]]|$)"
#
# Round 17 C2: the plain run also stopped at every `}`, so a value with a brace in it and
# fewer than eight characters before the brace (`k8s{Q}9aQ2vLm7RealSecret`) was never
# matched, and the real secret after the brace was never looked at. A `}` with more value
# glued straight after it is part of the value now; one followed by anything else still
# ends it, so a JSON or JavaScript object's own closing brace is never swallowed. So does a
# `}` followed by a backslash: read as source text, an f-string placeholder followed by an
# escape (`f"token={LEAKED}\n"`, all over this repository's own tests) is not a value.
_UNQUOTED_PLAIN_VALUE = (
    r"(?:[^\s\"',;}`\]]|\}(?=[^\s\"',;}`\]\\])){8,}(?:"
    + _UNQUOTED_PLAIN_TAIL
    + r")*|(?=[^\s\"'`}\]=:(){}\[<>]{8})[^\s\"',;}`\]=:(){}\[<>]{1,7}(?:"
    + _UNQUOTED_PLAIN_TAIL
    + r")+(?=[\s\"'`}\]]|$)"
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
        # Round 15 E12: the OpenPGP armor marker is "...PRIVATE KEY BLOCK-----", not
        # "...PRIVATE KEY-----" — the optional " BLOCK" was missing, so a PGP private key
        # was never caught even though an RSA/OpenSSH block was.
        _c(r"-----BEGIN [A-Z ]*PRIVATE KEY(?: BLOCK)?-----", case_sensitive=True),
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
        #
        # Round 16 E1: the digit lookahead used to be `(?=[A-Za-z0-9_-]*\d)` — unbounded,
        # and its class is the same one the body uses, so a run of nothing but "sk-" has no
        # character outside that class to stop the lookahead early. Every "sk-" in the run
        # is a legal start position (the lookbehind's class excludes the hyphen that
        # precedes each one), so a text of nothing but "sk-" repeated failed the lookahead
        # from every one of those positions, each failure re-scanning to the end of the
        # string: quadratic (80 KB took 6.3s; a 2 MB file never finished under the store,
        # generated and service locks this runs inside of). Bounding the lookahead's reach
        # keeps every attempt's cost constant regardless of how far away — or how absent —
        # the nearest digit is; a real key is nowhere near 200 characters long, so nothing
        # genuine stops matching.
        _c(
            r"(?<![A-Za-z0-9])(sk-(?=[A-Za-z0-9_-]{0,200}\d)[A-Za-z0-9_-]{20,})\b",
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
        # Round 15 E5: each of the three unbounded `{10,}` segments let the engine retry a
        # failed match at every offset of a long run of `eyJ`-like or `.`-heavy text, which is
        # quadratic in input length (a 120 KB adversarial file took 36s; 2 MB would take
        # hours, all under the store and service locks). Real JWT segments are a few hundred
        # characters at most; bounding each one at 4096 caps the work per starting offset
        # without narrowing what a real token looks like. That still left one attempt per
        # `eyJ` in a run of them, each reading up to 4096 characters before failing on the
        # missing `.`, which took 5 to 9 seconds on 2 MB in CI. The header segment is where
        # that work happens, and a real header (`alg`, `typ`, `kid`, `x5t`) encodes to well
        # under 512 characters, so it is bounded there; the payload keeps 4096. No leading
        # lookbehind: a JWT glued to a preceding letter must still match (round 13 E11).
        _c(
            r"(eyJ[A-Za-z0-9_-]{10,512}\.[A-Za-z0-9_-]{10,4096}\.[A-Za-z0-9_-]{10,4096})\b",
            case_sensitive=True,
        ),
    ),
    SecretPattern(
        "basic-auth-url",
        "Credentials embedded in a URL",
        # Round 15 E5: the unbounded scheme (`[a-z0-9+.-]*`) made this quadratic the same
        # way — every starting position re-scanned the rest of the text looking for `://`
        # that never came. No real URL scheme is anywhere near 32 characters; bounding it
        # (and the username/password spans, which were already implicitly bounded by their
        # excluded characters but had no explicit ceiling) keeps the work per offset constant.
        _c(r"\b[a-z][a-z0-9+.-]{0,31}://[^/\s:@]{1,255}:([^/\s:@]{3,255})@"),
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
        _c(r"(?:proxy-)?authorization\s*:\s*bearer\s+([A-Za-z0-9._~+/=-]{12,})"),
    ),
    # Round 15 E2: Jira Cloud's documented script authentication is HTTP Basic with
    # `email:api_token`, which base64 hides the `ATATT3…` prefix from the pattern above. A
    # `curl -v` transcript — exactly the command-record proof the Jira, Trello and GitHub
    # quests ask for — shows the header verbatim, so any Basic (or "Authorization: token …",
    # the scheme GitHub's and Django's APIs also accept) credential in transit is itself
    # sensitive, whether or not its decoded contents match a known prefix.
    SecretPattern(
        "basic-auth-header",
        "Basic credential in an Authorization header",
        _c(r"(?:proxy-)?authorization\s*:\s*(?:basic|token)\s+(\S{8,})"),
    ),
    # Round 16 E11: curl's own manual documents this flag as how it takes HTTP Basic
    # authentication on the command line, and it is exactly the shape the Jira, Trello and
    # GitHub quests' own `curl -v` proof asks participants to run. The scan requires the
    # literal word "curl" earlier on the same line, so an unrelated flag that happens to
    # take a colon-separated argument on some other line of a transcript (a container
    # runtime's own numeric-identifiers flag, which is not a credential) is not a false
    # positive. The scan-ahead to find the flag is bounded (round 15 E5's lesson: an
    # unbounded `[^\n]*?` ahead of a literal a pathological line never supplies is quadratic
    # across many `curl` occurrences on one huge line), since a real invocation puts the
    # flag well within the first couple hundred characters of the command.
    SecretPattern(
        "curl-user-credential",
        "Credential passed to curl's -u/--user flag",
        _c(r"curl\b[^\n]{0,200}?(?:-u|--user)[= ]([^\s'\"]{3,}:[^\s'\"]{3,})"),
    ),
    # Round 16 E11: a credential is not only ever assigned with `=`/`:` — Maven's
    # `settings.xml` and similar tooling write it as an XML element, and a YAML block
    # scalar (`password: >-` / `password: |`, followed by an indented value on its own
    # line) is valid YAML the flow-style unquoted pattern below never reaches, since it
    # requires the value on the same line as the keyword.
    SecretPattern(
        "xml-element-credential",
        "Secret-like value in an XML element",
        _c(r"<(?:" + _KEYWORDS + r")>([^<>\n]{8,})</(?:" + _KEYWORDS + r")>"),
    ),
    SecretPattern(
        "yaml-block-scalar-credential",
        "Secret-like value in a YAML block scalar",
        _c(_KEY + r"\s*:\s*[|>][+-]?\s*\n[ \t]+(\S[^\n]{7,})"),
    ),
    # Quoted assignment first, so a quoted value keeps its exact span even when it contains
    # characters the unquoted form would stop at.
    SecretPattern(
        "secret-assignment",
        "Secret-like assignment",
        _c(_ASSIGNMENT_KEY + r"[\"']([^\"'\n]{8,})[\"']"),
    ),
    # Unquoted: `.env` lines, shell transcripts and YAML. Stops at whitespace and at the
    # punctuation that ends a value in JSON, YAML flow style or a shell command. The
    # bracketed alternative is tried first: round 15 E1 found that this application's own
    # `REDACTION_PLACEHOLDER` (`[REDACTED]`) was not a fixed point of `scan_text` — the plain
    # class below stops at the closing `]`, so `TOKEN=[REDACTED]` captured `[REDACTED`
    # (without its bracket), which `_is_placeholder` did not recognize. No whitespace, quote
    # or comma is allowed inside the brackets: a real placeholder or token has none of these,
    # and this is also what stops the bracket branch from capturing a Python list literal or
    # comprehension assigned to a keyword-named variable in this repository's own source
    # (`secret = [f for f in findings ...]`) or a minified JSON array value
    # (`"current-password":["text","search","password"]`, from `vendor/axe.min.js`).
    #
    # Round 16 E4: the bracket alternative used to stop at the closing `]`, so a value that
    # is a placeholder glued to a real one (`[Pr0d]Sup3rS3cretValue`) captured only the
    # bracket, leaving the rest of the value uncaptured — never scanned, never redacted. A
    # placeholder is only ever a value that is *entirely* one bracketed token; anything
    # glued after the bracket is part of the value, so the trailing suffix (the same
    # character class the plain unquoted branch stops at) is captured too. `_is_placeholder`
    # already refuses anything but an exact `[redacted]` match for the bracket shape, so a
    # bare placeholder alone is unaffected and a value with a real suffix is now reported —
    # and redacted — in full. Both classes now also exclude a backtick: without that, this
    # very module's own prose — a markdown code span closing right after a keyword-shaped
    # example, `` `TOKEN=[REDACTED]` `` — captured the backtick along with it, so the exact
    # `[redacted]` placeholder match no longer held and the sentence became a finding. A
    # real value is never written with a backtick in it.
    #
    # Round 17 E3: the bracket still needed 3 to 80 characters inside it, so a short one
    # glued to a real value (`[X]Sup3rS3cretValue9`, `[ab]…`) failed the bracket branch, and
    # the plain branch then stopped at the `]` with too few characters to be a finding; and
    # the suffix after the bracket excluded `]`, so `[REDACTED]]Sup3r…` captured exactly
    # `[REDACTED]`, a placeholder, and `[abc]]Sup3r…` redacted to `[REDACTED]]Sup3r…`, which
    # itself rescanned clean with the real value still in it. A short bracket (0 to 2
    # characters) is allowed now when at least five value characters follow it, and the
    # suffix runs through any `]` that more value follows. A trailing run of nothing but
    # `]` is left out of the capture, so a redaction followed by a stray `]` — `[REDACTED]]`
    # — reads as the placeholder it is and the redacted text stays a fixed point.
    SecretPattern(
        "secret-assignment-unquoted",
        "Secret-like assignment",
        #
        # Round 17 E4: the plain class stops at `}`, so `${DB_PASSWORD}Sup3rS3cretValue9`
        # captured `${DB_PASSWORD`, which `_is_placeholder` read as a bare `${NAME}` — the
        # real value glued after the expansion was never looked at. A `${…}`, `$(…)` or
        # `{{…}}` template is now captured whole, closing delimiter included, together with
        # whatever is glued after it; only a capture that is entirely the template is a
        # placeholder. Each template body is bounded and excludes its own delimiters, so it
        # cannot backtrack.
        _c(
            _ASSIGNMENT_KEY
            + r"("
            + _UNQUOTED_BRACKET_VALUE
            + r"|(?:\$\{[^{}\n]{0,200}\}|\$\([^()\n]{0,200}\)|\{\{[^{}\n]{0,200}\}\})"
            + r"[^\s\"',;}`\]]*"
            + r"|"
            + _UNQUOTED_PLAIN_VALUE
            + r")"
        ),
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


# Round 16 E7: the names a genuine attribute-path exemption is allowed to start from — the
# object names this codebase's own source, and the config/environment shapes its docs give
# as examples (`self.x`, `config.x`, `os.environ...`), actually use. A passphrase never
# starts with one of these, which is what lets the exemption stay narrow.
_CODE_ATTRIBUTE_ROOTS: Final = frozenset(
    {"self", "cls", "config", "os", "ctx", "context", "app", "request", "response", "settings"}
)


# Round 17 E5: a digit between two letters is how a password is usually made from a word
# (`P4ssw0rd`, `Tr0ub4dor`, `Sup3rS3cret`); code names put digits there rarely, and then
# once, in a lowercase name (`b64encode`, `sha256sum`, `oauth2client`).
_SANDWICHED_DIGIT = re.compile(r"[A-Za-z]\d+(?=[A-Za-z])")
_CODE_EXPRESSION = re.compile(
    r"(?P<callee>[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*)"
    r"(?:\((?P<call_args>[^()]*)\)?|\[(?P<subscript_args>[^\[\]]*)\]?|(?P<closing>[)\]]))"
)


def _is_code_identifier(name: str) -> bool:
    """`name` reads as an identifier a programmer wrote, not as a password (round 17 E5)."""
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
        return False
    sandwiched = len(_SANDWICHED_DIGIT.findall(name))
    return sandwiched == 0 or (sandwiched == 1 and name.islower())


def _is_format_placeholder(value: str, *, closed: bool) -> bool:
    """`value` is a `{name}` format-string placeholder (round 17 E5).

    `closed=False` also accepts the forms the unquoted pattern captures, which stop before a
    closing brace or a comma: `{GITHUB` and `{total_tokens:`.
    """
    shape = (
        r"\{([A-Za-z_][A-Za-z0-9_]*)\}"
        if closed
        else r"\{([A-Za-z_][A-Za-z0-9_]*)(?::[^{}]{0,20})?\}?"
    )
    match = re.fullmatch(shape, value)
    if match is None:
        return False
    name = match.group(1)
    return _is_code_identifier(name) and (name.islower() or name.isupper())


def _is_code_expression(value: str) -> bool:
    """`value` is a call, subscript or format placeholder read out of source (round 17 E5)."""
    if _is_format_placeholder(value, closed=False):
        return True
    match = _CODE_EXPRESSION.fullmatch(value)
    if match is None:
        return False
    callee = match.group("callee")
    if not all(_is_code_identifier(segment) for segment in callee.split(".")):
        return False
    if match.group("closing") is not None:
        # A keyword-named variable passed as another call's own argument (`api_key=api_key)`):
        # a plain name, never one with a digit in it.
        return not any(ch.isdigit() for ch in callee)
    args = match.group("call_args")
    if args is None:
        args = match.group("subscript_args")
    if args:
        if not re.fullmatch(r"[A-Za-z0-9_.=*+\-\[\]]*", args) or not re.search(
            r"[A-Za-z0-9]", args
        ):
            return False
        if not all(
            _is_code_identifier(name) for name in re.findall(r"[A-Za-z_][A-Za-z0-9_]*", args)
        ):
            return False
    return True


def _is_placeholder(value: str, *, allow_call_expression: bool = False) -> bool:
    """`value` is documentation, a template, a mask, or code — not a live credential.

    `allow_call_expression` is set only for the unquoted assignment pattern (round 15 E12):
    it has no closing delimiter of its own, so scanning this module's own source (or any
    Python file `tools/secret_scan.py` reads) captures straight into a real call expression
    whenever a keyword-named variable holds one — `token = payload.get(`,
    `token=secrets.token_urlsafe(32)`. A real credential is never written unquoted with that
    shape, and the quoted pattern already covers a deliberately-quoted value on its own, so
    the cost of allowing this through is paid only by that one pattern rather than by every
    value this module inspects. Round 16 E6 narrowed what "this" is from any value
    containing a paren or brace anywhere to the specific call/subscript shape below, so a
    real password that happens to contain one (`Tr0ub4dor(3)xyz`) is caught instead of
    excused.
    """
    lowered = value.strip().lower()
    if lowered in PLACEHOLDERS:
        return True
    # Templates are instructions to the reader, not values: shell and CI expansions
    # (`${VAR}`, `$(cmd)`), documentation placeholders (`<your-token>`), and the format
    # placeholders that appear wherever this scanner reads its own source or a template.
    # Round 16 E11: a lone `<` or `>` at one end used to be enough on its own, so a real
    # value that merely started with a stray `<` (`"<Sup3rS3cretValue9"`, a quote typed
    # where a closing angle bracket should have gone) or ended with a stray `>`
    # (`Sup3rS3cretValue9>`) was waved through as a template. Only a value that is a matched
    # `<...>` pair, start to end, is a documentation placeholder now.
    #
    # Round 17 E4: `startswith(("$(", "{{"))` excused anything that merely began like a
    # command substitution or a Jinja expression, so `"$(true)Sup3rS3cretValue9"` and
    # `"{{ vault_pw }}Sup3rS3cretValue9"` were waved through. Only a value that is entirely
    # one `$(…)` is a command substitution now; the whole-value Jinja check is below.
    if re.fullmatch(r"\$\([^()]*\)", lowered) or re.fullmatch(r"<[^<>]*>", lowered):
        return True
    # Round 16 E5: this used to be `lowered.startswith("${")`, so anything shaped like a
    # shell or compose expansion was exempted regardless of what followed — including a
    # `${VAR:-default}`/`${VAR-default}` *default*, which is a real value the moment the
    # variable is unset (`DB_PASSWORD=${DB_PASSWORD:-Sup3rS3cretValue9}`)  # secret-scan: allow
    # is the ordinary docker-compose/.env shape. Only a value that is entirely
    # `${NAME}`, optionally with a `:?message` clause (an error string shown when unset,
    # never a default value), refers to the environment rather than holding one. The
    # unquoted pattern's value class excludes `}`, so a bare wrap used to be captured with
    # its closing brace already stripped off by the regex, and this allowed for that with a
    # trailing `\}?` — which also excused an unclosed `${NAME` with a real value glued on.
    # Round 17 E4: the unquoted pattern now captures a `${…}` whole, brace included, as the
    # quoted pattern always did, so the closing brace is required here.
    if re.fullmatch(r"\$\{[a-z_][a-z0-9_]*(?::\?[^{}]*)?\}", lowered):
        return True
    # A value that IS entirely one of the real template shapes below — a Jinja expression, a
    # bare `{name}` format-string/f-string placeholder (this module's own test fixtures are
    # full of exactly that shape, reading their own source: `f'token = "{GITHUB}"'`), or a
    # parenthetical annotation like `(redacted)` or `(see vault)` — is a placeholder.
    #
    # Round 17 E5: the `{name}` check matched the lowered value, so `{Sup3rS3cretValue9}`
    # read as a format placeholder too. A real one names a variable, and a variable name is
    # written in one case (`{api_key}`, `{GITHUB}`) without a password's mixed-in digits;
    # `_is_format_placeholder` checks the value as written.
    if (
        re.fullmatch(r"\{\{\s*[^{}]*\s*\}\}", lowered)
        or _is_format_placeholder(value.strip(), closed=True)
        or re.fullmatch(r"\([a-z][a-z0-9 _-]*\)", lowered)
    ):
        return True
    # Round 16 E6: round 15 E12 excused ANY value containing a paren or brace ANYWHERE, so
    # `Tr0ub4dor(3)xyz` and `k8s{X}9aQ2vLm7` — ordinary unquoted `.env` passwords that
    # happen to contain one — were excused right along with a real call expression. A real
    # call or subscript this module's own source contains has a specific shape: an
    # identifier (optionally dotted) immediately followed by `(` or `[`, with nothing after
    # the matching close but what the value class already stopped at — or, when the
    # keyword-named value is itself just a bare identifier passed as another call's own
    # argument (`OpenAI(api_key=api_key)`, this repository's own source), a single
    # unmatched closing `)`/`]` left over once the value class stops at the *enclosing*
    # call's own close. The fourth alternative is this module's own f-string test fixtures
    # (`f"token = {GITHUB}"`): read as source text rather than evaluated, `{GITHUB}` is a
    # bare format placeholder in exactly the shape `_is_placeholder`'s own dedicated check a
    # few lines below recognizes, truncated the same way the unquoted class always
    # truncates before a closing brace. `Tr0ub4dor(3)xyz` has a *closed* paren with more
    # value after it — not how any of these shapes read — so it fails every alternative
    # below and stays a finding.
    #
    # Round 17 E5: that shape was still matched on the lowered value with no look at what
    # the identifiers or the arguments were, so any password that merely *ended* like a
    # call was excused with it: `Tr0ub4dor(3)`, `Summer2024(!)`, `MyP4ssw0rd(` (the value
    # class stopped where a quote would have been), `Sup3rS3cr3t)` (a "bare closing"),
    # `abc[Sup3rS3cretValue9` and `{Sup3rS3cretValue9}`. `_is_code_expression` keeps the
    # same four shapes but checks them as written: every identifier in them must read as a
    # code identifier rather than a password (see `_is_code_identifier`), a call's or
    # subscript's arguments may only be identifiers, numbers and the operators code puts
    # between them, a bare closing is only ever a digit-free name, and a `{name}` must be
    # written in one case. `token = payload.get(`, `token_urlsafe(32)`, `OpenAI(api_key=
    # api_key)` and `load_api_key(config[` — the real code this repository's own source
    # contains — all still pass.
    if allow_call_expression and _is_code_expression(value.strip()):
        return True
    # Round 17 E1: once a keyword can carry a suffix, the unquoted pattern reads three more
    # code shapes from this repository's own source that no suffix-free name ever produced:
    # a keyword-named constant or variable assigned from another one (`TOKEN_PLACEHOLDER =
    # REQUEST_TOKEN_PLACEHOLDER`, `"total_tokens": total_tokens`), an f-string placeholder
    # with a format spec (`{total_tokens:,}`, cut at the comma), and minified JavaScript
    # whose property value is a function or a return expression (`tokenList:function(){`,
    # `"nmtokens":return(...)`, both in `vendor/axe.min.js`). Each is excused only in the
    # narrow form code takes: a bare identifier must be single-case snake_case with no digit,
    # contain an underscore, and itself contain a credential keyword — the name of a
    # credential, not a value — and the JavaScript case must start with the reserved word
    # itself. A real password of any of these shapes (`super_secret_token`) is the trade.
    if allow_call_expression and (
        (
            re.fullmatch(r"[a-z_]+|[A-Z_]+", value.strip())
            and "_" in value
            and re.search(_KEYWORDS, value, re.IGNORECASE)
        )
        or _is_format_placeholder(value.strip(), closed=False)
        or re.match(r"(?:function|return)(?![a-z0-9_$])", lowered)
    ):
        return True
    # A short dotted identifier chain is an attribute path, not a secret — but only when it
    # actually starts from one of the names this codebase's own source uses for the object
    # being accessed (round 16 E7). Before this, ANY short dotted chain qualified, so a
    # dotted passphrase (`correct.horse.battery.staple`, `Welcome.To.Acme`) read exactly like
    # one and was never reported. The length bounds still matter too: without them this also
    # matches a JWT, whose three base64 segments are exactly a long dotted chain.
    #
    # Round 17 E6: the root was the only part checked, and on the lowered value, so a
    # passphrase that merely started with a root name (`context.is.king2024`,
    # `settings.Sup3r.Secret9`) still read as an attribute path. Every segment is now
    # checked as written: an attribute name is a lowercase `snake_case` name or an
    # `UPPER_SNAKE` constant (`settings.SECRET_KEY`), with no digit in it — the digits and
    # mixed case are what a word-based password adds — and the chain is at most four names
    # long, root included.
    written = value.strip()
    segments = written.split(".")
    if (
        len(written) <= 40
        and 2 <= len(segments) <= 4
        and segments[0] in _CODE_ATTRIBUTE_ROOTS
        and all(
            len(segment) <= 20 and re.fullmatch(r"[a-z_]+|[A-Z_]+", segment) for segment in segments
        )
    ):
        return True
    # Round 15 E1: `gh auth status` and this application's own redaction print a value that
    # is mostly mask characters after a real-looking prefix (`gho_************************
    # ************`) — a distinctive prefix alone no longer proves a live credential once
    # the rest of it has been starred, x'd or dotted out.
    mask_chars = sum(1 for ch in lowered if ch in "*x•")
    if lowered and mask_chars / len(lowered) >= 0.6:
        return True
    # A run of a single repeated character is a mask, not a secret.
    return len(set(lowered)) <= 2


def scan_text(text: str) -> list[SecretMatch]:
    """Every secret-like span in `text`, ordered by position.

    Overlapping matches from different patterns are reported once, by the first pattern in
    `PATTERNS` that claims the span, so the most specific name wins.
    """
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

    # Round 16 E2: `claimed` used to be a set scanned end to end for every new match — a
    # match count of `m` costs O(m) to check, and there were `m` of them, so a file of 95k
    # distinct AWS keys (2 MB) took 497s just in this bookkeeping, with every per-pattern
    # regex itself staying linear. `finditer` already returns one pattern's own matches
    # left to right and non-overlapping, and the accepted set stays disjoint and sorted by
    # construction, so each pattern's whole batch of new claims can be folded into the
    # existing sorted set with a single merge of two already-sorted sequences — the same
    # `O(a + b)` step a merge sort's merge is — rather than a fresh membership scan per match.
    # `PATTERNS` has a fixed, small length, so the handful of merges this performs (one per
    # pattern) costs `O(n)` overall, not `O(n^2)`.
    claimed: list[tuple[int, int]] = []
    for pattern in PATTERNS:
        allow_call_expression = pattern.id == "secret-assignment-unquoted"
        batch: list[tuple[int, int, SecretMatch]] = []
        claim_index = 0
        for match in pattern.regex.finditer(text):
            captured = match.group(1) if match.re.groups else match.group(0)
            if _is_placeholder(captured, allow_call_expression=allow_call_expression):
                continue
            start, end = match.span(1) if match.re.groups else match.span(0)
            while claim_index < len(claimed) and claimed[claim_index][1] <= start:
                claim_index += 1
            if claim_index < len(claimed) and claimed[claim_index][0] < end:
                continue  # overlaps a span an earlier, more specific pattern already claimed
            line, column = position(start)
            batch.append(
                (
                    start,
                    end,
                    SecretMatch(
                        pattern_id=pattern.id,
                        description=pattern.description,
                        line=line,
                        column=column,
                        excerpt=_excerpt(captured),
                    ),
                )
            )
        if not batch:
            continue
        matches.extend(item[2] for item in batch)
        merged: list[tuple[int, int]] = []
        old_index = new_index = 0
        while old_index < len(claimed) or new_index < len(batch):
            take_old = new_index >= len(batch) or (
                old_index < len(claimed) and claimed[old_index][0] <= batch[new_index][0]
            )
            if take_old:
                merged.append(claimed[old_index])
                old_index += 1
            else:
                merged.append(batch[new_index][:2])
                new_index += 1
        claimed = merged
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
            if _is_placeholder(
                captured, allow_call_expression=pattern.id == "secret-assignment-unquoted"
            ):
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
