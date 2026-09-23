"""The one shape every authoring and runtime problem takes.

`docs/VIEW-MODEL-CONTRACT.md` specifies a single error structure so the terminal, the
generated error page, and the machine-readable output all describe a problem the same way.
It also specifies what must never appear in one: absolute machine paths, stack traces,
secrets, or raw request data. `ContentProblem.public_message` is written on the assumption
that it will be rendered in a browser.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from quest_app.compat import Self, StrEnum
from quest_app.secret_patterns import redact_text

MAX_RECEIVED_SUMMARY = 120


class Severity(StrEnum):
    """Severities from `CLAUDE.md`. Only `error` and `blocking` stop a build."""

    BLOCKING = "blocking"
    ERROR = "error"
    WARNING = "warning"
    INFORMATION = "information"

    @property
    def stops_the_build(self) -> bool:
        return self in (Severity.BLOCKING, Severity.ERROR)


@dataclass(frozen=True, slots=True)
class ContentProblem:
    """One problem with one document.

    `source` is always relative to the repository root. Constructing one with an absolute
    path is a programming error, because the value reaches a browser.
    """

    code: str
    severity: Severity
    public_message: str
    source: str | None = None
    entity_id: str | None = None
    field_path: str | None = None
    line: int | None = None
    column: int | None = None
    expected: str | None = None
    received: str | None = None
    suggestion: str | None = None
    documentation: str | None = None

    def __post_init__(self) -> None:
        if self.source is not None and Path(self.source).is_absolute():
            raise ValueError(
                f"ContentProblem.source must be repository-relative, got {self.source!r}"
            )
        # `received` reaches a browser too, and the usual way an absolute path gets there is
        # `str(OSError)`, which embeds the filename (Stage 2 audit H5). Refusing it at
        # construction means the next person to write that cannot ship it. The first attempt
        # at this fix wrote `_looks_absolute` and never called it, so the guard that was
        # supposed to make the leak impossible was itself dead code.
        if self.received is not None and _looks_absolute(self.received):
            raise ValueError(
                f"ContentProblem.received must not contain an absolute path; got {self.received!r}"
            )

    @classmethod
    def build(cls, *, received: object = None, **kwargs: Any) -> Self:
        """Preferred constructor: summarizes and redacts `received` before it is stored."""
        return cls(received=summarize_received(received), **kwargs)

    @property
    def location(self) -> str:
        """`path:line:column: field` — as much as is known, in the usual order."""
        parts = [self.source or "<unknown>"]
        if self.line is not None:
            parts.append(str(self.line))
            if self.column is not None:
                parts.append(str(self.column))
        location = ":".join(parts)
        if self.field_path:
            location = f"{location}: {self.field_path}"
        return location

    def to_text(self) -> str:
        """The terminal form. One problem per line, then indented detail."""
        lines = [f"{self.location}: [{self.severity}] {self.public_message}"]
        for label, value in (
            ("expected", self.expected),
            ("received", self.received),
            ("suggestion", self.suggestion),
            ("documentation", self.documentation),
        ):
            if value:
                lines.append(f"    {label}: {value}")
        return "\n".join(lines)

    def to_dict(self) -> dict[str, object]:
        """The machine-readable form, with empty fields omitted so output stays diffable."""
        data: dict[str, object] = {
            "code": self.code,
            "severity": str(self.severity),
            "message": self.public_message,
        }
        for key in (
            "source",
            "entity_id",
            "field_path",
            "line",
            "column",
            "expected",
            "received",
            "suggestion",
            "documentation",
        ):
            value = getattr(self, key)
            if value is not None:
                data[key] = value
        return data


def _looks_absolute(text: str) -> bool:
    """Whether `text` contains something shaped like an absolute filesystem path."""
    return bool(re.search(r"(?:^|[\s'\"(])(?:/[^\s'\"]*/|[A-Za-z]:\\)", text))


def summarize_received(value: object) -> str | None:
    """A short, redacted rendering of what was actually found.

    An author needs to see enough to recognize their mistake. Nobody needs to see a whole
    document, and nothing needs to see a credential that ended up in content by accident.
    """
    if value is None:
        return None
    if isinstance(value, str):
        text = value
    elif isinstance(value, (list, tuple, set)):
        text = f"{type(value).__name__} of {len(value)} item(s)"
    elif isinstance(value, dict):
        keys = ", ".join(sorted(map(str, value))[:5])
        text = f"object with keys: {keys}" if keys else "empty object"
    else:
        text = repr(value)
    text = " ".join(text.split())
    redacted, _ = redact_text(text)
    if len(redacted) > MAX_RECEIVED_SUMMARY:
        redacted = redacted[: MAX_RECEIVED_SUMMARY - 1] + "…"
    return redacted


@dataclass(slots=True)
class ProblemReport:
    """Every problem found in one pass, kept in discovery order.

    Validation does not stop at the first error. `CONTENT-MODEL.md` requires an author to
    see everything wrong with their content, not the first thing.
    """

    problems: list[ContentProblem] = field(default_factory=list)

    def add(self, problem: ContentProblem) -> None:
        self.problems.append(problem)

    def extend(self, problems: list[ContentProblem]) -> None:
        self.problems.extend(problems)

    @property
    def errors(self) -> list[ContentProblem]:
        return [p for p in self.problems if p.severity.stops_the_build]

    @property
    def warnings(self) -> list[ContentProblem]:
        return [p for p in self.problems if p.severity is Severity.WARNING]

    @property
    def ok(self) -> bool:
        return not self.errors

    def sorted_problems(self) -> list[ContentProblem]:
        """Deterministic order for output that gets diffed: by file, then position, then code."""
        return sorted(
            self.problems,
            key=lambda p: (p.source or "", p.line or 0, p.column or 0, p.field_path or "", p.code),
        )

    def to_text(self) -> str:
        return "\n".join(p.to_text() for p in self.sorted_problems())

    def to_dict(self) -> dict[str, object]:
        return {
            "ok": self.ok,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "problems": [p.to_dict() for p in self.sorted_problems()],
        }


class ContentLoadError(RuntimeError):
    """Raised when a caller asks for content that failed validation."""

    def __init__(self, report: ProblemReport) -> None:
        super().__init__(f"{len(report.errors)} content error(s)")
        self.report = report


def filesystem_message(error: OSError) -> str:
    """What went wrong, named by operation rather than by path.

    `strerror` alone ("Permission denied") does not say what to fix; the filename would put
    an absolute path in front of a browser or into a terminal. This says both what failed
    and what to check.

    It lives here rather than in `serve.py` because both surfaces need it. The service
    caught `OSError` and said this; the CLI caught `StoreError` and `ValueError` only, so a
    participant directory it could not write printed a traceback with absolute paths in it.
    """
    reason = error.strerror or type(error).__name__
    return (
        f"The change could not be written to your participant directory: {reason}. "
        "Check that it exists and that you can write to it."
    )


def read_failure_message(error: OSError) -> str:
    """The same courtesy for a read, which is a different thing to go and look at.

    The read path reported its failures with the sentence above, so a page the service
    could not open told the participant their change could not be written — when nothing
    was being changed and the participant directory was not involved. They were sent to
    inspect the wrong tree.
    """
    reason = error.strerror or type(error).__name__
    return (
        f"That page could not be read from the generated site: {reason}. "
        "Run `quest-app build` to regenerate it."
    )
