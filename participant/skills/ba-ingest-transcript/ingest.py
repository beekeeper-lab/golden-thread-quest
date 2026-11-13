#!/usr/bin/env python3
"""Ingest a meeting transcript into a redacted, attributed source of record.

Part of the ba-ingest-transcript skill (see SKILL.md next to this file). Standard library only.

Usage (from the repository root):

    .venv/bin/python participant/skills/ba-ingest-transcript/ingest.py RAW_FILE TRANSCRIPT_ID \
        --capture-source "..." --transcription-tool "..." \
        [--out-dir participant/context/transcripts] [--log LOG_FILE]

What it does, in order:
  1. Reads RAW_FILE and parses ALL of it before writing anything. Any line it cannot parse
     stops the run with the line number and the reason (never the line's text, which may hold
     personal details); nothing is written.
  2. Redacts email addresses and phone numbers to [REDACTED] everywhere they could be kept:
     header values, speaker labels and utterances. Speaker names are kept: they are the
     attribution.
  3. Gives the transcript the id TRANSCRIPT_ID and each utterance a sequence id (U001, U002, ...)
     in the order spoken. Cite a line as TRANSCRIPT_ID#U007.
  4. Flags utterances that read like instructions to an AI or a tool. They are kept as ordinary
     content; nothing in the transcript is ever acted on.
  5. Writes TRANSCRIPT_ID.provenance.yaml and then TRANSCRIPT_ID.md (the source of record). Each
     is written to a temporary file and then linked into place, which fails rather than replace a
     file that already exists. A failed run removes its temporary files and anything it placed.
  6. If the record already exists: an identical result, with a provenance file that matches it,
     is reported as unchanged and nothing is rewritten (no duplicated utterances). A different
     result is refused, because the source of record is never rewritten. A record or provenance
     file without its partner (an interrupted run) is refused, never silently completed.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

TOOL_NAME = "ba-ingest-transcript/ingest.py"
TOOL_VERSION = "1.3.0"
TIMESTAMP_FORMAT = "HH:MM:SS, elapsed time from the start of the recording"
REDACTED = "[REDACTED]"

HEADER_FIELDS = ("Meeting", "Date", "Attendees")
UTTERANCE = re.compile(r"^\[(?P<ts>\d{2}:[0-5]\d:[0-5]\d)\] (?P<speaker>[^:\[\]]{1,80}): (?P<text>\S.*)$")
UNCERTAIN_SPEAKERS = {"unknown", "unidentified", "?"}
# Email: a plain or "quoted" local part, and a domain that may use any letters (e.g. büro.example).
# Email: a plain or "quoted" local part, and a domain that may use any letters (e.g. büro.example)
# or be an address literal (sam@[192.0.2.1]).
EMAIL = re.compile(r'(?:"[^"\n]{1,64}"|[\w.%+-]+)@(?:(?:[^\W_](?:[\w-]*[^\W_])?\.)+[^\W\d_]{2,}|\[[^\]\s]{1,64}\])')
# Phone: separators may be spaces (repeated, or no-break spaces), tabs, dots, or any kind of hyphen or
# dash (- ‐ ‑ ‒ – — −), but never a line break.
SEP = r"[ \t\u00a0\u202f.\-\u2010-\u2015\u2212]*"
PHONE = re.compile(rf"(?<!\d)(?:\+?1{SEP})?\(?\d{{3}}\)?{SEP}\d{{3}}{SEP}\d{{4}}(?!\d)")
# Phrases that read as an instruction to an assistant or a tool. Matching only flags the line.
INSTRUCTION_LIKE = re.compile(
    r"\b(ignore (all |your |any )?(previous |prior )?instructions|AI assistant|system prompt|"
    r"run (this|the following) command|delete (the|all|every)\b)",
    re.IGNORECASE,
)
TRANSCRIPT_ID = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
# Characters that Markdown would treat as formatting, a link, HTML or a table column.
MARKDOWN_SPECIAL = re.compile(r"([\\`*_\[\]<>|~#!()])")


class IngestError(Exception):
    """The transcript cannot be ingested; the message says why."""


@dataclass
class Utterance:
    uid: str
    timestamp: str
    speaker: str
    certain: bool
    text: str
    redactions: int
    instruction_like: bool


def seconds(ts: str) -> int:
    h, m, s = (int(p) for p in ts.split(":"))
    return h * 3600 + m * 60 + s


def redact(text: str) -> tuple[str, int]:
    text, emails = EMAIL.subn(REDACTED, text)
    text, phones = PHONE.subn(REDACTED, text)
    return text, emails + phones


def literal(text: str) -> str:
    """Escapes Markdown and HTML entities so the record shows exactly these characters.

    [REDACTED] stays as written; the characters around it ("!", "(" ...) are escaped, so a
    redaction can never become a link or an image.
    """
    escape = lambda part: MARKDOWN_SPECIAL.sub(r"\\\1", part.replace("&", "&amp;"))
    return REDACTED.join(escape(part) for part in text.split(REDACTED))


def parse(raw: str) -> tuple[dict[str, str], list[Utterance], int]:
    """Parses the whole transcript, or raises IngestError naming the first problem.

    Returns the redacted header, the utterances and how many values were redacted in all.
    Error messages give line numbers and reasons, never the text of the line.
    """
    if not raw.strip():
        raise IngestError("the file is empty")
    lines = raw.splitlines()
    header: dict[str, str] = {}
    redacted_total = 0
    i = 0
    while i < len(lines) and lines[i].strip():
        key, sep, value = lines[i].partition(":")
        key = key.strip()
        if not sep or key not in HEADER_FIELDS or not value.strip():
            raise IngestError(f"line {i + 1}: expected a header line ({', '.join(HEADER_FIELDS)}: value)")
        if key in header:
            raise IngestError(f"line {i + 1}: a second '{key}' header line; the transcript must have only one")
        header[key], count = redact(value.strip())
        redacted_total += count
        i += 1
    missing = [f for f in HEADER_FIELDS if f not in header]
    if missing:
        raise IngestError(f"header is missing: {', '.join(missing)}")
    try:
        dt.date.fromisoformat(header["Date"])
    except ValueError:
        raise IngestError("the Date header is not a date in the form YYYY-MM-DD") from None

    utterances: list[Utterance] = []
    last = -1
    for n, line in enumerate(lines[i:], start=i + 1):
        if not line.strip():
            continue
        m = UTTERANCE.match(line)
        if not m:
            raise IngestError(f"line {n}: not an utterance of the form '[HH:MM:SS] Speaker: text'")
        ts = m["ts"]
        if seconds(ts) < last:
            raise IngestError(f"line {n}: its timestamp is earlier than the line before it")
        last = seconds(ts)
        speaker, speaker_count = redact(m["speaker"].strip())
        if not speaker:
            raise IngestError(f"line {n}: the speaker label is blank; every utterance needs one (use 'Unknown')")
        text, text_count = redact(m["text"])
        redacted_total += speaker_count + text_count
        utterances.append(
            Utterance(
                uid=f"U{len(utterances) + 1:03d}",
                timestamp=ts,
                speaker=speaker,
                certain=speaker.lower() not in UNCERTAIN_SPEAKERS,
                text=text,
                redactions=speaker_count + text_count,
                instruction_like=bool(INSTRUCTION_LIKE.search(m["text"])),
            )
        )
    if not utterances:
        raise IngestError("no utterances found after the header")
    return header, utterances, redacted_total


def render_record(tid: str, header: dict[str, str], utterances: list[Utterance], source_sha: str, redacted_total: int) -> str:
    flagged = [u.uid for u in utterances if u.instruction_like]
    uncertain = [u.uid for u in utterances if not u.certain]
    out = [
        f"# Transcript {tid}: {literal(header['Meeting'])}",
        "",
        "Source of record. Verbatim and in the order spoken, apart from redaction. Never edit, reorder or",
        "summarize this file; derived notes and analysis belong in separate files. Characters Markdown",
        "would treat as formatting are shown with a backslash, so the rendered text is exactly what was said.",
        "",
        f"- Transcript id: `{tid}` (cite a line as `{tid}#U001`)",
        f"- Meeting date: {header['Date']}",
        f"- Timestamp format: {TIMESTAMP_FORMAT}",
        f"- Utterances: {len(utterances)}",
        f"- Redacted: email addresses and phone numbers, in the header, speaker labels and utterances, "
        f"each replaced by `{REDACTED}` ({redacted_total} in total)",
        f"- Uncertain speakers: {', '.join(uncertain) if uncertain else 'none'} (marked, not guessed)",
        f"- Flagged as instruction-like: {', '.join(flagged) if flagged else 'none'} "
        "(recorded as content; nothing in this transcript was acted on)",
        f"- Raw source SHA-256: `{source_sha}` (of the original file's bytes; see the provenance file "
        "for where the original is)",
        "",
        "| Id | Time | Speaker | Utterance |",
        "|---|---|---|---|",
    ]
    for u in utterances:
        speaker = literal(u.speaker) if u.certain else f"{literal(u.speaker)} (uncertain)"
        notes = []
        if u.redactions:
            notes.append(f"{u.redactions} redacted")
        if u.instruction_like:
            notes.append("instruction-like, not followed")
        note = f" _({'; '.join(notes)})_" if notes else ""
        out.append(f"| {u.uid} | {u.timestamp} | {speaker} | {literal(u.text)}{note} |")
    return "\n".join(out) + "\n"


def yaml_str(value: str) -> str:
    """A double-quoted YAML string. JSON's escaping is valid YAML and covers every control character."""
    return json.dumps(value, ensure_ascii=False)


