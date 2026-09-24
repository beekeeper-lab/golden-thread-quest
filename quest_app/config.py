"""Where things are, decided once.

Every root is injected rather than derived at the point of use, which is what makes the
participant root movable (ADR-018) and the whole loader testable against `fixtures/`
without writing anywhere near a real participant's work.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Final
from urllib.parse import unquote

from quest_app.compat import Self

# The schema version this build understands. A document declaring a higher one is refused
# rather than partially interpreted.
SUPPORTED_SCHEMA_VERSION: Final = 1

APPLICATION_VERSION: Final = "0.1.0"

DEFAULT_SERVICE_HOST: Final = "127.0.0.1"
DEFAULT_SERVICE_PORT: Final = 8765


@dataclass(frozen=True, slots=True)
class AppConfig:
    repo_root: Path
    content_root: Path
    schemas_root: Path
    templates_root: Path
    assets_root: Path
    participant_root: Path
    generated_root: Path
    local_data_root: Path
    validators_root: Path
    service_host: str = DEFAULT_SERVICE_HOST
    service_port: int = DEFAULT_SERVICE_PORT

    @classmethod
    def for_repo(
        cls,
        repo_root: Path,
        *,
        participant_root: Path | None = None,
        generated_root: Path | None = None,
        local_data_root: Path | None = None,
        service_host: str | None = None,
        service_port: int | None = None,
    ) -> Self:
        root = repo_root.resolve()
        return cls(
            repo_root=root,
            content_root=root / "content",
            schemas_root=root / "schemas",
            templates_root=root / "templates",
            assets_root=root / "assets",
            participant_root=(participant_root or root / "participant").resolve(),
            generated_root=(generated_root or root / "generated").resolve(),
            local_data_root=(local_data_root or root / "local-data").resolve(),
            validators_root=root / "validators",
            service_host=service_host or DEFAULT_SERVICE_HOST,
            service_port=service_port if service_port is not None else DEFAULT_SERVICE_PORT,
        )

    @classmethod
    def from_environment(cls, repo_root: Path | None = None) -> Self:
        """Configuration as the CLI sees it. Only the documented variables are read."""
        root = repo_root or Path(__file__).resolve().parent.parent
        participant = os.environ.get("GTQ_PARTICIPANT_ROOT")
        port = os.environ.get("GTQ_SERVICE_PORT")
        return cls.for_repo(
            root,
            participant_root=Path(participant) if participant else None,
            service_host=os.environ.get("GTQ_SERVICE_HOST"),
            service_port=int(port) if port else None,
        )

    def relative(self, path: Path) -> str:
        """A short, non-absolute label for display. Never leaks a home directory.

        With a participant root outside the repository, falling straight back to the file
        name made every review problem report `source: "review.yaml"` with no way to tell
        which attempt it came from (Stage 2 audit M13). The participant root is therefore
        tried second, and labeled with the `participant/` prefix the schemas already use.
        """
        resolved = path.resolve()
        try:
            return str(resolved.relative_to(self.repo_root))
        except ValueError:
            pass
        try:
            return f"participant/{resolved.relative_to(self.participant_root).as_posix()}"
        except ValueError:
            return path.name

    def resolve_participant_path(self, declared: str) -> Path:
        """Turn a `participant/...` contract path into a real one, proven inside the root.

        The prefix is part of the published schemas and is not relaxed (ADR-018); only the
        base directory moves. Resolution follows symbolic links and then re-checks, so a
        link planted inside the participant tree cannot reach outside it.
        """
        prefix = "participant/"
        if not declared.startswith(prefix):
            raise ValueError(f"participant path must start with {prefix!r}, got {declared!r}")
        relative = PurePosixCheck(declared[len(prefix) :]).checked()
        candidate = (self.participant_root / relative).resolve()
        root = self.participant_root.resolve()
        if candidate != root and root not in candidate.parents:
            raise ValueError(f"{declared!r} resolves outside the participant root")
        return candidate

    def participant_write_path(self, declared: str) -> Path:
        """Where a `participant/...` contract path lies, for writing: no link resolved.

        `resolve_participant_path` follows links and then checks the result, which is right
        for reading and wrong for writing: it turns a link inside the tree into the place it
        leads, so the write never sees that there was a link at all. A writer needs the
        lexical path, which `safe_io.atomic_write` then walks one component at a time and
        refuses at the first link (round 12 E1). The same traversal checks apply.
        """
        prefix = "participant/"
        if not declared.startswith(prefix):
            raise ValueError(f"participant path must start with {prefix!r}, got {declared!r}")
        return self.participant_root / PurePosixCheck(declared[len(prefix) :]).checked()


@dataclass(frozen=True, slots=True)
class PurePosixCheck:
    """Rejects the path shapes that make traversal possible, before anything touches disk."""

    raw: str

    def checked(self) -> str:
        if not self.raw:
            raise ValueError("empty participant path")
        if self.raw.startswith("/"):
            raise ValueError("participant path must be relative")
        if "\x00" in self.raw:
            raise ValueError("participant path contains a null byte")
        # Percent-decode before checking. Nothing legitimate in a participant path is
        # percent-encoded, and `..%2f..%2f` is the form a traversal takes once a path has
        # been round-tripped through a URL — which it will be, the moment the local service
        # in Stage 4 starts handing route fragments around.
        decoded = unquote(self.raw)
        if decoded != self.raw and ("/" in decoded.replace(self.raw, "") or ".." in decoded):
            raise ValueError("participant path contains percent-encoded path characters")
        for candidate in (self.raw, decoded):
            if any(part == ".." for part in candidate.split("/")):
                raise ValueError("participant path contains a parent-directory segment")
        return self.raw
