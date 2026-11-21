#!/usr/bin/env python3
"""Turns a Jira description into Markdown, for the jira-read-story quest.

Jira does not store a description as text. It stores a tree, in what Atlassian
calls the Atlassian Document Format: a document holds blocks (paragraphs,
headings, lists, tables, code blocks), and blocks hold pieces of text that
carry marks (bold, italic, link, code).

    to_markdown(document) -> (markdown text, notes)

Three rules it follows.

1. Structure stays structure. A table comes out as a table, a code block as a
   code block, a list inside a list as a list inside a list.

2. Text stays text. Whatever a person typed is escaped so that it cannot turn
   into Markdown structure. Plain text that reads "# not a heading" or
   "*not bold*" comes out as those characters and nothing more. This is also
   what keeps ticket text as content: it cannot add a heading, a link or a
   block of its own.

3. Nothing is dropped without a trace. A kind of block or mark this converter
   does not know is carried along at the place it occurred: a block as a
   fenced block of its JSON under a comment naming it, a mark as a comment
   after the text. `notes` counts each such thing, so a run can report it.

A person mentioned in the text is written as their account id. This converter
never writes a display name.
"""
import datetime
import json
import re

KNOWN_MARKS = ("strong", "em", "strike", "code", "link", "underline", "subsup")


class Notes(dict):
    def add(self, what):
        self[what] = self.get(what, 0) + 1


def fence_for(text, least=3):
    """A run of backticks longer than any run inside the text, so the text cannot close it."""
    longest = max([len(run) for run in re.findall(r"`+", text)] or [0])
    return "`" * max(least, longest + 1)


def escape(text):
    """Make typed text inert: every character that means something in Markdown is escaped."""
    text = text.replace("\\", "\\\\")
    for ch in "`*_[]<>|~":
        text = text.replace(ch, "\\" + ch)
    return text


def guard_line_starts(text):
    """Escape what would start a block at the beginning of a line: a heading, a list, a quote, a rule."""
    lines = []
    for line in text.split("\n"):
        stripped = line.lstrip(" ")
        indent = line[: len(line) - len(stripped)]
        if re.match(r"(#{1,6}(\s|$)|[-+](\s|$)|={3,}\s*$|-{3,}\s*$)", stripped):
            stripped = "\\" + stripped
        else:
            numbered = re.match(r"(\d{1,9})([.)])(\s|$)", stripped)
            if numbered:
                stripped = "%s\\%s" % (numbered.group(1), stripped[len(numbered.group(1)):])
        lines.append(indent + stripped)
    return "\n".join(lines)


def comment(label, data):
    """Something Markdown cannot express, carried along where it occurred. `--` cannot appear inside a comment."""
    body = json.dumps(data, sort_keys=True, ensure_ascii=False).replace("--", "-\\u002d")
    return "<!-- %s: %s -->" % (label, body)


# ---------------------------------------------------------------- inline


def inline(nodes, notes, in_table=False):
    return "".join(one_inline(node, notes, in_table) for node in nodes or [])


def one_inline(node, notes, in_table):
    kind = node.get("type")
    attrs = node.get("attrs") or {}
    if kind == "text":
        return marked_text(node, notes)
    if kind == "hardBreak":
        return "<br>" if in_table else "\\\n"
    if kind == "mention":
        return "@account:%s" % escape(str(attrs.get("id", "unknown")))
    if kind == "emoji":
        return escape(str(attrs.get("text") or attrs.get("shortName") or ""))
    if kind == "inlineCard":
        return "<%s>" % str(attrs.get("url", "")).replace(">", "%3E").replace(" ", "%20")
    if kind == "date":
        try:
            when = datetime.datetime.fromtimestamp(int(attrs["timestamp"]) / 1000, datetime.timezone.utc)
            return when.strftime("%Y-%m-%d")
        except (KeyError, ValueError, TypeError, OverflowError):
            return escape(str(attrs.get("timestamp", "")))
    if kind == "status":
        return "\\[%s\\]" % escape(str(attrs.get("text", "")))
    if kind in ("media", "mediaInline"):
        return media(node, notes)
    notes.add("unrecognised inline: %s" % kind)
    return comment("jira-unrecognised-inline", node)


