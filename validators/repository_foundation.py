"""Checks the repository foundations every later quest depends on.

Deliberately not a file-existence checker. `docs/VALIDATOR-CONTRACT.md` warns against checks
that "merely restate file existence when the quest is about behavior", so each check below
looks at what the file *says* — that the ignore rules actually cover the categories that
matter, that the evidence package answers the questions a reviewer will ask.
"""

from __future__ import annotations

from fnmatch import fnmatchcase
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from quest_app.validator_runner import ValidatorOutput, Workspace

from quest_app.validator_runner import Check

# The categories a participant's ignore rules must cover, each as names a rule for that
# category would ignore. Named by example rather than by exact pattern, because there are
# many correct spellings of each: `*.pem`, `secrets/` and `**/credentials.json` all cover
# credentials. A rule covers a category when it would ignore one of these names.
#
# These were substrings, so a rule was read as a bag of letters: `mysecretfolder/` covered
# "credentials" because it contains "secret", and `rebuild.log` covered "generated output"
# because it contains "build". Neither ignores anything of the kind.
IGNORE_CATEGORIES = {
    "generated output": ("generated", "dist", "build"),
    "local runtime data": ("local-data", ".cache", "tmp"),
    "environment files": (".env", ".env.local"),
    "credentials": (
        "server.pem",
        "server.key",
        "credentials",
        "credentials.json",
        "secret",
        "secrets",
    ),
}

PROOF_QUESTIONS = {
    "what was built": ("what was built", "what was created", "what exists"),
    "where the artifacts are": ("where", "artifact", "location", "path"),
    "how to reproduce": ("reproduce", "how to run", "steps"),
    "what was validated": ("test", "validat", "check"),
    "remaining limitations": ("limitation", "remaining", "does not", "known issue"),
}


def run(workspace: Workspace, output: ValidatorOutput) -> None:
    """Entry point named by `validators/registry.yaml`."""
    _check_ignore_rules(workspace, output)
    _check_evidence_package(workspace, output)
    _check_no_secrets_in_evidence(workspace, output)


def _ignore_patterns(text: str) -> list[str]:
    """The lines of a .gitignore that actually ignore something.

    A comment is not a rule. Read as a bag of words, a file whose only mention of
    credentials is a note to the reader covers every category and ignores nothing, and the
    check cannot tell that file from one that works. A negation un-ignores, so it is not
    coverage either.
    """
    patterns = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith(("#", "!")):
            continue
        patterns.append(line.lower())
    return patterns


def _ignores(pattern: str, name: str) -> bool:
    """Whether a .gitignore rule would ignore a file or directory called `name`.

    Git matches a rule against the final component of a path (or, with a slash inside, the
    whole path), so the rule's last real segment is what names the thing ignored:
    `/generated/`, `**/secrets/` and `dist/**` name `generated`, `secrets` and `dist`, while
    `build/output` ignores only `output` inside `build`. The segment is then matched as the
    glob it is. `**` alone ignores everything, and so covers every category.
    """
    segments = [part for part in pattern.strip("/").split("/") if part and part != "**"]
    if not segments:
        return pattern.strip("/") == "**"
    return fnmatchcase(name, segments[-1])


def _check_ignore_rules(workspace: Workspace, output: ValidatorOutput) -> None:
    candidates = [".gitignore"]
    present = False
    patterns: list[str] = []
    for candidate in candidates:
        if workspace.exists(candidate):
            present = True
            patterns.extend(_ignore_patterns(workspace.read_text(candidate)))
    if not patterns:
        output.add(
            Check(
                id="ignore-rules-present",
                outcome="fail",
                severity="high",
                summary="No ignore rules were found.",
                evidence=(
                    "A .gitignore is present, but every line in it is blank, a comment or a "
                    "negation, so it ignores nothing."
                    if present
                    else "Neither the participant directory nor the repository root has a "
                    ".gitignore."
                ),
                suggested_action=(
                    "Add a .gitignore covering generated output, local data, environment files and "
                    "credentials."
                ),
            )
        )
        return

    missing = [
        category
        for category, names in sorted(IGNORE_CATEGORIES.items())
        if not any(_ignores(pattern, name) for pattern in patterns for name in names)
    ]
    if missing:
        output.add(
            Check(
                id="ignore-rules-cover-categories",
                outcome="fail",
                severity="high",
                summary="The ignore rules do not cover every category that matters.",
                evidence=f"No rule appears to cover: {', '.join(missing)}.",
                suggested_action=(
                    "Add a rule for each. A missing credentials rule is the one that costs the "
                    "most."
                ),
            )
        )
    else:
        output.add(
            Check(
                id="ignore-rules-cover-categories",
                outcome="pass",
                summary=(
                    "Ignore rules cover generated output, local data, environment files and "
                    "credentials."
                ),
                evidence=f"All {len(IGNORE_CATEGORIES)} categories are represented.",
            )
        )


