#!/usr/bin/env python3
"""A fake story tracker, standing in for something like Jira, to show previewed and confirmed writes.

Part of the base-camp-write-preview quest (rules: participant/context/write-preview-rules.md).
Run from the repository root:

    .venv/bin/python participant/tools/fake-story-tracker.py preview --stories participant/context/write-preview/follow-up-stories.yaml
    .venv/bin/python participant/tools/fake-story-tracker.py confirm --stories participant/context/write-preview/follow-up-stories.yaml
    .venv/bin/python participant/tools/fake-story-tracker.py list

The "outside system" is a folder Git ignores, local-data/fake-story-tracker/. Nothing real is
touched. A write takes two separate runs:

  1. preview shows the target, the action and every field of every story that would be written,
     changes nothing and says so, and ends with a fingerprint: a code made from the exact change,
     the tracker as it is now, and the time the preview was made.
  2. confirm asks the person, at the keyboard, to type the fingerprint of the preview they approve.
     It writes only if that preview exists and hasn't been used, is no older than 15 minutes, the
     stories file still holds exactly the change that was previewed, and the tracker hasn't changed
     since. Otherwise it refuses, says why, and writes nothing. A written story records the
     fingerprint it was confirmed under, who confirmed it and when.

There is no option that skips the preview or the typed confirmation. The token the write needs
(FAKE_STORY_TRACKER_TOKEN) is read only by confirm, never printed and never stored.
"""

from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import errno
import fcntl
import getpass
import hashlib
import json
import os
import re
import secrets
import stat
import subprocess
import sys
import textwrap
import unicodedata
from collections.abc import Callable, Iterator
from pathlib import Path

import yaml

VERSION = "1.11.0"
DATA_DIR = Path("local-data/fake-story-tracker")
TIME_LIMIT = dt.timedelta(minutes=15)
TOKEN_VAR = "FAKE_STORY_TRACKER_TOKEN"

# The stories file holds exactly these keys, and every value is plain one-line text: anything else
# is reported, never guessed at.
TOP_KEYS = {"target", "action", "stories"}
TARGET_KEYS = {"system", "project"}
STORY_KEYS = {"from_question", "answer_assumed", "type", "priority", "title", "description",
              "acceptance_criteria"}
ACTIONS = ("create",)
TYPES = ("Story",)
PRIORITIES = ("Highest", "High", "Medium", "Low")
QUESTION_ID = re.compile(r"^Q-\d{2}$")
PROJECT = re.compile(r"^[A-Z]{2,10}$")
FINGERPRINT = re.compile(r"^[0-9A-F]{12}$")
MAX_FILE_BYTES = 2_000_000
# Folders are opened without following a link, so a folder that is (or is swapped for) a link to
# somewhere else is refused instead of written through.
DIR_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)
FILE_FLAGS = os.O_NOFOLLOW | os.O_NONBLOCK | getattr(os, "O_CLOEXEC", 0)
STORED_KEYS = STORY_KEYS | {"key", "confirmed_by", "confirmed_at", "preview_fingerprint"}
PREVIEW_KEYS = {"fingerprint", "made_at", "change", "tracker_state", "used"}
MAX_STORIES = 20
MAX_CRITERIA = 10
# Every field has a length limit, so a preview and the tracker always stay small enough to read
# back (MAX_FILE_BYTES below); a write that would still go over that is refused before it starts.
MAX_TITLE = 120
MAX_SHORT = 300    # target system, answer assumed
MAX_DESCRIPTION = 2000
MAX_CRITERION = 500
WIDTH = 96
# Lines wrap only at spaces, never inside a word or at a hyphen ("doors-open" stays whole), so
# joining a wrapped value's lines with single spaces gives back exactly the text in the file.
WRAP = {"break_long_words": False, "break_on_hyphens": False}


class Refused(Exception):
    """The run stops without writing anything; the message says why."""


class BadInput(Exception):
    """The stories file can't be read as a proposed change; the message says why."""


