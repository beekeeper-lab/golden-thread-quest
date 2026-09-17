"""WCAG 2.2 AA contrast, computed from the design tokens.

No browser needed: the tokens are the source of every color in the product, so checking
them checks every component that consumes them. A pairing that fails here fails everywhere
it is used, which is the point of having tokens at all.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

AA_NORMAL = 4.5
AA_LARGE = 3.0
AA_NON_TEXT = 3.0


def tokens(repo_root: Path) -> dict[str, str]:
    """Every color token, with one level of `var()` aliasing resolved.

    Semantic tokens such as `--meter-fill` point at a palette token rather than repeating a
    hex value, so following the alias is what makes this check test the color that actually
    renders.
    """
    text = (repo_root / "assets" / "css" / "tokens.css").read_text()
    values = dict(re.findall(r"--([a-z0-9-]+):\s*(#[0-9a-fA-F]{6})\s*;", text))
    for name, target in re.findall(r"--([a-z0-9-]+):\s*var\(--([a-z0-9-]+)\)\s*;", text):
        if target in values:
            values[name] = values[target]
    return values


def _channel(value: int) -> float:
    fraction = value / 255
    return fraction / 12.92 if fraction <= 0.03928 else ((fraction + 0.055) / 1.055) ** 2.4


def luminance(color: str) -> float:
    red, green, blue = (int(color[index : index + 2], 16) for index in (1, 3, 5))
    return 0.2126 * _channel(red) + 0.7152 * _channel(green) + 0.0722 * _channel(blue)


def contrast(foreground: str, background: str) -> float:
    first, second = luminance(foreground), luminance(background)
    lighter, darker = max(first, second), min(first, second)
    return (lighter + 0.05) / (darker + 0.05)


@pytest.fixture(scope="module")
def palette(repo_root: Path) -> dict[str, str]:
    values = tokens(repo_root)
    assert values, "no color tokens were found"
    return values


# Every pairing the stylesheet actually produces, named by what it is rather than by hex.
TEXT_PAIRS = [
    ("ink-900", "paper", "body text on the page"),
    ("ink-900", "surface", "text on a card"),
    ("ink-600", "paper", "muted text on the page"),
    ("ink-600", "surface", "muted text on a card"),
    ("blue-700", "paper", "a link on the page"),
    ("blue-700", "surface", "a link on a card"),
    ("gold-700", "gold-100", "verified state chip"),
    ("green-700", "green-100", "locally-validated chip"),
    ("blue-700", "blue-100", "submitted chip"),
    ("orange-700", "orange-100", "needs-changes chip"),
    ("red-700", "red-100", "error alert text"),
    ("violet-700", "violet-100", "in-progress chip"),
    ("ink-700", "surface-muted", "available chip and tag"),
    ("paper", "ink-900", "sidebar text"),
    ("paper", "ink-800", "primary button label"),
    ("gold-300", "ink-800", "current navigation item"),
    # The participant summary renders on the dark sidebar as well as on light surfaces.
    # axe found this class of defect; pairing tokens against `paper` alone never would.
    ("text-muted-inverse", "ink-900", "muted label on the sidebar"),
    ("paper", "ink-900", "a total on the sidebar"),
    ("accent-inverse", "ink-900", "the verified total on the sidebar"),
]

# Only graphics that carry meaning. A card's decorative edge is not one of them, which is
# why `--line-strong` is absent and `--border-control` is here instead.
NON_TEXT_PAIRS = [
    ("ink-500", "surface", "a control border (--border-control)"),
    ("gold-600", "surface-muted", "a progress meter fill (--meter-fill)"),
    ("focus", "surface", "the focus ring"),
]


@pytest.mark.parametrize(
    ("foreground", "background", "what"), TEXT_PAIRS, ids=[pair[2] for pair in TEXT_PAIRS]
)
def test_text_meets_aa(
    palette: dict[str, str], foreground: str, background: str, what: str
) -> None:
    ratio = contrast(palette[foreground], palette[background])
    assert ratio >= AA_NORMAL, f"{what}: {ratio:.2f}:1, needs {AA_NORMAL}:1"


@pytest.mark.parametrize(
    ("foreground", "background", "what"),
    NON_TEXT_PAIRS,
    ids=[pair[2] for pair in NON_TEXT_PAIRS],
)
def test_essential_graphics_meet_aa(
    palette: dict[str, str], foreground: str, background: str, what: str
) -> None:
    """Borders, meter fills and the focus ring carry meaning, so they are not decoration."""
    ratio = contrast(palette[foreground], palette[background])
    assert ratio >= AA_NON_TEXT, f"{what}: {ratio:.2f}:1, needs {AA_NON_TEXT}:1"


def test_large_display_text_meets_at_least_the_large_threshold(palette: dict[str, str]) -> None:
    """The passport's verified total is display-sized, so the large-text threshold applies."""
    assert contrast(palette["gold-700"], palette["surface"]) >= AA_LARGE
