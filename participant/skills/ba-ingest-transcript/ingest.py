#!/usr/bin/env python3
"""Ingest a WebVTT meeting transcript into a redacted source of record.

Reads a raw .vtt transcript and its meeting file (JSON), both kept outside source
control, and writes two files under participant/context/transcripts/:
  <name>.md               the redacted, verbatim source of record
  <name>.provenance.yaml  where the record came from and how it was made
Nothing is written unless the whole transcript parses. See SKILL.md. Needs Python 3.10
or later; the application's .venv/bin/python works. Run from the repository root:
  .venv/bin/python participant/skills/ba-ingest-transcript/ingest.py RAW.vtt \\
      --meeting MEETING.json --out participant/context/transcripts/NAME.md
Exit codes: 0 written or unchanged, 2 unparseable or invalid input, 3 refused.
"""
import argparse
import bisect
import dataclasses
import datetime
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import unicodedata
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent
REPO = SKILL_DIR.parents[2]
PARTICIPANT = REPO / "participant"
OUTPUT_DIR = PARTICIPANT / "context" / "transcripts"

RECORD_FORMAT = "gtq-transcript-record/1"
PROVENANCE_FORMAT = "gtq-transcript-provenance/1"
TIMESTAMP_FORMAT = "HH:MM:SS.mmm, offset from the start of the recording"
ID_FORMAT = "<transcript_id>#U-NNNN, numbered in source order from U-0001"
UNATTRIBUTED = "Unattributed"
NO_LABEL = "no listed or generic speaker label"
NOT_LISTED = "label is not in the meeting's participant list"
TEMP_PREFIX = ".ingest-"

# \Z, not $: $ also matches before a final line feed, so "tr-x" and a line feed would pass.
TRANSCRIPT_ID = re.compile(r"^tr-[a-z0-9]+(?:-[a-z0-9]+)*\Z")
RECORD_NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*\.md\Z")
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}\Z", re.ASCII)
# ASCII digits only, as WebVTT reads a timestamp.
TIMESTAMP = re.compile(r"^(?:(\d{2,}):)?([0-5]\d):([0-5]\d)\.(\d{3})$", re.ASCII)
# Characters are written as chr() codes so that this file stays plain ASCII.
BOM = chr(0xFEFF)
NO_BREAK_SPACES = "".join(chr(code) for code in (0x00A0, 0x2007, 0x2009, 0x202F))  # no-break, figure, thin, narrow
DASHES = "".join(chr(code) for code in range(0x2010, 0x2016))  # hyphen through horizontal bar
MIDDLE_DOT = chr(0x00B7)
RIGHT_ARROW = chr(0x2192)

TIMING = re.compile(r"^(\S+)[ \t]+-->[ \t]+(\S+)(?:[ \t].*)?$")
# A damaged timing line is made only of these pieces and starts like a timing line (see is_timing_line).
TIME_PIECE = re.compile(r"^\d+(?::\d*)+(?:[.,]\d*)?$")  # a time, whole or cut short
NUMBER_PIECE = re.compile(r"^[:.,]*\d[\d:.,]*$")  # digits, colons, full stops and commas, holding a digit
TIME_LIKE_NUMBER = re.compile(r"^(?:0\d|\d+\.\d{3})$")  # 00 to 09, or digits, a full stop and three digits
# A run of arrow-like characters holding at least one that is not a full stop or a parenthesis.
ARROW_PIECE = re.compile("^[.()]*[-=~<>" + DASHES + RIGHT_ARROW + "][-=~<>.()" + DASHES + RIGHT_ARROW + "]*$")
SETTING_PIECE = re.compile(r"^[A-Za-z]+:\S+$")
DIGIT = re.compile(r"\d")
# The start of a voice tag, read loosely: in a header or block it marks a line as a cue's words.
BLOCK_VOICE_TAG = re.compile(r"<v(?:[ \t.>]|$)")
# Speaker tags. Every part is bounded, so a long run of '<v' openers is searched in linear time,
# and a class segment may not contain '.', so a run of '.class' parts can be split only one way.
VOICE_TAG = r"<v(?:\.[^\s>.<]{1,50}){0,20}[ \t]+"
VOICE_OPEN = re.compile(VOICE_TAG + r"([^<>]{0,200})>")
VOICE_SPAN = re.compile(VOICE_TAG + r"[^<>]{0,200}>.*?(?:</v>|\Z)", re.S)
VOICE_CLOSE = re.compile(r"</v>")
# Where a voice tag starts: '<v' followed by a full stop, a space, a tab, a line break or the end of
# the cue, or '<v>'. split_speaker refuses a cue where a start does not begin a VOICE_OPEN match.
VOICE_START = re.compile(r"<v(?=[. \t\n>]|\Z)")
ANY_TAG = re.compile(r"<[^<>\n]{0,200}>")
# A Name: label of up to 200 characters, as a voice tag allows. Zoom writes some display names with an
# affiliation in parentheses, which can run past 60 characters.
PREFIX_LABEL = re.compile(r"^([^:\n]{1,200}):[ \t" + NO_BREAK_SPACES + r"]*(.*)$", re.DOTALL)
# Inside a word of a name that starts a line (see is_name_word): apostrophes, hyphens, full stops.
NAME_MARKS = "'.-" + chr(0x2010) + chr(0x2011) + chr(0x2019)
OTHER_SPEAKER_NOTE = 'a line starts with "{}:", which may be another speaker'
GENERIC_LABEL = re.compile(r"^(?:speaker[ \t]*\d+|unknown(?:[ \t]+speaker)?|guest(?:[ \t]*\d+)?)$", re.I)
ENTITY = re.compile(r"&(amp|lt|gt|nbsp|lrm|rlm);|&#(\d+);|&#[xX]([0-9a-fA-F]+);")
ENTITIES = {"amp": "&", "lt": "<", "gt": ">", "nbsp": chr(0x00A0), "lrm": chr(0x200E), "rlm": chr(0x200F)}

# Redaction. Each pattern is replaced with its marker in utterance text, speaker labels
# and every string written to the provenance file. Between two groups of digits in a phone
# number, one to six separators may sit: a space, tab, line break, dot, slash, hyphen or dash,
# minus sign, full-width hyphen-minus, middle dot, or a no-break, figure, thin, narrow or
# zero-width space.
# The minus sign, the full-width hyphen-minus and the zero-width space:
# Also every other Unicode space, the line and paragraph separators, the invisible soft hyphen, zero-width
# non-joiner and joiner, word joiner and zero-width no-break space, four more dash-like characters (small
# hyphen-minus, modifier letter minus, hyphen bullet, one dot leader), the left-to-right and right-to-left
# marks and the other bidirectional controls, the combining grapheme joiner, the Arabic letter mark, the
# Mongolian vowel separator, the Hangul filler, the blank Braille pattern, and the full-width, small and
# ideographic full stops, the two dot leader, the bullet and the full-width slash.
OTHER_PHONE_SEPARATORS = "".join(chr(code) for code in (
    0x2212, 0xFF0D, 0x200B, 0x1680, *range(0x2000, 0x200B), 0x205F, 0x3000, 0x2028, 0x2029,
    0x00AD, 0x200C, 0x200D, 0x2060, 0xFEFF, 0xFE63, 0x02D7, 0x2043, 0x2024,
    0x200E, 0x200F, *range(0x202A, 0x202F), *range(0x2066, 0x206A), 0x061C, 0x034F, 0x180E, 0x3164, 0x2800,
    0xFF0E, 0xFE52, 0x3002, 0x2025, 0x2022, 0xFF0F))
