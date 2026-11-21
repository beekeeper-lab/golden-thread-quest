#!/usr/bin/env python3
"""Checks the fake story tracker against the quest's acceptance criteria, the same way every run.

Part of the base-camp-write-preview quest. The recorded logs show a person using the tracker for
real, so their fingerprints and times can't repeat. This check runs the same steps in a temporary
folder with a fixed clock and a fixed time zone, so a reviewer gets the identical output each time
and can compare it with the recorded result. It never touches local-data/ or anything else in the
repository, and it writes only inside the temporary folder.

    .venv/bin/python participant/tools/check-write-preview.py \\
        --stories participant/context/write-preview/follow-up-stories.yaml
"""

from __future__ import annotations

import argparse
import contextlib
import io
import datetime as dt
import importlib.util
import json
import os
import re
import pty
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

VERSION = "1.5.1"
ROOT = Path(__file__).resolve().parents[2]
TOOL_PATH = ROOT / "participant/tools/fake-story-tracker.py"
CLOCK = dt.datetime(2026, 10, 29, 13, 0, 0, tzinfo=dt.timezone.utc)  # 09:00 AM in Indiana
ZONE = "America/Indiana/Indianapolis"
STAND_IN = "stand-in-value-for-the-check"  # made up; the tracker only checks one is set
WHO = "Reviewer check"


