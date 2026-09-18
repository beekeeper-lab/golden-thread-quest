"""Standard-library pieces that differ across the Python versions this supports.

The floor is 3.10 rather than something more recent for one concrete reason: the
sandboxed environments participants work in — the Cowork VM in particular — ship 3.10,
and an install that fails on the interpreter is an install that never happens. Nothing
here is a preference; each entry exists because a real environment needs it.
"""

from __future__ import annotations

import sys

if sys.version_info >= (3, 11):  # pragma: no cover - version split
    from enum import StrEnum
else:  # pragma: no cover - version split
    from enum import Enum

    class StrEnum(str, Enum):
        """`enum.StrEnum` for Python 3.10.

        Equivalent for every use here: members are strings, compare as their value, and
        format as their value rather than as `Class.MEMBER`. The explicit `__str__` is
        what makes the last part true; without it a mixin enum formats as its repr and
        every rendered state name in the UI would change.
        """

        __str__ = str.__str__


if sys.version_info >= (3, 11):  # pragma: no cover - version split
    from typing import Self
else:  # pragma: no cover - version split
    from typing_extensions import Self


__all__ = ["Self", "StrEnum"]