def _check_evidence_package(workspace: Workspace, output: ValidatorOutput) -> None:
    # The attempt being validated, not whichever PROOF.md in the participant tree was
    # written most recently. The older form judged another quest's blank template and
    # reported its path as this attempt's failing artifact.
    proofs = workspace.attempt_files("PROOF.md")
    if not proofs:
        output.add(
            Check(
                id="evidence-package-exists",
                outcome="inconclusive",
                summary="No evidence package was found to evaluate.",
                evidence="This attempt's evidence package contains no PROOF.md.",
                suggested_action="Start the quest to create an evidence package.",
            )
        )
        return

    newest = max(proofs, key=lambda path: path.stat().st_mtime)
    text = workspace.read_text(str(newest)).lower()
    unanswered = [
        question
        for question, markers in sorted(PROOF_QUESTIONS.items())
        if not any(marker in text for marker in markers)
    ]
    # A template that has been filled in has content under its headings, not just headings.
    substantive = len(
        [
            line
            for line in text.splitlines()
            if line.strip() and not line.strip().startswith(("#", "<!--"))
        ]
    )

    if unanswered:
        output.add(
            Check(
                id="proof-answers-reviewer-questions",
                outcome="fail",
                severity="medium",
                summary="The proof document does not answer every question a reviewer will ask.",
                evidence=f"Unanswered: {', '.join(unanswered)}.",
                suggested_action=(
                    "A reviewer should not have to hunt. Answer each heading in a sentence or two."
                ),
                artifact=workspace.relative(newest),
            )
        )
    elif substantive < 5:
        output.add(
            Check(
                id="proof-answers-reviewer-questions",
                outcome="warning",
                severity="low",
                summary="The proof document has every heading but very little content.",
                evidence=f"{substantive} non-heading line(s) of content.",
                suggested_action="Say what you actually did under each heading.",
                artifact=workspace.relative(newest),
            )
        )
    else:
        output.add(
            Check(
                id="proof-answers-reviewer-questions",
                outcome="pass",
                summary="The proof document answers the questions a reviewer will ask.",
                evidence=f"All {len(PROOF_QUESTIONS)} questions are addressed.",
                artifact=workspace.relative(newest),
            )
        )


def _check_no_secrets_in_evidence(workspace: Workspace, output: ValidatorOutput) -> None:
    from quest_app.secret_patterns import scan_text

    findings: list[str] = []
    truncated: list[str] = []
    # This attempt's evidence. A secret in another attempt's package is that attempt's
    # failure: `submit-for-review` scans whichever package is being submitted, so nothing
    # goes unscanned, and no attempt is blocked by a file it does not own.
    for path in workspace.attempt_files():
        if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".webp", ".pdf"}:
            continue
        text, was_truncated = workspace.read_text_bounded(str(path), limit=200_000)
        if was_truncated:
            # Round 13 E9: this used to read the whole file and quietly check only the
            # first 200,000 characters, so a secret past that point passed as clean. This
            # check cannot vouch for what it never read, so it reports that instead.
            truncated.append(workspace.relative(path))
        for match in scan_text(text):
            findings.append(f"{workspace.relative(path)}:{match.line} ({match.description})")

    if findings:
        output.add(
            Check(
                id="evidence-carries-no-secrets",
                outcome="fail",
                severity="blocking",
                summary="Something secret-like is in the evidence.",
                evidence="; ".join(findings[:5]),
                suggested_action=(
                    "Remove it and rotate the value. Evidence is committed and reviewed by other "
                    "people."
                ),
            )
        )
    elif truncated:
        output.add(
            Check(
                id="evidence-carries-no-secrets",
                outcome="inconclusive",
                severity="medium",
                summary="Part of the evidence is too large for this check to read in full.",
                evidence=(
                    "; ".join(truncated[:5]) + " exceeded the 200,000-character window this "
                    "check reads. Nothing was found in the part that was read."
                ),
                suggested_action=(
                    "This is a secondary check; submission's own secret scan still reads the "
                    "whole file. Trim the file if you want this check to cover it completely."
                ),
            )
        )
    else:
        output.add(
            Check(
                id="evidence-carries-no-secrets",
                outcome="pass",
                summary="No secret-like value was found in the evidence.",
                evidence="Pattern detection is a safety net, not a guarantee.",
            )
        )
