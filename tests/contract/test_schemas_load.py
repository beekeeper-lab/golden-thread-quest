"""Every published schema must be a valid Draft 2020-12 schema.

A schema that does not compile silently validates nothing, so this runs before any content
test that depends on one.
"""

from __future__ import annotations

import pytest
from jsonschema import Draft202012Validator

EXPECTED = {
    "badge",
    "progress",
    "quest",
    "region",
    "review",
    "site",
    "track",
    "validation-result",
    "validator-registry",
    "submission",
}


def test_every_expected_schema_is_present(schemas: dict[str, dict[str, object]]) -> None:
    assert set(schemas) == EXPECTED


def test_schemas_compile(schemas: dict[str, dict[str, object]]) -> None:
    for name, schema in schemas.items():
        Draft202012Validator.check_schema(schema)
        assert schema.get("$id"), f"{name} has no $id"


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_schemas_reject_unknown_fields(name: str, schemas: dict[str, dict[str, object]]) -> None:
    """`additionalProperties: false` is what turns a typo into a build error instead of a
    silently ignored field. It must not be relaxed (CLAUDE.md rule 12)."""
    assert schemas[name].get("additionalProperties") is False
