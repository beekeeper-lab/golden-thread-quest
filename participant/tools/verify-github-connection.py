#!/usr/bin/env python3
"""Checks the GitHub connection on this computer using read operations only.

Part of the github-verify-connection quest. It uses the GitHub CLI's existing sign-in (`gh`) and
reports who the connection acts as, the scopes it has, the repositories it can reach and one safe
read, then compares all of that with participant/context/github/expected-access.yaml, so a lost
repository or a changed scope is reported as a FAIL rather than looking like an empty answer.

    .venv/bin/python participant/tools/verify-github-connection.py
    .venv/bin/python participant/tools/verify-github-connection.py --denied OWNER/REPO

The second form tries to read a repository the connection should not reach and reports it as
inaccessible, next to a list that is reachable but empty, so the two can't be confused.

Safety:
- Every request goes through one function that always sends GET, so the check can't change
  anything on GitHub; the output ends with every request it made.
- The token is never asked for or printed. The check doesn't run "gh auth token" or "gh auth
  status", turns off gh's debug output, and blanks anything shaped like a GitHub token. Nothing is
  printed until the whole output has been scanned with the quest app's own credential patterns;
  if the scan finds anything, the whole output is withheld, and an error message is checked the
  same way, so a credential can't reach the screen or a log.
- A repository name must be OWNER/REPO, and "." or ".." is refused, so a name can't reach another
  part of the API.
- Repositories owned by anyone other than the signed-in account are only counted, never named.
- Only names, visibility and permissions are printed; no description, issue or comment text, which
  is third-party input.

Exit codes: 0 every check passed, 1 a check failed, 2 the check couldn't run.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

VERSION = "1.0.0"
ROOT = Path(__file__).resolve().parents[2]
EXPECTED = ROOT / "participant/context/github/expected-access.yaml"

# What each classic OAuth scope allows, in plain words, and whether it allows a change.
SCOPE_MEANING = {
    "repo": ("read and write every repository the account can reach, private ones included", True),
    "public_repo": ("read and write public repositories", True),
    "workflow": ("change GitHub Actions workflow files", True),
    "gist": ("create and change gists", True),
    "read:org": ("read organization membership and teams", False),
    "read:user": ("read the account's profile", False),
}

# Anything shaped like a GitHub token is blanked before it is printed, wherever it appears, even
# run together with other text (so no word-boundary rule): blanking a little too much is the safe
# side. The quest app's scan doesn't recognise every GitHub token shape, so this blanking matters.
TOKEN_SHAPE = re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}")

REQUESTS: list[str] = []  # every request made, in order
OUTPUT: list[str] = []  # every line printed, for the credential scan at the end


class CannotRun(Exception):
    """The check couldn't run, so nothing was checked (exit 2). fixed=True marks a message made of
    the script's own words only, with no value from the command line, a file or gh, so it can be
    printed even when the credential scan isn't available."""

    def __init__(self, message: str, *, fixed: bool = False) -> None:
        super().__init__(message)
        self.fixed = fixed


def say(text: str = "") -> None:
    """Holds text for printing, one held entry per line. Nothing is printed until the whole output
    has been scanned for credentials (see flush), so a credential can't reach the screen or a log
    first."""
    OUTPUT.extend(TOKEN_SHAPE.sub("[blanked]", text).split("\n"))


def scanner():
    """The quest app's own credential scan, or None when it isn't available."""
    sys.path.insert(0, str(ROOT))
    try:
        from quest_app.secret_patterns import scan_text
    except Exception:  # missing, or written for a newer Python than the one running this
        return None
    return scan_text


def flush() -> int:
    """Scans every held line with the quest app's own credential patterns, then prints them. If the
    scan finds anything, none of the held output is printed: a credential can span several lines,
    so withholding only the flagged line could still let part of it through. Returns the number of
    findings."""
    scan_text = scanner()
    if scan_text is None:
        OUTPUT.clear()
        raise CannotRun("the quest app's credential patterns aren't available; run this with .venv/bin/python", fixed=True)
    findings = scan_text("\n".join(OUTPUT))
    if findings:
        print(f"[output withheld: {len(OUTPUT)} lines, because the scan found something that looks like a credential]")
        for finding in findings:
            print(f"      line {finding.line}: [{finding.pattern_id}] {finding.description}")
    else:
        for line in OUTPUT:
            print(line)
    OUTPUT.clear()
    return len(findings)


def safe_message(error: CannotRun) -> str:
    """An error message as it may be printed: blanked like the output, and withheld entirely if the
    scan finds a credential in it or can't run, since it can carry a value given on the command
    line or text from gh. The script's own fixed messages are always printed."""
    message = TOKEN_SHAPE.sub("[blanked]", str(error))
    if error.fixed:
        return message
    scan_text = scanner()
    if scan_text is None or scan_text(message):
        return "details withheld, because they may contain a credential"
    return message