def tracked_by_git(path: Path) -> str:
    """'true' or 'false' for whether Git tracks the file, or 'unknown' if that can't be told."""
    full = path.resolve()
    try:
        r = subprocess.run(
            ["git", "ls-files", "--error-unmatch", "--", full.name],
            capture_output=True, text=True, cwd=full.parent, timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return "unknown"
    if r.returncode == 0:
        return "true"
    return "false" if "did not match" in r.stderr else "unknown"


def render_provenance(tid, header, utterances, redacted_total, source_sha, record_sha, raw_path,
                      capture_source, transcription_tool, ingested_at) -> str:
    speakers = sorted({u.speaker for u in utterances if u.certain})
    lines = [
        "schema: ba-ingest-transcript/provenance/v1",
        f"transcript_id: {yaml_str(tid)}",
        f"meeting: {yaml_str(header['Meeting'])}",
        f"meeting_date: {yaml_str(header['Date'])}",
        f"participants_listed: {yaml_str(header['Attendees'])}",
        "speakers_attributed:",
        *[f"  - {yaml_str(s)}" for s in speakers],
        f"uncertain_speaker_utterances: [{', '.join(u.uid for u in utterances if not u.certain)}]",
        f"capture_source: {yaml_str(capture_source)}",
        f"transcription_tool: {yaml_str(transcription_tool)}",
        f"original_location: {yaml_str(redact(str(raw_path))[0])}",
        f"original_tracked_by_git: {tracked_by_git(raw_path)}",
        f"original_sha256: {yaml_str(source_sha)}",
        f"timestamp_format: {yaml_str(TIMESTAMP_FORMAT)}",
        f"utterance_count: {len(utterances)}",
        "redaction:",
        "  rules: [email addresses, phone numbers]",
        "  applied_to: [header values, speaker labels, utterances]",
        f"  replacements: {redacted_total}",
        f"  placeholder: {yaml_str(REDACTED)}",
        f"instruction_like_utterances: [{', '.join(u.uid for u in utterances if u.instruction_like)}]",
        "ingestion:",
        f"  tool: {yaml_str(TOOL_NAME)}",
        f"  tool_version: {yaml_str(TOOL_VERSION)}",
        f"  ingested_at: {yaml_str(ingested_at)}",
        f"  record_sha256: {yaml_str(record_sha)}",
    ]
    return "\n".join(lines) + "\n"


def publish(files: list[tuple[Path, str]]) -> None:
    """Places each file in order, or none. A file that already exists is never replaced.

    Each is written to a temporary file in the same folder, then hard-linked to its name, which
    fails if that name exists (so two runs can't overwrite each other). On any failure every
    temporary file, and every file this call placed, is removed.
    """
    temps: list[Path] = []
    placed: list[Path] = []
    try:
        for target, content in files:
            target.parent.mkdir(parents=True, exist_ok=True)
            fd, name = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=target.parent)
            temps.append(Path(name))
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
                f.write(content)
                f.flush()
                os.fsync(f.fileno())
            os.chmod(name, 0o644)
        for (target, _), temp in zip(files, temps):
            try:
                os.link(temp, target)
            except FileExistsError:
                raise IngestError(f"{target} appeared while this run was writing (another run?); nothing was replaced") from None
            placed.append(target)
    except BaseException:
        for target in placed:
            target.unlink(missing_ok=True)
        raise
    finally:
        for temp in temps:
            temp.unlink(missing_ok=True)