def marked_text(node, notes):
    text = node.get("text", "")
    marks = node.get("marks") or []
    kinds = [mark.get("type") for mark in marks]
    if "code" in kinds:
        fence = fence_for(text, least=1)
        pad = " " if text.startswith("`") or text.endswith("`") or not text.strip() else ""
        out = "%s%s%s%s%s" % (fence, pad, text.replace("\n", " "), pad, fence)
    else:
        lead = text[: len(text) - len(text.lstrip())]
        tail = text[len(text.rstrip()):] if text.strip() else ""
        core = escape(text.strip()) if text.strip() else ""
        if core:
            if "strong" in kinds:
                core = "**%s**" % core
            if "em" in kinds:
                core = "*%s*" % core
            if "strike" in kinds:
                core = "~~%s~~" % core
            if "underline" in kinds:
                core = "<u>%s</u>" % core
            for mark in marks:
                if mark.get("type") == "subsup":
                    tag = "sup" if (mark.get("attrs") or {}).get("type") == "sup" else "sub"
                    core = "<%s>%s</%s>" % (tag, core, tag)
        out = lead + core + tail if core else text
    for mark in marks:
        if mark.get("type") == "link":
            href = str((mark.get("attrs") or {}).get("href", "")).replace(">", "%3E").replace(" ", "%20")
            out = "[%s](<%s>)" % (out, href)
    for mark in marks:
        if mark.get("type") not in KNOWN_MARKS:
            notes.add("unrecognised mark: %s" % mark.get("type"))
            out += comment("jira-unrecognised-mark", mark)
    return out


def media(node, notes):
    """An image or file, kept as a reference to it. The file itself is not fetched."""
    attrs = node.get("attrs") or {}
    notes.add("media kept as a reference")
    alt = escape(str(attrs.get("alt") or "attachment"))
    if attrs.get("type") == "external" and attrs.get("url"):
        target = str(attrs["url"]).replace(">", "%3E").replace(" ", "%20")
    else:
        target = "jira-media:%s" % re.sub(r"[^A-Za-z0-9._-]", "", str(attrs.get("id", "unknown")))
    rest = {k: v for k, v in sorted(attrs.items()) if k not in ("alt", "url") and v not in ("", None)}
    return "![%s](<%s>)%s" % (alt, target, " " + comment("jira-media", rest) if rest else "")


# ---------------------------------------------------------------- blocks


def blocks(nodes, notes):
    out = [text for text in (one_block(node, notes) for node in nodes or []) if text != ""]
    return "\n\n".join(out)


def indent(text, first, rest):
    lines = text.split("\n")
    return "\n".join([first + lines[0]] + [(rest + line) if line else line for line in lines[1:]])


def one_block(node, notes):
    kind = node.get("type")
    attrs = node.get("attrs") or {}
    content = node.get("content") or []
    if kind == "paragraph":
        return guard_line_starts(inline(content, notes))
    if kind == "heading":
        level = attrs.get("level", 1)
        level = level if isinstance(level, int) and 1 <= level <= 6 else 1
        return "%s %s" % ("#" * level, inline(content, notes).replace("\\\n", " ").replace("\n", " "))
    if kind in ("bulletList", "orderedList"):
        number = attrs.get("order", 1) if isinstance(attrs.get("order", 1), int) else 1
        items = []
        for item in content:
            marker = "%d. " % number if kind == "orderedList" else "- "
            number += 1
            body = blocks(item.get("content"), notes) or ""
            items.append(indent(body, marker, " " * len(marker)))
        return "\n".join(items)
    if kind == "taskList":
        items = []
        for item in content:
            if item.get("type") == "taskList":
                items.append(indent(one_block(item, notes), "  ", "  "))
                continue
            box = "[x]" if (item.get("attrs") or {}).get("state") == "DONE" else "[ ]"
            items.append("- %s %s" % (box, inline(item.get("content"), notes).replace("\\\n", " ")))
        return "\n".join(items)
    if kind == "codeBlock":
        code = "".join(child.get("text", "") for child in content)
        fence = fence_for(code)
        language = re.sub(r"[^A-Za-z0-9+#._-]", "", str(attrs.get("language") or ""))
        return "%s%s\n%s\n%s" % (fence, language, code, fence)
    if kind == "blockquote":
        return indent(blocks(content, notes), "> ", "> ").replace("\n\n", "\n>\n")
    if kind == "panel":
        title = "**%s panel**" % escape(str(attrs.get("panelType", "info")).capitalize())
        return indent(title + "\n\n" + blocks(content, notes), "> ", "> ").replace("\n\n", "\n>\n")
    if kind == "rule":
        return "---"
    if kind == "table":
        return table(node, notes)
    if kind in ("mediaSingle", "mediaGroup"):
        return "\n\n".join(media(child, notes) for child in content if child.get("type") == "media")
    if kind == "expand":
        title = escape(str(attrs.get("title", "")))
        return "<details><summary>%s</summary>\n\n%s\n\n</details>" % (title, blocks(content, notes))
    if kind == "doc":
        return blocks(content, notes)
    notes.add("unrecognised block: %s" % kind)
    body = json.dumps(node, indent=1, sort_keys=True, ensure_ascii=False)
    fence = fence_for(body)
    return "%s\n%sjson\n%s\n%s" % (comment("jira-unrecognised-block", {"type": kind}), fence, body, fence)