# --- time and display -----------------------------------------------------------------------------

def shown_time(moment: dt.datetime) -> str:
    """A time as people read it here: MM-DD-YYYY and a 12-hour clock, in local time."""
    local = moment.astimezone()
    return local.strftime("%m-%d-%Y %I:%M:%S %p ") + (local.tzname() or "")


def iso(moment: dt.datetime) -> str:
    return moment.astimezone(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_iso(text: str) -> dt.datetime:
    return dt.datetime.fromisoformat(text.replace("Z", "+00:00"))


def grouped(fingerprint: str) -> str:
    """'7F3A91C20B4D' as '7F3A-91C2-0B4D', easier to read and type."""
    return "-".join(fingerprint[i:i + 4] for i in range(0, len(fingerprint), 4))


def tidy_name(name: str) -> str:
    """A name as one line of visible text: invisible characters removed, spacing collapsed."""
    return " ".join("".join(c for c in name if c.isprintable() or c.isspace()).split())[:MAX_SHORT]


def actor() -> str:
    """Who is confirming: the Git user name, or the login name if that is empty or unusable."""
    try:
        name = subprocess.run(["git", "config", "user.name"], capture_output=True, text=True,
                              timeout=5).stdout
    except (OSError, subprocess.SubprocessError):
        name = ""
    return tidy_name(name) or tidy_name(getpass.getuser()) or "unknown person"


# --- the stories file -----------------------------------------------------------------------------

def visible_line(text: str) -> bool:
    """One line of visible text: no line breaks, tabs or characters that can't be shown or saved
    (a lone surrogate from a hand-edited file is not printable, so it is refused here too)."""
    return not any(c in text for c in "\n\r\t") and all(c.isprintable() for c in text)


def plain(value: object, where: str, limit: int | None = None) -> str:
    """A field's value: one line of visible text, in one standard form. Characters that look the
    same are stored the same way (Unicode's composed form, so "café" typed either way is one
    text), and runs of spaces become one, so what a person sees in the preview is exactly what is
    fingerprinted and stored."""
    if not isinstance(value, str):
        raise BadInput(f"{where} must be text")
    text = value.strip()
    if not text:
        raise BadInput(f"{where} is empty")
    if not visible_line(text):
        raise BadInput(f"{where} must be one line of visible text")
    text = re.sub(" {2,}", " ", unicodedata.normalize("NFC", text))
    if limit is not None and len(text) > limit:
        raise BadInput(f"{where} is {len(text)} characters; the limit is {limit}")
    return text


def exact_keys(mapping: object, keys: set[str], where: str) -> dict:
    if not isinstance(mapping, dict):
        raise BadInput(f"{where} must be a set of named fields")
    missing = sorted(keys - set(mapping))
    extra = sorted(set(mapping) - keys)
    if missing or extra:
        parts = ([f"missing {', '.join(missing)}"] if missing else []) + \
                ([f"unknown {', '.join(map(str, extra))}"] if extra else [])
        raise BadInput(f"{where}: {'; '.join(parts)}")
    return mapping


def load_change(path: Path) -> dict:
    """The proposed change in the stories file, checked and in a fixed form."""
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise BadInput(f"can't read {path}: {exc}") from exc
    try:
        # Every value is read as text, so YAML can't quietly turn one into a date, number or yes/no.
        raw = yaml.load(text, Loader=yaml.BaseLoader)
    except yaml.YAMLError as exc:
        raise BadInput(f"{path} isn't valid YAML: {exc}") from exc
    return validate_change(raw)


def validate_change(raw: object) -> dict:
    """A proposed change checked against every rule, in a fixed form. The same rules apply to the
    stories file and to the change saved in a preview, so neither can hold what the other can't."""
    top = exact_keys(raw, TOP_KEYS, "the stories file")
    target = exact_keys(top["target"], TARGET_KEYS, "target")
    project = plain(target["project"], "target.project")
    if not PROJECT.match(project):
        raise BadInput("target.project must be 2 to 10 capital letters, like TIX")
    action = plain(top["action"], "action")
    if action not in ACTIONS:
        raise BadInput(f"action must be one of: {', '.join(ACTIONS)}")
    raw_stories = top["stories"]
    if not isinstance(raw_stories, list) or not raw_stories:
        raise BadInput("stories must be a list of at least one story")
    if len(raw_stories) > MAX_STORIES:
        raise BadInput(f"{len(raw_stories)} stories; one preview holds at most {MAX_STORIES}")
    stories, seen = [], set()
    for i, raw_story in enumerate(raw_stories, 1):
        where = f"story {i}"
        s = exact_keys(raw_story, STORY_KEYS, where)
        limits = {"title": MAX_TITLE, "description": MAX_DESCRIPTION, "answer_assumed": MAX_SHORT}
        story = {k: plain(s[k], f"{where} {k}", limits.get(k, MAX_SHORT))
                 for k in sorted(STORY_KEYS - {"acceptance_criteria"})}
        if not QUESTION_ID.match(story["from_question"]):
            raise BadInput(f"{where} from_question must look like Q-02")
        if story["from_question"] in seen:
            raise BadInput(f"{where} repeats {story['from_question']}; one story per question")
        seen.add(story["from_question"])
        if story["type"] not in TYPES:
            raise BadInput(f"{where} type must be one of: {', '.join(TYPES)}")
        if story["priority"] not in PRIORITIES:
            raise BadInput(f"{where} priority must be one of: {', '.join(PRIORITIES)}")
        if len(story["title"]) > MAX_TITLE:
            raise BadInput(f"{where} title is {len(story['title'])} characters; the limit is {MAX_TITLE}")
        criteria = s["acceptance_criteria"]
        if not isinstance(criteria, list) or not criteria or len(criteria) > MAX_CRITERIA:
            raise BadInput(f"{where} acceptance_criteria must be a list of 1 to {MAX_CRITERIA} items")
        story["acceptance_criteria"] = [plain(c, f"{where} acceptance criterion {j}", MAX_CRITERION)
                                        for j, c in enumerate(criteria, 1)]
        stories.append(story)
    return {"target": {"system": plain(target["system"], "target.system", MAX_SHORT), "project": project},
            "action": action, "stories": stories}


# --- the simulated tracker ------------------------------------------------------------------------

class Folders:
    """The tracker folder and its previews folder, each opened once without following a link.
    Every read, write and lock below goes through these, never through a path string, so a
    folder swapped for a link part-way through a run is still never written through."""

    def __init__(self, data: int, previews: int | None) -> None:
        self.data = data
        self.previews = previews


def _open_folder(parent: int | None, name: str | Path, create: bool) -> int | None:
    """A folder opened without following a link; None if it doesn't exist and create is off."""
    if create and parent is not None:
        with contextlib.suppress(FileExistsError):
            os.mkdir(name, dir_fd=parent)
    try:
        return os.open(name, DIR_FLAGS, dir_fd=parent)
    except FileNotFoundError:
        if create:
            raise
        return None
    except OSError as exc:
        if exc.errno in (errno.ELOOP, errno.ENOTDIR):
            raise Refused(f"{Path(name).name} is a link or not a folder, so nothing is read or written "
                          "through it; nothing was written") from exc
        raise


@contextlib.contextmanager
def folders(data: Path, create: bool) -> Iterator[Folders | None]:
    """The opened folders, or None when the tracker doesn't exist yet and create is off. The
    folder that holds the tracker (local-data) is refused if it is itself a link."""
    opened: list[int] = []
    try:
        try:
            if create:
                data.parent.mkdir(parents=True, exist_ok=True)
            holder = _open_folder(None, data.parent, create=False)
        except OSError as exc:
            raise Refused(f"the tracker folder can't be set up ({exc.strerror}); "
                          "nothing was written") from exc
        if holder is None:
            yield None
            return
        opened.append(holder)
        try:
            tracker = _open_folder(holder, data.name, create)
        except OSError as exc:
            raise Refused(f"the tracker folder can't be set up ({exc.strerror}); "
                          "nothing was written") from exc
        if tracker is None:
            yield None
            return
        opened.append(tracker)
        try:
            previews = _open_folder(tracker, "previews", create)
        except OSError as exc:
            raise Refused(f"the tracker's previews folder can't be set up ({exc.strerror}); "
                          "nothing was written") from exc
        if previews is not None:
            opened.append(previews)
        yield Folders(tracker, previews)
    finally:
        for descriptor in reversed(opened):
            os.close(descriptor)


@contextlib.contextmanager
def tracker_lock(data: Path) -> Iterator[Folders]:
    """Only one run at a time may check and change the tracker. A second confirm waits here, then
    sees the first one's result: the preview already used, or the tracker already changed."""
    with folders(data, create=True) as opened:
        assert opened is not None and opened.previews is not None
        try:
            lock = os.open(".lock", os.O_RDWR | os.O_CREAT | FILE_FLAGS, 0o600, dir_fd=opened.data)
        except OSError as exc:
            raise Refused(f"the tracker's lock file can't be opened ({exc.strerror}); "
                          "nothing was written") from exc
        try:
            if not stat.S_ISREG(os.fstat(lock).st_mode):
                raise Refused("the tracker's lock file isn't an ordinary file; nothing was written")
            fcntl.flock(lock, fcntl.LOCK_EX)
            yield opened
        finally:
            os.close(lock)  # closing releases the lock


def read_file(folder: int, name: str) -> str | None:
    """A small, ordinary file's text, never through a link; None if it doesn't exist."""
    try:
        descriptor = os.open(name, os.O_RDONLY | FILE_FLAGS, dir_fd=folder)
    except FileNotFoundError:
        return None
    except OSError as exc:
        if exc.errno == errno.ELOOP:
            raise Refused(f"{name} is a link, so it isn't read; nothing was written") from exc
        raise Refused(f"{name} can't be opened ({exc.strerror}); nothing was written") from exc
    # What was opened is checked before anything reads it: a folder, a FIFO or a device at this
    # name is refused, never read.
    status = os.fstat(descriptor)
    if not stat.S_ISREG(status.st_mode) or status.st_size > MAX_FILE_BYTES:
        os.close(descriptor)
        raise Refused(f"{name} isn't a small, ordinary file; nothing was written")
    with os.fdopen(descriptor, "rb") as stream:
        raw = stream.read(MAX_FILE_BYTES + 1)
    if len(raw) > MAX_FILE_BYTES:
        raise Refused(f"{name} isn't a small, ordinary file; nothing was written")
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise Refused(f"{name} isn't readable text; nothing was written") from exc


def write_file(folder: int, name: str, text: str) -> None:
    """Replaces a file with the whole text or leaves it as it was, never through a link. A file
    too big to read back is refused before anything is written, so a write can never leave the
    tracker unreadable."""
    data = text.encode("utf-8")
    if len(data) > MAX_FILE_BYTES:
        raise Refused(f"{name} would be {len(data)} bytes, over the {MAX_FILE_BYTES} the tracker can "
                      "read back; nothing was written")
    try:
        if not stat.S_ISREG(os.lstat(name, dir_fd=folder).st_mode):
            raise Refused(f"{name} is a link or special file, so it was not written")
    except FileNotFoundError:
        pass
    temporary = f".{name}.{secrets.token_hex(6)}.tmp"
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | FILE_FLAGS, 0o644,
                         dir_fd=folder)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, name, src_dir_fd=folder, dst_dir_fd=folder)
    except BaseException:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(temporary, dir_fd=folder)
        raise


