"""Read authored curriculum from disk and turn it into validated, normalized models.

The order matters and is the same every time: discover, parse, validate against the
published schema, then normalize. Nothing downstream ever sees a raw dictionary, and
nothing here renders anything.

Every failure produces a `ContentProblem` naming the file, the field path and, where the
parser can tell, the line — because the person who has to fix it is a curriculum author
looking at a text editor, not a developer reading a traceback.
"""

from __future__ import annotations

import difflib
import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

import yaml
from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import SchemaError

from quest_app.config import SUPPORTED_SCHEMA_VERSION, AppConfig
from quest_app.errors import ContentProblem, ProblemReport, Severity
from quest_app.hashing import hash_mapping, hash_quest, hash_text
from quest_app.markdown_render import render_inline, render_markdown
from quest_app.markdown_structure import (
    all_top_level_items,
    first_list_items,
    split_sections,
)
from quest_app.models import (
    AcceptanceCriterion,
    Badge,
    BadgeCriteria,
    ContentBundle,
    NarrativeSection,
    NavigationItem,
    ProofRequirement,
    Quest,
    Region,
    Risk,
    SiteConfig,
    Track,
    TrackBalance,
)
from quest_app.yaml_loader import DeepNestingError, strict_safe_load

FRONT_MATTER = re.compile(r"\A---\r?\n(?P<yaml>.*?)\r?\n---\r?\n(?P<body>.*)\Z", re.S)
HEADING = re.compile(r"^(#{1,6})\s+(?P<title>.+?)\s*$", re.M)
ORDERED_ITEM = re.compile(r"^\s*\d+[.)]\s+(?P<text>.+?)\s*$")
BULLET_ITEM = re.compile(r"^\s*[-*+]\s+(?P<text>.+?)\s*$")

# CONTENT-MODEL.md canonical body headings, mapped to the key a template asks for.
SECTION_KEYS: dict[str, str] = {
    "mission": "mission",
    "scenario": "scenario",
    "acceptance criteria": "acceptance_criteria",
    "required evidence": "required_evidence",
    "safety constraints": "safety",
    "hints": "hints",
    "reflection": "reflection",
    "stretch goals": "stretch_goals",
}

# Sections whose content is structured data rather than narrative, so they are not rendered
# into the narrative list a template iterates.
STRUCTURED_SECTIONS = frozenset({"acceptance_criteria"})

DOC_ROUTE = "/docs/content-authoring/"


@dataclass(frozen=True, slots=True)
class ParsedDocument:
    """A document that parsed. Whether it is *valid* is a separate question."""

    path: Path
    relative: str
    data: dict[str, Any]
    body: str = ""
    front_matter_offset: int = 0


def read_yaml(path: Path, config: AppConfig, report: ProblemReport) -> dict[str, Any] | None:
    """Parse one YAML document safely (ADR-025), reporting position on failure."""
    relative = config.relative(path)
    text = read_text(path, relative, report)
    if text is None:
        return None
    return parse_yaml_text(text, relative, report)


def read_text(path: Path, relative: str, report: ProblemReport) -> str | None:
    """File contents as text, or a problem that names no absolute path.

    `str(OSError)` embeds the filename, which for a developer's checkout is an absolute path
    under their home directory. `VIEW-MODEL-CONTRACT.md` forbids that in anything a browser
    renders, so only the error's own description is reported (Stage 2 audit H5).

    Read as `utf-8-sig` so a byte-order mark is consumed rather than becoming the first
    character of the front-matter delimiter (Stage 2 audit L1).

    Bounded by `safe_io.read_bounded_text`: a FIFO, a device, a directory, or a file over the
    size ceiling is refused before it is read, the same rule `discover()` applies while
    scanning `content/` — this is the call sites that path never sees, a fixed path opened
    directly (`participant/progress.yaml`, `review.yaml`, `submission.yaml`, `site.yaml`).
    """
    from quest_app.safe_io import UnsafeStateFileError, read_bounded_text

    try:
        return read_bounded_text(path)
    except UnsafeStateFileError:
        report.add(
            ContentProblem(
                code="content.not_a_regular_file",
                severity=Severity.ERROR,
                public_message=("This is not an ordinary, size-bounded file, so it was not read."),
                source=relative,
                expected="a regular file no larger than the size limit",
                suggestion="Replace the link or special file with the file itself, or trim it.",
            )
        )
        return None
    except UnicodeDecodeError as exc:
        report.add(
            ContentProblem.build(
                code="content.not_utf8",
                severity=Severity.ERROR,
                public_message="The file is not valid UTF-8 text.",
                source=relative,
                received=exc.reason,
                suggestion="Save the file as UTF-8.",
            )
        )
        return None
    except OSError as exc:
        report.add(
            ContentProblem.build(
                code="content.unreadable",
                severity=Severity.ERROR,
                public_message="The file could not be read.",
                source=relative,
                received=exc.strerror or "unknown error",
                suggestion="Check the file's permissions.",
            )
        )
        return None


