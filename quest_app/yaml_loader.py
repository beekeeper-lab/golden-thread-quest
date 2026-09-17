"""YAML reading, with the two behaviours PyYAML gets wrong for reviewable content.

`safe_load` is required (ADR-025) but not sufficient. Two of its defaults are dangerous
specifically because this content arrives through pull requests:

* **Duplicate keys win silently.** `xp: 10` followed by `xp: 90` parses as 90 while a
  reviewer reading the diff sees 10. A curriculum change that means one thing in review and
  another at build time is exactly the failure this repository's whole validation story
  exists to prevent, so a duplicate key is an error.
* **Deep nesting crashes the process.** Around nine hundred levels of nesting raises
  `RecursionError` from the scanner, which is not a `YAMLError`, so it escaped the loader's
  handling and took out the whole run with a traceback and absolute paths in it.

Both were found by the Stage 2 audit.
"""

from __future__ import annotations

from typing import Any

import yaml


class StrictSafeLoader(yaml.SafeLoader):
    """`SafeLoader` that refuses a duplicate mapping key."""


def _construct_mapping(loader: StrictSafeLoader, node: yaml.MappingNode, deep: bool = False) -> Any:
    seen: set[Any] = set()
    for key_node, _ in node.value:
        key = loader.construct_object(key_node, deep=deep)
        try:
            hashable = key if isinstance(key, str | int | float | bool | None | tuple) else str(key)
        except TypeError:  # pragma: no cover - defensive
            hashable = str(key)
        if hashable in seen:
            raise yaml.constructor.ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                f"found duplicate key {key!r}",
                key_node.start_mark,
            )
        seen.add(hashable)
    return yaml.SafeLoader.construct_mapping(loader, node, deep=deep)


StrictSafeLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_mapping,
)


class DeepNestingError(ValueError):
    """The document nests too deeply to parse safely."""


def strict_safe_load(text: str) -> Any:
    """Parse `text` with `StrictSafeLoader`, turning a recursion crash into a normal error.

    Only ever called with `StrictSafeLoader`, which is `SafeLoader` plus a duplicate-key
    check — no constructor is added that could instantiate a Python object (ADR-025).
    """
    try:
        return yaml.load(text, Loader=StrictSafeLoader)  # noqa: S506 - StrictSafeLoader is SafeLoader
    except RecursionError as exc:
        raise DeepNestingError("the document nests too deeply to parse") from exc
