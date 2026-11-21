#!/usr/bin/env python3
"""Previews the creation of one Trello card from a local draft. It writes nothing to Trello.

    preview.py --source live|fake --draft DRAFT.md --allowlist FILE --boards FOLDER --state FOLDER
               [--payload-out FILE.md] [--log FILE] [--now 2026-11-20T09:00:00Z]

It reads a draft, asks Trello about the board and the list the draft names,
and shows exactly what a later create would send. Then it stops. This file
has no code that sends a write: every request it makes is a GET.

The draft is a Markdown file. Between two lines of three dashes are the
card's fields, one per line, a name, a colon and a JSON value:

    format: "trello-card-draft/1"
    board: "<board id>"                 the board, by its Trello id
    list: "<list id>"                   the list, by its Trello id
    position: "bottom"                  "top", "bottom" or a number above zero. Required
    name: "..."
    labels: ["export"]                  optional, by name. Each must exist on the board
    members: ["<member id>"]            optional. Each must be a member of the board
    due: "2026-12-04T17:00:00.000Z"     optional
    duplicate_decision: "link"          optional: a person's decision about likely duplicates
    duplicate_candidates: ["<card id>"] the cards that decision was made about

Under the heading "## Description" is the description, sent as written. Under
"## Sources" is one line per citation:

    - name: sources/notes.md line 7: "the words quoted"
    - description: sources/notes.md lines 8-9: "more words"

Every piece of content in the draft needs at least one citation, and every
citation is checked: the file must be under participant/context/, and the
quoted words must be on the lines named.

There are two kinds of problem.

REFUSED. The draft points at something that is not there, or is not allowed:
the board is not on the sandbox allowlist, the list does not exist, belongs
to another board or is archived, a label or a member does not exist on the
board, a citation is not true. No payload is shown, saved or written.

NOT READY TO WRITE. The draft is valid and the write should not go ahead yet:
the token may not write, the token's member may not add cards to the board,
or the duplicate search found a likely duplicate that no recorded decision
covers. The whole preview is shown, with each reason. Nothing is saved for a
later write.

Otherwise the verdict is READY TO WRITE, and the payload, its SHA-256 and a
fingerprint are saved in the state folder for a later write to check.

The payload is built in one place, build_payload, and turned into the bytes
that would be sent in one place, body_bytes.

For a live run the key and the token come from the environment variables
TRELLO_API_KEY and TRELLO_API_TOKEN. Neither is stored, and everything that
would be shown or saved is searched for them first.

Text from Trello is other people's writing. List, board and label names are
shown quoted. No card's name or description from Trello is printed, and
nothing in any of it is acted on.

Exit codes: 0 a preview was made and is READY; 3 a preview was made and is
NOT READY; 1 refused, with the reason.
"""
import argparse
import datetime
import hashlib
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "participant", "skills", "trello-read-card"))
sys.path.insert(0, os.path.join(ROOT, "participant", "skills", "trello-duplicate-search"))
sys.path.insert(0, HERE)
import search  # noqa: E402
from search import index  # noqa: E402