def parse_yaml_text(
    text: str, relative: str, report: ProblemReport, *, line_offset: int = 0
) -> dict[str, Any] | None:
    try:
        data = strict_safe_load(text)
    except DeepNestingError:
        report.add(
            ContentProblem(
                code="content.too_deeply_nested",
                severity=Severity.ERROR,
                public_message="The YAML in this file nests too deeply to parse.",
                source=relative,
                expected="a document nesting no more than a few levels",
                suggestion="Content this deeply nested is almost always a mistake or an attack.",
            )
        )
        return None
    except yaml.YAMLError as exc:
        mark = getattr(exc, "problem_mark", None)
        duplicate = "duplicate key" in (getattr(exc, "problem", "") or "")
        report.add(
            ContentProblem.build(
                code="content.duplicate_key" if duplicate else "content.invalid_yaml",
                severity=Severity.ERROR,
                public_message=(
                    "The same field is set twice in this file."
                    if duplicate
                    else "The YAML in this file could not be parsed."
                ),
                source=relative,
                line=(mark.line + 1 + line_offset) if mark else None,
                column=(mark.column + 1) if mark else None,
                received=getattr(exc, "problem", None) or "parse error",
                suggestion=(
                    "A later value silently wins over an earlier one, so a reviewer reading "
                    "the diff would see a different value from the one that applies."
                    if duplicate
                    else "Check indentation and that every value containing a colon is quoted."
                ),
                documentation=DOC_ROUTE,
            )
        )
        return None
    if data is None:
        report.add(
            ContentProblem(
                code="content.empty",
                severity=Severity.ERROR,
                public_message="The file is empty.",
                source=relative,
                expected="a YAML mapping",
            )
        )
        return None
    if not isinstance(data, dict):
        report.add(
            ContentProblem.build(
                code="content.not_a_mapping",
                severity=Severity.ERROR,
                public_message="The top level of this file must be a mapping of fields.",
                source=relative,
                expected="a YAML mapping",
                received=data,
            )
        )
        return None
    return data


def split_front_matter(
    path: Path, config: AppConfig, report: ProblemReport
) -> ParsedDocument | None:
    """Separate YAML front matter from the Markdown body of a quest file."""
    relative = config.relative(path)
    text = read_text(path, relative, report)
    if text is None:
        return None
    match = FRONT_MATTER.match(text)
    if match is None:
        has_delimiters = text.lstrip().startswith("---") and text.count("\n---") >= 1
        report.add(
            ContentProblem(
                code="content.malformed_front_matter"
                if has_delimiters
                else "content.missing_front_matter",
                severity=Severity.ERROR,
                public_message=(
                    "The front-matter block is not closed correctly."
                    if has_delimiters
                    else "The quest has no YAML front matter."
                ),
                source=relative,
                line=1,
                expected=(
                    "the file to begin with a '---' line, YAML fields, then a closing "
                    "'---' line followed by a newline"
                ),
                suggestion=(
                    "Check that the closing '---' is on its own line and is followed by a newline."
                    if has_delimiters
                    else "Add the front-matter block described in the content-authoring guide."
                ),
                documentation=DOC_ROUTE,
            )
        )
        return None
    data = parse_yaml_text(match.group("yaml"), relative, report, line_offset=1)
    if data is None:
        return None
    return ParsedDocument(
        path=path,
        relative=relative,
        data=data,
        body=match.group("body"),
        front_matter_offset=text[: match.start("body")].count("\n"),
    )


