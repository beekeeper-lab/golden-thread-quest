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

import hashlib
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
    # Round 17 E8: tells two values apart without holding either. Truncated SHA-256 of the
    # captured value, never printed; `excerpt` is what people see.
    fingerprint: str = ""


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
        r"(?<=_)pass\b",
        r"pwd",
        # Round 17 E2: `TRELLO_KEY`, `STRIPE_KEY` — an env-var name whose credential word
        # is a bare KEY. A lowercase `_key` is left out: `cache_key`, `sort_key` and
        # `primary_key` are ordinary identifiers in the code a participant quotes, while an
        # upper-case env-var name ending in `_KEY` almost always holds a key.
        r"(?<=[A-Z0-9]_)(?-i:KEY)",
        r"signing[_-]?key",
    )
)

# Round 17 E2: the assignment patterns used to require the separator straight after the
# keyword, so every name with anything after its credential word — `SECRET_KEY=`,
# `DB_PASSWORD_PROD=`, `secretKey:`, `passwordHash=` — was never looked at. A short
# identifier tail is allowed now. What the tail says can also make the name plainly not a
# credential (`password_file`, `token_expires_at`, `tokenizer`), and `_name_is_excused`
# reads it for that, which is why it has a group of its own.
_NAME_TAIL = r"(?P<tail>[A-Za-z0-9_]{0,40})"

# Words that, appearing in a name's tail, say the value describes a credential rather than
# being one: where it lives, what it is called, when it expires, how big it is.
_EXCUSING_TAIL_WORDS: Final = frozenset(
    {
        "file", "files", "path", "paths", "dir", "directory", "name", "names", "type",
        "types", "url", "uri", "id", "ids", "count", "size", "len", "length", "hint",
        "policy", "expiry", "expires", "expiration", "expired", "ttl", "at", "time",
        "timeout", "date", "limit", "max", "min", "header", "prefix", "env", "var",
        "field", "format", "kind", "mode", "scope", "scopes", "enabled", "required",
        "version", "ref", "label", "endpoint", "location", "provider", "store", "manager",
        "source", "help", "prompt", "regex", "pattern", "izer", "ize", "ized", "less",
        "ary", "arn", "rotation", "created", "updated", "placeholder", "list", "s",
    }
)  # fmt: skip

