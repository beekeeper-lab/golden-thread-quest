"""List and checksum every file under a folder, and compare two such listings.

This looks at the files themselves. It does not ask the agent what it did.

    python3 -B snapshot.py <folder>          print a listing digest
"""
import hashlib
import os
import stat
import sys
from pathlib import Path


def _entry(path):
    try:
        st = os.lstat(path)
    except OSError:
        return {"kind": "vanished", "sha": "", "size": 0, "mode": 0, "mtime_ns": 0}
    base = {"size": st.st_size, "mode": stat.S_IMODE(st.st_mode), "mtime_ns": st.st_mtime_ns}
    if stat.S_ISLNK(st.st_mode):
        return dict(base, kind="link", sha="-> " + os.readlink(path))
    if stat.S_ISDIR(st.st_mode):
        return dict(base, kind="dir", sha="", size=0)
    if not stat.S_ISREG(st.st_mode):
        return dict(base, kind="special", sha="")
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
    except OSError as e:
        return dict(base, kind="unreadable", sha=type(e).__name__)
    return dict(base, kind="file", sha=h.hexdigest())


def take(root, exclude=()):
    """Map of path (relative, with /) to kind, content hash, size, permission and time, for everything under root."""
    root = Path(root)
    skip = {e.strip("/") for e in exclude}
    snap = {}
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        rel_dir = Path(dirpath).relative_to(root).as_posix()
        rel_dir = "" if rel_dir == "." else rel_dir + "/"
        keep = []
        for d in sorted(dirnames):
            rel = rel_dir + d
            if rel in skip:
                continue
            if os.path.islink(os.path.join(dirpath, d)):
                snap[rel] = _entry(os.path.join(dirpath, d))
            else:
                keep.append(d)
        dirnames[:] = keep
        names = [n for n in sorted(filenames) if rel_dir + n not in skip]
        for n in names:
            snap[rel_dir + n] = _entry(os.path.join(dirpath, n))
        if rel_dir and not keep and not names and not any(k.startswith(rel_dir) for k in snap):
            snap[rel_dir] = _entry(dirpath)
    return snap


def take_files(labelled):
    """Snapshot single files given as (label, path). A missing file is recorded as absent."""
    out = {}
    for label, path in labelled:
        out[label] = _entry(path) if os.path.lexists(path) else {"kind": "absent", "sha": "", "size": 0, "mode": 0, "mtime_ns": 0}
    return out


def digest(snap, with_times=False):
    h = hashlib.sha256()
    for rel in sorted(snap):
        e = snap[rel]
        line = f"{rel}\t{e['kind']}\t{e['sha']}\t{e['size']}\t{e['mode']:o}"
        if with_times:
            line += f"\t{e['mtime_ns']}"
        h.update(line.encode("utf-8", "surrogateescape") + b"\n")
    return h.hexdigest()


def compare(before, after):
    added = sorted(set(after) - set(before))
    removed = sorted(set(before) - set(after))
    changed, touched = [], []
    for rel in sorted(set(before) & set(after)):
        b, a = before[rel], after[rel]
        if (b["kind"], b["sha"], b["size"]) != (a["kind"], a["sha"], a["size"]):
            changed.append(rel)
        elif (b["mode"], b["mtime_ns"]) != (a["mode"], a["mtime_ns"]) and b["kind"] != "dir":
            touched.append(rel)
    return {"added": added, "removed": removed, "changed": changed, "touched": touched,
            "total": len(added) + len(removed) + len(changed) + len(touched)}


def _line(name, snap):
    files = sum(1 for e in snap.values() if e["kind"] != "dir")
    size = sum(e["size"] for e in snap.values())
    return f"  {name:<7} entries {len(snap):>6}  files {files:>6}  bytes {size:>12}  checksum {digest(snap)}\n" \
           f"  {'':<7} checksum including modification times {digest(snap, True)}"


def report(label, before, after, diff, exclude):
    out = [f"Folder: {label}",
           "Skipped folders: " + (", ".join(sorted(exclude)) if exclude else "none"),
           "Checksum = SHA-256 over every path with its type, size, permission and content hash.",
           _line("before", before), _line("after", after),
           f"  added {len(diff['added'])}, removed {len(diff['removed'])}, content changed {len(diff['changed'])}, "
           f"same content but new time or permission {len(diff['touched'])}"]
    for kind, title in (("added", "added"), ("removed", "removed"), ("changed", "content changed"), ("touched", "new time or permission")):
        for rel in diff[kind][:200]:
            out.append(f"    {title}: {rel}")
        if len(diff[kind]) > 200:
            out.append(f"    ... and {len(diff[kind]) - 200} more {title}")
    tops = sorted({rel.split("/")[0] + ("/" if "/" in rel else "") for rel in set(before) | set(after)})
    out.append("  By top-level name (entries before, entries after, checksums match?):")
    for top in tops:
        pick = (lambda s: {k: v for k, v in s.items() if k == top or k.startswith(top)}) if top.endswith("/") else (lambda s: {k: v for k, v in s.items() if k == top})
        b, a = pick(before), pick(after)
        same = digest(b, True) == digest(a, True)
        out.append(f"    {top:<34} {len(b):>6} {len(a):>6}  {'same' if same else 'DIFFERENT'}  {digest(a)[:16]}")
    out.append(f"  Folder verdict: {'UNCHANGED' if diff['total'] == 0 else 'CHANGED'}")
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    s = take(sys.argv[1], sys.argv[2:])
    print(_line("now", s))
