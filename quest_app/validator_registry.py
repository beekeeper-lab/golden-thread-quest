"""The registry: the complete set of programs this application may execute.

The policy in `docs/VALIDATOR-CONTRACT.md` is simple to state and easy to lose. A quest
names a validator by ID. Everything else — what runs, where, for how long, with which
environment variables, over which paths — is program-owned and lives in
`validators/registry.yaml`, which is reviewed like code.

Nothing in this module builds a command from a request. There is no code path from a browser
to an argument list, which is the property that makes the local service safe to run at all.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from quest_app.config import AppConfig
from quest_app.errors import ContentProblem, ProblemReport, Severity
from quest_app.yaml_loader import strict_safe_load

REGISTRY_FILENAME = "registry.yaml"


def resolve_root(config: AppConfig, root: str) -> Path:
    """Turn a registry path into a real one, honouring the configured participant root.

    Registry paths are written against the production tree, where participant files live at
    `participant/`. The participant root is configuration (ADR-018) — under test it points
    at `fixtures/participant` — so a root written as `participant/...` has to follow it.
    Resolving it against the repository root instead would silently point every validator at
    a directory that does not exist, and every check would come back inconclusive.
    """
    parts = Path(root).parts
    if parts and parts[0] == "participant":
        return (config.participant_root.joinpath(*parts[1:])).resolve()
    return (config.repo_root / root).resolve()


class ValidatorError(RuntimeError):
    """A validator that cannot be run, with a reason safe to show a participant."""


@dataclass(frozen=True, slots=True)
class Parameter:
    name: str
    type: str
    description: str | None = None
    allowed: tuple[str, ...] = ()
    minimum: int | None = None
    maximum: int | None = None
    default: Any = None

    def coerce(self, value: Any) -> Any:
        """Validate one supplied value, or refuse it.

        Refusal is by allowlist for enums and by range for integers. There is no string
        parameter type on purpose: a free string is how an argument becomes an injection.
        """
        if value is None:
            if self.default is None:
                raise ValidatorError(f"{self.name!r} is required.")
            return self.default
        if self.type == "enum":
            if not isinstance(value, str) or value not in self.allowed:
                raise ValidatorError(f"{self.name!r} must be one of: {', '.join(self.allowed)}.")
            return value
        if self.type == "boolean":
            if not isinstance(value, bool):
                raise ValidatorError(f"{self.name!r} must be true or false.")
            return value
        if self.type == "integer":
            if isinstance(value, bool) or not isinstance(value, int):
                raise ValidatorError(f"{self.name!r} must be a whole number.")
            if self.minimum is not None and value < self.minimum:
                raise ValidatorError(f"{self.name!r} must be at least {self.minimum}.")
            if self.maximum is not None and value > self.maximum:
                raise ValidatorError(f"{self.name!r} must be at most {self.maximum}.")
            return value
        raise ValidatorError(f"{self.name!r} has an unsupported type.")


@dataclass(frozen=True, slots=True)
class ValidatorDefinition:
    id: str
    version: int
    display_name: str
    description: str
    entrypoint: str
    working_directory: str
    timeout_seconds: int
    max_output_bytes: int
    read_roots: tuple[str, ...]
    write_roots: tuple[str, ...]
    network: str
    parameters: dict[str, Parameter] = field(default_factory=dict)
    environment_allowlist: tuple[str, ...] = ()
    quest_ids: tuple[str, ...] = ()

    def may_run_for(self, quest_id: str) -> bool:
        return not self.quest_ids or quest_id in self.quest_ids

    def bind_parameters(self, supplied: dict[str, Any] | None) -> dict[str, Any]:
        """Turn a request's parameters into validated values, or refuse.

        An unexpected key is an error rather than ignored: silently dropping it would let a
        caller believe they had changed the run when they had not.
        """
        supplied = supplied or {}
        unexpected = sorted(set(supplied) - set(self.parameters))
        if unexpected:
            raise ValidatorError(f"unknown parameter(s): {', '.join(unexpected)}")
        return {
            name: parameter.coerce(supplied.get(name))
            for name, parameter in sorted(self.parameters.items())
        }

    def resolved_read_roots(self, config: AppConfig) -> tuple[Path, ...]:
        return tuple(resolve_root(config, root) for root in self.read_roots)

    def resolved_write_roots(self, config: AppConfig) -> tuple[Path, ...]:
        return tuple(resolve_root(config, root) for root in self.write_roots)

    def resolved_working_directory(self, config: AppConfig) -> Path:
        return resolve_root(config, self.working_directory)


@dataclass(frozen=True, slots=True)
class ValidatorRegistry:
    definitions: dict[str, ValidatorDefinition]

    def get(self, validator_id: str) -> ValidatorDefinition:
        definition = self.definitions.get(validator_id)
        if definition is None:
            # The lookup is by exact ID against a loaded table. An unknown ID never becomes
            # a path, a module name or a command.
            raise ValidatorError(f"{validator_id!r} is not a registered validator.")
        return definition

    def ids(self) -> list[str]:
        return sorted(self.definitions)


def load_registry(config: AppConfig, report: ProblemReport) -> ValidatorRegistry | None:
    """Load and validate the registry against its published schema."""
    from quest_app.content_loader import SchemaSet

    path = config.validators_root / REGISTRY_FILENAME
    relative = config.relative(path)
    if not path.exists():
        report.add(
            ContentProblem(
                code="validator.registry_missing",
                severity=Severity.ERROR,
                public_message="The validator registry is missing.",
                source=relative,
                expected="validators/registry.yaml",
            )
        )
        return None

    data = strict_safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        report.add(
            ContentProblem(
                code="validator.registry_invalid",
                severity=Severity.ERROR,
                public_message="The validator registry is not a mapping of fields.",
                source=relative,
            )
        )
        return None

    schemas = SchemaSet(config.schemas_root)
    if "validator-registry" not in schemas.names():
        report.add(
            ContentProblem(
                code="validator.registry_schema_missing",
                severity=Severity.ERROR,
                public_message="The validator registry schema is missing.",
                source="schemas/validator-registry.schema.json",
            )
        )
        return None
    if not schemas.validate("validator-registry", data, relative, report):
        return None

    definitions: dict[str, ValidatorDefinition] = {}
    for entry in data["validators"]:
        parameters = {
            name: Parameter(
                name=name,
                type=spec["type"],
                description=spec.get("description"),
                allowed=tuple(spec.get("allowed", ())),
                minimum=spec.get("minimum"),
                maximum=spec.get("maximum"),
                default=spec.get("default"),
            )
            for name, spec in sorted((entry.get("parameters") or {}).items())
        }
        definition = ValidatorDefinition(
            id=entry["id"],
            version=entry["version"],
            display_name=entry["display_name"],
            description=entry["description"],
            entrypoint=entry["entrypoint"],
            working_directory=entry["working_directory"],
            timeout_seconds=entry["timeout_seconds"],
            max_output_bytes=entry["max_output_bytes"],
            read_roots=tuple(entry["read_roots"]),
            write_roots=tuple(entry.get("write_roots", ())),
            network=entry["network"],
            parameters=parameters,
            environment_allowlist=tuple(entry.get("environment_allowlist", ())),
            quest_ids=tuple(entry.get("quest_ids", ())),
        )
        if definition.id in definitions:
            report.add(
                ContentProblem(
                    code="validator.duplicate_id",
                    severity=Severity.ERROR,
                    public_message=f"Two validators share the ID {definition.id!r}.",
                    source=relative,
                    entity_id=definition.id,
                )
            )
            continue
        definitions[definition.id] = definition

    return ValidatorRegistry(definitions=definitions)


def check_quest_references(
    registry: ValidatorRegistry, quests: dict[str, Any], report: ProblemReport
) -> None:
    """Every validator a quest declares must exist and be permitted to run for it."""
    for quest in sorted(quests.values(), key=lambda q: q.id):
        for validator_id in quest.validators:
            definition = registry.definitions.get(validator_id)
            if definition is None:
                report.add(
                    ContentProblem.build(
                        code="validator.unknown",
                        severity=Severity.ERROR,
                        public_message=(
                            f"Quest {quest.id!r} declares a validator that is not registered."
                        ),
                        source=quest.source,
                        entity_id=quest.id,
                        field_path="validators",
                        expected=f"one of: {', '.join(registry.ids())}",
                        received=validator_id,
                        suggestion="Register it in validators/registry.yaml, or remove it.",
                    )
                )
            elif not definition.may_run_for(quest.id):
                report.add(
                    ContentProblem.build(
                        code="validator.not_permitted_for_quest",
                        severity=Severity.ERROR,
                        public_message=(
                            f"Validator {validator_id!r} is not registered to run for "
                            f"quest {quest.id!r}."
                        ),
                        source=quest.source,
                        entity_id=quest.id,
                        field_path="validators",
                        expected=f"one of: {', '.join(definition.quest_ids)}",
                        received=quest.id,
                    )
                )