class SchemaFileError(RuntimeError):
    """A published schema that is not valid JSON Schema. The application cannot validate."""


class SchemaSet:
    """The published schemas, compiled once.

    Loading them from `schemas/` rather than restating them in Python is the point: the file
    a maintainer reads is the file that validates their work (ADR-020).
    """

    def __init__(self, schemas_root: Path) -> None:
        self._validators: dict[str, Draft202012Validator] = {}
        for path in sorted(schemas_root.glob("*.schema.json")):
            try:
                schema = json.loads(path.read_text(encoding="utf-8"))
                Draft202012Validator.check_schema(schema)
            except (OSError, UnicodeDecodeError, json.JSONDecodeError, SchemaError) as exc:
                # A program file, not authored content, so it stops everything; but with a
                # sentence naming the file rather than a traceback through the JSON decoder.
                where = f" at line {exc.lineno}" if isinstance(exc, json.JSONDecodeError) else ""
                raise SchemaFileError(
                    f"schemas/{path.name} is not a valid JSON Schema{where}. It ships with the "
                    "application: restore it with `git checkout -- schemas/`."
                ) from None
            # Without a format checker, `format: date-time` is documentation rather than a
            # rule: `started_at: "banana"` produced no error, and every downstream
            # comparison then fell back to string ordering of garbage (Stage 2 audit H6).
            self._validators[path.name.removesuffix(".schema.json")] = Draft202012Validator(
                schema, format_checker=FormatChecker()
            )

    def names(self) -> list[str]:
        return sorted(self._validators)

    def validate(
        self,
        name: str,
        data: dict[str, Any],
        relative: str,
        report: ProblemReport,
        *,
        entity_id: str | None = None,
    ) -> bool:
        """Report every schema violation, not just the first."""
        validator = self._validators[name]
        found = False
        for error in sorted(validator.iter_errors(data), key=lambda e: list(e.absolute_path)):
            found = True
            field_path = ".".join(str(part) for part in error.absolute_path) or None
            report.add(
                ContentProblem.build(
                    code=f"schema.{name}.{error.validator}",
                    severity=Severity.ERROR,
                    public_message=schema_message(error.message),
                    source=relative,
                    entity_id=entity_id or _safe_id(data),
                    field_path=field_path,
                    expected=describe_rule(error.validator, error.validator_value),
                    received=error.instance,
                    documentation=DOC_ROUTE,
                )
            )
        return not found


def _safe_id(data: dict[str, Any]) -> str | None:
    value = data.get("id")
    return value if isinstance(value, str) else None


def schema_message(message: str) -> str:
    """jsonschema's message, with its repr of the whole instance removed.

    The default message embeds the offending value, which for a large document means the
    document. The value is reported separately, summarized and redacted.
    """
    trimmed = message.split(" is not of type ")[0]
    if len(trimmed) > 200:
        trimmed = trimmed[:199] + "…"
    return trimmed if trimmed != message else message[:200]


def describe_rule(keyword: str, value: Any) -> str:
    """The rule an author violated, in words rather than JSON Schema vocabulary."""
    descriptions: dict[str, Callable[[Any], str]] = {
        "required": lambda v: f"these fields are required: {', '.join(v)}",
        "type": lambda v: f"a value of type {v}",
        "enum": lambda v: f"one of: {', '.join(map(str, v))}",
        "pattern": lambda v: f"text matching {v}",
        "minLength": lambda v: f"at least {v} characters",
        "maxLength": lambda v: f"at most {v} characters",
        "minimum": lambda v: f"at least {v}",
        "maximum": lambda v: f"at most {v}",
        "minItems": lambda v: f"at least {v} item(s)",
        "maxItems": lambda v: f"at most {v} item(s)",
        "uniqueItems": lambda _: "no duplicate items",
        "additionalProperties": lambda _: "only the documented fields",
    }
    describe = descriptions.get(keyword)
    return describe(value) if describe else f"{keyword}: {value}"