DRAFT_FORMAT = "trello-card-draft/1"
DRAFT_NAMES = ("format", "board", "list", "position", "name", "labels", "members", "due", "duplicate_decision", "duplicate_candidates")
CONTENT = ("name", "description", "labels", "members", "due")
CONTEXT = os.path.join(ROOT, "participant", "context")
LIMIT_MINUTES = 15
TIME_FORMAT = "%Y-%m-%d %H:%M:%S UTC"
TRELLO_ID = re.compile(r"[0-9a-f]{24}")
DUE = re.compile(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{3}Z")
SOURCE = re.compile(r'- (?P<what>[^:]+): (?P<file>\S+) lines? (?P<first>\d+)(?:-(?P<last>\d+))?: "(?P<quote>.+)"')
CARD_LIMIT = 1000
PATH_SHOWN = "/tokens/[the token]"
REQUEST = "POST https://api.trello.com/1/cards"

LINES = []


class Refused(Exception):
    """No preview is made. The message is the reason."""


def say(text=""):
    LINES.append(text)


# ---------------------------------------------------------------- the connection: reading only


class Connection:
    """Every request goes through here and is written down. There is only get."""

    def __init__(self, get, token_path):
        self._get, self._token_path, self.sent = get, token_path, []

    def get(self, path, params=None):
        self.sent.append(("GET", PATH_SHOWN if path == self._token_path else path))
        try:
            status, _, body = self._get(path, params)
        except Exception as err:
            if type(err).__name__ != "Stop" and not isinstance(err, (OSError, TimeoutError)):
                raise
            # the approved reader raises its own Stop for a network failure
            raise Refused("could not reach Trello (%s)" % (str(err)[:80] if type(err).__name__ == "Stop" else type(err).__name__))
        return status, body

    def token(self):
        """The token's own record. The path holds the token, so it is never written down."""
        return self.get(self._token_path, {"fields": "permissions,dateExpires,idMember"})


def make_live():
    import card  # the reader approved in the trello-read-card quest. Its only request function sends GET.
    try:
        get, secrets = card.make_live_get()
    except card.Stop as stop:
        raise Refused(str(stop))
    return Connection(get, "/tokens/%s" % secrets[1]), secrets


def load_allowlist(path):
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        raise Refused("there is no sandbox allowlist at the path given")
    except ValueError:
        raise Refused("the sandbox allowlist is not JSON")
    entries = data.get("sandbox_boards") if isinstance(data, dict) else None
    if not isinstance(entries, list) or not all(isinstance(entry, str) and TRELLO_ID.fullmatch(entry) for entry in entries):
        raise Refused("the sandbox allowlist must hold a list of board ids named sandbox_boards")
    return set(entries)


# ---------------------------------------------------------------- the draft


def read_draft(path):
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except (OSError, UnicodeDecodeError):
        raise Refused("the draft could not be read")
    front = index.front_matter(text)
    if front is None or front.get("format") != DRAFT_FORMAT:
        raise Refused("the file is not a card draft: its format is not %s" % DRAFT_FORMAT)
    for name, value in front.items():
        if name not in DRAFT_NAMES:
            raise Refused("the draft has a field this preview does not support: %s. It supports %s"
                          % (json.dumps(name[:40]), ", ".join(DRAFT_NAMES[1:])))
        if value is index.Unreadable:
            raise Refused("the draft's value for %s is not JSON" % name)

    def ident(name, what):
        value = front.get(name)
        if not isinstance(value, str) or not TRELLO_ID.fullmatch(value):
            raise Refused("the draft must give the %s by its Trello id, 24 characters of 0-9 and a-f, as %s. A name is "
                          "not accepted, because two can share one" % (what, name))
        return value

    def list_of(name, pattern=None):
        value = front.get(name)
        if value is None:
            return []
        if not isinstance(value, list) or not value or not all(isinstance(item, str) and item.strip() for item in value) \
                or len(set(value)) != len(value) or (pattern and not all(pattern.fullmatch(item) for item in value)):
            raise Refused("the draft's %s must be a list of different %s" % (name, "Trello ids" if pattern else "names"))
        return value
    draft = {"path": os.path.abspath(path), "board": ident("board", "board"), "list": ident("list", "list"),
             "labels": list_of("labels"), "members": list_of("members", TRELLO_ID),
             "candidates": list_of("duplicate_candidates", TRELLO_ID)}
    name = front.get("name")
    if not isinstance(name, str) or not name.strip() or "\n" in name:
        raise Refused("the draft has no usable name")
    if len(name) > 16384:
        raise Refused("the draft's name is longer than the 16,384 characters Trello allows")
    draft["name"] = name.strip()
    position = front.get("position")
    if position in ("top", "bottom"):
        draft["position"] = position
    elif isinstance(position, (int, float)) and not isinstance(position, bool) and position > 0:
        draft["position"] = position
    else:
        raise Refused('the draft must say where in the list the card goes: position is "top", "bottom" or a number above '
                      "zero. There is no default")
    due = front.get("due")
    if due is not None:
        try:
            if not isinstance(due, str) or not DUE.fullmatch(due):
                raise ValueError
            datetime.datetime.strptime(due, "%Y-%m-%dT%H:%M:%S.%fZ")
        except ValueError:
            raise Refused("the draft's due is not a real time written like 2026-12-04T17:00:00.000Z")
    draft["due"] = due
    decision = front.get("duplicate_decision")
    if decision is not None and decision not in search.ADVICE:
        raise Refused("the draft's duplicate_decision must be one of: %s" % ", ".join(search.ADVICE))
    if draft["candidates"] and not decision:
        raise Refused("the draft names duplicate_candidates and records no duplicate_decision about them")
    draft["decision"] = decision

    body = text.split("\n## Description\n", 1)[1] if "\n## Description\n" in text else ""
    described, _, cited = body.partition("\n## Sources\n")
    draft["description"] = described.strip()
    if len(draft["description"]) > 16384:
        raise Refused("the draft's description is longer than the 16,384 characters Trello allows")
    draft["sources"] = []
    for line in cited.split("\n"):
        if not line.strip():
            continue
        match = SOURCE.fullmatch(line.strip())
        if not match:
            raise Refused("a line under Sources could not be read as a citation: %s" % json.dumps(line.strip()[:60]))
        first = int(match.group("first"))
        draft["sources"].append({"what": match.group("what").strip(), "file": match.group("file"), "first": first,
                                 "last": int(match.group("last") or first), "quote": match.group("quote")})
    return draft


def check_sources(draft):
    """Every piece of content is cited, and every citation is true. Returns the checked citations."""
    needed = [name for name in CONTENT if draft[name]]
    for source in draft["sources"]:
        if source["what"] not in needed:
            raise Refused("a citation is for %s, which is not in the draft" % json.dumps(source["what"][:40]))
        path = os.path.realpath(os.path.join(os.path.dirname(draft["path"]), source["file"]))
        if os.path.commonpath([path, os.path.realpath(CONTEXT)]) != os.path.realpath(CONTEXT):
            raise Refused("the citation for %s points outside participant/context/" % source["what"])
        try:
            with open(path, encoding="utf-8") as f:
                lines = f.read().split("\n")
        except (OSError, UnicodeDecodeError):
            raise Refused("the source cited for %s could not be read: %s" % (source["what"], source["file"]))
        if not 1 <= source["first"] <= source["last"] <= len(lines):
            raise Refused("the citation for %s names lines that %s does not have" % (source["what"], source["file"]))
        there = " ".join(" ".join(lines[source["first"] - 1:source["last"]]).split())
        if " ".join(source["quote"].split()) not in there:
            raise Refused("the citation for %s is not true: the quoted words are not at %s line %d"
                          % (source["what"], source["file"], source["first"]))
    missing = [name for name in needed if not any(source["what"] == name for source in draft["sources"])]
    if missing:
        raise Refused("the draft gives no source for: %s. Every piece of content needs a citation" % ", ".join(missing))
    return draft["sources"]


# ---------------------------------------------------------------- reading Trello


def rows_of(conn, path, params, what):
    status, body = conn.get(path, params)
    if status != 200 or not isinstance(body, list) or not all(isinstance(row, dict) and isinstance(row.get("id"), str) for row in body):
        raise Refused("Trello did not give %s (status %d), so nothing is assumed" % (what, status))
    return body


def read_me(conn):
    status, body = conn.get("/members/me", {"fields": "id"})
    if status == 401:
        raise Refused("Trello rejected the key or the token (401). Check TRELLO_API_KEY and TRELLO_API_TOKEN")
    if status != 200 or not isinstance(body, dict) or not isinstance(body.get("id"), str):
        raise Refused("Trello did not say which member this token belongs to (status %d)" % status)
    return body["id"]


def read_board(conn, board_id):
    status, body = conn.get("/boards/%s" % board_id, {"fields": "name,closed"})
    if status in (400, 401, 403, 404):
        raise Refused("the board %s is not visible to this token (Trello answered %d). It does not exist, or the token's "
                      "member cannot see it" % (board_id, status))
    if status != 200 or not isinstance(body, dict) or body.get("id") != board_id or not isinstance(body.get("name"), str):
        raise Refused("Trello's answer for the board could not be used (status %d)" % status)
    if body.get("closed") is not False:
        raise Refused("the board %s is closed. A card cannot be created on a closed board" % board_id)
    return {"id": board_id, "name": body["name"]}


def read_list(conn, list_id, board, lists):
    """The target list, asked for by its id. It must exist, be on the stated board and be open."""
    status, body = conn.get("/lists/%s" % list_id, {"fields": "name,closed,idBoard,pos"})
    if status in (400, 404):
        raise Refused("the list %s does not exist (Trello answered %d). The draft must name a list of board %s by its id. "
                      "The board's open lists are: %s" % (list_id, status, board["id"], open_lists(lists)))
    if status != 200 or not isinstance(body, dict) or body.get("id") != list_id:
        raise Refused("Trello's answer for the list could not be used (status %d)" % status)
    if body.get("idBoard") != board["id"]:
        raise Refused("the list %s is not on the stated board. The draft says board %s, and Trello says the list belongs to "
                      "board %s. The stated board's open lists are: %s"
                      % (list_id, board["id"], str(body.get("idBoard"))[:24], open_lists(lists)))
    if list_id not in [row["id"] for row in lists]:
        raise Refused("the list %s is not among the lists Trello gives for board %s" % (list_id, board["id"]))
    if body.get("closed") is not False:
        raise Refused("the list %s, %s, is archived. A card created there would not be seen on the board. The board's open "
                      "lists are: %s" % (list_id, json.dumps(str(body.get("name"))), open_lists(lists)))
    return {"id": list_id, "name": str(body.get("name")), "pos": body.get("pos")}


def open_lists(lists):
    shown = sorted((row for row in lists if row.get("closed") is False), key=lambda row: (index.number(row.get("pos")) or 0, row["id"]))
    return ", ".join("%s (%s)" % (json.dumps(str(row.get("name"))), row["id"]) for row in shown) or "none"


def resolve_labels(conn, board, wanted):
    """The board's label id for each name in the draft. A name must match exactly one label."""
    if not wanted:
        return []
    labels = rows_of(conn, "/boards/%s/labels" % board["id"], {"fields": "name,color", "limit": 1000}, "the board's labels")
    named = sorted(set(str(row.get("name")) for row in labels if row.get("name")))
    found = []
    for name in wanted:
        matches = [row["id"] for row in labels if row.get("name") == name]
        if not matches:
            raise Refused("the label %s does not exist on board %s. Its named labels are: %s. This preview does not create a "
                          "label" % (json.dumps(name), board["id"], ", ".join(json.dumps(item) for item in named) or "none"))
        if len(matches) > 1:
            raise Refused("the board has %d labels named %s, so the name does not say which is meant" % (len(matches), json.dumps(name)))
        found.append(matches[0])
    return found


def check_members(conn, board, wanted):
    if not wanted:
        return
    on_board = set(row["id"] for row in rows_of(conn, "/boards/%s/members" % board["id"], {"fields": "id"}, "the board's members"))
    for member in wanted:
        if member not in on_board:
            raise Refused("the member %s is not a member of board %s, which has %d. Only a member of the board can be put on "
                          "its cards" % (member, board["id"], len(on_board)))


def snapshot(conn, board_id):
    """The board's lists and cards as Trello gives them now, and one code for all of it."""
    lists = rows_of(conn, "/boards/%s/lists" % board_id, {"filter": "all", "fields": "name,pos,closed"}, "the board's lists")
    cards = rows_of(conn, "/boards/%s/cards" % board_id,
                    {"filter": "all", "fields": "idList,pos,closed,dateLastActivity", "limit": CARD_LIMIT}, "the board's cards")
    if len(cards) >= CARD_LIMIT:
        raise Refused("the board has more cards than this preview reads to check 'unchanged'")
    seen = sorted([row["id"], str(row.get("idList")), str(row.get("pos")), str(row.get("closed")), str(row.get("dateLastActivity"))] for row in cards)
    seen += sorted([row["id"], str(row.get("name")), str(row.get("pos")), str(row.get("closed"))] for row in lists)
    code = hashlib.sha256(json.dumps(seen, separators=(",", ":")).encode("utf-8")).hexdigest()[:16]
    return {"lists": lists, "cards": cards, "shown": (len(lists), len(cards), code)}


def placement(draft, cards):
    """Where in the list the card would sit, from the open cards in it now. Returns the lines to show."""
    here = sorted((row for row in cards if row.get("idList") == draft["list"] and row.get("closed") is False
                   and index.number(row.get("pos")) is not None), key=lambda row: (row["pos"], row["id"]))
    total = len(here)
    if not here:
        return ["the list has no open card now, so the card would be the only one."]
    if draft["position"] == "bottom":
        at = total
    elif draft["position"] == "top":
        at = 0
    else:
        at = sum(1 for row in here if row["pos"] < draft["position"])
        if any(row["pos"] == draft["position"] for row in here):
            return ["the open card %s is at position %s already. Trello orders two cards with one position in a way this "
                    "preview does not know." % (next(row["id"] for row in here if row["pos"] == draft["position"]), draft["position"])]
    out = ["number %d of %d open cards, counting the new one." % (at + 1, total + 1)]
    out.append("after:  %s" % ("card %s, at position %s" % (here[at - 1]["id"], here[at - 1]["pos"]) if at else "nothing. It would be first."))
    out.append("before: %s" % ("card %s, at position %s" % (here[at]["id"], here[at]["pos"]) if at < total else "nothing. It would be last."))
    return out


def check_permission(conn, board, me):
    """(lines to show, reasons the write may not go ahead). Asked of Trello, not assumed."""
    lines, reasons = [], []
    memberships = rows_of(conn, "/boards/%s/memberships" % board["id"], {"filter": "all"}, "the board's memberships")
    mine = [row for row in memberships if row.get("idMember") == me]
    role = mine[0].get("memberType") if len(mine) == 1 and not mine[0].get("deactivated") else None
    if role in ("admin", "normal"):
        lines.append("the token's member is on the board as: %s. That role may add cards: yes" % role)
    else:
        shown = "an observer" if role == "observer" else "not an active member"
        lines.append("the token's member is on the board as: %s. That role may add cards: NO" % (role or "not an active member"))
        reasons.append("the token's member is %s of the board, and only an ordinary member or an admin may add cards" % shown)
    status, body = conn.token()
    permissions = body.get("permissions") if status == 200 and isinstance(body, dict) else None
    if not isinstance(permissions, list):
        lines.append("the token's own permissions: Trello did not give them (status %d). May it write: NOT KNOWN" % status)
        reasons.append("Trello did not say what this token may do, so it is not assumed that it may write")
        return lines, reasons
    boards = [row for row in permissions if isinstance(row, dict) and row.get("modelType") == "Board" and row.get("idModel") in ("*", board["id"])]
    may_read, may_write = any(row.get("read") is True for row in boards), any(row.get("write") is True for row in boards)
    lines.append("the token's own permissions for boards: read %s, write %s" % ("yes" if may_read else "NO", "yes" if may_write else "NO"))
    expires = body.get("dateExpires")
    lines.append("the token expires: %s" % (expires if isinstance(expires, str) and re.fullmatch(r"[0-9T:.Z-]{10,30}", expires) else "Trello gives no expiry"))
    if not may_write:
        reasons.append("this token may read boards and may not write to them. A create sent with it would be refused by "
                       "Trello. A write needs a token made with write scope")
    return lines, reasons


# ---------------------------------------------------------------- the payload


def build_payload(draft, label_ids):
    """The one place a payload is made. Returns (payload, rows).

    rows are (the payload's name for the field, the value as shown, the name a citation uses for it or None).
    Only what the draft sets is in the payload. Lists of ids are joined with commas, as Trello's documentation gives them.
    """
    payload, rows = {}, []

    def put(key, value, shown, cited=None):
        payload[key] = value
        rows.append((key, shown, cited))
    put("idList", draft["list"], draft["list"])
    put("pos", draft["position"], json.dumps(draft["position"]))
    put("name", draft["name"], json.dumps(draft["name"], ensure_ascii=False), "name")
    if draft["description"]:
        put("desc", draft["description"], "%d characters, shown in full in the payload" % len(draft["description"]), "description")
    if draft["due"]:
        put("due", draft["due"], draft["due"], "due")
    if label_ids:
        put("idLabels", ",".join(label_ids), ", ".join("%s (label id %s)" % (json.dumps(name), label_id)
                                                       for name, label_id in zip(draft["labels"], label_ids)), "labels")
    if draft["members"]:
        put("idMembers", ",".join(draft["members"]), ", ".join(draft["members"]), "members")
    return payload, rows


def body_bytes(payload):
    """The exact bytes of the request body. The one place a payload becomes bytes."""
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def pretty(payload):
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2)