def full_name(name: str) -> bool:
    """Whether name is an OWNER/REPO pair; "." and ".." are refused so a name can't step out of
    the repos/ path to another part of the API."""
    parts = name.split("/")
    return len(parts) == 2 and all(re.fullmatch(r"[A-Za-z0-9_.-]+", p) and p not in (".", "..") for p in parts)


def gh_get(path: str, *, paginate: bool = False, jq: str | None = None) -> tuple[int, dict[str, str], str]:
    """Reads one GitHub API path with GET and returns (HTTP status, headers of the first page with
    lower-case names, body). The only way this script talks to GitHub; it never sends any other
    method."""
    args = ["gh", "api", "--method", "GET", "--include"]
    if paginate:
        args.append("--paginate")
    if jq is not None:
        args += ["--jq", jq]
    args.append(path)
    REQUESTS.append(f"GET {path}")
    env = {k: v for k, v in os.environ.items() if k not in ("GH_DEBUG", "DEBUG")}
    try:
        result = subprocess.run(args, capture_output=True, text=True, env=env, timeout=60)
    except FileNotFoundError as error:
        raise CannotRun("the GitHub CLI (gh) isn't installed", fixed=True) from error
    except subprocess.TimeoutExpired as error:
        raise CannotRun(f"GitHub didn't answer within 60 seconds ({path})") from error
    # With --include, each page is a status line and headers, a blank line, then the body (or the
    # --jq output).
    pages = re.split(r"^(?=HTTP/\S+ \d{3})", result.stdout.replace("\r\n", "\n"), flags=re.MULTILINE)
    pages = [page for page in pages if page.startswith("HTTP/")]
    if not pages:
        message = result.stderr.strip().splitlines()[-1:] or ["no answer"]
        raise CannotRun(f"gh couldn't read {path}: {TOKEN_SHAPE.sub('[blanked]', message[0])}")
    if len(pages) > 1:
        REQUESTS[-1] += f" ({len(pages)} pages, one GET each)"
    statuses = [int(page.split(None, 2)[1]) for page in pages]
    # A page that didn't succeed decides the status, so a list that failed part-way is never read
    # as a complete one.
    deciding = next((index for index, code in enumerate(statuses) if code != 200), 0)
    status = statuses[deciding]
    if status == 200 and result.returncode != 0:
        message = result.stderr.strip().splitlines()[-1:] or ["no message"]
        raise CannotRun(f"gh failed reading {path}: {TOKEN_SHAPE.sub('[blanked]', message[0])}")
    first_head = pages[0].partition("\n\n")[0].splitlines()
    headers = {}
    for line in first_head[1:]:
        name, sep, value = line.partition(":")
        if sep:
            headers[name.strip().lower()] = value.strip()
    deciding_head = {}
    for line in pages[deciding].partition("\n\n")[0].splitlines()[1:]:
        name, sep, value = line.partition(":")
        if sep:
            deciding_head[name.strip().lower()] = value.strip()
    # GitHub slows clients down with 403 or 429: either the hourly limit is used up, or a shorter
    # "secondary" limit applies, which usually comes with Retry-After and always says "rate limit"
    # in its message. Neither says anything about access.
    deciding_body = pages[deciding].partition("\n\n")[2].lower()
    if status in (403, 429) and (deciding_head.get("x-ratelimit-remaining") == "0" or "retry-after" in deciding_head
                                 or "rate limit" in deciding_body):
        raise CannotRun("GitHub is limiting how fast this connection may ask; try again later", fixed=True)
    body = "".join(page.partition("\n\n")[2] for page in pages)
    return status, headers, body


def parse_json(body: str, what: str):
    """Reads GitHub's answer as JSON; an answer that isn't means the check can't run."""
    try:
        return json.loads(body)
    except ValueError as error:
        raise CannotRun(f"GitHub's answer to {what} wasn't readable") from error


def load_expected(path: Path) -> dict:
    try:
        import yaml
    except ImportError as error:
        raise CannotRun("PyYAML isn't installed; run this with the repository's .venv/bin/python", fixed=True) from error
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise CannotRun(f"couldn't read {path}") from error
    except (yaml.YAMLError, UnicodeDecodeError) as error:
        # The parser's own message can quote the file, so it is left out.
        raise CannotRun(f"{path} isn't valid YAML text") from error
    if not isinstance(data, dict):
        raise CannotRun(f"{path} isn't a YAML mapping")
    login = data.get("login")
    if not isinstance(login, str) or not re.fullmatch(r"[A-Za-z0-9-]+", login):
        raise CannotRun(f"login in {path} must be a GitHub account name")
    scopes = data.get("scopes")
    if not isinstance(scopes, list) or not all(isinstance(s, str) and s for s in scopes):
        raise CannotRun(f"scopes in {path} must be a list of scope names")
    repositories = data.get("repositories")
    if not isinstance(repositories, list) or not repositories or not all(isinstance(r, str) and full_name(r) for r in repositories):
        raise CannotRun(f"repositories in {path} must be a list of at least one OWNER/REPO name")
    if not full_name(str(data.get("safe_read", ""))):
        raise CannotRun(f"safe_read in {path} isn't an OWNER/REPO name")
    empty = str(data.get("empty_read", ""))
    if not (empty.startswith("repos/") and empty.count("/") == 3 and full_name("/".join(empty.split("/")[1:3]))
            and re.fullmatch(r"[a-z_]+", empty.split("/")[3])):
        raise CannotRun(f"empty_read in {path} isn't a repos/OWNER/REPO/LIST path")
    return data