def suggest(unknown: str, known: list[str]) -> str | None:
    """'Did you mean…' for a mistyped stable ID.

    `CONTENT-MODEL.md` asks for this by name, and it is the difference between an author
    fixing a typo in ten seconds and grepping the whole content tree.
    """
    matches = difflib.get_close_matches(unknown, known, n=1, cutoff=0.6)
    return f"Did you mean {matches[0]!r}?" if matches else None


# --------------------------------------------------------------------------------------
# Quest body parsing
# --------------------------------------------------------------------------------------


# --------------------------------------------------------------------------------------
# Normalization: validated dictionaries become models
# --------------------------------------------------------------------------------------


def _tuple(value: Any) -> tuple[str, ...]:
    return tuple(value) if isinstance(value, list) else ()


def build_quest(document: ParsedDocument, report: ProblemReport) -> Quest | None:
    """Turn one validated quest document into a model, or report why it cannot be."""
    data = document.data
    quest_id = str(data["id"])
    sections_raw = parse_sections(document.body)

    missing = [
        name
        for name in ("mission", "acceptance_criteria", "required_evidence")
        if name not in sections_raw
    ]
    if missing:
        readable = ", ".join(title for title, key in SECTION_KEYS.items() if key in missing)
        report.add(
            ContentProblem(
                code="content.quest.missing_section",
                severity=Severity.ERROR,
                public_message=f"The quest body is missing required heading(s): {readable}.",
                source=document.relative,
                entity_id=quest_id,
                expected=(
                    "'## Mission', '## Acceptance criteria' and '## Required evidence' headings"
                ),
                suggestion="Add the missing headings. Their order in the file does not matter.",
                documentation=DOC_ROUTE,
            )
        )
        return None

    duplicates = duplicate_section_titles(document.body)
    if duplicates:
        report.add(
            ContentProblem.build(
                code="content.quest.duplicate_heading",
                severity=Severity.ERROR,
                public_message=(
                    "Two headings would be stored under the same name, so one copy would "
                    "be discarded."
                ),
                source=document.relative,
                entity_id=quest_id,
                field_path="body",
                expected="each '##' heading to appear once",
                received=", ".join(duplicates),
                suggestion="Merge the duplicate sections or rename one of them.",
            )
        )
        return None

    _, criteria_markdown = sections_raw["acceptance_criteria"]
    criteria, ordered, has_empty = parse_acceptance_criteria(criteria_markdown)
    if has_empty:
        report.add(
            ContentProblem(
                code="content.quest.empty_criterion",
                severity=Severity.ERROR,
                public_message="An acceptance criterion is empty.",
                source=document.relative,
                entity_id=quest_id,
                field_path="body.acceptance_criteria",
                expected="every list item to state a criterion",
                suggestion=(
                    "An empty item would shift the identifier of every criterion after it, "
                    "so a reviewer finding pinned to 'ac-3' would silently move."
                ),
                documentation=DOC_ROUTE,
            )
        )
        return None
    if not criteria:
        report.add(
            ContentProblem(
                code="content.quest.no_acceptance_criteria",
                severity=Severity.ERROR,
                public_message="'## Acceptance criteria' contains no list items.",
                source=document.relative,
                entity_id=quest_id,
                field_path="body.acceptance_criteria",
                expected="a numbered list, one criterion per item",
                suggestion=(
                    "Write each criterion as a numbered list item so it has a stable identifier."
                ),
                documentation=DOC_ROUTE,
            )
        )
        return None

    orphaned = orphaned_list_items(criteria_markdown)
    if orphaned:
        report.add(
            ContentProblem.build(
                code="content.quest.split_criteria_list",
                severity=Severity.ERROR,
                public_message=(
                    f"{orphaned} acceptance criterion item(s) are in a second list and would "
                    "not be used."
                ),
                source=document.relative,
                entity_id=quest_id,
                field_path="body.acceptance_criteria",
                expected="one unbroken list",
                received=f"{orphaned} item(s) outside the first list",
                suggestion=(
                    "A paragraph between items starts a new list. Move the explanation inside "
                    "the item it belongs to, or above the list."
                ),
                documentation=DOC_ROUTE,
            )
        )
        return None

    if not ordered:
        report.add(
            ContentProblem(
                code="content.quest.unnumbered_criteria",
                severity=Severity.WARNING,
                public_message="Acceptance criteria use a bullet list rather than a numbered list.",
                source=document.relative,
                entity_id=quest_id,
                field_path="body.acceptance_criteria",
                expected="a numbered list",
                suggestion=(
                    "Number the criteria. Identifiers are positional either way (ADR-026), "
                    "but participants and reviewers refer to them by number."
                ),
            )
        )

    sections = tuple(
        NarrativeSection(
            key=key,
            title=title,
            heading_id=f"section-{key.replace('_', '-')}",
            safe_rendered_html=render_markdown(markdown),
        )
        for key, (title, markdown) in sections_raw.items()
        if key not in STRUCTURED_SECTIONS
    )

    proof_data = data["proof"]
    proof = tuple(
        [_proof_item(item, required=True) for item in proof_data["required"]]
        + [_proof_item(item, required=False) for item in proof_data.get("optional", [])]
    )

    risk_data = data.get("risk") or {}
    level = str(data["level"])
    xp = int(data["xp"])
    typical = TYPICAL_XP_FOR(level)
    if typical is not None and not (typical // 2 <= xp <= typical * 2):
        report.add(
            ContentProblem.build(
                code="content.quest.unusual_xp",
                severity=Severity.WARNING,
                public_message=f"{xp} XP is unusual for a {level} quest (typical is {typical}).",
                source=document.relative,
                entity_id=quest_id,
                field_path="xp",
                expected=f"roughly {typical // 2} to {typical * 2} XP",
                received=xp,
                suggestion="Adjust the XP or the level, unless the weighting is deliberate.",
            )
        )
    if data.get("bookend") is None:
        report.add(
            ContentProblem(
                code="content.quest.no_bookend",
                severity=Severity.WARNING,
                public_message=(
                    "The quest declares no bookend, so it is excluded from track balance."
                ),
                source=document.relative,
                entity_id=quest_id,
                field_path="bookend",
                expected="one of: intent, validation, cross-bookend, foundation",
                suggestion=(
                    "Add a bookend so catalog filters and track balance can classify this quest."
                ),
            )
        )

    return Quest(
        id=quest_id,
        version=int(data["version"]),
        title=str(data["title"]),
        summary=str(data["summary"]),
        region=str(data["region"]),
        level=level,
        xp=xp,
        estimated_minutes=int(data["estimated_minutes"]),
        tags=_tuple(data["tags"]),
        outcomes=_tuple(data["outcomes"]),
        proof=proof,
        acceptance_criteria=tuple(criteria),
        sections=sections,
        content_hash=hash_quest(data, document.body),
        source=document.relative,
        order=data.get("order"),
        tools=_tuple(data.get("tools")),
        bookend=data.get("bookend"),
        risk=Risk(
            external_write=bool(risk_data.get("external_write", False)),
            sensitive_data=bool(risk_data.get("sensitive_data", False)),
            notes=risk_data.get("notes"),
        ),
        prerequisites=_tuple(data.get("prerequisites")),
        related_quests=_tuple(data.get("related_quests")),
        validators=_tuple(data.get("validators")),
        author=data.get("author"),
        last_reviewed=data.get("last_reviewed"),
        deprecated=bool(data.get("deprecated", False)),
    )


def TYPICAL_XP_FOR(level: str) -> int | None:  # noqa: N802 - reads as a table lookup at call site
    from quest_app.models import TYPICAL_XP

    return TYPICAL_XP.get(level)


def _proof_item(item: dict[str, Any], *, required: bool) -> ProofRequirement:
    return ProofRequirement(
        id=str(item["id"]),
        type=str(item["type"]),
        description=str(item["description"]),
        path=item.get("path"),
        validator=item.get("validator"),
        required=required,
    )


def build_region(document: ParsedDocument) -> Region:
    data = document.data
    return Region(
        id=str(data["id"]),
        version=int(data["version"]),
        title=str(data["title"]),
        summary=str(data["summary"]),
        order=int(data["order"]),
        accent=str(data["accent"]),
        outcomes=_tuple(data["outcomes"]),
        source=document.relative,
        short_title=data.get("short_title"),
        icon=data.get("icon"),
        tags=_tuple(data.get("tags")),
    )


def build_badge(document: ParsedDocument) -> Badge:
    data = document.data
    criteria = data["criteria"]
    return Badge(
        id=str(data["id"]),
        version=int(data["version"]),
        title=str(data["title"]),
        summary=str(data["summary"]),
        award_type=str(data["award_type"]),
        icon=str(data["icon"]),
        criteria=BadgeCriteria(
            all_quests=_tuple(criteria.get("all_quests")),
            any_quests=_tuple(criteria.get("any_quests")),
            verified_quest_count=criteria.get("verified_quest_count"),
            verified_xp=criteria.get("verified_xp"),
            region=criteria.get("region"),
            required_tags=_tuple(criteria.get("required_tags")),
            reviewer_statement=criteria.get("reviewer_statement"),
        ),
        source=document.relative,
    )


def build_track(document: ParsedDocument) -> Track:
    data = document.data
    balance = data.get("balance") or {}
    return Track(
        id=str(data["id"]),
        version=int(data["version"]),
        title=str(data["title"]),
        summary=str(data["summary"]),
        quest_ids=_tuple(data["quest_ids"]),
        source=document.relative,
        focus_tags=_tuple(data.get("focus_tags")),
        balance=TrackBalance(
            intent_minimum=int(balance.get("intent_minimum", 0)),
            validation_minimum=int(balance.get("validation_minimum", 0)),
            cross_bookend_minimum=int(balance.get("cross_bookend_minimum", 0)),
        ),
    )


def build_site(document: ParsedDocument) -> SiteConfig:
    data = document.data
    return SiteConfig(
        schema_version=int(data["schema_version"]),
        title=str(data["title"]),
        curriculum=str(data["curriculum"]),
        tagline=str(data["tagline"]),
        default_track=str(data["default_track"]),
        navigation=tuple(
            NavigationItem(
                id=item["id"], label=item["label"], route=item["route"], icon=item.get("icon")
            )
            for item in data["navigation"]
        ),
        source=document.relative,
        professional_role=data.get("professional_role"),
    )


# --------------------------------------------------------------------------------------
# Discovery and the top-level load
# --------------------------------------------------------------------------------------


def discover(root: Path, pattern: str, config: AppConfig, report: ProblemReport) -> list[Path]:
    """Content files in a stable order.

    Sorted by POSIX relative path so the build does not depend on the filesystem's ordering,
    which differs between machines and is the classic source of non-reproducible output.

    Only regular files inside the content tree are read. A symlink to `/dev/zero` was read
    until the process ran out of memory, a FIFO hung `validate` indefinitely, and a symlink
    to a file outside `content/` was loaded as curriculum without a word.
    """
    if not root.exists():
        return []
    inside = config.content_root.resolve()
    found: list[Path] = []
    for path in sorted(root.rglob(pattern), key=lambda p: p.relative_to(root).as_posix()):
        resolved = path.resolve()
        if resolved.is_file() and resolved.is_relative_to(inside):
            found.append(path)
            continue
        if path.is_dir():
            continue
        report.add(
            ContentProblem(
                code="content.not_a_regular_file",
                severity=Severity.ERROR,
                public_message=(
                    "This is not an ordinary file inside content/, so it was not read."
                ),
                source=config.relative(path),
                expected="a regular file inside content/",
                suggestion="Replace the link or special file with the file itself.",
            )
        )
    return found


def load_content(config: AppConfig, report: ProblemReport) -> ContentBundle | None:
    """Load and validate everything under `content/`.

    Returns `None` when an error stopped the build. Warnings never stop it.
    """
    schemas = SchemaSet(config.schemas_root)

    site_path = config.content_root / "site.yaml"
    if not site_path.exists():
        report.add(
            ContentProblem(
                code="content.missing_site",
                severity=Severity.ERROR,
                public_message="content/site.yaml is missing.",
                source="content/site.yaml",
                expected="a site configuration file",
            )
        )
        return None
    site_data = read_yaml(site_path, config, report)
    site: SiteConfig | None = None
    if site_data is not None and schemas.validate(
        "site", site_data, config.relative(site_path), report
    ):
        if int(site_data.get("schema_version", 0)) > SUPPORTED_SCHEMA_VERSION:
            report.add(
                ContentProblem.build(
                    code="content.unsupported_schema_version",
                    severity=Severity.ERROR,
                    public_message=(
                        "This content was written for a newer version of the application."
                    ),
                    source=config.relative(site_path),
                    field_path="schema_version",
                    expected=f"at most {SUPPORTED_SCHEMA_VERSION}",
                    received=site_data.get("schema_version"),
                    suggestion="Update the application before loading this content.",
                )
            )
        else:
            site = build_site(ParsedDocument(site_path, config.relative(site_path), site_data))

    regions: dict[str, Region] = {}
    badges: dict[str, Badge] = {}
    tracks: dict[str, Track] = {}
    quests: dict[str, Quest] = {}
    hashes: list[str] = []

    # One loop per entity type rather than a table of heterogeneous dictionaries: the three
    # builders return three different models, and a shared loop can only express that by
    # discarding the types that make the rest of the pipeline safe.
    for path in discover(config.content_root / "regions", "*.yaml", config, report):
        if (document := _yaml_document(path, config, schemas, "region", report)) is not None:
            region = build_region(document)
            _register(regions, region.id, region, document.relative, "region", report)
            hashes.append(hash_mapping(document.data))

    for path in discover(config.content_root / "badges", "*.yaml", config, report):
        if (document := _yaml_document(path, config, schemas, "badge", report)) is not None:
            badge = build_badge(document)
            _register(badges, badge.id, badge, document.relative, "badge", report)
            hashes.append(hash_mapping(document.data))

    for path in discover(config.content_root / "tracks", "*.yaml", config, report):
        if (document := _yaml_document(path, config, schemas, "track", report)) is not None:
            track = build_track(document)
            _register(tracks, track.id, track, document.relative, "track", report)
            hashes.append(hash_mapping(document.data))

    for path in discover(config.content_root / "quests", "*.md", config, report):
        parsed = split_front_matter(path, config, report)
        if parsed is None:
            continue
        if not schemas.validate("quest", parsed.data, parsed.relative, report):
            continue
        quest = build_quest(parsed, report)
        if quest is None:
            continue
        _register(quests, quest.id, quest, parsed.relative, "quest", report)
        hashes.append(quest.content_hash)

    if site is None or not report.ok:
        return None

    return ContentBundle(
        site=site,
        quests=quests,
        regions=regions,
        badges=badges,
        tracks=tracks,
        content_hash=hash_mapping(sorted(hashes)),
    )


def _yaml_document(
    path: Path,
    config: AppConfig,
    schemas: SchemaSet,
    schema_name: str,
    report: ProblemReport,
) -> ParsedDocument | None:
    """Read, parse and schema-validate one YAML document, or report why it is unusable."""
    relative = config.relative(path)
    data = read_yaml(path, config, report)
    if data is None:
        return None
    if not schemas.validate(schema_name, data, relative, report):
        return None
    return ParsedDocument(path, relative, data)


class _HasIdAndSource(Protocol):
    """What `_register` needs from a model: a stable ID and the file it came from.

    Declared as read-only properties because the models are frozen.
    """

    @property
    def id(self) -> str: ...

    @property
    def source(self) -> str: ...


def _register(
    destination: dict[str, Any],
    entity_id: str,
    model: _HasIdAndSource,
    relative: str,
    kind: str,
    report: ProblemReport,
) -> None:
    """Add a model, refusing a duplicate stable ID.

    A duplicate is an error rather than a last-one-wins overwrite: two documents claiming the
    same ID means one participant's attempt could silently point at the other's definition.
    """
    if entity_id in destination:
        report.add(
            ContentProblem(
                code="content.duplicate_id",
                severity=Severity.ERROR,
                public_message=f"Two {kind} documents share the stable ID {entity_id!r}.",
                source=relative,
                entity_id=entity_id,
                field_path="id",
                expected="an ID that is unique within its entity type",
                suggestion=(
                    f"The other document is {destination[entity_id].source}. Rename one of them."
                ),
                documentation=DOC_ROUTE,
            )
        )
        return
    destination[entity_id] = model


# --------------------------------------------------------------------------------------
# Quest body structure, read from the Markdown token stream (see markdown_structure.py)
# --------------------------------------------------------------------------------------


def parse_sections(body: str) -> dict[str, tuple[str, str]]:
    """`{key: (title, markdown)}` for each `##` section of a quest body.

    A canonical heading maps to its documented key. Anything else gets a slugged key with a
    `custom-` prefix, so an author's `## Mission!` can never masquerade as `## Mission` and
    satisfy the required-heading check (Stage 2 audit M3).
    """
    sections: dict[str, tuple[str, str]] = {}
    for index, section in enumerate(split_sections(body)):
        sections[section_key(section.title, index)] = (section.title, section.markdown)
    return sections


def section_key(title: str, index: int) -> str:
    """The key a heading is stored under. The guard below has to use this same function."""
    key = SECTION_KEYS.get(title.casefold())
    if key is None:
        slug = re.sub(r"[^a-z0-9]+", "-", title.casefold()).strip("-")
        key = f"custom-{slug or index}"
    return key


def duplicate_section_titles(body: str) -> list[str]:
    """Headings that would be stored under the same key, overwriting each other.

    It used to count exact title strings, which is not what `parse_sections` keys on: keys
    are casefolded and slugged, so `## Mission` beside `## MISSION`, or `## Rollback plan`
    beside `## Rollback (plan)`, passed the guard and then overwrote each other. The build
    succeeded, said nothing, and the quest page showed the second block where the author's
    first one should have been.
    """
    seen: dict[str, list[str]] = {}
    for index, section in enumerate(split_sections(body)):
        seen.setdefault(section_key(section.title, index), []).append(section.title)
    collisions = []
    for titles in seen.values():
        if len(titles) > 1:
            unique = sorted(set(titles))
            collisions.append(unique[0] if len(unique) == 1 else " / ".join(unique))
    return sorted(collisions)


def parse_acceptance_criteria(markdown: str) -> tuple[list[AcceptanceCriterion], bool, bool]:
    """Criteria from the first list, whether it was numbered, and whether any item is empty.

    Only the direct items of the first list count. `markdown_structure` does the parsing;
    this adds the positional IDs and hashes ADR-016 defines.
    """
    items, ordered = first_list_items(markdown)
    criteria: list[AcceptanceCriterion] = []
    has_empty = False
    for item in items:
        if item.is_empty:
            has_empty = True
            continue
        number = len(criteria) + 1
        criteria.append(
            AcceptanceCriterion(
                id=f"ac-{number}",
                number=number,
                text=item.text,
                text_hash=hash_text(item.text),
                safe_rendered_html=render_inline(item.text),
            )
        )
    return criteria, ordered, has_empty


def orphaned_list_items(markdown: str) -> int:
    """How many top-level list items in the section are not part of the first list.

    A numbered list interrupted by a paragraph parses as two lists. The author sees five
    criteria; only the first list is used. Counting the remainder lets the loader say so
    rather than quietly dropping them.
    """
    first, _ = first_list_items(markdown)
    return max(len(all_top_level_items(markdown)) - len(first), 0)