PHONE_SEPARATORS = r" \t\n./\-" + NO_BREAK_SPACES + DASHES + MIDDLE_DOT + OTHER_PHONE_SEPARATORS
PHONE_SEP = "[" + PHONE_SEPARATORS + "]{1,6}"  # between two groups of digits
# Between two digits of an international number: up to six separators or parentheses, with one more
# closing parenthesis just before them and one more opening parenthesis just after them, as in
# '+44 (20) 7946 0958'. Those two parentheses do not count as one of the six.
PHONE_GAP = r"\)?[()" + PHONE_SEPARATORS + r"]{0,6}\(?"
EXTENSION = "[ " + chr(0x00A0) + r"]?(?:x|ext\.?|extension)(?:[ " + chr(0x00A0) + r"]?\d{1,6})?"
PHONE_END = r"(?:" + EXTENSION + r"(?!\w)|(?!\d))"  # an optional extension, and no digit right after
DIGIT_WORD = r"(?<!\w)(?:zero|oh|o|one|two|three|four|five|six|seven|eight|nine)(?!\w)"
SPOKEN_DIGIT = r"(?:\d|" + DIGIT_WORD + r")"
SPOKEN_SEP = r"[ ,\-\n]{0,3}"  # between spoken digits: up to three spaces, commas, hyphens or line breaks
# A digit said on its own: a digit word, or a single digit with no other digit next to it, as Zoom
# writes a number read one digit at a time ('3, 1, 7, 5, 5, 5, 0, 1, 8, 6').
SINGLE_DIGIT = r"(?:" + DIGIT_WORD + r"|(?<!\d)\d(?!\d))"
# A number of varying length (international or spoken) never stops right after a group of three
# digits that starts a written local number (555 0100) or a number written three digits then
# seven (317-5550100). It stops before that group, so the shapes below redact the written number
# whole; if that leaves it too few digits, it is not read from that point.
NOT_INSIDE_A_WRITTEN_NUMBER = r"(?!(?<=\D\d{3})" + PHONE_SEP + r"(?:\d{4}|\d{7})(?!\d))"
PHONE_SHAPES = [
    # International shape: '+' and 8 to 15 digits in all (the most a phone number has), in any
    # number of groups split by separators or parentheses, as in '+44 (0)20 7946 0958'. The
    # country code may be in parentheses: '(+44)' or '+(44)'. Digits after the number join it
    # only while the count stays at 15, so a year after a 12-digit number stays visible, and a
    # '+' followed by more than 15 digits in one unbroken run is not a phone number. It comes
    # first, so a number whose first groups look North American ('+1 317 555 0100 1 2 3 4') is
    # taken whole. Every part is bounded, which keeps the search linear.
    r"(?:\(\+(?=\d{1,3}\))|\+\(?)\d(?:" + PHONE_GAP + r"\d){7,14}" + NOT_INSIDE_A_WRITTEN_NUMBER + PHONE_END,
    # North American shape: an optional '+' and country code, a three-digit area code (in
    # parentheses or not), then three digits and four, or seven together. Anything may sit
    # directly in front, as in 'tel317-555-0100' or '1317-555-0100'.
    r"(?:\+\d{1,3}(?:" + PHONE_SEP + r")?)?(?:\(\d{3}\)(?:" + PHONE_SEP + r")?|\d{3}" + PHONE_SEP + r")"
    r"(?:\d{3}" + PHONE_SEP + r"\d{4}|\d{7})" + PHONE_END,
    # Ten digits together, or eleven starting with 1, but not inside a longer run of digits.
    r"(?<!\d)1?\d{10}" + PHONE_END,
    # A seven-digit local number written with a separator, such as 555-0100. With a digit in
    # front it reads as two four-digit numbers, like the years in 2019-2020, so it is left.
    r"(?<!\d)\d{3}" + PHONE_SEP + r"\d{4}" + PHONE_END,
    # Spoken digits: a run of 7 to 15 digits said as digit words or single digits, or mixed with
    # groups of digits, holding three digit words or single digits in a row within its first 15
    # digits, as in 'three one seven, five five five, oh one eight six', '3, 1, 7, 5, 5, 5, 0, 1,
    # 8, 6' or '317 five five five oh one eight six', with an optional extension. A run never
    # stops inside a group of digits, so it can stop short of 15 digits; the search goes on
    # after it. A digit word must stand alone, so between two words there is always a separator.
    r"(?<!\w)(?=(?:" + SPOKEN_DIGIT + SPOKEN_SEP + r"){0,12}" + SINGLE_DIGIT + r"(?:" + SPOKEN_SEP + SINGLE_DIGIT + r"){2})"
    + SPOKEN_DIGIT + r"(?:" + SPOKEN_SEP + SPOKEN_DIGIT + r"){6,14}" + NOT_INSIDE_A_WRITTEN_NUMBER + PHONE_END,
]
# In an email address's name part, an apostrophe (straight or curly) or an ampersand may join two
# runs of the other name characters, as in o'brien@example.com. A match may start only where an
# address can start: not after a name character, and not after a name character and a joiner.
# That keeps the search linear on long text, and leaves outside the address an apostrophe used
# as a quotation mark in front of it.
EMAIL_JOINERS = "'&" + chr(0x2019)  # apostrophe, ampersand, right single quotation mark
EMAIL_START = r"(?<![\w.%+-])(?<![\w.%+-][" + EMAIL_JOINERS + "])"
EMAIL_NAME = r"[\w.%+-]+(?:[" + EMAIL_JOINERS + r"][\w.%+-]+)*"
# An address spoken aloud, as a transcription tool writes it down: "ada at example dot com",
# "ada dot lee at example dot org", "ada at example.com", "ada@example dot com", "ada at the
# rate example.com", or with "at" left out before a well-known mail provider's name, "<name> dot
# <name> gmail.com". After a written full stop it may end in any top-level domain of two or more
# letters; after a spoken "dot", in one of these words. A full stop may sit right before a spoken
# "at" or "dot", as when a cue ends "lee at example." and the next starts "Dot com.", and a comma
# right before "at", as in "Ada, A-D-A, at example.com". The name may have up to five parts
# joined by a spoken "dot". Any word can start a name, so that bound keeps the search linear on a
# long run of "dot" words; a domain is read only after "at", "@" or a space and a provider's
# name, so it needs no bound.
SPOKEN_TOP_LEVEL_DOMAINS = ["com", "org", "net", "edu", "gov", "mil", "int", "info", "biz", "io", "co", "us",
                            "uk", "ca", "au", "nz", "ie", "de", "fr", "eu", "ai", "dev", "app", "pro", "systems",
                            "example", "test", "invalid"]
MAIL_PROVIDERS = ["gmail", "googlemail", "yahoo", "hotmail", "outlook", "icloud", "aol", "msn", "protonmail",
                  "gmx"]
SPOKEN_SPACE = "[ \t\n" + NO_BREAK_SPACES + "]"
SPOKEN_DOT = r"[.,]?" + SPOKEN_SPACE + "{1,3}dot" + SPOKEN_SPACE + "{1,3}"
SPOKEN_AT = (r"(?:[.,]?" + SPOKEN_SPACE + "{1,3}at(?:" + SPOKEN_SPACE + "{1,3}the" + SPOKEN_SPACE + "{1,3}rate"
             + SPOKEN_SPACE + "{0,3}|" + SPOKEN_SPACE + "{1,3})|" + SPOKEN_SPACE + "{0,3}@" + SPOKEN_SPACE + "{0,3})")
NO_AT = SPOKEN_SPACE + "{1,3}(?=(?:" + "|".join(MAIL_PROVIDERS) + r")(?:\.|" + SPOKEN_DOT + "))"
SPOKEN_NAME_PART = r"[\w%+-]+(?:[." + EMAIL_JOINERS + r"][\w%+-]+)*"
SPOKEN_DOMAIN_PART = r"[^\W_][\w-]*(?:\.[^\W_][\w-]*)*"
SPOKEN_ENDING = "(?:" + "|".join(SPOKEN_TOP_LEVEL_DOMAINS) + r")(?![\w-])"
WRITTEN_ENDING = r"\.[^\W\d_]{2,}(?![\w-])"  # a full stop and two or more letters
REDACTIONS = [
    ("email", "[REDACTED:EMAIL]", re.compile(
        EMAIL_START + EMAIL_NAME + r"@[\w-]+(?:\.[\w-]+)*\.[^\W\d_]{2,}")),
    # One pattern for every phone shape, so each number is found once, by the shape that
    # starts first, and counts once.
    ("phone", "[REDACTED:PHONE]", re.compile("|".join(PHONE_SHAPES), re.I)),
    # Spoken addresses are read after phone numbers, so a number's last group of digits is not
    # taken for the name of an address that follows it. An address with no space in it is left to
    # the first pattern, which covers every such form, so that each pattern is tested on its own.
    ("email", "[REDACTED:EMAIL]", re.compile(
        EMAIL_START + "(?!" + SPOKEN_NAME_PART + "@" + SPOKEN_DOMAIN_PART + r"\.[^\W\d_]{2,})"
        + SPOKEN_NAME_PART + "(?:" + SPOKEN_DOT + SPOKEN_NAME_PART + "){0,4}(?:" + SPOKEN_AT + "|" + NO_AT + ")"
        + SPOKEN_DOMAIN_PART + "(?:" + SPOKEN_DOT + SPOKEN_DOMAIN_PART + ")*"
        + "(?:" + WRITTEN_ENDING + "|" + SPOKEN_DOT + SPOKEN_ENDING + ")", re.I)),
    # A spoken address that ends at a mail provider's name with no top-level domain, as in "ada dot lee at
    # gmail" or "ada dot lee gmail". Its name needs a spoken "dot", so "I use gmail" stays words.
    ("email", "[REDACTED:EMAIL]", re.compile(
        EMAIL_START + SPOKEN_NAME_PART + "(?:" + SPOKEN_DOT + SPOKEN_NAME_PART + "){1,4}(?:" + SPOKEN_AT + "|"
        + SPOKEN_SPACE + "{1,3})(?:" + "|".join(MAIL_PROVIDERS) + r")(?![\w-])", re.I)),
]

# Text that reads as an instruction to an agent. A match is only reported. It never
# changes what is parsed, redacted or written.
INSTRUCTION_HINTS = [
    re.compile(r"\b(?:ai|assistant|agent|claude|chatgpt|copilot|llm|bot)\b.{0,80}?"
               r"\b(?:ignore|disregard|delete|remove|keep|include|run|execute|send|forget|skip)\b",
               re.I | re.S),
    re.compile(r"\b(?:ignore|disregard|forget)\b.{0,30}?\b(?:previous|prior|above|instructions|rules)\b",
               re.I | re.S),
    re.compile(r"\b(?:system prompt|developer message)\b", re.I),
]

