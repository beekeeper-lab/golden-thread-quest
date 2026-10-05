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

APPLICATION_VERSION: Final = "0.2.4"

DEFAULT_SERVICE_HOST: Final = "127.0.0.1"
DEFAULT_SERVICE_PORT: Final = 8765

# The marker `quest_app.serve` substitutes the live, per-run request token into. Defined
# here rather than in `serve.py` so `quest_app.markdown_render` can neutralize any occurrence
# that sanitized, participant-authored content reproduces (round 15 E7) without importing
# the service module — `serve.py` already imports from here, and this way the builder does
# not have to import the service to know what to guard against.
REQUEST_TOKEN_PLACEHOLDER: Final = "__GTQ_REQUEST_TOKEN__"  # noqa: S105 - a marker, not a secret


class UnsafeParticipantRootError(RuntimeError):
    """The participant root is not safe to write participant state into.

    Two distinct reasons raise this:

    - The default `participant/` is a symbolic link, and nobody configured a root.
      `participant/` is a fixed name inside a clone, exactly like `generated` and
      `local-data` (ADR-043) — anyone can commit a link at that name. A participant who
      points `GTQ_PARTICIPANT_ROOT` or `--participant-root` somewhere themselves is trusted
      there (ADR-042: they chose it); nobody chose this one, so it is not trusted merely
      for being where the default happens to look (round 14 E6 amends ADR-043).
    - A configured root — default or explicit — is, is inside, or contains one of the
      repository's own program-owned folders (round 15 E13 amends ADR-042 again: "they
      chose it" stops being a reason to trust it once what they chose is content, schemas,
      templates, quest_app, validators, generated or local-data — no participant meant to
      write their state into the curriculum every other participant pulls).
    """


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
        default_participant_root = root / "participant"
        # Only the default is checked. An explicit `participant_root` is a participant's own
        # choice of where their work lives and stays trusted wherever it points (ADR-042);
        # the default is a fixed name inside the clone that nobody chose, so a committed link
        # at that name redirected every write below it (round 14 E6) exactly the way a
        # committed `generated -> ..` redirected a build before ADR-043 checked its own name.
        if participant_root is None and default_participant_root.is_symlink():
            raise UnsafeParticipantRootError(
                "Refusing to use participant/: it is a symbolic link, and no participant root "
                "was configured. Replace it with an ordinary directory, or set "
                "GTQ_PARTICIPANT_ROOT (or --participant-root) to where your work lives."
            )
        resolved_participant_root = (participant_root or default_participant_root).resolve()
        resolved_generated_root = _absolute(generated_root or root / "generated")
        resolved_local_data_root = _absolute(local_data_root or root / "local-data")
        _refuse_participant_root_inside_program_owned_folders(root, resolved_participant_root)
        return cls(
            repo_root=root,
            content_root=root / "content",
            schemas_root=root / "schemas",
            templates_root=root / "templates",
            assets_root=root / "assets",
            participant_root=resolved_participant_root,
            # Lexical, never resolved (ADR-043). Resolving turned a committed
            # `generated -> ..` into the repository's parent, which the build then renamed and
            # deleted, and turned a linked `local-data` into wherever it led, so the check
            # that refuses a link never saw one.
            generated_root=resolved_generated_root,
            local_data_root=resolved_local_data_root,
            validators_root=root / "validators",
            service_host=service_host or DEFAULT_SERVICE_HOST,
            service_port=service_port if service_port is not None else DEFAULT_SERVICE_PORT,
        )

    @classmethod
    def from_environment(cls, repo_root: Path | None = None) -> Self:
        """Configuration as the CLI sees it. Only the documented variables are read.

        `GTQ_GENERATED_ROOT` and `GTQ_LOCAL_DATA_ROOT` exist for the same reason
        `GTQ_PARTICIPANT_ROOT` does (ADR-018): a test that shells out to the CLI must be able
        to point every writable root away from the repository it is running from, not only
        the participant one.
        """
        root = repo_root or Path(__file__).resolve().parent.parent
        participant = os.environ.get("GTQ_PARTICIPANT_ROOT")
        generated = os.environ.get("GTQ_GENERATED_ROOT")
        local_data = os.environ.get("GTQ_LOCAL_DATA_ROOT")
        port = os.environ.get("GTQ_SERVICE_PORT")
        return cls.for_repo(
            root,
            participant_root=Path(participant) if participant else None,
            generated_root=Path(generated) if generated else None,
            local_data_root=Path(local_data) if local_data else None,
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


def _absolute(path: Path) -> Path:
    """`path` made absolute and normalized as text, with no link followed."""
    return Path(os.path.abspath(path))  # noqa: PTH100 - `resolve()` follows links


# The repository's own folders, none of them the participant's to write state into. Not
# `docs`, `fixtures`, `prototype`, `scripts`, `tests`, `tools` or `.git`: those are source
# too, but a participant root landing there is a much odder mistake than the one round 15
# E13 actually found (a path meant for one of these), and refusing more than the report
# asked for risks a false refusal `refuse_unsafe_output_root` (`build.py`) does not carry.
_PROGRAM_OWNED_FOLDER_NAMES = (
    "content",
    "schemas",
    "templates",
    "assets",
    "validators",
    "quest_app",
    "generated",
    "local-data",
)


def _refuse_participant_root_inside_program_owned_folders(
    repo_root: Path, participant_root: Path
) -> None:
    """Round 15 E13: `GTQ_PARTICIPANT_ROOT=./content` was accepted with 0 warnings, and
    every write a participant makes — `progress.yaml`, evidence, `ACTIVITY.md` — landed
    inside authored curriculum content instead. ADR-042 trusts an explicitly configured
    root "because the participant chose it"; that reasoning does not extend to a folder the
    participant does not own regardless of who pointed at it.

    Checked against these folders' fixed, conventional names, lexically — not against
    whatever `GTQ_GENERATED_ROOT`/`GTQ_LOCAL_DATA_ROOT` happen to be set to for this run
    (`refuse_unsafe_output_root` in `build.py` already checks those against the participant
    root, at build time), and not through a symbolic link at one of these names: a link at
    `generated` or `local-data` pointing somewhere unrelated is `refuse_unsafe_output_root`'s
    finding to make, not this one's to chase and misreport as the participant root's fault.
    `participant_root` is resolved already (`AppConfig.for_repo` resolves it), so a
    participant root that is itself a link to one of these folders is still caught. Equal
    to, containing, or inside one of these refuses; anywhere else stays trusted.

    Round 16 S1: the comparison used to be exact-case `Path` equality, which never matches
    on a case-sensitive filesystem but silently stops matching on a case-insensitive one
    (macOS's default APFS, or Windows) — `GTQ_PARTICIPANT_ROOT=./Content` resolves to a path
    string that is not `repo_root / "content"` by `==`, even though both names the same
    directory to the filesystem underneath. Comparing `casefold()`-ed POSIX strings instead
    means this refuses a same-name-different-case path everywhere, including on a
    case-sensitive system where the two are actually different, unowned directories — a
    handful of extra refusals there, never a missed one on the filesystems this exists to
    protect.
    """
    candidates = {repo_root / name: name for name in _PROGRAM_OWNED_FOLDER_NAMES}

    def _casefolded(path: Path) -> str:
        return path.as_posix().casefold()

    participant_key = _casefolded(participant_root)
    participant_parent_keys = {_casefolded(parent) for parent in participant_root.parents}
    for candidate, name in candidates.items():
        candidate_key = _casefolded(candidate)
        candidate_parent_keys = {_casefolded(parent) for parent in candidate.parents}
        if (
            participant_key == candidate_key
            or candidate_key in participant_parent_keys
            or participant_key in candidate_parent_keys
        ):
            raise UnsafeParticipantRootError(
                f"Refusing to use {participant_root} as the participant root: it is, is "
                f"inside, or contains {name}/, which this application owns, not the "
                "participant. Set GTQ_PARTICIPANT_ROOT (or --participant-root) to a "
                "directory that is only yours."
            )


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
