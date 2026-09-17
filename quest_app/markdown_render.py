"""Markdown to HTML that is safe to put in a page.

Two independent steps, deliberately (ADR-021). `markdown-it-py` renders CommonMark with raw
HTML disabled, and `nh3` then applies an explicit allowlist to the result. The second step
does not trust the first: if a renderer option is ever changed or a future version escapes
something differently, the allowlist still holds.

Authored content is not hostile by assumption, but it arrives through pull requests and
quests quote ticket text, transcripts and repository files, which are exactly the places
`SECURITY-AND-PRIVACY.md` expects injected content to come from.
"""

from __future__ import annotations

import re
from typing import Final

import nh3
from markdown_it import MarkdownIt

# Structural and emphasis tags only. No <img> (a remote image is a network request and a
# tracking pixel), no <style>, no <iframe>, no form elements.
ALLOWED_TAGS: Final[frozenset[str]] = frozenset(
    {
        "p",
        "br",
        "hr",
        "em",
        "strong",
        "del",
        "code",
        "pre",
        "blockquote",
        "ul",
        "ol",
        "li",
        "a",
        "h3",
        "h4",
        "h5",
        "h6",
        "table",
        "thead",
        "tbody",
        "tr",
        "th",
        "td",
        "sup",
        "sub",
        "abbr",
        "kbd",
    }
)

ALLOWED_ATTRIBUTES: Final[dict[str, set[str]]] = {
    # "rel" is absent deliberately: nh3 sets it itself via link_rel and refuses to be given
    # both. Letting content supply its own rel would let it drop noopener.
    "a": {"href", "title", "target"},
    "abbr": {"title"},
    "code": {"class"},
    "pre": {"class"},
    "th": {"scope", "colspan", "rowspan"},
    "td": {"colspan", "rowspan"},
}

# Anything not on this list is dropped, which removes javascript:, data:, vbscript: and
# every scheme a future browser invents.
ALLOWED_URL_SCHEMES: Final[frozenset[str]] = frozenset({"http", "https", "mailto"})

_EXTERNAL = re.compile(r'<a\s+([^>]*?)href="(https?://[^"]+)"([^>]*)>', re.IGNORECASE)


def _markdown() -> MarkdownIt:
    # `html=False` is the renderer refusing to pass raw HTML through; `linkify=False` keeps
    # bare URLs as text so content cannot create links the author did not write.
    parser = MarkdownIt("commonmark", {"html": False, "linkify": False, "typographer": False})
    parser.enable("table")
    return parser


_PARSER = _markdown()


def render_markdown(text: str) -> str:
    """CommonMark in, sanitized HTML out. Safe to mark as rendered content."""
    rendered = _PARSER.render(text)
    cleaned = nh3.clean(
        rendered,
        tags=set(ALLOWED_TAGS),
        attributes={tag: set(attrs) for tag, attrs in ALLOWED_ATTRIBUTES.items()},
        url_schemes=set(ALLOWED_URL_SCHEMES),
        link_rel="noopener noreferrer",
        strip_comments=True,
    )
    return _mark_external_links(cleaned)


def _mark_external_links(html: str) -> str:
    """External links open in a new context, with the rel the security policy requires.

    `nh3`'s `link_rel` already sets the rel on every link; this adds the target so a quest
    that points at documentation does not navigate the participant out of their own work.
    """

    def add_target(match: re.Match[str]) -> str:
        before, href, after = match.group(1), match.group(2), match.group(3)
        if "target=" in (before + after).lower():
            return match.group(0)
        return f'<a {before}href="{href}"{after} target="_blank">'

    return _EXTERNAL.sub(add_target, html)


def render_inline(text: str) -> str:
    """Render a single line without wrapping it in a paragraph — for list items and titles."""
    rendered = _PARSER.renderInline(text)
    return nh3.clean(
        rendered,
        tags=set(ALLOWED_TAGS) - {"p", "pre", "blockquote", "ul", "ol", "li", "table"},
        attributes={tag: set(attrs) for tag, attrs in ALLOWED_ATTRIBUTES.items()},
        url_schemes=set(ALLOWED_URL_SCHEMES),
        link_rel="noopener noreferrer",
        strip_comments=True,
    )


def strip_markdown(text: str) -> str:
    """Plain text for search indexes and summaries, with no markup at all."""
    rendered = _PARSER.render(text)
    plain = nh3.clean(rendered, tags=set(), attributes={}, strip_comments=True)
    return " ".join(plain.split())