# ---------------------------------------------------------------- duplicates


def find_duplicates(draft, boards_folder):
    proposal = {"name": draft["name"], "board": draft["board"], "desc": draft["description"], "labels": draft["labels"],
                "members": draft["members"], "checklist": [], "due": draft["due"][:10] if draft["due"] else None}
    try:
        return search.search(proposal, boards_folder)
    except search.Stop as stop:
        raise Refused("the duplicate search could not run, so no preview is made: %s" % stop)
    except OSError:
        raise Refused("the duplicate search could not read the boards folder at %s, so no preview is made" % index.place(boards_folder))


def duplicate_lines(draft, result, boards_folder, in_trello):
    """(lines to show, reasons the write may not go ahead)."""
    local = next(len(board["cards"]) for board in result["boards"] if board["id"] == draft["board"])
    out = ["the local indexes in %s, %s on %s, searched with the trello-duplicate-search skill."
           % (index.place(boards_folder), search.count(result["searched"], "card"), search.count(len(result["boards"]), "board"))]
    if local < in_trello:
        out.append("WARNING: the index of this board holds %d cards and Trello holds %d. %d in Trello have NOT been searched. "
                   "Save them locally and rebuild the index for a complete search." % (local, in_trello, in_trello - local))
    elif local > in_trello:
        out.append("the index of this board holds %d cards and Trello holds %d. Some in the index are no longer on the board." % (local, in_trello))
    else:
        out.append("the index of this board holds %d cards and Trello holds %d: the counts agree." % (local, in_trello))
    out.append("Result: %s." % (search.count(len(result["candidates"]), "candidate") if result["candidates"]
                                else "NONE. No card on any board searched matches this draft on three or more signals beyond the name"))
    for c in result["candidates"]:
        out.append("  card %s, %s, on %s board: confidence %s, %d of %d points, matched on %s. Recommendation: %s."
                   % (c["entry"]["id"], c["finished"] or "open", "the SAME" if c["same_board"] else "ANOTHER", c["level"].upper(),
                      c["score"], search.TOP, ", ".join(c["matched"]), c["advice"].upper()))
    for c in result["dismissed"]:
        out.append("  looked at and not reported: card %s, matched on %s only." % (c["entry"]["id"], " and ".join(c["matched"])))
    out.append("The search's overall recommendation: %s. A person decides." % result["overall"].upper())
    reasons = []
    found = [c["entry"]["id"] for c in result["candidates"] if c["advice"] != "proceed"]
    if draft["decision"]:
        out.append("The draft records a person's decision: %s, made about %s."
                   % (draft["decision"].upper(), ", ".join("card " + item for item in draft["candidates"]) or "no card"))
    if draft["decision"] == "archive-as-duplicate":
        reasons.append("the decision recorded in the draft is archive-as-duplicate, which means this card is not to be created")
    else:
        uncovered = [item for item in found if item not in draft["candidates"]]
        if uncovered and draft["decision"]:
            reasons.append("the duplicate search found %s, which the decision recorded in the draft does not cover"
                           % ", ".join("card " + item for item in uncovered))
        elif uncovered:
            reasons.append("the duplicate search recommends %s for %s, and the draft records no person's decision about it. "
                           "Add duplicate_decision and duplicate_candidates to the draft"
                           % (result["overall"].upper(), ", ".join("card " + item for item in uncovered)))
    out.append("The indexes are a local copy: a card created in Trello since the records were saved is not in them.")
    return out, reasons