# Round 17 E4: `:=` (Go, and Makefiles) and `=>` (PHP, Ruby, Perl) assign too.
_SEPARATOR = r"[ \t]*(?::=|=>|[=:])[ \t]*"


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
        #
        # Round 17 E1: the match used to stop at the BEGIN line, so redaction replaced that
        # line and left the base64 body and the END line in clear, while still reporting that
        # it had redacted something. The match now runs on over the block's body — armor
        # headers (`Proc-Type:`, `Comment:`) and base64 lines, a blank line between them —
        # and through the END line when there is one, so a key cut off before its END line
        # is still redacted as far as its body goes. Neither line shape can match a BEGIN or
        # END line, which open with a hyphen, so each match reads only its own block and the
        # pattern stays linear however many BEGIN lines a file repeats. The 512-line bound is
        # several times the longest real key (RSA-4096 is about 50 lines).
        _c(
            r"-----BEGIN [A-Z ]*PRIVATE KEY(?: BLOCK)?-----"
            r"(?:[ \t\r]*\n[ \t]*(?:[A-Za-z][A-Za-z0-9-]*:[^\n]*"
            r"|[A-Za-z0-9+/=]+(?=[ \t\r]*(?:\n|$))|(?=[ \t\r]*\n))){0,512}"
            r"(?:[ \t\r]*\n[ \t]*-----END [A-Z ]*PRIVATE KEY(?: BLOCK)?-----)?",
            case_sensitive=True,
        ),
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
        # Round 17 L10: also percent-encoded (`%3Ftoken%3D…`), the shape a URL takes once it
        # is itself a query value — a redirect target or a logged request line.
        _c(r"(?:[?&]|%3F|%26)(?:key|token)(?:=|%3D)([A-Za-z0-9_-]{16,})"),
    ),
    # Round 17 L10: a Slack incoming-webhook URL is its own credential, with no keyword.
    SecretPattern(
        "slack-webhook",
        "Slack incoming-webhook URL",
        _c(
            r"(hooks\.slack\.com/(?:services|workflows|triggers)/[A-Za-z0-9_/-]{20,200})",
            case_sensitive=True,
        ),
    ),
    # Round 17 L10: an Azure storage or Service Bus connection string carries its key as a
    # `;`-separated field no assignment pattern reads (`AccountKey=` has no keyword).
    SecretPattern(
        "azure-connection-key",
        "Key in an Azure connection string",
        _c(r"(?:AccountKey|SharedAccessKey)=([A-Za-z0-9+/=]{20,200})"),
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
        _c(r"(?:" + _KEYWORDS + r")\s*:\s*[|>][+-]?\s*\n[ \t]+(\S[^\n]{7,})"),
    ),
    # Round 17 E4: a credential passed as a separate command-line argument rather than
    # glued on with `=` — `--password Ab3x…`, `docker login -p …`, `mysql -p…` — which the
    # assignment patterns below never see. Each scan-ahead is bounded like curl's above.
    SecretPattern(
        "cli-flag-credential",
        "Credential passed as a command-line flag",
        _c(r"(?<![A-Za-z0-9-])--(?:" + _KEYWORDS + r")\s+([^\s\"'`=-][^\s\"'`]{7,})"),
    ),
    SecretPattern(
        "cli-login-password",
        "Password passed to a login command",
        _c(
            r"\b(?:docker|podman|nerdctl|helm\s+registry)\s+login\b[^\n]{0,200}?\s-p"
            r"(?:=|\s+)([^\s\"'`-][^\s\"'`]{7,})"
            r"|\bmysql(?:dump|admin)?\b[^\n]{0,200}?\s-p([^\s\"'`]{8,})"
        ),
    ),
    # Round 17 E4: a session cookie in a `curl -v` transcript is as good as the password
    # that created it. Only the first cookie in the header is read, which is the session
    # cookie for every service the quests talk to.
    SecretPattern(
        "cookie-header",
        "Session cookie in a Cookie or Set-Cookie header",
        _c(r"\b(?:set-)?cookie\s*:\s*[^\s=;]{1,64}=([^\s;\"']{12,})"),
    ),
    # Quoted assignment first, so a quoted value keeps its exact span even when it contains
    # characters the unquoted form would stop at. Round 17 E4: each quote type now has its
    # own branch, so a double-quoted value may contain an apostrophe (`"it's-…"`) and either
    # may contain an escaped quote (`"abc\"…"`). The 1024 bound keeps an unclosed quote on a
    # long line from being re-read from every keyword on it.
    SecretPattern(
        "secret-assignment",
        "Secret-like assignment",
        _c(
            r"[\"']?(?:"
            + _KEYWORDS
            + r")"
            + _NAME_TAIL
            + r"[\"']?"
            + _SEPARATOR
            + r"(?:\"(?P<value>(?:[^\"\\\n]|\\.){8,1024})\""
            + r"|'(?P<value2>(?:[^'\\\n]|\\.){8,1024})')"
        ),
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
    SecretPattern(
        "secret-assignment-unquoted",
        "Secret-like assignment",
        _c(
            r"[\"']?(?:"
            + _KEYWORDS
            + r")"
            + _NAME_TAIL
            + r"[\"']?"
            + _SEPARATOR
            + r"(?P<value>\[[^\]\n\s,\"']{3,80}\][^\s\"',;}`\]]*|[^\s\"',;}`\]]{8,})"
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
    if lowered.startswith(("$(", "{{")) or re.fullmatch(r"<[^<>]*>", lowered):
        return True
    # Round 16 E5: this used to be `lowered.startswith("${")`, so anything shaped like a
    # shell or compose expansion was exempted regardless of what followed — including a
    # `${VAR:-default}`/`${VAR-default}` *default*, which is a real value the moment the
    # variable is unset (`DB_PASSWORD=${DB_PASSWORD:-Sup3rS3cretValue9}`)  # secret-scan: allow
    # is the ordinary docker-compose/.env shape. Only a value that is entirely
    # `${NAME}`, optionally with a `:?message` clause (an error string shown when unset,
    # never a default value), refers to the environment rather than holding one. The
    # unquoted pattern's value class excludes `}`, so a bare wrap is captured with its
    # closing brace already stripped off by the regex — the trailing `\}?` here accounts
    # for that, and for the quoted pattern, which does capture the closing brace.
    if re.fullmatch(r"\$\{[a-z_][a-z0-9_]*(?::\?[^{}]*)?\}?", lowered):
        return True
    # A value that IS entirely one of the real template shapes below — a Jinja expression, a
    # bare `{name}` format-string/f-string placeholder (this module's own test fixtures are
    # full of exactly that shape, reading their own source: `f'token = "{GITHUB}"'`), or a
    # parenthetical annotation like `(redacted)` or `(see vault)` — is a placeholder.
    #
    # Round 17 E3: the last two were matched against the lowered value, so a value that
    # merely *wrapped* a real password in braces or parens (`{Sup3rS3cretValue9}`,
    # `(Ab3dEfGh12xy)`) read as a template. A format placeholder is a name — letters and
    # underscores — and an annotation is words, so neither shape admits a digit now.
    stripped = value.strip()
    if (
        re.fullmatch(r"\{\{\s*[^{}]*\s*\}\}", lowered)
        or re.fullmatch(r"\{[A-Za-z_]+\}", stripped)
        or re.fullmatch(r"\([a-z][a-z _-]*\)", stripped)
    ):
        return True
    # Round 17 E4: a bare shell variable (`--token $GITHUB_TOKEN`) refers to the
    # environment exactly as `${GITHUB_TOKEN}` does.
    if re.fullmatch(r"\$[A-Za-z_][A-Za-z0-9_]*", stripped):
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
    # Round 17 E3: that shape was still matched against the lowered value with the closing
    # paren optional, so `Pa55word(Winter2026!`, `Hunter2[prod-2026` and
    # `Sup3rS3cretValue9)` all read as code. Code in the files this reads is lower-case
    # snake_case, so the identifier is matched as written, not lowered; an unclosed paren
    # or bracket may be followed only by more identifiers and openers, never by anything
    # else (the value class stopped at the quote of an argument: `payload.get("token")`,
    # `load_api_key(config["provider"]`, `dict[str, str]`); and a `{NAME}` fixture is
    # letters and underscores only.
    if allow_call_expression and re.fullmatch(
        r"[a-z_][a-z0-9_.]*"
        r"(?:\([^()]*\)|\[[^\[\]]*\]|(?:[(\[][a-z_][a-z0-9_.]*)+[(\[]?|[(\[]|[)\]])"
        r"|\{[A-Za-z_]+\}?",
        stripped,
    ):
        return True
    # A short dotted identifier chain is an attribute path, not a secret — but only when it
    # actually starts from one of the names this codebase's own source uses for the object
    # being accessed (round 16 E7). Before this, ANY short dotted chain qualified, so a
    # dotted passphrase (`correct.horse.battery.staple`, `Welcome.To.Acme`) read exactly like
    # one and was never reported. The length bounds still matter too: without them this also
    # matches a JWT, whose three base64 segments are exactly a long dotted chain.
    if (
        len(lowered) <= 40
        and re.fullmatch(r"[a-z_][a-z0-9_]*(?:\.[a-z_][a-z0-9_]*)+", lowered)
        and all(len(segment) <= 20 for segment in lowered.split("."))
        and lowered.split(".", 1)[0] in _CODE_ATTRIBUTE_ROOTS
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


def _value(match: re.Match[str]) -> tuple[str, int, int]:
    """The sensitive span of `match` and where it is.

    A pattern names it `value` (or `value2`, for its other quote branch) when it has other
    groups; otherwise it is the first group that took part, or the whole match.
    """
    for name in ("value", "value2"):
        if name in match.re.groupindex and match.group(name) is not None:
            return match.group(name), match.start(name), match.end(name)
    for index in range(1, match.re.groups + 1):
        if match.group(index) is not None:
            return match.group(index), match.start(index), match.end(index)
    return match.group(0), match.start(), match.end()


def _name_is_excused(match: re.Match[str]) -> bool:
    """The assignment's name says its value describes a credential rather than being one.

    `password_file`, `tokenExpiresAt`, `tokenizer`: the tail after the credential word is
    split on underscores, hyphens and camel-case humps, and any excusing word excuses it.
    """
    if "tail" not in match.re.groupindex or not match.group("tail"):
        return False
    words = re.findall(r"[A-Z]?[a-z]+|[A-Z]+(?![a-z])|\d+", match.group("tail"))
    return any(word.lower() in _EXCUSING_TAIL_WORDS for word in words)


def _is_finding(pattern: SecretPattern, match: re.Match[str], captured: str) -> bool:
    if _name_is_excused(match):
        return False
    return not _is_placeholder(
        captured, allow_call_expression=pattern.id == "secret-assignment-unquoted"
    )


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
        batch: list[tuple[int, int, SecretMatch]] = []
        claim_index = 0
        for match in pattern.regex.finditer(text):
            captured, start, end = _value(match)
            if not _is_finding(pattern, match, captured):
                continue
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
                        fingerprint=hashlib.sha256(captured.encode()).hexdigest()[:16],
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
            captured, start, end = _value(match)
            if _is_finding(pattern, match, captured):
                spans.append((start, end))
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