def stored_items(opened: Folders) -> list[dict]:
    """The stories in the tracker, each checked to be whole, or Refused if any is damaged."""
    text = read_file(opened.data, "stories.json")
    if text is None:
        return []
    try:
        items = json.loads(text)
    except ValueError as exc:
        raise Refused(f"the tracker file can't be read ({exc}); nothing was written") from exc
    if not isinstance(items, list):
        raise Refused("the tracker file isn't a list of stories; nothing was written")
    for n, item in enumerate(items, 1):
        problem = None
        if not isinstance(item, dict) or set(item) != STORED_KEYS:
            problem = "it doesn't have exactly the fields a story has"
        elif not all(isinstance(item[k], str) and item[k] and visible_line(item[k])
                     for k in STORED_KEYS - {"acceptance_criteria"}):
            problem = "a field is empty or isn't one line of visible text"
        elif not (isinstance(item["acceptance_criteria"], list) and item["acceptance_criteria"]
                  and all(isinstance(c, str) and c and visible_line(c) for c in item["acceptance_criteria"])):
            problem = "its acceptance criteria aren't a list of visible text"
        else:
            try:
                parse_iso(item["confirmed_at"])
            except ValueError:
                problem = "its confirmed time isn't a date and time"
        if problem:
            raise Refused(f"the tracker holds a damaged story (number {n}: {problem}); "
                          "nothing was written")
    return items


