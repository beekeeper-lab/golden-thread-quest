"""Plant one bug at a time in a copy of the scripts and report whether the tests notice."""
import shutil, subprocess, sys, tempfile
from pathlib import Path

SRC = Path(sys.argv[1])
BUGS = [
 ("chain check switched off", "auditlog.py",
  "if chain != chain_of(prev_chain, cells[:9]):", "if False:"),
 ("sequence number check switched off", "auditlog.py",
  "if seq != str(i):", "if False:"),
 ("anchor ignores rows cut from the end", "auditlog.py",
  "if len(rows) < count:", "if False:"),
 ("anchor ignores rows added without the tool", "auditlog.py",
  "if exact and len(rows) > count:", "if False:"),
 ("anchor head comparison switched off", "auditlog.py",
  "if actual != head:", "if False:"),
 ("missing anchor accepted", "auditlog.py",
  "    if anchor is None:\n        return [f\"{label} is missing or unreadable\"]",
  "    if anchor is None:\n        return []"),
 ("committed anchor never consulted", "auditlog.py",
  "    if git_ref:\n", "    if False:\n"),
 ("time order check switched off", "auditlog.py",
  "if prev_time is not None and this_time < prev_time:", "if False:"),
 ("bad time format accepted", "auditlog.py",
  "            problems.append(f\"{where}: time is missing or not in the form YYYY-MM-DD HH:MM:SS\")",
  "            pass"),
 ("unknown kind accepted by check", "auditlog.py",
  "        if kind not in KINDS:\n            problems.append", "        if False:\n            problems.append"),
 ("empty field accepted by check", "auditlog.py",
  "            if not cells[col]:", "            if False:"),
 ("confirmed write needs no preview", "auditlog.py",
  "if earlier is None or earlier[2] != needs:", "if earlier is None:"),
 ("preview for another target accepted", "auditlog.py",
  "elif kind == \"confirmed write\" and earlier[4] != target:", "elif False:"),
 ("credential scan switched off", "auditlog.py",
  "    for name, pattern in SECRET_RULES:\n        if pattern.search(text):", "    for name, pattern in SECRET_RULES:\n        if False:"),
 ("refusal message echoes the value", "auditlog.py",
  "raise AuditError(f\"{name} looks like it holds a credential ({rule}); \"", "raise AuditError(f\"{name} = {value} looks like it holds a credential ({rule}); \""),
 # Both places that refuse a | are switched off together. Switching off only the first
 # changes nothing a caller can see, because the row check refuses it as well.
 ("pipe in a field accepted", "auditlog.py",
  "return any(c == \"|\" or unicodedata.category(c)", "return any(unicodedata.category(c)"),
 ("control characters accepted (only | refused)", "auditlog.py",
  "return any(c == \"|\" or unicodedata.category(c) in (\"Cc\", \"Cf\", \"Zl\", \"Zp\") for c in text)", "return \"|\" in text"),
 ("heading above the rows not checked", "auditlog.py",
  "    if not text.startswith(HEADER):\n        return [], [", "    if \"|---\" not in text:\n        return [], ["),
 ("row spacing and line endings not checked", "auditlog.py",
  "if format_row(cells) != line + \"\\n\":", "if False:"),
 ("missing final line break accepted", "auditlog.py",
  "if body and not body.endswith(\"\\n\"):", "if False:"),
 ("check does not scan existing rows for credentials", "auditlog.py",
  "            rule = secret_rule(cells[col])\n            if rule:\n                problems.append(f\"{where}: {COLUMNS[col]} looks", "            rule = None\n            if rule:\n                problems.append(f\"{where}: {COLUMNS[col]} looks"),
 ("recovery needs no failure link", "auditlog.py",
  "needs = {\"confirmed write\": \"preview\", \"recovery\": \"failure\"}.get(kind)", "needs = {\"confirmed write\": \"preview\"}.get(kind)"),
 ("Ref on other kinds not checked", "auditlog.py",
  "elif ref and earlier_row(ref, i) is None:", "elif False:"),
 ("Ref accepts non-ASCII digits", "auditlog.py",
  "if ref.isascii() and ref.isdigit() and 1 <= int(ref) < i:", "if ref.isdigit() and 1 <= int(ref) < i:"),
 ("append allowed onto a log that fails its check", "auditlog.py",
  "        if problems:\n            raise AuditError(\"the existing log does not pass", "        if False:\n            raise AuditError(\"the existing log does not pass"),
 ("local time written instead of UTC", "auditlog.py",
  "when = (now or datetime.now(timezone.utc)).strftime(TIME_FORMAT)", "when = (now or datetime.now()).strftime(TIME_FORMAT)"),
 ("partly masked rule removed", "auditlog.py",
  "    (\"partly masked value\", re.compile(r\"[A-Za-z0-9]{2,}\\*{3,}|\\*{3,}[A-Za-z0-9]{2,}\")),\n", ""),
 ("known token prefix rule removed", "auditlog.py",
  "    (\"known token prefix\",\n     re.compile(r\"\\b(ATATT|AKIA|gh[pousr]_|sk-|xox[abprs]-)[A-Za-z0-9*_\\-]{4,}\")),\n", ""),
 ("private key rule removed", "auditlog.py",
  "    (\"private key block\", re.compile(r\"-----BEGIN\")),\n", ""),
 ("long opaque value rule removed", "auditlog.py",
  "[A-Za-z0-9+_=]{32,}\\b\")),", "[A-Za-z0-9+_=]{3200,}\\b\")),"),
 ("failure row uses the generic reason", "run_workflow.py",
  "reason = REASONS.get(error.code, \"an error", "reason = REASONS.get(\"none\", \"an error"),
 ("terminal answer recorded as piped", "run_workflow.py",
  "    typed = sys.stdin.isatty()", "    typed = False"),
 ("final read-back row not logged", "run_workflow.py",
  "            log(\"read\", \"Read the ticket back to confirm the change\", \"n/a\",\n                f\"Done. Assignee is {after}.\")\n", ""),
 ("middle of the private text leaks into the failure row", "run_workflow.py",
  "f\"Failed. Reason: {reason}. The tool does not yet know \"", "f\"Failed. Reason: {reason} {str(error)[-40:-10]}. The tool does not yet know \""),
 ("demo skips the attacks on the text around the rows", "tamper_demo.py",
  "            if result.returncode == 1 and changed:", "            if True:"),
 ("append rewrites the file instead of appending", "auditlog.py",
  "    with log.open(\"a\", encoding=\"utf-8\") as f:  # append mode: earlier bytes are not rewritten\n        f.write(format_row(cells))",
  "    with log.open(\"w\", encoding=\"utf-8\") as f:\n        f.write(HEADER + ''.join(format_row(r).replace(' |\\n', '|\\n') for r in rows) + format_row(cells))"),
 ("failure row logs the raw error text", "run_workflow.py",
  "reason = REASONS.get(error.code, \"an error the tool does not recognise \"\n                                                     \"(details withheld from the log)\")",
  "reason = str(error)"),
 ("raw error text printed to the screen", "run_workflow.py",
  "say(f\"The write failed: {reason}.\")", "say(f\"The write failed: {error}.\")"),
 ("piped answer recorded as typed", "run_workflow.py",
  "return True, (\"Yes, typed at the prompt\" if typed", "return True, (\"Yes, typed at the prompt\" if True"),
 ("write goes ahead after a no", "run_workflow.py",
  "            if not yes:\n                log(\"preview\", \"Closed the preview without writing\"", "            if False:\n                log(\"preview\", \"Closed the preview without writing\""),
 ("recovery row not linked to its failure", "run_workflow.py",
  "\"The same change can be tried again.\", failure)", "\"The same change can be tried again.\")"),
 ("no failure injected (tracker never fails)", "run_workflow.py",
  "self.failures_left = 1", "self.failures_left = 0"),
 ("demo reports DETECTED whatever the checker says", "tamper_demo.py",
  "if result.returncode != 0 and changed:", "if True:"),
 ("demo edits the real log", "tamper_demo.py",
  "            rewrite(copy, change)\n            changed", "            rewrite(log, change)\n            changed"),
]
survived = 0
ONLY = [int(x) for x in sys.argv[2:]]
for n, (title, fname, old, new) in enumerate(BUGS, start=1):
    if ONLY and n not in ONLY: continue
    with tempfile.TemporaryDirectory() as d:
        work = Path(d) / "attempt"
        shutil.copytree(SRC, work, ignore=shutil.ignore_patterns("__pycache__"))
        f = work / "scripts" / fname
        text = f.read_text()
        if text.count(old) != 1:
            print(f"NOT PLANTED (pattern found {text.count(old)} times): {title}"); survived += 1; continue
        f.write_text(text.replace(old, new))
        r = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", str(work / "tests")],
                           capture_output=True, text=True)
        tail = r.stderr.strip().splitlines()[-1] if r.stderr.strip() else ""
        if r.returncode == 0:
            survived += 1; print(f"SURVIVED (tests still pass): {title}")
        else:
            print(f"CAUGHT: {title}  [{tail}]")
print(f"\n{len(BUGS)} bugs planted, {len(BUGS) - survived} caught, {survived} survived or not planted")
sys.exit(1 if survived else 0)