MD_SPECIAL = set("\\`*_[]<>|#~&")
# Spaces and tabs at the start of a quotation line. Written as they are, a Markdown renderer drops
# them, and after an empty line it shows a line indented far enough as code, with its backslashes.
# So they are written as these character references, which it shows as the characters themselves.
# Every '&' in the words is escaped, so a reference typed in the words is never read as one of these.
INDENT_REFERENCES = {" ": "&#32;", "\t": "&#9;"}
INDENT_REFERENCE_RUN = re.compile(r"(?:&#32;|&#9;)*")


class Unparseable(Exception):
    """The transcript cannot be read as WebVTT. Nothing is written."""

    def __init__(self, line, reason):
        self.line = line
        self.reason = reason
        super().__init__(f"line {line}: {reason}" if line else reason)


class InvalidInput(Exception):
    """The meeting file or a path is not acceptable. Nothing is written."""


class Refused(Exception):
    """Writing would overwrite or contradict an existing source of record."""


@dataclasses.dataclass
class Cue:
    line: int
    start_ms: int
    end_ms: int
    label: str | None
    text: str
    on_label_line: bool = False  # text starts with words on the line that holds the cue's Name: label


@dataclasses.dataclass
class Utterance:
    uid: str
    start: str
    end: str
    speaker: str
    certain: bool
    reason: str | None
    text: str


# ---------------------------------------------------------------- parsing

def parse_timestamp(value, line):
    match = TIMESTAMP.match(value)
    if not match:
        raise Unparseable(line, f"timestamp {value!r} is not HH:MM:SS.mmm or MM:SS.mmm")
    hours, minutes, seconds, millis = match.groups()
    return ((int(hours or 0) * 60 + int(minutes)) * 60 + int(seconds)) * 1000 + int(millis)