def load_tracker(data: Path) -> list[dict]:
    """The stories in the tracker, read without changing anything; empty if there is no tracker."""
    with folders(data, create=False) as opened:
        return [] if opened is None else stored_items(opened)


def canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def tracker_state(items: list[dict]) -> str:
    """A short code for the tracker's whole contents: it changes if any story does."""
    return hashlib.sha256(canonical(items).encode("utf-8")).hexdigest()[:12].upper()


def make_fingerprint(change: dict, state: str, made_at: str) -> str:
    material = canonical({"change": change, "tracker_state": state, "made_at": made_at})
    return hashlib.sha256(material.encode("utf-8")).hexdigest()[:12].upper()


# --- the preview ----------------------------------------------------------------------------------

def wrapped(label: str, text: str, indent: int = 4) -> list[str]:
    first = " " * indent + f"{label:<13}"
    return textwrap.wrap(text, WIDTH, initial_indent=first, subsequent_indent=" " * len(first),
                         **WRAP) or [first]


def story_lines(heading: str, story: dict) -> list[str]:
    """One story with every field, the same way in a preview and in the list, so the two can be
    compared side by side."""
    lines = ["", heading]
    lines += wrapped("Type:", story.get("type", "?"))
    lines += wrapped("Priority:", story.get("priority", "?"))
    lines += wrapped("Title:", story.get("title", "?"))
    lines += wrapped("From:", f"{story.get('from_question', '?')} (answer assumed: "
                              f"{story.get('answer_assumed', '?')})")
    lines += wrapped("Description:", story.get("description", "?"))
    lines.append("    Acceptance criteria:")
    for j, criterion in enumerate(story.get("acceptance_criteria", []), 1):
        lines += textwrap.wrap(criterion, WIDTH, initial_indent=f"      {j}. ", subsequent_indent=" " * 9,
                               **WRAP)
    return lines