# ---------------------------------------------------------------- the preview


def now_utc():
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0, tzinfo=None)


def cited(sources, what):
    return "; ".join("%s line%s" % (s["file"], " %d" % s["first"] if s["first"] == s["last"] else "s %d-%d" % (s["first"], s["last"]))
                     for s in sources if s["what"] == what)


def cmd_preview(args, conn):
    draft = read_draft(args.draft)
    sources = check_sources(draft)
    if draft["due"] and datetime.datetime.strptime(draft["due"], "%Y-%m-%dT%H:%M:%S.%fZ") < args.now:
        raise Refused("the draft's due, %s, is before now, %s. A new card is not created already overdue"
                      % (draft["due"], args.now.strftime(TIME_FORMAT)))
    if draft["board"] not in load_allowlist(args.allowlist):
        raise Refused("board %s is not on the sandbox allowlist (%s). A card could not be created there, so no preview is "
                      "made" % (draft["board"], index.place(os.path.abspath(args.allowlist))))
    me = read_me(conn)
    board = read_board(conn, draft["board"])
    before = snapshot(conn, board["id"])
    target = read_list(conn, draft["list"], board, before["lists"])
    label_ids = resolve_labels(conn, board, draft["labels"])
    check_members(conn, board, draft["members"])
    payload, rows = build_payload(draft, label_ids)
    body = body_bytes(payload)
    digest = hashlib.sha256(body).hexdigest()
    permission, reasons = check_permission(conn, board, me)
    result = find_duplicates(draft, os.path.abspath(args.boards))
    duplicates, more = duplicate_lines(draft, result, os.path.abspath(args.boards), len(before["cards"]))
    reasons += more
    after = snapshot(conn, board["id"])
    if after["shown"] != before["shown"]:
        raise Refused("the board's lists or cards changed in Trello while the preview was being made. Preview again")
    ready = not reasons

    say("PREVIEW OF A NEW CARD. Nothing has been written to Trello.")
    say("")
    say("Board:  %s (board id %s). On the sandbox allowlist: yes." % (json.dumps(board["name"]), board["id"]))
    say("List:   %s (list id %s). Chosen by id. Trello says it belongs to board %s, the stated board: yes. Archived: no."
        % (json.dumps(target["name"]), target["id"], board["id"]))
    say("        The board's lists by position: %s."
        % ", ".join("%s%s" % (json.dumps(str(row.get("name"))), " (ARCHIVED)" if row.get("closed") else "")
                    for row in sorted(before["lists"], key=lambda row: (index.number(row.get("pos")) or 0, row["id"]))))
    say("Draft:  %s" % index.place(draft["path"]))
    say("Would be sent, by a later write and not by this preview: %s" % REQUEST)
    say("")
    say("FIELD BY FIELD, %d fields in the payload:" % len(rows))
    for key, shown, _ in rows:
        say("  %-10s %s" % (key, shown))
    say("Labels and members were each found on the board before being put in the payload: %s, %s."
        % (search.count(len(label_ids), "label"), search.count(len(draft["members"]), "member")))
    say("Not in the payload, so decided by Trello and not by this draft: the card's id, its short link and its number on")
    say("the board; who it is created by, which is the token's member; and, for \"top\" or \"bottom\", the position number.")
    say("")
    say("WHERE IN THE LIST. Position %s:" % json.dumps(draft["position"]))
    for line in placement(draft, before["cards"]):
        say("  " + line)
    say("  This is the list as it is now. A card added or moved before the write changes it.")
    say("")
    say("THE EXACT PAYLOAD. This is the request body, not a summary of it:")
    for line in pretty(payload).split("\n"):
        say("  " + line)
    say("As sent it is the same data with no spaces or line breaks and its names in alphabetical order:")
    say("  %d bytes, SHA-256 %s" % (len(body), digest))
    say("")
    say("SOURCES for the content, each checked against the file: %d citations, all true." % len(sources))
    for source in sources:
        say("  %-12s %s line%s: %s" % (source["what"], source["file"],
                                      " %d" % source["first"] if source["first"] == source["last"] else "s %d-%d" % (source["first"], source["last"]),
                                      json.dumps(source["quote"], ensure_ascii=False)))
    say("")
    say("PERMISSION CHECK, asked of Trello for this board and this token:")
    for line in permission:
        say("  " + line)
    say("")
    say("DUPLICATE SEARCH:")
    for line in duplicates:
        say("  " + line)
    say("")
    say("What Trello cannot be asked: it has no way to try a create without making one, so this preview cannot")
    say("promise the create would be accepted.")
    say("")
    say("Snapshot of the board in Trello before the preview: %d lists, %d cards, %s" % before["shown"])
    say("Snapshot of the board in Trello after the preview:  %d lists, %d cards, %s" % after["shown"])
    say("The two are the same. The board is unchanged.")
    say("Requests sent to Trello: %d. Every one was a GET, which reads and cannot change anything." % len(conn.sent))
    for method, path in conn.sent:
        say("  %s %s" % (method, path))
    say("")
    if ready:
        say("VERDICT: READY TO WRITE. Every check passed.")
        made = now_utc()
        record = {"made_at": made.strftime(TIME_FORMAT), "expires_at": (made + datetime.timedelta(minutes=LIMIT_MINUTES)).strftime(TIME_FORMAT),
                  "board": board["id"], "list": target["id"], "request": REQUEST, "payload": payload, "payload_sha256": digest,
                  "payload_bytes": len(body), "board_snapshot": after["shown"][2],
                  "duplicates": {"overall": result["overall"], "decision": draft["decision"],
                                 "candidates": [[c["entry"]["id"], c["level"], c["advice"]] for c in result["candidates"]]}}
        fingerprint = hashlib.sha256(json.dumps(record, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()
        folder = os.path.join(args.state, "card-previews")
        path = os.path.join(folder, fingerprint[:12] + ".json")
        if os.path.exists(path):
            raise Refused("a preview with this fingerprint was made a moment ago. Wait a second and preview again")
        saved = json.dumps(dict(record, fingerprint=fingerprint, state="open"), indent=2, ensure_ascii=False, sort_keys=True) + "\n"
        say("Fingerprint of this preview: %s" % fingerprint[:12])
        say("Made:    %s" % record["made_at"])
        say("Expires: %s (%d minutes after it was made)" % (record["expires_at"], LIMIT_MINUTES))
        say("The payload, its SHA-256 and this fingerprint are saved in the state folder for a later write to check.")
    else:
        path = saved = None
        say("VERDICT: NOT READY TO WRITE. %s:" % search.count(len(reasons), "reason"))
        for number, reason in enumerate(reasons, 1):
            say("  %d. %s." % (number, reason[0].upper() + reason[1:]))
        say("Nothing was saved for a later write. The payload above is what would be sent once the reasons are dealt with.")
    say("")
    say("Nothing has been written to Trello. This preview creates nothing, and has no way to.")
    files = {}
    if saved:
        files[path] = saved
    if args.payload_out:
        files[os.path.abspath(args.payload_out)] = payload_file(board, target, draft, rows, payload, body, digest, sources, ready, reasons)
        say("The payload was also written, field by field, where --payload-out said.")
    return (0 if ready else 3), files


def payload_file(board, target, draft, rows, payload, body, digest, sources, ready, reasons):
    cell = search.md
    out = ["# Payload preview: one new Trello card", "",
           "> Generated by `participant/skills/trello-create-card-preview/preview.py` from the draft",
           "> `%s`. Do not edit it by hand: change the draft and preview again." % index.place(draft["path"]),
           "> Nothing in this file has been sent to Trello.", "",
           "## Where it would go", "",
           "| | |", "|---|---|",
           "| Board | %s, board id `%s`, on the sandbox allowlist |" % (cell(board["name"]), board["id"]),
           "| List | %s, list id `%s`, on that board and not archived |" % (cell(target["name"]), target["id"]),
           "| Position in the list | `%s` |" % json.dumps(draft["position"]),
           "| Request | `%s` |" % REQUEST, "",
           "## Field by field", "",
           "| Field in the payload | Value | Source |", "|---|---|---|"]
    for key, shown, what in rows:
        out.append("| `%s` | %s | %s |" % (key, cell(shown), cell(cited(sources, what)) if what else "the draft's target"))
    out += ["", "Only these fields are sent. The card's id, short link, number, creator and, for `top` or `bottom`, its position",
            "number are decided by Trello.", "",
            "## The exact payload", "",
            "This is the request body. A later write sends this data and nothing else.", "",
            "```json", pretty(payload), "```", "",
            "As sent it is the same data with no spaces or line breaks and its names in alphabetical order:",
            "%d bytes, SHA-256 `%s`." % (len(body), digest), "",
            "## Verdict when this was generated", ""]
    out += ["READY TO WRITE."] if ready else ["NOT READY TO WRITE:", ""] + ["- %s." % cell(reason[0].upper() + reason[1:]) for reason in reasons]
    return "\n".join(out) + "\n"


def refusal(reason):
    del LINES[:]
    say("REFUSED: %s." % reason)
    say("No preview was made, no payload was shown or saved, and nothing has been written to Trello.")
    return 1, {}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Preview the creation of one Trello card from a local draft. Writes nothing to Trello.")
    parser.add_argument("--source", choices=("live", "fake"), required=True)
    parser.add_argument("--draft", required=True, help="the card draft, a Markdown file")
    parser.add_argument("--allowlist", required=True, help="the sandbox allowlist of board ids")
    parser.add_argument("--boards", required=True, help="the folder of local board indexes to search for duplicates")
    parser.add_argument("--state", required=True, help="the folder where a READY preview is saved")
    parser.add_argument("--payload-out", help="also write the payload, field by field, to this Markdown file")
    parser.add_argument("--log", help="also save the output here")
    parser.add_argument("--now", help="the time a due date is checked against, like 2026-11-20T09:00:00Z. The default is the clock")
    args = parser.parse_args(argv)
    del LINES[:]
    secrets, files = [], {}
    try:
        try:
            args.now = datetime.datetime.strptime(args.now, "%Y-%m-%dT%H:%M:%SZ") if args.now else now_utc()
        except ValueError:
            raise Refused("--now must be a time written like 2026-11-20T09:00:00Z")
        if args.source == "fake":
            import fake_trello
            conn = Connection(fake_trello.FakeTrello().get, fake_trello.TOKEN_PATH)
        else:
            conn, secrets = make_live()
        code, files = cmd_preview(args, conn)
    except Refused as refused:
        code, files = refusal(refused)
    text = "\n".join(LINES)
    if any(secret and secret in piece for secret in secrets for piece in [text] + list(files.values())):
        print("STOPPED: the key or the token was found in what would have been shown or saved, so nothing was shown or saved.")
        return 1
    for path, content in files.items():
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
    print(text)
    if secrets:
        note = "\nThe output above, and each file written, was searched for the API key and the token: neither found."
        print(note)
        text += "\n" + note
    if args.log:
        os.makedirs(os.path.dirname(os.path.abspath(args.log)), exist_ok=True)
        with open(args.log, "w", encoding="utf-8") as f:
            f.write(text + "\n")
    return code


if __name__ == "__main__":
    sys.exit(main())