def format_ms(ms):
    seconds, millis = divmod(ms, 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{millis:03d}"


def decode_entities(text, line=None):
    def replace(match):
        name, decimal, hexadecimal = match.groups()
        if name:
            return ENTITIES[name]
        digits = (decimal or hexadecimal).lstrip("0") or "0"
        code = int(digits, 10 if decimal else 16) if len(digits) <= 7 else -1
        if code <= 0 or code > 0x10FFFF or 0xD800 <= code <= 0xDFFF:
            raise Unparseable(line, f"character reference {snippet(match.group(0))} is not a character")
        return chr(code)
    return ENTITY.sub(replace, text)


def has_control(text, allowed=""):
    return any(unicodedata.category(c) == "Cc" and c not in allowed for c in text)


def snippet(text):
    """A line quoted in a refusal: redacted before it is cut short, so a cut cannot leave part of a detail."""
    text = redact(text, {})
    return repr(text if len(text) <= 60 else text[:57] + "...")


def normalized_text(text):
    """The transcript text with any byte-order mark removed and every line ending made a newline."""
    return text.removeprefix(BOM).replace("\r\n", "\n").replace("\r", "\n")


def text_fingerprint(text):
    """SHA-256 of the normalized text, so a re-saved copy of the same transcript is recognized."""
    return hashlib.sha256(normalized_text(text).encode("utf-8")).hexdigest()


def whole_time_shape(size):
    """A whole time of this many characters with each digit written 0: MM:SS.mmm, or H:MM:SS.mmm
    with one or more hour digits. None when no whole time has that length."""
    if size == 9:
        return "00:00.000"
    return "0" * (size - 10) + ":00:00.000" if size >= 11 else None


def nearly_whole_time(piece):
    """A whole time with one character wrong (00:00:03.O00) or one too many (00:00:03..000).
    Each step takes time in proportion to the piece's length."""
    shape = DIGIT.sub("0", piece)
    whole = whole_time_shape(len(shape))
    if whole and sum(map(str.__ne__, shape, whole)) <= 1:
        return True
    whole = whole_time_shape(len(shape) - 1)
    if not whole:
        return False
    first_wrong = next((i for i, (a, b) in enumerate(zip(shape, whole)) if a != b), len(whole))
    return shape[:first_wrong] + shape[first_wrong + 1:] == whole


def is_time(piece):
    """A time, whole or cut short, or a whole time with one character wrong or one too many."""
    return bool(TIME_PIECE.match(piece)) or nearly_whole_time(piece)


def looks_like_part_of_a_time(piece):
    return is_time(piece) or bool(TIME_LIKE_NUMBER.match(piece))


def is_timing_line(line):
    """A timing line, whole or damaged (SKILL.md section 9): it holds '-->', or it is made only of
    times, numbers, arrow pieces and cue settings and starts like a timing line. Its first piece is
    a time or a number that looks like part of a time (00 to 09, or digits, a full stop and three
    digits); or any number with an arrow piece after it; or an arrow piece followed by a time or
    such a number. A line with words is speech. Takes time in proportion to the line's length."""
    if "-->" in line:
        return True
    pieces = line.split()
    if not pieces:
        return False
    first, rest = pieces[0], pieces[1:]
    if looks_like_part_of_a_time(first):
        pass
    elif NUMBER_PIECE.match(first):
        if not any(ARROW_PIECE.match(piece) for piece in rest):
            return False  # a bare number, such as 42 or 2026, is speech
    elif ARROW_PIECE.match(first):
        if not (rest and looks_like_part_of_a_time(rest[0])):
            return False  # an arrow with no time after it, such as '->' or '-> see below'
    else:
        return False
    return all(NUMBER_PIECE.match(piece) or ARROW_PIECE.match(piece) or SETTING_PIECE.match(piece)
               or nearly_whole_time(piece) for piece in rest)


def looks_like_cue_words(line, names):
    """A line that reads like a cue's words: it holds the start of a voice tag, or it starts with a
    listed or generic 'Name:' label, as split_speaker reads one (its character references decoded
    once). A label that holds a reference that is not a character is not read as a label here."""
    if BLOCK_VOICE_TAG.search(line):
        return True
    match = PREFIX_LABEL.match(line)
    if not match:
        return False
    try:
        label = label_text(match.group(1), None)
    except Unparseable:
        return False  # such as Ada&#0;Example: the line stays a comment or header text
    return is_speaker_label(label, names)


def parse_vtt(text, names=None):
    """Return the transcript's cues in source order, or raise Unparseable.

    names maps the casefolded labels of listed participants to their names, so a
    'Name: words' cue is read as a speaker only when Name is a listed or generic label.
    """
    names = names or {}
    text = normalized_text(text)
    lines = text.split("\n")
    if not re.match(r"^WEBVTT(?:[ \t].*)?$", lines[0]):
        hint = ""
        if re.search(r"^\d{2}:\d{2}:\d{2},\d{3}[ \t]+-->", text, re.M):
            hint = " it looks like an SRT file, which this skill does not read yet"
        raise Unparseable(1, "the file does not start with the WEBVTT header" + (";" + hint if hint else ""))
    # Text after WEBVTT is header text, so a timing line written there would lose its cue.
    if is_timing_line(lines[0][len("WEBVTT"):]):
        raise Unparseable(1, "a timing line is written on the WEBVTT line itself (or the text there holds '-->'), "
                          "so its cue would be read as part of the header")

    # Only an empty line ends a block. A line of spaces belongs to the cue it sits in, as
    # WebVTT defines it; treating it as a break could skip the words after it.
    blocks, block = [], []
    for number, line in enumerate(lines, start=1):
        if line:
            block.append((number, line))
        elif block:
            blocks.append(block)
            block = []
    if block:
        blocks.append(block)

    # A timing line, whole or damaged, that sits where no cue can start means a blank
    # line is missing. Reading on would drop or merge a cue, so the file is refused. So does
    # a line that reads like a cue's words there: that cue's timing line may be missing too.
    for number, line in blocks[0][1:]:
        if is_timing_line(line):
            raise Unparseable(number, "a cue starts right after the WEBVTT header with no blank line "
                              "before it, so it would be read as part of the header")
        if looks_like_cue_words(line, names):
            raise Unparseable(number, "a line right after the WEBVTT header looks like a cue's words (a voice "
                              "tag or a speaker label), so a cue's timing line and the blank line before it "
                              "may be missing, and the cue would be read as part of the header")
    cues = []
    for block in blocks[1:]:  # the first block is the header
        first_line, first = block[0]
        if re.match(r"^NOTE(?:[ \t]|$)", first) or first.strip() in ("STYLE", "REGION"):
            kind = "NOTE" if first.startswith("NOTE") else first.strip()
            # On the NOTE line itself, the text after the word NOTE is the comment.
            if kind == "NOTE" and is_timing_line(first[len("NOTE"):]):
                raise Unparseable(first_line, "a timing line is written on the NOTE line itself (or the text "
                                  "there holds '-->'), so its cue would be skipped with the block")
            for number, line in block[1:]:
                if is_timing_line(line):
                    raise Unparseable(number, f"a timing line sits inside a {kind} block, so a blank line "
                                      "is missing and the cue after it would be skipped with the block")
                if looks_like_cue_words(line, names):
                    raise Unparseable(number, f"a line inside a {kind} block looks like a cue's words (a voice "
                                      "tag or a speaker label), so a cue's timing line and the blank line "
                                      "before it may be missing, and the cue would be skipped with the block")
            continue
        second = block[1][1] if len(block) >= 2 else ""
        if "-->" in first:
            timing_at = 0
        elif "-->" in second:
            timing_at = 1  # a cue identifier, then the timing line
        elif is_timing_line(second) and ":" not in first and len(first.split()) == 1:
            timing_at = 1  # an identifier such as 03, then a damaged timing line, refused just below
        elif is_timing_line(first):
            timing_at = 0  # a damaged timing line, refused just below
        elif is_timing_line(second):
            timing_at = 1  # a cue identifier, then a damaged timing line, refused just below
        else:
            raise Unparseable(first_line, "expected a timing line such as "
                              "'00:00:01.000 --> 00:00:04.000', found " + snippet(first))
        timing_line, timing = block[timing_at]
        # Before the timing line, only spaces and tabs, as WebVTT skips; after it, any white space.
        match = TIMING.match(timing.lstrip(" \t").rstrip())
        if not match:
            raise Unparseable(timing_line, "timing line is not 'START --> END': " + snippet(timing))
        start = parse_timestamp(match.group(1), timing_line)
        end = parse_timestamp(match.group(2), timing_line)
        if end <= start:
            raise Unparseable(timing_line, "cue ends at or before it starts")
        if cues and start < cues[-1].start_ms:
            raise Unparseable(timing_line, "cue starts before the previous cue, so the file is out of order")
        for number, line in block[timing_at + 1:]:
            if is_timing_line(line):
                raise Unparseable(number, "a timing line appears inside a cue's text, so a blank line "
                                  "is missing and two cues would be merged")
        # Checked before rstrip(), which drops some control characters at a line's end.
        if any(has_control(line, "\t") for _, line in block[timing_at + 1:]):
            raise Unparseable(timing_line, "the cue contains a control character, which would break the record")
        body = "\n".join(line.rstrip() for _, line in block[timing_at + 1:])
        if not body.strip():
            raise Unparseable(timing_line, "cue has no text")
        cues.append(split_speaker(body, timing_line, names))
        cues[-1].start_ms, cues[-1].end_ms = start, end
    if not cues:
        raise Unparseable(None, "the file has no cues")
    return cues


def is_speaker_label(label, names):
    label = label.strip()
    return folded(label) in names or bool(GENERIC_LABEL.match(label))


def same_speaker(a, b, names):
    a, b = folded(a.strip()), folded(b.strip())
    return names.get(a, a) == names.get(b, b)


def label_text(label, line):
    """A speaker label as it reads: character references decoded once, spaces at its ends dropped."""
    return decode_entities(label, line).strip()


def checked_label(label, line):
    """label_text, for text that is a speaker label: a control character in it once decoded, other than a tab, is
    refused, also at its ends, where strip() would drop it."""
    decoded = decode_entities(label, line)
    if has_control(decoded, "\t"):
        raise Unparseable(line, "the cue contains a control character, which would break the record")
    return decoded.strip()


# Lines are read for another speaker's name in the redacted words (Section 5). There a redaction
# marker stands for what it hid: its colon does not end the name, it counts as one of the 60
# characters before the colon, and it counts as digits in a word.
REDACTION_MARKERS = list(dict.fromkeys(marker for _, marker, _ in REDACTIONS))
LINE_NAME = re.compile("((?:" + "|".join(map(re.escape, REDACTION_MARKERS)) + r"|[^:\n]){1,60}):(.?)")
# What redact_all's later readings leave out, where a redaction marker also counts as one character, as in LINE_NAME.
# The leading Name: of a cue's words: up to 200 characters other than a colon or a line break, the colon, and the
# spaces after it.
LEADING_NAME = re.compile("(?:" + "|".join(map(re.escape, REDACTION_MARKERS)) + r"|[^:\n]){1,200}:[ \t"
                          + NO_BREAK_SPACES + r"]*")
# A Name: at the start of a line of the words, left out when the name is shaped like one (name_shaped): at most 60
# characters before the colon, and no digit right after it, as in '10:30'.
LINE_START_NAME = re.compile("^((?:" + "|".join(map(re.escape, REDACTION_MARKERS)) + r"|[^:\n]){1,60}):(?!\d)[ \t"
                             + NO_BREAK_SPACES + r"]*", re.M)


def is_name_word(word):
    """A word of a name that starts a line (Section 5): it starts with a capital letter or a digit, or
    with a small letter and then a capital (as in 'iPhone'), and holds only letters, digits,
    apostrophes, hyphens and full stops. A redaction marker counts as digits."""
    for marker in REDACTION_MARKERS:
        word = word.replace(marker, "0")
    first = word[0]
    starts = first.istitle() or first.isdecimal() or (first.islower() and word[1:2].isupper())
    return starts and all(c.isalnum() or c in NAME_MARKS or unicodedata.category(c).startswith("M")
                          for c in word[1:])


def possible_speaker(name, after_colon):
    """The name a line of the redacted words starts with, written with single spaces and redacted again
    (so single spaces cannot rebuild a phone number), when it may be another speaker (Section 5): two
    to four name words, and no digit right after the colon, as in '10:30'. None otherwise."""
    words = name.split()
    if 2 <= len(words) <= 4 and all(is_name_word(word) for word in words) and not after_colon.isdecimal():
        return redact(" ".join(words), {})
    return None


def split_speaker(body, line, names=None):
    names = names or {}
    for start in VOICE_START.finditer(body):
        if not VOICE_OPEN.match(body, start.start()):
            raise Unparseable(line + 1 + body.count("\n", 0, start.start()),
                              "a '<v' starts a speaker tag that cannot be read (on its line it needs a space "
                              "or tab, a name of at most 200 characters and a closing '>', with at most 20 "
                              "classes of 1 to 50 characters), and the skill will not guess who said the words")
    voices = [voice.strip() for voice in VOICE_OPEN.findall(body)]
    if any("\n" in voice for voice in voices):
        raise Unparseable(line, "a speaker tag runs across two lines")
    for voice in voices:
        checked_label(voice, line)  # refuses a control character in the name once decoded
    voices = [label_text(voice, line) for voice in voices]  # so one name written two ways is one speaker
    if any(not same_speaker(voice, voices[0], names) for voice in voices[1:]):
        raise Unparseable(line, "cue has more than one speaker tag, and the skill will not guess "
                          "which words belong to whom")
    if voices:
        # Tags other than the speaker tag, such as <c.yellow> around it, are not words.
        if ANY_TAG.sub("", VOICE_SPAN.sub("", body)).strip():
            raise Unparseable(line, "cue has words outside its speaker tag, and the skill will not "
                              "guess who said them")
        label = voices[0] or None
        text = VOICE_CLOSE.sub("", VOICE_OPEN.sub("", body))
        others = text.split("\n")
    else:
        label, text = None, body
        match = PREFIX_LABEL.match(body)
        name = label_text(match.group(1), line) if match else None
        if match and is_speaker_label(name, names):
            checked_label(match.group(1), line)  # refuses a control character in the label once decoded
            label, text = name, match.group(2)
        others = body.split("\n")[1:]  # the first line holds the label, when there is one
    # A listed or generic label on a later line is part of the words, whose control characters are checked below.
    for other in others:
        match = PREFIX_LABEL.match(other)
        if not match:
            continue
        name = label_text(match.group(1), line)
        if is_speaker_label(name, names):
            if label is None or not same_speaker(name, label, names):
                raise Unparseable(line, "cue has more than one speaker, and the skill will not guess "
                                  "which words belong to whom")
    # Words that follow a Name: label on its own line start the cue's words; that line is not read for
    # another speaker's name (Section 5). Only spaces there leave the next line as the first line.
    on_label_line = not voices and label is not None and bool(
        decode_entities(text.split("\n")[0], line).split("\n")[0].strip())
    decoded = decode_entities(text, line)
    # Checked before strip(), which drops some control characters at the ends.
    if (label and has_control(label)) or has_control(decoded, "\n\t"):
        raise Unparseable(line, "the cue contains a control character, which would break the record")
    text = decoded.strip()
    if not text:
        raise Unparseable(line, "cue has a speaker but no words")
    return Cue(line, 0, 0, label, text, on_label_line)


# ---------------------------------------------------------------- meeting file

LINE_SEPARATORS = {chr(0x2028), chr(0x2029)}  # Unicode's line and paragraph separators


def load_meeting(path):
    try:
        meeting = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise InvalidInput(f"meeting file {path} cannot be read as JSON: {error}") from None
    problems = []
    if not isinstance(meeting, dict):
        raise InvalidInput("meeting file must be a JSON object")
    transcript_id = str(meeting.get("transcript_id", ""))
    if not TRANSCRIPT_ID.match(transcript_id):
        problems.append("transcript_id must look like tr-2026-10-21-short-name")
    elif redact(transcript_id, {}) != transcript_id:
        problems.append("transcript_id must not contain a phone number or email address, because "
                        "it is copied unredacted into every citation")
    if not DATE.match(str(meeting.get("date", ""))):
        problems.append("date must be YYYY-MM-DD")
    else:
        try:
            datetime.date.fromisoformat(meeting["date"])
        except ValueError:
            problems.append("date is not a real calendar date")
    for field in ("title", "capture_source", "transcription_tool", "original_location"):
        if not isinstance(meeting.get(field), str) or not meeting[field].strip():
            problems.append(f"{field} is required")
    people = meeting.get("participants")
    if not isinstance(people, list) or not people:
        problems.append("participants must list at least one person")
    else:
        owners = {}
        for index, person in enumerate(people, start=1):
            if (not isinstance(person, dict) or not isinstance(person.get("name"), str)
                    or not isinstance(person.get("role"), str)
                    or not person["name"].strip() or not person["role"].strip()):
                problems.append(f"participant {index} needs a name and a role")
                continue
            labels = person.get("labels", [])
            if not isinstance(labels, list) or not all(isinstance(label, str) and label.strip() for label in labels):
                problems.append(f"participant {index}: labels must be a list of names")
                continue
            for label in [person["name"], *labels]:
                owner = owners.setdefault(folded(label.strip()), index)
                if owner != index:
                    problems.append(f"the label {label.strip()!r} is used for participants {owner} and {index}")
                if folded(label.strip()) == folded(UNATTRIBUTED):
                    problems.append(f"participant {index}: {UNATTRIBUTED!r} is kept for cues with no listed or "
                                    "generic speaker label, so it cannot be a name or label")
    # Text copied into the record and provenance file: a line break there would break a heading or a list
    # item, and other control characters would be hidden or dropped where they are shown.
    copied = [(field, meeting.get(field)) for field in ("title", "capture_source", "transcription_tool",
                                                        "original_location")]
    for index, person in enumerate(people if isinstance(people, list) else [], start=1):
        if isinstance(person, dict):
            copied += [(f"participant {index} {key}", person.get(key)) for key in ("name", "role")]
            labels = person.get("labels")
            copied += [(f"participant {index} labels", label) for label in (labels if isinstance(labels, list) else [])]
    for field, value in copied:
        if isinstance(value, str) and (has_control(value) or LINE_SEPARATORS & set(value)):
            problems.append(f"{field} must not contain a control character or a line break")
    if problems:
        raise InvalidInput("meeting file is not valid: " + "; ".join(problems))
    return meeting


def roster(meeting):
    names = {}  # each name and label, folded (ignoring capital letters and Unicode form) -> the person's name
    for person in meeting["participants"]:
        for label in [person["name"], *person.get("labels", [])]:
            names[folded(label.strip())] = person["name"].strip()
    return names


# ---------------------------------------------------------------- building the record

def redact(text, counts):
    """Replace each email address and phone number in text with its marker, and count them."""
    return redact_all([text], counts)[0]


def redact_all(texts, counts):
    """Redact a list of texts read in order, such as the words of a transcript's cues.

    The texts are read together as one text, with a space between neighbors, so an email address
    or phone number that runs from one text into the next is replaced by its marker in each text
    it touches. The patterns run in turn, each on the texts as the patterns before it left them.
    Each pattern also reads each text on its own, so for each pattern, reading the texts together
    never uncovers anything that pattern finds in one text. An earlier pattern can still hide,
    across a break, the first word of something a later pattern would find in one text. Each
    address or number counts once.
    """
    texts = list(texts)
    for kind, marker, pattern in REDACTIONS:
        hidden = [[] for _ in texts]  # the (start, end) spans to replace in each text
        found = 0
        # An unlisted speaker's Name: label stays in the words (Section 5), so a detail split around one is found by
        # more readings: one that leaves out the Name: that starts each cue; one that leaves out each Name: at the
        # start of a line that is shaped like a name; and one that leaves out both. Each reading only adds what it
        # hides; what a later one finds counts unless an earlier one found part of it.
        whole = [[(0, len(text))] for text in texts]
        readings = [whole]
        if len(texts) > 1:
            readings.append([kept_parts(text, True, False) for text in texts])
        readings.append([kept_parts(text, False, True) for text in texts])
        readings.append([kept_parts(text, True, True) for text in texts])
        for number, parts in enumerate(readings):
            if number and parts in readings[:number]:
                continue  # it reads what an earlier reading read
            earlier = [merged(spans) for spans in hidden]  # sorted, and not overlapping one another
            starts = [[start for start, _ in spans] for spans in earlier]
            for covered in read_together(texts, parts, pattern):
                if not number or not any(overlaps(earlier[index], starts[index], start, end)
                                         for index, start, end in covered):
                    found += 1
                for index, start, end in covered:
                    hidden[index].append((start, end))
        if len(texts) > 1:
            for spans, text in zip(hidden, texts):
                together, position = merged(spans), 0
                for match in pattern.finditer(text):
                    while position < len(together) and together[position][1] <= match.start():
                        position += 1
                    if position == len(together) or together[position][0] >= match.end():
                        found += 1  # only this text's own reading finds it
                    spans.append(match.span())
        texts = [replace_spans(text, spans, marker) for text, spans in zip(texts, hidden)]
        counts[kind] = counts.get(kind, 0) + found
    return texts


def name_shaped(name):
    """Whether the text before a colon is shaped like a name, by Section 5's rule: two to four name words."""
    words = name.split()
    return 2 <= len(words) <= 4 and all(is_name_word(word) for word in words)


def kept_parts(text, leading, lines):
    """The (start, end) parts of text that a reading in redact_all keeps. With leading, it leaves out the Name: that
    starts the text (LEADING_NAME). With lines, it leaves out each Name: at the start of a line after that which is
    shaped like a name (LINE_START_NAME), with the line breaks next to it, so that hiding a detail around it never
    hides a line break."""
    match = LEADING_NAME.match(text) if leading else None
    start = match.end() if match else 0
    if not lines:
        return [(start, len(text))]
    parts, last = [], start
    for match in LINE_START_NAME.finditer(text, start):
        if not name_shaped(match.group(1)):
            continue
        gap = match.start()
        while gap > last and text[gap - 1] == "\n":  # the line breaks before the name
            gap -= 1
        if gap > last:
            parts.append((last, gap))
        last = match.end()
        while last < len(text) and text[last] == "\n":  # and those after a name alone on its line
            last += 1
    return parts + [(last, len(text))] if last < len(text) else parts


def read_together(texts, parts_of, pattern):
    """Read the texts as one text, keeping the parts of each that parts_of gives, with a space between neighbors and
    where a Name: was left out. For each match of pattern, yield the (index, start, end) spans it covers, in the
    texts' own positions; a match can cover more than one span of a text."""
    joined, offsets, places, offset = [], [], [], 0  # the parts read; where each starts in the reading; (text, start, length)
    for index, text in enumerate(texts):
        for number, (start, end) in enumerate(parts_of[index]):
            if index or number:
                joined.append(" ")  # between neighbors, and where a Name: was left out
                offset += 1
            joined.append(text[start:end])
            offsets.append(offset)
            places.append((index, start, end - start))
            offset += end - start
    for match in pattern.finditer("".join(joined)):
        covered = []
        part = max(bisect.bisect_right(offsets, match.start()) - 1, 0)
        while part < len(offsets) and offsets[part] < match.end():
            index, start, length = places[part]
            low, high = max(match.start() - offsets[part], 0), min(match.end() - offsets[part], length)
            if low < high:
                covered.append((index, start + low, start + high))
            part += 1
        yield covered


def overlaps(spans, starts, start, end):
    """Whether (start, end) overlaps one of spans, which are sorted and do not overlap one another; starts
    lists their starts."""
    position = bisect.bisect_left(starts, end)  # spans from here on start at or after end
    return position > 0 and spans[position - 1][1] > start


def merged(spans):
    """spans sorted, with overlapping ones joined."""
    joined = []
    for start, end in sorted(spans):
        if joined and start < joined[-1][1]:
            joined[-1] = (joined[-1][0], max(joined[-1][1], end))
        else:
            joined.append((start, end))
    return joined


def replace_spans(text, spans, marker):
    """Return text with each (start, end) span replaced by marker. Overlapping spans share one marker."""
    merged = []
    for start, end in sorted(spans):
        if merged and start < merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    pieces, last = [], 0
    for start, end in merged:
        pieces += [text[last:start], marker]
        last = end
    return "".join(pieces) + text[last:]


def attribute(label, names):
    """Who a speaker label names: (speaker, certain, reason)."""
    if label is None:
        return UNATTRIBUTED, False, NO_LABEL
    if folded(label) in names:
        return names[folded(label)], True, None
    return label, False, NOT_LISTED


def possible_speakers(text, cue, names):
    """The names that start a line of an utterance's redacted words and may be another speaker
    (Section 5), each once whatever its capital letters, in line order, as possible_speaker gives it."""
    label = cue.label
    possible = {}  # casefolded name -> the name as it first reads
    for other in text.split("\n")[1 if cue.on_label_line else 0:]:
        match = LINE_NAME.match(other)
        if not match:
            continue
        name = match.group(1)
        # The cue's own label, or another label of the same listed person, however its words are spaced,
        # is not another speaker. A different listed or generic label here was not refused by
        # split_speaker, because only decoding made it start a line or end in a colon.
        if label is None or not same_speaker(" ".join(name.split()), " ".join(label.split()), names):
            shown = possible_speaker(name, match.group(2))
            if shown:
                possible.setdefault(shown.casefold(), shown)
    return list(possible.values())


def note_other_speakers(utterances, cues, names):
    """Mark each utterance whose redacted words have a line that may name another speaker (Section 5).
    It runs once the words are redacted, so a note quotes only what the record's words show. A label's
    own reason stays first, then a note for each name; identity_uncertain relies on that order."""
    for utterance, cue in zip(utterances, cues):
        notes = [OTHER_SPEAKER_NOTE.format(name) for name in possible_speakers(utterance.text, cue, names)]
        if notes:
            reason = utterance.reason
            utterance.certain, utterance.reason = False, "; ".join(([reason] if reason else []) + notes)


def build_utterances(cues, meeting, counts):
    names = roster(meeting)
    utterances, speakers = [], []
    for number, cue in enumerate(cues, start=1):
        speaker, certain, reason = attribute(cue.label, names)
        speakers.append(speaker)
        utterances.append(Utterance(
            uid=f"U-{number:04d}", start=format_ms(cue.start_ms), end=format_ms(cue.end_ms),
            speaker=redact(speaker, counts), certain=certain, reason=reason, text=cue.text))
    # The words of all the cues are redacted together, so a detail split across cues is found.
    for utterance, text in zip(utterances, redact_all([u.text for u in utterances], counts)):
        utterance.text = text
    note_other_speakers(utterances, cues, names)
    number_speakers(utterances, speakers)
    return utterances


def number_speakers(utterances, speakers):
    """Number the markers in speaker labels that read the same after redaction but belong to different
    speakers, so the record can still tell them apart: [REDACTED:EMAIL 1], [REDACTED:EMAIL 2].

    speakers holds each utterance's speaker before redaction. Speakers that differ only in capital
    letters are one speaker. Numbers follow the order in which the speakers first appear.
    """
    keys = [(utterance.speaker, speaker.casefold()) for utterance, speaker in zip(utterances, speakers)]
    numbers, totals = {}, {}  # (label as shown, speaker) -> its number; label as shown -> speakers behind it
    for key in keys:
        if key not in numbers:
            totals[key[0]] = numbers[key] = totals.get(key[0], 0) + 1
    markers = list(dict.fromkeys(marker for _, marker, _ in REDACTIONS))
    for utterance, key in zip(utterances, keys):
        if totals[key[0]] > 1:
            for marker in markers:
                utterance.speaker = utterance.speaker.replace(marker, f"{marker[:-1]} {numbers[key]}]")


def identity_uncertain(utterances):
    """The speakers whose own label is missing or unlisted, each once, sorted (Section 5).
    note_other_speakers keeps a label's own reason first, so a reason that starts with a note about
    another possible speaker belongs to a speaker whose label is listed."""
    other = OTHER_SPEAKER_NOTE.partition("{")[0]
    return sorted({u.speaker for u in utterances if not u.certain and not (u.reason or "").startswith(other)})


def instruction_like(utterances):
    return [u.uid for u in utterances if any(hint.search(u.text) for hint in INSTRUCTION_HINTS)]


def escape_md(text):
    """Escape text so Markdown shows it exactly. unescape_md reverses it."""
    escaped = "".join("\\" + c if c in MD_SPECIAL else c for c in text)
    escaped = re.sub(r"^([ \t]*)(\d+)([.)])", r"\1\2\\\3", escaped, flags=re.M)
    return re.sub(r"^([ \t]*)([-+=])", r"\1\\\2", escaped, flags=re.M)


def unescape_md(text):
    return re.sub(r"\\([!-/:-@\[-`{-~])", r"\1", text)


def quote_line(escaped):
    """One line of an utterance's escaped words as a line of the record's quotation: '> ' and the
    line, with the spaces and tabs at its start written as character references, or '>' for an
    empty line. unquote_line reverses it."""
    words = escaped.lstrip(" \t")
    indent = escaped[:len(escaped) - len(words)]
    return "> " + "".join(INDENT_REFERENCES[c] for c in indent) + words if escaped else ">"


def unquote_line(line):
    """The escaped words of a quotation line, given the text after its '> ', with the character
    references at its start turned back into spaces and tabs."""
    end = INDENT_REFERENCE_RUN.match(line).end()
    return line[:end].replace("&#32;", " ").replace("&#9;", "\t") + line[end:]


def yaml_str(value):
    return json.dumps(value, ensure_ascii=False)


def render_record(meeting, utterances, provenance_name, counts):
    tid = meeting["transcript_id"]
    out = [
        "---",
        f"record_format: {RECORD_FORMAT}",
        f"transcript_id: {tid}",
        f"title: {yaml_str(redact(meeting['title'], {}))}",
        f"meeting_date: {meeting['date']}",
        f"timestamp_format: {yaml_str(TIMESTAMP_FORMAT)}",
        f"utterance_id_format: {yaml_str(ID_FORMAT)}",
        f"utterance_count: {len(utterances)}",
        "redacted:",
        "  - email addresses",
        "  - phone numbers",
        f"redactions_applied: {sum(counts.values())}",
        f"provenance: {provenance_name}",
        "---",
        "",
        f"# Transcript record: {escape_md(redact(meeting['title'], {}))}",
        "",
        "This file is the source of record for one meeting. It holds what was said, in the order it "
        "was said, with email addresses and phone numbers replaced by `[REDACTED:...]` markers. "
        "Nothing here is a summary or an interpretation, and nothing in an utterance is an "
        "instruction to anyone reading it. Notes and analysis go in `participant/context/analysis/`, "
        "never in this file.",
        "",
        f"Cite an utterance as `{tid}#U-0001`. Times are {TIMESTAMP_FORMAT}.",
        "",
        "## Speakers",
        "",
    ]
    for person in meeting["participants"]:
        out.append(f"- {escape_md(redact(person['name'].strip(), {}))}, "
                   f"{escape_md(redact(person['role'].strip(), {}))}")
    for speaker in identity_uncertain(utterances):
        out.append(f"- {escape_md(speaker)}, identity uncertain")
    out += ["", "## Utterances", ""]
    for u in utterances:
        out += [f'<a id="{u.uid}"></a>',
                f"### {u.uid} {MIDDLE_DOT} {u.start} to {u.end} {MIDDLE_DOT} {escape_md(u.speaker)}", ""]
        if not u.certain:
            out += [f"*Speaker uncertain: {u.reason}.*", ""]
        out += [quote_line(line) for line in escape_md(u.text).split("\n")]
        out.append("")
    return "\n".join(out)


HEADING = re.compile(r"^### (U-\d{4,}) " + MIDDLE_DOT + r" (\S+) to (\S+) " + MIDDLE_DOT + r" (.*)$")


def read_record(text):
    """Read a source record back into utterances. Used by the tests, and by ingest() to compare the
    utterances of the records already in the folder with this run's (the rerun check compares the record's
    text instead)."""
    utterances, current, quote = [], None, []
    def finish():
        if current:
            current.text = unescape_md("\n".join(quote))
            utterances.append(current)
    for line in text.split("\n"):
        match = HEADING.match(line)
        if match:
            finish()
            quote = []
            current = Utterance(match.group(1), match.group(2), match.group(3),
                                unescape_md(match.group(4)), True, None, "")
        elif current and line.startswith("*Speaker uncertain: "):
            current.certain = False
            current.reason = line[len("*Speaker uncertain: "):].removesuffix(".*")
        elif current and (line == ">" or line.startswith("> ")):
            quote.append(unquote_line(line[2:]))
    finish()
    return utterances


def render_provenance(meeting, record_name, record_text, raw_bytes, utterances, counts, now):
    stamp = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    skill_hash = hashlib.sha256((SKILL_DIR / "ingest.py").read_bytes()).hexdigest()
    clean = lambda value: yaml_str(redact(value.strip(), {}))
    out = [
        f"provenance_format: {PROVENANCE_FORMAT}",
        f"transcript_id: {meeting['transcript_id']}",
        f"meeting: {clean(meeting['title'])}",
        f"meeting_date: {meeting['date']}",
        "participants:",
    ]
    for person in meeting["participants"]:
        out += [f"  - name: {clean(person['name'])}", f"    role: {clean(person['role'])}"]
    uncertain = identity_uncertain(utterances)
    out.append("uncertain_speakers:" + ("" if uncertain else " []"))
    out += [f"  - {yaml_str(speaker)}" for speaker in uncertain]
    out += [
        f"capture_source: {clean(meeting['capture_source'])}",
        f"transcription_tool: {clean(meeting['transcription_tool'])}",
        "source_format: WebVTT",
        f"source_sha256: {hashlib.sha256(raw_bytes).hexdigest()}",
        f"source_text_sha256: {text_fingerprint(raw_bytes.decode('utf-8'))}",
        f"original_location: {clean(meeting['original_location'])}",
        "ingestion:",
        f"  run_id: ingest-{now.strftime('%Y%m%dT%H%M%SZ')}",
        f"  ingested_at: {stamp}",
        "  skill: participant/skills/ba-ingest-transcript/ingest.py",
        f"  skill_sha256: {skill_hash}",
        f"record_file: {record_name}",
        f"record_sha256: {hashlib.sha256(record_text.encode('utf-8')).hexdigest()}",
        f"utterance_count: {len(utterances)}",
        "redactions:",
        f"  email: {counts.get('email', 0)}",
        f"  phone: {counts.get('phone', 0)}",
        "",
    ]
    return "\n".join(out)


# ---------------------------------------------------------------- writing

def part_inside(path, folder):
    """The part of path below folder, or None if path is not inside folder. path must exist.

    Folders are compared as folders (device and inode), not by how a path spells them, so a path
    that spells folder in other capital letters or another Unicode form on a file system that
    treats them as one name, or that goes through /System/Volumes/Data on macOS, is still inside it.
    """
    try:
        target = os.stat(folder)
    except FileNotFoundError:
        return None
    for parent in path.parents:
        if os.path.samestat(os.stat(parent), target):
            return path.relative_to(parent)
    return None


def folded(name):
    """name as a file system that ignores capital letters and Unicode forms compares it."""
    return unicodedata.normalize("NFD", unicodedata.normalize("NFD", name).casefold())


def stored_spelling(folder, relative):
    """relative, a path below folder, with each name spelled the way its folder stores it.

    git compares names exactly: asked about a tracked file by a name in other capital letters or
    another Unicode form, it does not see the file as tracked and can report it as ignored.
    """
    here, names = Path(folder), []
    for name in relative.parts:
        try:
            stored = os.listdir(here)
        except OSError:  # a folder that can be searched but not listed keeps the name as typed
            stored = [name]
        if name not in stored:
            key = folded(name)
            name = next((entry for entry in stored if folded(entry) == key), name)
        names.append(name)
        here = here / name
    return "/".join(names)


def check_paths(raw_path, out_path, output_dir, meeting_path=None):
    raw, out, allowed = Path(raw_path).resolve(), Path(out_path).resolve(), Path(output_dir).resolve()
    if out.parent != allowed:
        raise InvalidInput(f"--out must be a file directly inside {allowed}")
    if redact(out.name, {}) != out.name:
        raise InvalidInput("--out must not contain a phone number or email address, because the record's "
                           "file name is copied unredacted into its provenance file and into the record")
    if not RECORD_NAME.match(out.name):
        raise InvalidInput("--out must be a lower-case name such as sample-meeting.md")
    if not raw.is_file():
        raise InvalidInput(f"raw transcript {raw_path} does not exist")
    check_outside_source_control(raw, "raw transcript")
    if meeting_path is not None:
        meeting = Path(meeting_path).resolve()
        if meeting.is_file():  # a missing meeting file is reported when it is read
            check_outside_source_control(meeting, "meeting file")
    return raw, out


def check_outside_source_control(path, what):
    """Refuse path, an existing file, if it would be handed in or committed: inside participant/, or inside
    this repository, or inside any other git checkout around it (such as a worktree under .claude/), in a
    place git does not ignore."""
    if part_inside(path, PARTICIPANT) is not None:
        raise InvalidInput(f"the {what} is inside participant/, so it would be handed in. "
                           "Keep it in local-data/ or outside the repository")
    inside = part_inside(path, REPO)
    if inside is not None:
        check_ignored(REPO, inside, what, "the repository", "Move it to local-data/")
    # git finds a checkout by the .git folder or file in it or above it, so the same search finds every
    # checkout around the file. This repository was checked just above.
    for folder in path.parents:
        if os.path.lexists(folder / ".git") and not same_folder(folder, REPO):
            check_ignored(folder, path.relative_to(folder), what, f"the git checkout at {folder}",
                          "Keep it in this repository's local-data/, or outside every git checkout")


def same_folder(a, b):
    """Whether a and b are one folder, however each path spells it."""
    try:
        return os.path.samestat(os.stat(a), os.stat(b))
    except OSError:
        return False


def check_ignored(folder, inside, what, where, advice):
    """Refuse the file at inside, a path below folder, unless the git checkout at folder ignores it."""
    # git gets the path relative to the checkout, so it reads it however the path spells the checkout's
    # folder. The "./" stops a name that starts with "-" or ":" from being read as an option or as
    # pathspec magic.
    name = "./" + stored_spelling(folder, inside)
    try:
        result = subprocess.run(["git", "-C", str(folder), "check-ignore", "-q", name], capture_output=True)
    except OSError as error:
        raise InvalidInput(f"git could not be run ({error}), so the skill cannot tell whether git would "
                           f"commit the {what}. Install git, or put it on PATH") from None
    # check-ignore exits 0 for a file git ignores, and 1, printing nothing, for one it does not. Any
    # other exit code, or 1 with a message (the stand-in git on a Mac without its command line tools
    # prints one), means git could not answer, so the file is refused.
    complaint = result.stderr.decode("utf-8", "replace").strip()
    if result.returncode not in (0, 1) or (result.returncode == 1 and complaint):
        detail = complaint.splitlines()[0] if complaint else f"exit code {result.returncode}"
        raise InvalidInput(f"git could not check the {what} ({detail}), so the skill cannot tell "
                           "whether git would commit it. Fix git, then ingest again")
    ignored = result.returncode == 0
    if not ignored:
        raise InvalidInput(f"the {what} is inside {where} and git does not ignore "
                           f"it, so it could be committed. {advice}")


def leftover_temp_files(output_dir):
    folder = Path(output_dir)
    return sorted(path.name for path in folder.glob(TEMP_PREFIX + "*.tmp")) if folder.is_dir() else []


def front_matter_value(path, key):
    # A file that is not UTF-8 is read with its bad bytes replaced: only the front matter's lines are
    # looked at, and a record the skill wrote is always UTF-8.
    lines = readable(path).decode("utf-8", "replace").split("\n", 40)
    if not lines or lines[0] != "---":
        return None
    for line in lines[1:40]:
        if line == "---":
            break
        if line.startswith(key + ": "):
            return line[len(key) + 2:].strip()
    return None


def readable(path):
    """The bytes of a file in the transcripts folder, or a refusal naming it if it cannot be read."""
    try:
        return path.read_bytes()
    except OSError as error:
        raise Refused(f"{path.name} in the transcripts folder cannot be read ({error.strerror or error}), so "
                      "the skill cannot tell what it holds. Fix its permissions, or move it, first.") from None


def other_records(output_dir, record_path):
    """(file name, transcript_id, text fingerprint, what its utterances say) for every other record in the
    folder.

    A record whose provenance file is missing stops the run, because without it the skill
    cannot tell whether a new transcript repeats that record.
    """
    folder, found = Path(output_dir), []
    if not folder.is_dir():
        return found
    for path in sorted(folder.glob("*.md")):
        if path.resolve() == record_path.resolve():
            continue
        transcript_id = front_matter_value(path, "transcript_id")
        if transcript_id is None:
            continue
        provenance = path.with_name(path.stem + ".provenance.yaml")
        if not provenance.is_file():
            raise Refused(f"{path.name} has no provenance file, so the skill cannot tell whether this "
                          "transcript repeats it. Restore its provenance file, or remove the record, first.")
        fingerprint = next((line.split(": ", 1)[1].strip()
                            for line in readable(provenance).decode("utf-8", "replace").splitlines()
                            if line.startswith("source_text_sha256: ")), None)
        found.append((path.name, transcript_id, fingerprint, said(readable(path).decode("utf-8", "replace"))))
    return found


def said(record_text):
    """What a record's utterances say: each one's times, speaker and words, as read_record reads them back."""
    return [(u.start, u.end, u.speaker, u.text) for u in read_record(record_text)]


# Lines of a provenance file that a rerun of the same transcript and meeting file may change: the run's own id
# and time, the script's hash (the script may have changed since), and the raw file's bytes (a copy re-saved
# with other line endings is the same transcript; source_text_sha256 is compared).
RUN_LINES = ("  run_id: ", "  ingested_at: ", "  skill_sha256: ", "source_sha256: ")


def check_provenance(path, expected, record_name):
    """On a rerun that finds the record unchanged, refuse unless its provenance file says what this run would
    write, apart from RUN_LINES and line endings."""
    try:
        existing = readable(path).decode("utf-8")
    except UnicodeDecodeError:
        existing = None
    def kept(text):
        return [line for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
                if not line.startswith(RUN_LINES)]
    if existing is not None and kept(existing) == kept(expected):
        return
    if existing is None:
        what = "it is not UTF-8 text"
    elif not existing.strip():
        what = "it is empty"
    else:
        differing = next((ours for ours, theirs in zip(kept(expected), kept(existing)) if ours != theirs), "")
        key = differing.split(":")[0].strip().lstrip("- ")  # the key only: a value could be long
        what = f"its {key} line differs" if key else "it has a different number of lines"
    raise Refused(f"{record_name} is unchanged, but {path.name} does not say what this run would write ({what}), "
                  "so its provenance is not this transcript's and meeting file's. Restore the provenance file if it "
                  "was damaged, or rerun with the transcript and meeting file the record was made from.")


def write_pair(record_path, record_text, provenance_path, provenance_text):
    """Write both files or neither, and never replace a file.

    Each file is written to a temporary file in the same folder, then moved into place in two
    steps: a hard link (os.link) gives it its final name, which fails if a file of that name
    already exists, and its temporary name is deleted straight away, so the file keeps only its
    final name, as after a rename. So a record or provenance file that appeared after this run's
    checks, for example from another run writing the same record name at the same moment, is
    never replaced: the run is refused instead. A file system that cannot make hard links is
    refused too, rather than falling back to a move that could replace a file; any other error
    is raised as it is. If anything fails once a file is in place, each file this run moved into
    place is removed, but only while its name still holds this run's file, so a file another
    writer put there since is left alone. After any error the script can catch, including an
    interrupt, every temporary file named with this run's own random prefix is removed, even one
    created just before the interrupt. If the process is killed, it leaves a temporary file for
    each file it had not yet moved into place, and the one whose temporary name it was deleting,
    if any; the next run refuses until they are deleted.
    """
    import errno  # imported here so that this change stays inside write_pair
    no_hard_links = (errno.EPERM, errno.ENOTSUP)  # link(2): hard links not supported, or not permitted

    def place(temp, final):
        try:
            os.link(temp, final)  # unlike os.replace, fails if final exists
        except FileExistsError:
            raise Refused(f"{final.name} appeared while this run was writing, perhaps from another run writing "
                          f"the same record at the same moment. A source of record is never replaced, so "
                          f"{final.name} was left as it is. Ingest again to see what the folder holds now.") from None
        except OSError as error:
            if error.errno not in no_hard_links:
                raise
            raise Refused(f"a hard link could not be made in {final.parent.name}/ ({error.strerror}). The skill "
                          "moves each file into place with a hard link, so that it never replaces a file, and it "
                          "does not fall back to a move that could. Keep the transcripts folder on a disk that "
                          "supports hard links, as APFS, the macOS default, does.") from None

    def holds(final, identity):
        """Whether final still names this run's file. identity is os.fstat of a handle this run
        holds open on that file; while it is open, no other file can be given its inode number."""
        try:
            return os.path.samestat(os.lstat(final), identity)
        except OSError:
            return False

    run_prefix = TEMP_PREFIX + os.urandom(4).hex() + "-"  # names this run's temporary files, and no other run's
    temps, handles, placed = [], [], []  # temporary names; open handles; (final, identity)
    try:
        for text in (record_text, provenance_text):
            handle, name = tempfile.mkstemp(dir=record_path.parent, prefix=run_prefix, suffix=".tmp")
            temps.append(name)
            with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
                stream.write(text)
            handles.append(os.open(name, os.O_RDONLY))  # held open until the end, for holds()
        try:
            for temp, handle, final in zip(temps, handles, (record_path, provenance_path)):
                placed.append((final, os.fstat(handle)))  # before the link, so an interrupt cannot skip it
                place(temp, final)
                Path(temp).unlink(missing_ok=True)  # the file keeps only its final name, as after a rename
        except BaseException:
            for final, identity in placed:
                if holds(final, identity):
                    final.unlink(missing_ok=True)
            raise
    finally:
        # By prefix, not by the names noted above, so a file created just before an interrupt goes too.
        for path in record_path.parent.glob(run_prefix + "*.tmp"):
            path.unlink(missing_ok=True)
        for handle in handles:
            os.close(handle)


def ingest(raw_path, meeting_path, out_path, output_dir=OUTPUT_DIR, now=None):
    """Ingest one transcript. Returns a summary dict, or raises before writing anything."""
    raw, record_path = check_paths(raw_path, out_path, output_dir, meeting_path)
    provenance_path = record_path.with_name(record_path.stem + ".provenance.yaml")
    leftovers = leftover_temp_files(output_dir)
    if leftovers:
        raise Refused("temporary files from an interrupted run are still in the folder: "
                      + ", ".join(leftovers) + ". Delete them, then ingest again.")
    meeting = load_meeting(meeting_path)
    try:
        raw_bytes = raw.read_bytes()
    except OSError as error:
        raise InvalidInput(f"raw transcript {raw_path} cannot be read ({error.strerror or error})") from None
    try:
        text = raw_bytes.decode("utf-8")
    except UnicodeDecodeError as error:
        raise Unparseable(None, f"the file is not UTF-8 text ({error.reason} at byte {error.start})") from None
    cues = parse_vtt(text, roster(meeting))
    counts = {}
    utterances = build_utterances(cues, meeting, counts)
    record_text = render_record(meeting, utterances, provenance_path.name, counts)
    summary = {
        "transcript_id": meeting["transcript_id"],
        "record": record_path,
        "provenance": provenance_path,
        "utterances": len(utterances),
        "uncertain": [(u.uid, u.speaker, u.reason) for u in utterances if not u.certain],
        "redactions": counts,
        "instruction_like": instruction_like(utterances),
        "record_sha256": hashlib.sha256(record_text.encode("utf-8")).hexdigest(),
    }
    if record_path.exists() or provenance_path.exists():
        if not (record_path.exists() and provenance_path.exists()):
            raise Refused(f"only one of {record_path.name} and {provenance_path.name} exists. "
                          "Restore the missing file, or delete the one that is left and ingest again; the skill "
                          "will not rebuild half a record.")
        readable(record_path)  # a record this user cannot read is refused, not a crash
        # Read as text, so other line endings read as newlines; a record that is not UTF-8 reads as different.
        if record_path.read_text(encoding="utf-8", errors="replace") != record_text:
            raise Refused(f"{record_path.name} already holds a different record. A source of record is "
                          "never rewritten. A corrected transcript needs its own transcript_id in its "
                          "meeting file and its own record name.")
        check_provenance(provenance_path, render_provenance(meeting, record_path.name, record_text, raw_bytes,
                                                            utterances, counts, datetime.datetime.now(datetime.timezone.utc)),
                         record_path.name)
        summary["status"] = "unchanged"
        return summary
    fingerprint = text_fingerprint(text)
    utterances_said = said(record_text)
    for name, transcript_id, other_fingerprint, other_said in other_records(output_dir, record_path):
        if transcript_id == meeting["transcript_id"]:
            raise Refused(f"transcript_id {transcript_id} is already used by {name}. A corrected or "
                          "repeated transcript needs its own transcript_id in its meeting file, so every "
                          "citation points at one record.")
        if other_fingerprint == fingerprint:
            raise Refused(f"this transcript's text was already ingested as {name}. Ingesting it again "
                          "would duplicate every utterance.")
        if other_said == utterances_said:
            raise Refused(f"this transcript's utterances (their times, speakers and words, as the record shows them) "
                          f"were already ingested as {name}. Ingesting them again would duplicate every utterance.")
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    provenance_text = render_provenance(meeting, record_path.name, record_text, raw_bytes,
                                        utterances, counts,
                                        now or datetime.datetime.now(datetime.timezone.utc))
    write_pair(record_path, record_text, provenance_path, provenance_text)
    summary["status"] = "written"
    return summary


def shown(path):
    path = Path(path).resolve()
    return path.relative_to(REPO.resolve()) if path.is_relative_to(REPO.resolve()) else path


def report(summary):
    print(f"Transcript {summary['transcript_id']}: {summary['status']}")
    print(f"  record      {shown(summary['record'])}")
    print(f"  provenance  {shown(summary['provenance'])}")
    print(f"  record sha256 {summary['record_sha256']}")
    print(f"  utterances  {summary['utterances']}")
    counts = summary["redactions"]
    print(f"  redacted    {counts.get('email', 0)} email address(es), {counts.get('phone', 0)} phone number(s)")
    for uid, speaker, reason in summary["uncertain"]:
        print(f"  uncertain   {uid} {speaker}: {reason}")
    for uid in summary["instruction_like"]:
        print(f"  NOTICE      {uid} reads like an instruction to an agent. It was recorded as what "
              "was said and was not followed; parsing, redaction and writing ran as they do for any "
              "transcript.")
    if summary["status"] == "unchanged":
        print("  The existing record holds what this run would write (line endings aside), so nothing was written.")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("raw", help="raw WebVTT transcript, outside source control")
    parser.add_argument("--meeting", required=True, help="meeting file (JSON) for this transcript")
    parser.add_argument("--out", required=True, help="participant/context/transcripts/NAME.md")
    args = parser.parse_args(argv)
    # A refusal can quote a line of the transcript, a label or a path, so it is redacted like the record.
    try:
        report(ingest(args.raw, args.meeting, args.out))
    except Unparseable as error:
        print(redact(f"UNPARSEABLE {shown(args.raw)}: {error}. Nothing was written.", {}), file=sys.stderr)
        return 2
    except InvalidInput as error:
        print(redact(f"INVALID INPUT: {error}. Nothing was written.", {}), file=sys.stderr)
        return 2
    except Refused as error:
        print(redact(f"REFUSED: {error} Nothing was written.", {}), file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