def preview_lines(change: dict, items: list[dict], fingerprint: str, made: dt.datetime) -> list[str]:
    project = change["target"]["project"]
    count = len(change["stories"])
    next_number = len(items) + 1
    lines = [
        "PREVIEW: nothing has been written.",
        "",
        f"Target:   {change['target']['system']}, project {project}",
        f"Action:   {change['action']} {count} {'story' if count == 1 else 'stories'}, all or none",
        f"Tracker now: {len(items)} {'story' if len(items) == 1 else 'stories'}",
    ]
    for i, story in enumerate(change["stories"]):
        lines += story_lines(f"Story {i + 1} of {count}, to be created as {project}-{next_number + i}",
                             story)
    expires = made + TIME_LIMIT
    lines += [
        "",
        f"Preview fingerprint: {grouped(fingerprint)}",
        f"Made {shown_time(made)}; it can be confirmed until {shown_time(expires)} (15 minutes).",
        "To approve exactly this change, run confirm and type this fingerprint.",
        "",
        f"Nothing was written. The tracker still has {len(items)} "
        f"{'story' if len(items) == 1 else 'stories'}.",
    ]
    return lines


def do_preview(stories_file: Path, data: Path, now: dt.datetime,
               made_at: dt.datetime | None = None) -> tuple[list[str], str]:
    """Records a preview and returns what to show and its fingerprint. Writes no story."""
    change = load_change(stories_file)
    with tracker_lock(data) as opened:
        return _record_preview(change, opened, now, made_at)