def cell_text(cell, notes):
    """The blocks of one table cell on one line. A Markdown table cell cannot hold a block.

    Paragraphs are joined with <br>. A list becomes one line for each item,
    starting with a dash. A code block becomes inline code. The content and
    its order are kept. The list is no longer a real list.
    """
    parts = []

    def walk(nodes, depth):
        for node in nodes or []:
            kind = node.get("type")
            if kind == "paragraph":
                text = inline(node.get("content"), notes, in_table=True)
                if text:
                    parts.append("&nbsp;&nbsp;" * depth + text)
            elif kind in ("bulletList", "orderedList"):
                notes.add("list inside a table cell, kept as lines")
                number = (node.get("attrs") or {}).get("order", 1)
                for item in node.get("content") or []:
                    marker = "%d\\. " % number if kind == "orderedList" else "\\- "
                    number += 1
                    before = len(parts)
                    walk(item.get("content"), depth + 1)
                    if len(parts) > before:
                        parts[before] = "&nbsp;&nbsp;" * depth + marker + parts[before].replace("&nbsp;&nbsp;" * (depth + 1), "", 1)
            elif kind == "codeBlock":
                notes.add("code block inside a table cell, kept as inline code")
                code = "".join(child.get("text", "") for child in node.get("content") or [])
                for line in code.split("\n"):
                    fence = fence_for(line, least=1)
                    parts.append("%s %s %s" % (fence, line, fence))
            else:
                text = one_block(node, notes)
                if text:
                    notes.add("block inside a table cell, kept on one line")
                    parts.append(text.replace("\n", " "))

    walk(cell.get("content"), 0)
    return "<br>".join(parts).replace("\n", " ")


def table(node, notes):
    rows = [row for row in node.get("content") or [] if row.get("type") == "tableRow"]
    if not rows:
        return ""
    grid = [[cell for cell in row.get("content") or []] for row in rows]
    width = max(len(row) for row in grid)
    for row in grid:
        for cell in row:
            spans = {k: v for k, v in (cell.get("attrs") or {}).items() if k in ("colspan", "rowspan") and v not in (None, 1)}
            if spans:
                notes.add("merged table cell, kept unmerged")
    text = [[cell_text(cell, notes) for cell in row] + [""] * (width - len(row)) for row in grid]
    has_header = all(cell.get("type") == "tableHeader" for cell in grid[0]) and len(grid[0]) > 0
    lines = []
    if not has_header:
        lines.append("| " + " | ".join([""] * width) + " |")
        lines.append("|" + "---|" * width)
    for number, row in enumerate(text):
        lines.append("| " + " | ".join(row) + " |")
        if has_header and number == 0:
            lines.append("|" + "---|" * width)
    return "\n".join(lines)


def to_markdown(document):
    """A Jira description as Markdown. Returns (text, notes)."""
    notes = Notes()
    if document is None or document == "":
        return "", notes
    if isinstance(document, str):   # an older Jira may send plain text
        return guard_line_starts(escape(document)), notes
    if not isinstance(document, dict):
        notes.add("description was not a document")
        fence = "```"
        return "%s\n%sjson\n%s\n%s" % (comment("jira-unrecognised-block", {"type": "not a document"}), fence,
                                       json.dumps(document, indent=1, sort_keys=True, ensure_ascii=False), fence), notes
    return one_block(document, notes), notes
