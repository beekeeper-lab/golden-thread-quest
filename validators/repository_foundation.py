"""Checks the repository foundations every later quest depends on.

Deliberately not a file-existence checker. `docs/VALIDATOR-CONTRACT.md` warns against checks
that "merely restate file existence when the quest is about behaviour", so each check below
looks at what the file *says* — that the ignore rules actually cover the categories that
matter, that the evidence package answers the questions a reviewer will ask.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from quest_app.validator_runner import ValidatorOutput, Workspace

from quest_app.validator_runner import Check

# The categories a participant's ignore rules must cover. Named by intent rather than by
# exact pattern, because there are many correct spellings of each.
IGNORE_CATEGORIES = {
    "generated output": ("generated", "dist", "build/"),
    "local runtime data": ("local-data", ".cache", "tmp/"),
    "environment files": (".env",),
    "credentials": ("*.pem", "*.key", "credentials", "secret"),
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


def _check_ignore_rules(workspace: Workspace, output: ValidatorOutput) -> None:
    candidates = [".gitignore"]
    contents = ""
    for candidate in candidates:
        if workspace.exists(candidate):
            contents += workspace.read_text(candidate).lower()
    if not contents:
        output.add(
            Check(
                id="ignore-rules-present",
                outcome="fail",
                severity="high",
                summary="No ignore rules were found.",
                evidence=(
                    "Neither the participant directory nor the repository root has a .gitignore."
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
        for category, markers in sorted(IGNORE_CATEGORIES.items())
        if not any(marker in contents for marker in markers)
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
    proofs = workspace.iter_files("participant/evidence", "PROOF.md")
    if not proofs:
        output.add(
            Check(
                id="evidence-package-exists",
                outcome="inconclusive",
                summary="No evidence package was found to evaluate.",
                evidence="participant/evidence contains no PROOF.md.",
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
    for path in workspace.iter_files("participant/evidence"):
        if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".webp", ".pdf"}:
            continue
        for match in scan_text(workspace.read_text(str(path), limit=200_000)):
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
    else:
        output.add(
            Check(
                id="evidence-carries-no-secrets",
                outcome="pass",
                summary="No secret-like value was found in the evidence.",
                evidence="Pattern detection is a safety net, not a guarantee.",
            )
        )