def finish(results: list[tuple[bool, str]]) -> int:
    """Prints the request log and the credential scan, then the result."""
    say()
    say(f"Requests made ({len(REQUESTS)}), every one a read:")
    for request in REQUESTS:
        say(f"  {request}")
    writes = [r for r in REQUESTS if not r.startswith("GET ")]
    say(f"Only read operations were issued: {'yes' if not writes else 'NO'}; no write was attempted.")
    results.append((not writes, "only read operations were issued"))
    say()
    for ok, text in results:
        say(f"{'PASS' if ok else 'FAIL'}  {text}")
    # The credential scan covers every line above, using the quest app's own patterns.
    scanned = len(OUTPUT)
    findings = flush()
    clean = findings == 0
    print(f"{'PASS' if clean else 'FAIL'}  no credential in this output (scanned {scanned} lines, {findings} finding(s))")
    passed = clean and all(ok for ok, _ in results)
    print(f"RESULT: {'PASSED' if passed else 'FAILED'}")
    return 0 if passed else 1


def verify(expected: dict) -> int:
    results: list[tuple[bool, str]] = []

    # 1. Identity and scopes, read from the connection.
    status, headers, body = gh_get("user")
    if status != 200:
        raise CannotRun(f"GitHub answered {status} when asked who this connection is; is gh signed in?")
    answer = parse_json(body, "who this connection is")
    login = answer.get("login", "") if isinstance(answer, dict) else ""
    say(f"Identity (read from the connection): {login}")
    results.append((login == expected.get("login"), f"the connection acts as {expected.get('login')}"))

    scopes = sorted(s.strip() for s in headers.get("x-oauth-scopes", "").split(",") if s.strip())
    say()
    say(f"Scopes reported by GitHub: {', '.join(scopes) if scopes else '(none reported)'}")
    for scope in scopes:
        meaning, writes = SCOPE_MEANING.get(scope, ("not described here", False))
        say(f"  {scope:<10} {meaning}{'  [allows changes]' if writes else ''}")
    want = sorted(expected.get("scopes", []))
    added, removed = sorted(set(scopes) - set(want)), sorted(set(want) - set(scopes))
    change = "; ".join(p for p in [f"added: {', '.join(added)}" if added else "", f"removed: {', '.join(removed)}" if removed else ""] if p)
    results.append((not added and not removed, f"the scopes are the expected ones{f' ({change})' if change else ''}"))

    # 2. Reachable repositories: the account's own by full name, everyone else's only counted.
    status, _, body = gh_get(
        "user/repos?per_page=100&affiliation=owner,collaborator,organization_member",
        paginate=True,
        jq='.[] | [.full_name, .owner.login, .owner.type, .visibility] | @tsv',
    )
    if status != 200:
        raise CannotRun(f"GitHub answered {status} when asked for the reachable repositories")
    rows = [line.split("\t") for line in body.splitlines() if line.count("\t") == 3]
    own = sorted(name for name, owner, _, _ in rows if owner == login)
    others = [(owner, kind, visibility) for _, owner, kind, visibility in rows if owner != login]
    say()
    say(f"Repositories this connection can reach: {len(rows)}")
    say(f"  Owned by {login} ({len(own)}), by full name:")
    for name in own:
        say(f"    {name}")
    by_owner = Counter(owner for owner, _, _ in others)
    for kind in ("Organization", "User"):
        owners = sorted({owner for owner, k, _ in others if k == kind})
        if not owners:
            continue
        label = "organization" if kind == "Organization" else "other account"
        say(f"  Owned by {len(owners)} {label}{'s' if len(owners) != 1 else ''} (counted only; names withheld because some are private):")
        for index, owner in enumerate(owners, start=1):
            seen = Counter(v for o, _, v in others if o == owner)
            detail = ", ".join(f"{count} {visibility}" for visibility, count in sorted(seen.items()))
            say(f"    {label} {index}: {by_owner[owner]} repositories ({detail})")
    missing = sorted(set(expected.get("repositories", [])) - set(own))
    results.append((not missing, "every expected repository is reachable" + (f" (LOST ACCESS: {', '.join(missing)})" if missing else "")))

    # 3. One safe read: the repository's details, which change nothing.
    target = expected.get("safe_read", "")
    status, _, body = gh_get(f"repos/{target}")
    say()
    if status == 200:
        repo = parse_json(body, f"repos/{target}")
        if not isinstance(repo, dict):
            raise CannotRun(f"GitHub's answer to repos/{target} wasn't a repository")
        owner = (repo.get("owner") or {}).get("login") if isinstance(repo.get("owner"), dict) else None
        if owner != login:
            # GitHub follows a moved repository to its new place; if that now belongs to someone
            # else, its name stays withheld like every other owner's.
            say(f"Safe read: repos/{target} answered 200, but for a repository owned by another account (name withheld)")
            results.append((False, f"the safe read of {target} succeeded (it now belongs to another account)"))
            return finish(results)
        rights = repo.get("permissions", {})
        granted = ", ".join(k for k in ("admin", "maintain", "push", "triage", "pull") if rights.get(k))
        say(f"Safe read: repos/{target} answered 200")
        say(f"  full name {repo.get('full_name')}; visibility {repo.get('visibility')}; default branch {repo.get('default_branch')}")
        say(f"  this connection's rights here: {granted or 'none reported'} (the check uses none of them to change anything)")
    else:
        say(f"Safe read: repos/{target} answered {status}")
    results.append((status == 200, f"the safe read of {target} succeeded"))
    return finish(results)