def load_tool():
    spec = importlib.util.spec_from_file_location("fake_story_tracker", TOOL_PATH)
    if spec is None or spec.loader is None:
        sys.exit(f"Can't load {TOOL_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


LABEL_LINE = re.compile(r"^    ([A-Z][A-Za-z ]*):(?:\s+(.*))?$")
CRITERION_LINE = re.compile(r"^      (\d+)\. (.*)$")


def read_preview(text: str) -> tuple[dict[str, str], list[tuple[str, dict[str, str], list[str]]]]:
    """The preview's header values and, for each story, its heading, labeled values and criteria.
    Wrapped lines are joined back on to the value they continue, so each value is read whole."""
    header: dict[str, str] = {}
    stories: list[tuple[str, dict[str, str], list[str]]] = []
    last: tuple[dict | list, str | int] | None = None
    for line in text.splitlines():
        if line.startswith("Story "):
            stories.append((line, {}, []))
            last = None
        elif not stories:
            if ":" in line and not line.startswith(" "):
                label, value = line.split(":", 1)
                header[label] = value.strip()
        elif line.startswith("Preview fingerprint:"):
            break
        elif (m := LABEL_LINE.match(line)):
            values = stories[-1][1]
            values[m.group(1)] = (m.group(2) or "").strip()
            last = (values, m.group(1))
        elif (m := CRITERION_LINE.match(line)):
            stories[-1][2].append(m.group(2).strip())
            last = (stories[-1][2], len(stories[-1][2]) - 1)
        elif line.startswith("         ") and last is not None:
            holder, at = last
            holder[at] = f"{holder[at]} {line.strip()}"  # a wrapped line continues the value above
        else:
            last = None
    return header, stories


def labeled_values_missing(text: str, change: dict) -> list[str]:
    """Every labeled value compared whole and for equality, in its own story: a priority of
    'Highest' is not 'High', and a value under another story or label doesn't count."""
    missing = []
    header, shown_stories = read_preview(text)
    target, count = change["target"], len(change["stories"])
    for label, value in (("Target", f"{target['system']}, project {target['project']}"),
                         ("Action", f"{change['action']} {count} stories, all or none")):
        if header.get(label) != value:
            missing.append(f"{label}: expected {value!r}, shown {header.get(label)!r}")
    if len(shown_stories) != count:
        missing.append(f"{count} stories expected, {len(shown_stories)} shown")
    for i, s in enumerate(change["stories"], 1):
        if i > len(shown_stories):
            break
        heading, values, criteria = shown_stories[i - 1]
        expected_heading = f"Story {i} of {count}, to be created as {target['project']}-{i}"
        if heading != expected_heading:
            missing.append(f"story {i} heading: shown {heading!r}")
        expected = {"Type": s["type"], "Priority": s["priority"], "Title": s["title"],
                    "From": f"{s['from_question']} (answer assumed: {s['answer_assumed']})",
                    "Description": s["description"], "Acceptance criteria": ""}
        for label, value in expected.items():
            if values.get(label) != value:
                missing.append(f"story {i} {label}: expected {value[:30]!r}, shown "
                               f"{(values.get(label) or '')[:30]!r}")
        extra = sorted(set(values) - set(expected))
        if extra:
            missing.append(f"story {i} shows unexpected labels {extra}")
        if criteria != s["acceptance_criteria"]:
            missing.append(f"story {i} acceptance criteria differ from the stories file")
    return missing


def shown(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.name


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--stories", type=Path, required=True)
    ap.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")
    args = ap.parse_args(argv)
    os.environ["TZ"] = ZONE
    time.tzset()
    sys.dont_write_bytecode = True  # loading the tracker must not leave a cache file in the repository
    t = load_tool()
    results: list[tuple[str, bool, str]] = []

    def check(label: str, ok: bool, detail: str) -> None:
        results.append((label, ok, detail))

    def minutes(n: float) -> dt.datetime:
        return CLOCK + dt.timedelta(minutes=n)

    said: list[str] = []  # everything the tracker said in this check, scanned for the token at the end

    def refused(fn) -> str | None:
        try:
            result = fn()
            # A preview returns (lines, fingerprint); a confirmation returns lines.
            said.extend(str(x) for x in (result[0] if isinstance(result, tuple) else result))
        except t.Refused as exc:
            said.append(str(exc))
            return str(exc)
        return None

    def previewed(result: tuple[list[str], str]) -> str:
        """A preview's fingerprint, with everything it showed kept for the token scan."""
        said.extend(result[0])
        return result[1]

    printed_out, printed_err = io.StringIO(), io.StringIO()
    with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(printed_out), \
            contextlib.redirect_stderr(printed_err):
        try:
            work = Path(tmp)
            stories = work / "stories.yaml"
            shutil.copyfile(args.stories, stories)
            original = stories.read_text(encoding="utf-8")
            data = work / "tracker"
            change = t.load_change(stories)

            def state() -> str:
                return t.tracker_state(t.load_tracker(data))

            empty = state()

            # 1. The preview lists the target, the action and every field. Each label is looked for
            # with its own value inside its own story's section, so a value shown under another story
            # or another label doesn't count.
            lines, fp1 = t.do_preview(stories, data, CLOCK)
            said.extend(lines)
            text = "\n".join(lines)
            missing = labeled_values_missing(text, change)
            total = 2 + sum(5 + len(s["acceptance_criteria"]) for s in change["stories"])  # each compared whole
            check("1. Preview lists target, action and every field", not missing,
                  f"{total - len(missing)} of {total} labeled values shown in the right place"
                  + (f"; missing: {missing[0]}" if missing else ""))

            # 2. Without confirmation nothing changes, and the output says so.
            no_write = state() == empty and "Nothing was written" in text
            wrong = refused(lambda: t.do_confirm(stories, data, lambda: minutes(1), "0000-0000-0000", STAND_IN, WHO))
            blank = refused(lambda: t.do_confirm(stories, data, lambda: minutes(1), "", STAND_IN, WHO))
            check("2. No confirmation, no change, and it says so",
                  no_write and bool(wrong) and bool(blank) and state() == empty,
                  f"tracker state {t.grouped(state())} before and after the preview, a wrong "
                  "fingerprint and a blank answer")

            # 3. The confirmation names the exact preview it approves.
            edited = original.replace("buyers can't hold", "buyers cannot hold", 1)
            check("   (the check's edit really changes the file)", edited != original,
                  "one word of story 1's title")
            stories.write_text(edited, encoding="utf-8")
            differs = refused(lambda: t.do_confirm(stories, data, lambda: minutes(2), fp1, STAND_IN, WHO))
            stories.write_text(original, encoding="utf-8")

            # 5. A preview older than the limit can't be confirmed (made 20 minutes before now).
            fp_old = previewed(t.do_preview(stories, data, minutes(5), made_at=minutes(-15)))
            stale = refused(lambda: t.do_confirm(stories, data, lambda: minutes(5), fp_old, STAND_IN, WHO))
            fp_edge = previewed(t.do_preview(stories, data, minutes(5), made_at=minutes(-10)))
            piped = subprocess.run(
                [sys.executable, str(TOOL_PATH), "confirm", "--stories", str(stories)],
                input=t.grouped(fp1) + "\n", capture_output=True, text=True, cwd=work,
                env={**os.environ, t.TOKEN_VAR: STAND_IN})
            tokenless = refused(lambda: t.do_confirm(stories, data, lambda: minutes(3), fp1, None, WHO))
            tokenless_clean = state() == empty
            said.extend([piped.stdout, piped.stderr])

            # The real write: a fresh, matching preview confirmed in time. If an earlier step wrongly
            # wrote anything, this is refused, and the checks below report it rather than crash.
            try:
                written_lines = t.do_confirm(stories, data, lambda: minutes(3), fp1, STAND_IN, WHO)
            except t.Refused as exc:
                written_lines = [f"(refused: {exc})"]
            items = t.load_tracker(data)
            check("3. Confirmation names the exact preview",
                  len(items) == len(change["stories"])
                  and all(i["preview_fingerprint"] == fp1 for i in items),
                  f"typing {t.grouped(fp1)} wrote {len(items)} stories, each recording that fingerprint")

            # 4. A change that differs from the preview is refused, and nothing is written.
            check("4. Changed after preview: refused, nothing written",
                  bool(differs) and "title changed" in (differs or ""),
                  (differs or "not refused").split(" Nothing was written")[0])

            # 5 (continued).
            check("5. Preview older than 15 minutes: refused, nothing written",
                  bool(stale) and "expired" in (stale or ""),
                  (stale or "not refused").split(" Nothing was written")[0])
            edge = refused(lambda: t.do_confirm(stories, data, lambda: minutes(5), fp_edge, STAND_IN, WHO))
            check("   (at exactly 15 minutes the preview is still valid, until the tracker changes)",
                  bool(edge) and "expired" not in (edge or "") and "tracker has changed" in (edge or ""),
                  "refused only because the stories were already written")
            rollback_dir = work / "rollback"
            fp_back = previewed(t.do_preview(stories, rollback_dir, CLOCK))
            rolled_back = refused(lambda: t.do_confirm(stories, rollback_dir, lambda: minutes(-120), fp_back,
                                                       STAND_IN, WHO))
            check("   (a clock set back can't stretch the limit)",
                  bool(rolled_back) and "earlier than the preview was made" in (rolled_back or "")
                  and not t.load_tracker(rollback_dir),
                  "a confirmation with the clock 2 hours behind the preview is refused")

            # 6. The result records what was written and that a person confirmed it: every stored
            # field equals the previewed one, plus the key, who confirmed, when, and the fingerprint.
            expected = [{"key": f"TIX-{n}", **s, "confirmed_by": WHO, "confirmed_at": t.iso(minutes(3)),
                         "preview_fingerprint": fp1} for n, s in enumerate(change["stories"], 1)]
            recorded = items == expected
            again = refused(lambda: t.do_confirm(stories, data, lambda: minutes(4), fp1, STAND_IN, WHO))
            dup = refused(lambda: t.do_preview(stories, data, minutes(4)))
            check("6. Result records what was written and who confirmed it",
                  recorded and bool(again) and bool(dup) and len(t.load_tracker(data)) == len(items),
                  f"{', '.join(i['key'] for i in items)} hold every previewed field unchanged, plus who, "
                  "when and the fingerprint; the same preview can't be confirmed twice, and the same "
                  "stories can't be previewed again")

            # Two confirmations of one preview at the same moment: exactly one writes. The function
            # confirm uses to read the tracker is slowed down, and both start together, so without
            # the lock they would both read the empty tracker before either wrote.
            race_dir = work / "race"
            fp_race = previewed(t.do_preview(stories, race_dir, CLOCK))
            real_read = t.stored_items
            reads: list[int] = []

            def slow_read(opened):
                found = real_read(opened)
                reads.append(len(found))
                time.sleep(0.2)
                return found

            outcomes: list[str] = []
            start_together = threading.Barrier(2)

            def racer() -> None:
                start_together.wait()
                try:
                    said.extend(t.do_confirm(stories, race_dir, lambda: minutes(1), fp_race, STAND_IN, WHO))
                    outcomes.append("written")
                except t.Refused as exc:
                    said.append(str(exc))
                    outcomes.append("refused")

            t.stored_items = slow_read
            try:
                racers = [threading.Thread(target=racer) for _ in range(2)]
                for r in racers:
                    r.start()
                for r in racers:
                    r.join()
            finally:
                t.stored_items = real_read
            raced = t.load_tracker(race_dir)
            check("   Two confirmations at the same moment: one write",
                  sorted(outcomes) == ["refused", "written"] and len(raced) == len(change["stories"])
                  and len(reads) >= 1,  # the slowed reader really ran
                  f"one written, one refused; the tracker holds {len(raced)} stories, not "
                  f"{2 * len(change['stories'])}")

            # Safety constraints and refusals that stand on their own.
            check("   No typed confirmation from a pipe", piped.returncode == 1 and "keyboard" in piped.stdout,
                  "an answer piped in is refused")
            check("   No token, no write", bool(tokenless) and t.TOKEN_VAR in (tokenless or "")
                  and tokenless_clean, f"{t.TOKEN_VAR} unset is refused, and the tracker is unchanged")

            # The real commands, end to end: preview, then confirm with the fingerprint typed at a
            # simulated keyboard, then list. This is the path a person uses, not just the functions.
            cli = work / "cli"
            cli.mkdir()
            env = {**os.environ, t.TOKEN_VAR: STAND_IN}
            run = [sys.executable, str(TOOL_PATH)]
            shown_preview = subprocess.run(run + ["preview", "--stories", str(stories)], cwd=cli, env=env,
                                           capture_output=True, text=True)
            fp_line = [x for x in shown_preview.stdout.splitlines() if x.startswith("Preview fingerprint:")]
            keyboard, terminal = pty.openpty()
            confirming = subprocess.Popen(run + ["confirm", "--stories", str(stories)], cwd=cli, env=env,
                                          stdin=terminal, stdout=subprocess.PIPE,
                                          stderr=subprocess.PIPE, text=True)
            os.close(terminal)
            if fp_line:
                os.write(keyboard, (fp_line[0].split(": ", 1)[1] + "\n").encode())
            out, err = confirming.communicate(timeout=60)
            os.close(keyboard)
            listed = subprocess.run(run + ["list"], cwd=cli, env=env, capture_output=True, text=True)
            said.extend([shown_preview.stdout, shown_preview.stderr, out, err, listed.stdout, listed.stderr])
            check("   The real commands work end to end",
                  bool(fp_line) and confirming.returncode == 0 and "Tracker: 3 stories" in listed.stdout,
                  "preview, confirm with the fingerprint typed at a keyboard, then list shows 3 stories")

            # A tracker folder that is a link to somewhere else is refused, and nothing is written
            # through it.
            elsewhere = work / "elsewhere"
            elsewhere.mkdir()
            (elsewhere / "stories.json").write_text("[]\n", encoding="utf-8")
            linked = work / "linked"
            linked.mkdir()
            os.symlink(elsewhere, linked / "tracker")
            via_link = refused(lambda: t.do_preview(stories, linked / "tracker", CLOCK))
            check("   A tracker folder that is a link is refused",
                  bool(via_link) and sorted(x.name for x in elsewhere.iterdir()) == ["stories.json"]
                  and (elsewhere / "stories.json").read_text(encoding="utf-8") == "[]\n",
                  "nothing is read or written through it, and the folder it points to is untouched")

            # Every file saved anywhere in the check's folder, read as bytes, and everything the
            # tracker printed (in this process or the real commands) or returned.
            stored = b"".join(p.read_bytes() for p in work.rglob("*") if p.is_file() and not p.is_symlink())
            shown_text = "\n".join([text, *written_lines, *said, printed_out.getvalue(),
                                    printed_err.getvalue()])
            check("   The token is never stored or shown",
                  STAND_IN.encode() not in stored and STAND_IN not in shown_text,
                  "not in any saved file, nor in anything the tracker printed or returned")
        except t.Refused as exc:
            # A step was refused that should have worked: something earlier wrote when it
            # shouldn't have. That is a failure to report, not a crash.
            check("   Every step ran as planned", False, f"unexpected refusal: {str(exc)[:80]}")

    width = max(len(label) for label, _, _ in results)
    print(f"# check-write-preview.py {VERSION}")
    print(f"Stories: {shown(args.stories)}")
    print(f"Clock:   fixed at {t.shown_time(CLOCK)}, in a temporary folder")
    print()
    for label, ok, detail in results:
        print(f"{'PASS' if ok else 'FAIL'}  {label:<{width}}  {detail}")
    print("      7. A person can read the preview and say what will happen: judged by a person, "
          "from logs/preview.txt.")
    failed = [label for label, ok, _ in results if not ok]
    print()
    print(f"result: {'FAILED' if failed else 'PASSED'} (exit status {1 if failed else 0})")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