def _record_preview(change: dict, opened: Folders, now: dt.datetime,
                    made_at: dt.datetime | None) -> tuple[list[str], str]:
    items = stored_items(opened)
    taken = {i.get("from_question") for i in items}
    already = [s["from_question"] for s in change["stories"] if s["from_question"] in taken]
    if already:
        raise Refused(f"the tracker already has stories for {', '.join(already)}; "
                      "nothing to preview and nothing was written")
    made = now if made_at is None else made_at
    if made > now:
        raise Refused("a preview can't be dated in the future; nothing was written")
    state = tracker_state(items)
    fingerprint = make_fingerprint(change, state, iso(made))
    record = {"fingerprint": fingerprint, "made_at": iso(made), "change": change,
              "tracker_state": state, "used": False}
    try:
        write_file(opened.previews, f"{fingerprint}.json", json.dumps(record, indent=2) + "\n")
    except OSError as exc:
        raise Refused(f"the preview couldn't be saved ({exc.strerror}); nothing was written") from exc
    lines = preview_lines(change, items, fingerprint, made)
    if made_at is not None:
        lines.insert(1, f"(Dated {shown_time(made)} with --made-at, earlier than now, to show expiry.)")
    return lines, fingerprint


# --- the confirmation -----------------------------------------------------------------------------

def differences(previewed: dict, current: dict) -> list[str]:
    """Plain words for how the stories file differs from what was previewed."""
    found = []
    for key in ("target", "action"):
        if previewed[key] != current[key]:
            found.append(f"the {key} changed")
    old, new = previewed["stories"], current["stories"]
    if len(old) != len(new):
        found.append(f"the preview had {len(old)} stories; the file now has {len(new)}")
    for i, (a, b) in enumerate(zip(old, new), 1):
        changed = sorted(k for k in a if a[k] != b.get(k))
        if changed:
            found.append(f"story {i}: {', '.join(changed)} changed")
    return found or ["the change differs from the preview"]


def do_confirm(stories_file: Path, data: Path, clock: Callable[[], dt.datetime], typed: str,
               token: str | None, who: str) -> list[str]:
    """Writes the previewed stories if every check passes; otherwise raises Refused. The clock is
    read under the tracker lock, after the fingerprint was typed, so the 15-minute limit and the
    recorded time are the moment of approval, not the moment the command started."""
    if not token:
        raise Refused(f"{TOKEN_VAR} isn't set, so the tracker can't be written to; nothing was written")
    if not (who and visible_line(who) and len(who) <= MAX_SHORT):
        raise Refused("the name of the person confirming isn't one line of visible text, so it "
                      "can't be recorded; nothing was written")
    entered = re.sub(r"[\s-]", "", typed).upper()
    if not FINGERPRINT.match(entered):
        raise Refused("that isn't a fingerprint (12 letters and digits, like 7F3A-91C2-0B4D); "
                      "nothing was written")
    with tracker_lock(data) as opened:
        # The stories file is read under the lock too, so it is checked as it is at the moment of
        # writing, even if this run waited for another one.
        current = load_change(stories_file)
        return _check_and_write(current, opened, clock(), entered, who)