def denied(expected: dict, target: str) -> int:
    results: list[tuple[bool, str]] = []
    if not full_name(target):
        raise CannotRun(f'"{target}" isn\'t an OWNER/REPO name')
    status, _, _ = gh_get(f"repos/{target}")
    if status not in (200, 403, 404):
        raise CannotRun(f"GitHub answered {status} for repos/{target}, which says nothing about whether it can be read")
    say(f"Read of a repository outside this connection's reach: repos/{target}")
    if status in (403, 404):
        say(f"  INACCESSIBLE: GitHub answered {status}. GitHub gives the same answer for a repository that")
        say("  doesn't exist and for a private one this connection may not see, so the check can't tell")
        say("  which; either way nothing can be read from it, and it is reported as inaccessible, not as empty.")
    else:
        say(f"  GitHub answered {status}: the repository is readable, so it is NOT outside this connection's reach.")
    results.append((status in (403, 404), f"{target} is reported as inaccessible"))

    empty = expected.get("empty_read", "")
    status, _, body = gh_get(empty)
    items = parse_json(body, empty) if status == 200 else None
    if status == 200 and not isinstance(items, list):
        raise CannotRun(f"GitHub's answer to {empty} wasn't a list")
    count = len(items) if isinstance(items, list) else None
    say()
    say(f"For comparison, a list this connection can read: {empty}")
    if status == 200 and count == 0:
        say("  REACHABLE, EMPTY: GitHub answered 200 with 0 items. This is what empty looks like.")
    else:
        say(f"  GitHub answered {status}{f' with {count} items' if count is not None else ''}.")
    results.append((status == 200 and count == 0, "an empty list is reported as reachable and empty, unlike the inaccessible repository"))
    return finish(results)


class Parser(argparse.ArgumentParser):
    """Command-line parsing that never prints what was typed: argparse's own error message repeats
    the arguments, which could include a credential, so a mistake becomes a fixed message."""

    def error(self, message: str):  # type: ignore[override]
        raise CannotRun("the command line wasn't understood; run with --help to see the options", fixed=True)


def main() -> int:
    parser = Parser(description=__doc__.splitlines()[0])
    parser.add_argument("--denied", metavar="OWNER/REPO", help="try to read a repository outside the connection's reach")
    parser.add_argument("--expected", metavar="FILE", type=Path, default=EXPECTED,
                        help="the expected-access file to compare with (default: participant/context/github/expected-access.yaml)")
    now = dt.datetime.now().astimezone()
    say(f"verify-github-connection {VERSION}, run {now:%m-%d-%Y %I:%M %p}")
    try:
        args = parser.parse_args()
        expected = load_expected(args.expected)
        return denied(expected, args.denied) if args.denied is not None else verify(expected)
    except CannotRun as error:
        try:
            flush()  # what was found before the problem, scanned like everything else
        except CannotRun:
            pass
        sys.stdout.flush()  # so the held lines come before the error in a combined log
        print(f"verify-github-connection {VERSION}: couldn't run: {safe_message(error)}", file=sys.stderr)
        return 2
    except Exception as error:  # anything unforeseen: no traceback, which could quote a value
        OUTPUT.clear()
        print(f"verify-github-connection {VERSION}: couldn't run: an unexpected {type(error).__name__}; details withheld",
              file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
