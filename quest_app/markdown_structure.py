"""Structure of a quest body, read from the Markdown token stream.

The first implementation matched headings and list items with line regexes, and the Stage 2
audit broke it in four ways: a nested sub-detail became a top-level criterion, a fenced code
block containing numbers became criteria, an empty item silently renumbered every criterion
after it, and a criterion continued onto a second line lost that line from the model, the
page and its own hash.

Each of those is the same mistake — treating Markdown as lines instead of as a document.
This module asks the parser instead. `markdown-it-py` already knows that a `##` inside a
fence is text, that an indented list is nested, and where a list item's content ends.

That matters more here than anywhere else in the loader: ADR-016 promises that `ac-3` means
the same criterion to the participant reading the page and to the reviewer whose finding is
pinned to it. A parser that disagrees with the renderer breaks exactly that promise.
"""

from __future__ import annotations

from dataclasses import dataclass

from markdown_it import MarkdownIt
from markdown_it.token import Token

_PARSER = MarkdownIt("commonmark", {"html": False, "linkify": False, "typographer": False})
_PARSER.enable("table")


@dataclass(frozen=True, slots=True)
class Section:
    """One `##` section: its heading text and the raw Markdown beneath it."""

    title: str
    markdown: str
    line: int


@dataclass(frozen=True, slots=True)
class ListItem:
    """One top-level item of a list, with its full text and where it starts."""

    text: str
    line: int
    empty: bool

    @property
    def is_empty(self) -> bool:
        return self.empty


def _tokens(markdown: str) -> list[Token]:
    return _PARSER.parse(markdown)


def split_sections(body: str) -> list[Section]:
    """Every level-two section of a quest body, in document order.

    Content is sliced from the original Markdown by line, not reassembled from tokens, so
    the text handed to the renderer is exactly what the author wrote. A heading inside a
    fenced code block is not a heading, because the parser says so.
    """
    lines = body.splitlines()
    headings: list[tuple[int, int, str]] = []
    tokens = _tokens(body)
    for index, token in enumerate(tokens):
        if token.type != "heading_open" or token.tag != "h2" or token.map is None:
            continue
        inline = tokens[index + 1] if index + 1 < len(tokens) else None
        title = inline.content.strip() if inline is not None and inline.type == "inline" else ""
        headings.append((token.map[0], token.map[1], title))

    sections: list[Section] = []
    for position, (start, content_start, title) in enumerate(headings):
        end = headings[position + 1][0] if position + 1 < len(headings) else len(lines)
        markdown = "\n".join(lines[content_start:end]).strip()
        sections.append(Section(title=title, markdown=markdown, line=start + 1))
    return sections


def first_list_items(markdown: str) -> tuple[list[ListItem], bool]:
    """The items of the first list, and whether that list was numbered.

    Only the direct items of that one list are returned. A nested list is content *of* an
    item, not a sibling of it, which is the distinction the regex version could not make.

    An item's text is every paragraph it directly contains, joined into one line, so a
    criterion written across two lines arrives whole. Text from a nested list is excluded:
    it belongs to the item, and folding it in would make the parent's text — and therefore
    its hash — change whenever a sub-detail did.
    """
    tokens = _tokens(markdown)
    depth = 0
    list_depth: int | None = None
    ordered = False
    items: list[ListItem] = []
    item_depth: int | None = None
    buffer: list[str] = []
    item_line = 0

    def flush() -> None:
        nonlocal buffer
        if item_depth is None:
            return
        text = " ".join(" ".join(part.split()) for part in buffer if part.strip())
        items.append(ListItem(text=text, line=item_line, empty=not text))
        buffer = []

    for token in tokens:
        if token.type in ("ordered_list_open", "bullet_list_open"):
            if list_depth is None:
                list_depth = depth
                ordered = token.type == "ordered_list_open"
            depth += 1
            continue
        if token.type in ("ordered_list_close", "bullet_list_close"):
            depth -= 1
            if list_depth is not None and depth == list_depth:
                # The first list has closed. A later sibling list is a different list.
                flush()
                item_depth = None
                break
            continue
        if token.type == "list_item_open":
            if list_depth is not None and depth == list_depth + 1:
                flush()
                item_depth = depth
                item_line = (token.map[0] + 1) if token.map else 0
            depth += 1
            continue
        if token.type == "list_item_close":
            depth -= 1
            if item_depth is not None and depth == item_depth:
                flush()
                item_depth = None
            continue
        if token.type.endswith("_open"):
            depth += 1
            continue
        if token.type.endswith("_close"):
            depth -= 1
            continue
        if token.type == "inline" and item_depth is not None and depth == item_depth + 2:
            # An item's own text sits inside a paragraph inside the item, so two levels
            # down. Anything deeper is a nested list or a block quote: content of the item
            # rather than its statement, and folding it in would make the parent's hash
            # change whenever a sub-detail did.
            buffer.append(token.content)
        elif token.type == "fence" and item_depth is not None and depth == item_depth:
            # A fenced block inside an item is content, not part of the statement.
            continue

    flush()
    return items, ordered


def all_top_level_items(markdown: str) -> list[ListItem]:
    """Every top-level item of every list in the fragment.

    Used to notice items that are not in the first list: a numbered list interrupted by a
    paragraph parses as two lists, and an author who wrote five criteria would otherwise see
    only the first few used, with no message (Stage 2 audit H2).
    """
    items: list[ListItem] = []
    remaining = markdown
    guard = 0
    while remaining.strip() and guard < 50:
        guard += 1
        found, _ = first_list_items(remaining)
        if not found:
            break
        items.extend(found)
        last_line = max(item.line for item in found)
        lines = remaining.splitlines()
        # Continue after the last line the first list occupied. `line` is 1-based, and a
        # multi-line item may extend past it, so advance to the next blank line.
        cursor = last_line
        while cursor < len(lines) and lines[cursor].strip():
            cursor += 1
        remaining = "\n".join(lines[cursor:])
    return items