def preview_record(text: str, entered: str) -> tuple[dict, dt.datetime]:
    """A saved preview, checked to have exactly the shape a preview has, and when it was made."""
    damaged = f"the saved preview {grouped(entered)} is damaged; nothing was written"
    try:
        record = json.loads(text)
    except ValueError as exc:
        raise Refused(damaged) from exc
    if (not isinstance(record, dict) or set(record) != PREVIEW_KEYS
            or not all(isinstance(record[k], str) and visible_line(record[k])
                       for k in ("fingerprint", "made_at", "tracker_state"))
            or not isinstance(record["change"], dict) or not isinstance(record["used"], bool)):
        raise Refused(damaged)
    try:
        made = parse_iso(record["made_at"])
    except ValueError as exc:
        raise Refused(damaged) from exc
    if made.tzinfo is None:
        raise Refused(damaged)
    try:
        if validate_change(record["change"]) != record["change"]:
            raise Refused(damaged)
    except BadInput as exc:
        raise Refused(damaged) from exc
    return record, made


def _check_and_write(current: dict, opened: Folders, now: dt.datetime, entered: str,
                     who: str) -> list[str]:
    name = f"{entered}.json"
    text = read_file(opened.previews, name)
    if text is None:
        raise Refused(f"there is no preview with fingerprint {grouped(entered)}; nothing was written")
    record, made = preview_record(text, entered)
    # The record must still match its own fingerprint, so editing a saved preview (its time, its
    # stories or the tracker state it was made against) makes it useless rather than trusted.
    try:
        intact = (record["fingerprint"] == entered
                  and make_fingerprint(record["change"], record["tracker_state"], record["made_at"]) == entered)
    except (KeyError, TypeError):
        intact = False
    if not intact:
        raise Refused(f"the saved preview {grouped(entered)} has been altered since it was made; "
                      "nothing was written")
    if record.get("used"):
        raise Refused(f"preview {grouped(entered)} was already confirmed; a preview approves one "
                      "write only. Nothing was written")
    reasons = []
    if now < made:
        reasons.append(f"the computer's clock reads {shown_time(now)}, earlier than the preview was "
                       f"made ({shown_time(made)}), so the preview's age can't be trusted")
    elif now - made > TIME_LIMIT:
        reasons.append(f"the preview expired at {shown_time(made + TIME_LIMIT)} "
                       f"(made {shown_time(made)}; the limit is 15 minutes)")
    if current != record["change"]:
        reasons.append("the stories file no longer holds the change that was previewed: "
                       + "; ".join(differences(record["change"], current)))
    items = stored_items(opened)
    if tracker_state(items) != record["tracker_state"]:
        reasons.append("the tracker has changed since the preview was made")
    if reasons:
        raise Refused("Refused: " + " Also, ".join(r[0].upper() + r[1:] + "." for r in reasons)
                      + " Nothing was written; preview again to see the change as it is now.")
    # Every check passed: write all the stories at once, then mark the preview used.
    project = record["change"]["target"]["project"]
    written = []
    for i, story in enumerate(record["change"]["stories"], len(items) + 1):
        written.append({"key": f"{project}-{i}", **story, "confirmed_by": who,
                        "confirmed_at": iso(now), "preview_fingerprint": entered})
    # The preview is marked used before the stories are written. If writing them then fails,
    # nothing was written and this preview can't be used again, so the person previews again;
    # a failure can never be reported for a write that in fact happened.
    record["used"] = True
    try:
        write_file(opened.previews, name, json.dumps(record, indent=2) + "\n")
    except OSError as exc:
        raise Refused(f"the preview couldn't be marked as used ({exc.strerror}); "
                      "nothing was written") from exc
    try:
        write_file(opened.data, "stories.json", json.dumps(items + written, indent=2) + "\n")
    except (OSError, Refused) as exc:
        reason = exc.strerror if isinstance(exc, OSError) else str(exc).split(";")[0]
        raise Refused(f"the stories couldn't be written ({reason}). Nothing was written, and "
                      f"preview {grouped(entered)} can't be used again; preview again") from exc
    lines = [f"Confirmed by {who} at {shown_time(now)}, for preview {grouped(entered)}.", "Written:"]
    lines += [f"  {w['key']}  {w['priority']:<8} {w['title']}" for w in written]
    lines.append(f"The tracker now has {len(items) + len(written)} stories.")
    return lines