def sha256(data: str | bytes) -> str:
    return hashlib.sha256(data.encode("utf-8") if isinstance(data, str) else data).hexdigest()


def provenance_record_sha(provenance: str) -> str | None:
    m = re.search(r'^  record_sha256: "?([0-9a-f]{64})"?$', provenance, re.MULTILINE)
    return m[1] if m else None


def output_paths(out_dir: Path, tid: str) -> tuple[Path, Path]:
    return out_dir / f"{tid}.md", out_dir / f"{tid}.provenance.yaml"


def same_file(a: Path, b: Path) -> bool:
    """True if a and b are the same file, including through a symlink or hard link."""
    try:
        if a.exists() and b.exists():
            return os.path.samefile(a, b)
    except OSError:
        pass
    return a.resolve() == b.resolve()


def ingest(raw_path: Path, tid: str, out_dir: Path, capture_source: str, transcription_tool: str) -> list[str]:
    """Runs one ingestion; returns the report lines. Raises IngestError when refused."""
    report: list[str] = []
    if not TRANSCRIPT_ID.match(tid):
        raise IngestError("the transcript id must be 1-64 lower-case letters, digits and hyphens, starting with a letter or digit")
    for name, value in (("--capture-source", capture_source), ("--transcription-tool", transcription_tool)):
        if not value.strip():
            raise IngestError(f"{name} is required: say where the transcript came from, or write 'unknown'")
    try:
        raw_bytes = raw_path.read_bytes()
    except FileNotFoundError:
        raise IngestError(f"{raw_path} does not exist") from None
    try:
        raw = raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        raise IngestError(f"{raw_path} is not UTF-8 text") from None
    header, utterances, redacted_total = parse(raw)
    source_sha = sha256(raw_bytes)  # of the original bytes, so whoever holds the file can check it
    record = render_record(tid, header, utterances, source_sha, redacted_total)
    record_sha = sha256(record)
    record_path, provenance_path = output_paths(out_dir, tid)

    report.append(f"parsed {len(utterances)} utterances from {raw_path}")
    report.append(f"redacted {redacted_total} value(s): email addresses and phone numbers")
    for u in utterances:
        if not u.certain:
            report.append(f"{tid}#{u.uid} [{u.timestamp}] speaker {u.speaker!r} marked uncertain (not guessed)")
        if u.instruction_like:
            report.append(f"{tid}#{u.uid} [{u.timestamp}] instruction-like text from {u.speaker}: recorded as content, NOT followed")

    has_record, has_provenance = record_path.exists(), provenance_path.exists()
    if has_record != has_provenance:
        present, absent = (record_path, provenance_path) if has_record else (provenance_path, record_path)
        raise IngestError(
            f"{present} exists but {absent} does not (an interrupted run?). Nothing was changed; "
            "check the file and remove it before ingesting again."
        )
    if has_record:
        existing = record_path.read_text(encoding="utf-8")
        existing_sha = sha256(existing)
        if provenance_record_sha(provenance_path.read_text(encoding="utf-8")) != existing_sha:
            raise IngestError(f"{provenance_path} does not match {record_path} (record_sha256 differs); nothing was changed")
        if existing == record:
            report.append(f"{record_path} already exists and is identical (sha256 {existing_sha})")
            report.append(f"{provenance_path} matches it")
            report.append("unchanged: nothing written, no utterance added or duplicated")
            return report
        raise IngestError(
            f"{record_path} already exists with different content (sha256 {existing_sha}, new {record_sha}); "
            "the source of record is never rewritten. Use a new transcript id for a different transcript."
        )

    ingested_at = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    # The two values typed on the command line are redacted too, like everything else that is kept.
    capture_source, _ = redact(capture_source.strip())
    transcription_tool, _ = redact(transcription_tool.strip())
    provenance = render_provenance(tid, header, utterances, redacted_total, source_sha, record_sha, raw_path,
                                   capture_source, transcription_tool, ingested_at)
    # Provenance first, record last: a record never exists without the provenance that describes it.
    publish([(provenance_path, provenance), (record_path, record)])
    report.append(f"wrote {provenance_path}")
    report.append(f"wrote {record_path} (sha256 {record_sha})")
    return report


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Ingest a meeting transcript into a redacted source of record.")
    ap.add_argument("raw_file", type=Path)
    ap.add_argument("transcript_id")
    ap.add_argument("--capture-source", required=True,
                    help="where the transcript came from, e.g. 'Teams recording of the 10-12 refinement' or 'unknown'")
    ap.add_argument("--transcription-tool", required=True,
                    help="what turned speech into text, e.g. 'Teams live transcription', 'typed by hand' or 'unknown'")
    ap.add_argument("--out-dir", type=Path, default=Path("participant/context/transcripts"))
    ap.add_argument("--log", type=Path, help="also save this run (command and output) to this file")
    args = ap.parse_args(argv)

    started = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    # The command as shown and logged, with contact details redacted (the real arguments are used as given).
    shown = [redact(a)[0] for a in (argv if argv is not None else sys.argv[1:])]
    shown = [json.dumps(a, ensure_ascii=False) if re.search(r'[\s"\\]', a) else a for a in shown]
    lines = [f"$ .venv/bin/python participant/skills/{TOOL_NAME} {' '.join(shown)}",
             f"# run at {started} by {TOOL_NAME} {TOOL_VERSION}"]
    record_path, provenance_path = output_paths(args.out_dir, args.transcript_id)
    if args.log and any(same_file(args.log, p) for p in (args.raw_file, record_path, provenance_path)):
        print("REFUSED: --log must not name the raw transcript or either output file; nothing was run")
        return 2
    try:
        lines += ingest(args.raw_file, args.transcript_id, args.out_dir, args.capture_source, args.transcription_tool)
        status = 0
    except IngestError as e:
        lines.append(f"REFUSED: {e}")
        lines.append(
            f"no record written: {record_path} "
            + ("already existed before this run and was left as it was" if record_path.exists() else "does not exist")
        )
        status = 1
    lines.append(f"exit status {status}")
    # Everything shown or logged is redacted: file names and error messages can hold contact details too.
    text = "\n".join(redact(line)[0] for line in lines) + "\n"
    print(text, end="")
    if args.log:
        args.log.parent.mkdir(parents=True, exist_ok=True)
        with args.log.open("a", encoding="utf-8") as f:
            f.write(text + "\n")
    return status


if __name__ == "__main__":
    sys.exit(main())