def list_lines(data: Path) -> list[str]:
    items = load_tracker(data)
    lines = [f"Tracker: {len(items)} {'story' if len(items) == 1 else 'stories'} "
             f"(tracker state {grouped(tracker_state(items))})"]
    for item in items:
        lines += story_lines(str(item.get("key")), item)
        lines += wrapped("Confirmed:", f"by {item.get('confirmed_by')} at "
                                       f"{shown_time(parse_iso(item['confirmed_at']))}, under preview "
                                       f"{grouped(item.get('preview_fingerprint', ''))}")
    return lines


# --- command line ---------------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")
    sub = ap.add_subparsers(dest="command", required=True)
    p = sub.add_parser("preview", help="show the change and record a preview; writes no story")
    p.add_argument("--stories", type=Path, required=True)
    p.add_argument("--made-at", help="date the preview earlier than now (to show expiry), like "
                                     "2026-10-29T08:00:00-04:00; never later than now")
    c = sub.add_parser("confirm", help="type a preview's fingerprint to write exactly that change")
    c.add_argument("--stories", type=Path, required=True)
    sub.add_parser("list", help="show the stories in the tracker")
    args = ap.parse_args(argv)
    now = dt.datetime.now(dt.timezone.utc)
    print(f"# fake-story-tracker.py {VERSION} {args.command}")
    try:
        if args.command == "list":
            print("\n".join(list_lines(DATA_DIR)))
            return 0
        if args.command == "preview":
            made_at = None
            if args.made_at:
                try:
                    made_at = dt.datetime.fromisoformat(args.made_at)
                except ValueError:
                    raise BadInput("--made-at must be a date and time like 2026-10-29T08:00:00-04:00")
                if made_at.tzinfo is None:
                    raise BadInput("--made-at must include its time zone, like -04:00")
            lines, _ = do_preview(args.stories, DATA_DIR, now, made_at)
            print("\n".join(lines))
            return 0
        # confirm: the person types the fingerprint at the keyboard; piped-in answers are refused.
        if not sys.stdin.isatty():
            raise Refused("confirm needs a person at the keyboard; an answer piped or redirected in "
                          "is refused. Nothing was written")
        who = actor()
        try:
            typed = input("Type the fingerprint of the preview you approve: ")
        except (EOFError, KeyboardInterrupt):
            print()
            raise Refused("cancelled at the prompt; nothing was written")
        print(f"You typed: {typed.strip()}")  # so the record shows what was approved
        written = do_confirm(args.stories, DATA_DIR, lambda: dt.datetime.now(dt.timezone.utc),
                             typed, os.environ.get(TOKEN_VAR), who)
        # From here the stories ARE written. A failure to show the result must never be reported
        # as "nothing was written", or a person might confirm again.
        try:
            print("\n".join(written))
            sys.stdout.flush()
        except OSError as exc:
            with contextlib.suppress(OSError):
                sys.stderr.write(f"The stories were written, but the result couldn't be shown "
                                 f"({exc.strerror}). Run list to see them; don't confirm again.\n")
        return 0
    except BadInput as exc:
        print(f"Can't use the stories file: {exc}. Nothing was written.")
        return 2
    except Refused as exc:
        message = str(exc)
        print(message if message.startswith("Refused") else f"Refused: {message}.")
        return 1
    except OSError as exc:
        # A last safety net, for problems before any story is written: once confirm has written
        # the stories it handles its own reporting above, so this can only be reached before.
        print(f"Refused: the tracker's files couldn't be read or written ({exc.strerror}). "
              "Nothing was written.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
