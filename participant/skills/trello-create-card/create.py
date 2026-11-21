#!/usr/bin/env python3
"""Creates one Trello card from a local draft: preview first, then a person confirms, then the local link.

    create.py preview   --source live|fake --draft DRAFT.md --link LINK.md --allowlist FILE --boards FOLDER --state FOLDER
    create.py confirm   (the same options) --fingerprint CODE --confirmed-by NAME [--result FILE.md]
    create.py verify    --source live|fake --link LINK.md
    create.py reconcile --source live|fake --link LINK.md [--result FILE.md]

The draft is the one the trello-create-card-preview skill reads, and this
workflow builds its payload with that skill's own functions, build_payload
and body_bytes, so that a preview here and a preview there cannot mean
different things.

preview    reads Trello and writes nothing to it. It has no way to send a
           write. It shows the board, the list, every field, the exact
           payload, the token's scope and expiry, the permission check, the
           duplicate checks and a snapshot of the board before and after. If
           every check passes it is READY, and it saves the preview and shows
           its fingerprint. If not, it shows why and saves nothing, so there
           is nothing to confirm. It refuses if the draft is already linked to
           a Trello card.

confirm    creates the card of one preview, named by its fingerprint, and only
           if all of this holds at that moment: a fingerprint and the
           confirming person's name are given; the saved preview is unaltered,
           unused and at most 15 minutes old; the draft is byte for byte the one
           previewed; the payload worked out again from the draft and from
           Trello as it is now has the same SHA-256; the board is on the
           sandbox allowlist; the permission and duplicate checks still pass;
           and the draft has no link file.

           Then, in this order: it writes the link file saying a create is
           being sent, with the ids of the cards on the board at that moment;
           sends the create once; writes the ids that came back into the link
           file; reads the card back from Trello by its id; compares it with
           the payload field for field; and writes the comparison and the
           result record.

verify     reads the linked card from Trello by its id and compares it again
           with the payload that was sent. It writes nothing to Trello.

reconcile  is for when a create was sent and its result was never recorded.
           It reads the board's cards and looks for one that was not there
           before the create was sent and that holds what the payload sent.
           Exactly one: it is linked, read back and compared. None: it says
           so and creates nothing. More than one: nothing is linked. It writes
           nothing to Trello.

Trello has no way to refuse a second create of the same card. The protection
is this workflow's own: the link file, written before the create is sent.

A create is sent once and never retried.

For a live run the key and the token come from the environment variables
TRELLO_API_KEY and TRELLO_API_TOKEN. Neither is stored, and everything that
would be shown or saved is searched for them first. No other card's name or
text is printed.

Exit codes: 0 done; 1 refused, nothing written to Trello; 2 a create was sent
and a person needs to look; 3 a preview that is not ready, or a verify that
found the card changed.
"""
import argparse
import datetime
import hashlib
import importlib.util
import json
import os
import secrets
import sys
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "participant", "skills", "trello-create-card-preview"))
import preview as pv  # noqa: E402
from preview import Refused, index, search  # noqa: E402

LINK_FORMAT = "trello-linked-card/1"
SENT = "create sent, result not recorded"
CREATED = "created"
LIMIT_MINUTES = 15
TIME_FORMAT = pv.TIME_FORMAT
API = "https://api.trello.com/1"
LINK_NAMES = ("format", "state", "draft", "draft_sha256", "preview_fingerprint", "payload_sha256", "board_id", "list_id", "card_id",
              "short_link", "confirmed_by", "confirmed_at", "created_at", "trello_created_at", "compared_at", "comparison")
BEFORE_HEADING = "## Cards on the board before the create was sent"
PAYLOAD_HEADING = "## The payload that was sent"
CARD_FIELDS = "name,desc,due,idList,idBoard,idLabels,idMembers,closed,pos"

LINES = []


class NeedsLooking(Exception):
    """A create was sent. The message says what is and is not known."""


class NothingMade(Refused):
    """A create was sent, Trello refused it, and the board shows that no card was made."""


def say(text=""):
    LINES.append(text)


def now_utc():
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0, tzinfo=None)


# ---------------------------------------------------------------- the connection


class Connection(pv.Connection):
    """Every request goes through here and is written down. Without `post` there is no way to write."""

    def __init__(self, get, post, token_path):
        super().__init__(get, token_path)
        self._post = post

    def wrote(self):
        return any(method == "POST" for method, _ in self.sent)

    def get(self, path, params=None):
        try:
            return super().get(path, params)
        except Refused as refusal:
            if self.wrote():
                raise NeedsLooking("after the create was sent, a read failed: %s" % refusal)
            raise

    def create(self, body):
        """Send one create. `body` is the exact bytes of the request."""
        if self._post is None:
            raise Refused("this command has no way to write")
        if self.wrote():
            raise Refused("a create has already been sent in this run, and a create is sent once")
        self.sent.append(("POST", "/cards"))
        try:
            status, _, answer = self._post("/cards", None, body)
        except (OSError, TimeoutError) as err:
            raise NeedsLooking("the create was sent and no answer came back (%s). It is NOT KNOWN whether Trello created "
                               "the card. It was not sent again" % type(getattr(err, "reason", err)).__name__)
        return status, answer


def make_live(may_write):
    key, token = os.environ.get("TRELLO_API_KEY", ""), os.environ.get("TRELLO_API_TOKEN", "")
    for name, value in (("TRELLO_API_KEY", key), ("TRELLO_API_TOKEN", token)):
        if not value:
            raise Refused("the environment variable %s is not set" % name)

    def send(method, path, params, body):
        url = API + path + ("?" + urllib.parse.urlencode(params) if params else "")
        request = urllib.request.Request(url, data=body, method=method)
        request.add_header("Authorization", 'OAuth oauth_consumer_key="%s", oauth_token="%s"' % (key, token))
        request.add_header("Accept", "application/json")
        if body is not None:
            request.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                status, raw = response.status, response.read()
        except urllib.error.HTTPError as err:
            status, raw = err.code, err.read(300)
        try:
            parsed = json.loads(raw.decode("utf-8"))
        except ValueError:
            parsed = {"message": raw.decode("utf-8", "replace")[:300]}
        return status, {}, parsed

    def get(path, params=None):
        return send("GET", path, params, None)

    def post(path, params, body):
        if path != "/cards" or params or not isinstance(body, bytes):
            raise Refused("the only write this workflow sends is the creation of one card")
        return send("POST", path, None, body)

    return Connection(get, post if may_write else None, "/tokens/%s" % token), [key, token]


# ---------------------------------------------------------------- the link file


def sha_of(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def json_block(text, heading):
    return json.loads(text.split("\n%s\n" % heading, 1)[1].split("```json\n", 1)[1].split("\n```", 1)[0])


def read_link(path):
    """The link file as (its fields, the payload it holds, the card ids recorded before the create), or three Nones."""
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except FileNotFoundError:
        return None, None, None
    except (OSError, UnicodeDecodeError):
        raise Refused("the link file could not be read")
    front = index.front_matter(text)
    if front is None or front.get("format") != LINK_FORMAT or front.get("state") not in (SENT, CREATED):
        raise Refused("the file at the link path is not a link this workflow wrote, so it is left alone")
    try:
        payload = json_block(text, PAYLOAD_HEADING)
        before = json_block(text, BEFORE_HEADING) if "\n%s\n" % BEFORE_HEADING in text else None
    except (IndexError, ValueError):
        raise Refused("the link file's payload could not be read")
    return front, payload, before


def write_link(path, front, draft, payload, before=None, rows=None, extras=None, note=None):
    cell = search.md
    out = ["---"] + ["%s: %s" % (name, json.dumps(front.get(name), ensure_ascii=False, sort_keys=True)) for name in LINK_NAMES] + ["---", ""]
    out += ["# %s" % cell(draft["name"]), "",
            "> This file is written by `participant/skills/trello-create-card/create.py`. It is the local record of one",
            "> Trello card. The card is identified by its card id, `card_id` above. A name, a list and a position can change.", ""]
    if front["state"] == SENT:
        out += ["**A create was sent to Trello and its result has not been recorded.** The card may or may not exist.",
                "Do not create it again. Run the `reconcile` command, which looks on the board for a card that was not",
                "there before and holds what was sent.", ""]
    else:
        out += ["Linked to Trello card **%s** (short link %s), created in list %s on board %s."
                % (front["card_id"], front["short_link"], front["list_id"], front["board_id"]), ""]
    out += ["## Description", "", draft["description"] or "(none)", "",
            "## Sources", ""]
    out += ['- %s: %s line%s: "%s"' % (s["what"], s["file"], " %d" % s["first"] if s["first"] == s["last"] else "s %d-%d" % (s["first"], s["last"]), s["quote"])
            for s in draft["sources"]] or ["none"]
    if front["state"] == SENT:
        out += ["", BEFORE_HEADING, "",
                "The ids of all %d cards on board %s, archived ones included, read just before the create was sent. A card"
                % (len(before), front["board_id"]),
                "on the board that is not in this list was made afterwards.", "",
                "```json", json.dumps(sorted(before)), "```"]
    out += ["", "## Read-back and compare", ""]
    if rows is None:
        out += [note or "The card has not been read back yet."]
    else:
        out += ["The card was read back from Trello by its card id at %s and compared with the payload that was sent." % front["compared_at"],
                "Result: **%s**" % front["comparison"], "",
                "| Field | Sent | Read back from Trello | Verdict |", "|---|---|---|---|"]
        out += ["| `%s` | %s | %s | %s |" % (field, cell(sent), cell(back), verdict) for field, sent, back, verdict in rows]
        out += ["", "What Trello set that the payload did not send:", ""]
        out += ["- %s: %s" % (name, cell(value)) for name, value in extras]
    out += ["", PAYLOAD_HEADING, "",
            "%d bytes as sent, SHA-256 `%s`." % (len(pv.body_bytes(payload)), front["payload_sha256"]), "",
            "```json", pv.pretty(payload), "```"]
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path + ".tmp", "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    os.replace(path + ".tmp", path)


def refuse_if_linked(link_path, draft_path):
    front, _, _ = read_link(link_path)
    if front is None:
        return
    if front.get("draft") != os.path.relpath(draft_path, os.path.dirname(os.path.abspath(link_path))):
        raise Refused("the link file belongs to another draft, %s. Give this draft a link file of its own" % json.dumps(front.get("draft")))
    if front["state"] == CREATED:
        raise Refused("this draft has already been created in Trello as card %s, recorded in the link file. It is not "
                      "created twice. Use the verify command to compare it with Trello" % front.get("card_id"))
    raise Refused("a create for this draft was sent and its result was never recorded. The card may exist in Trello. "
                  "Run the reconcile command before anything else. Nothing is created")


# ---------------------------------------------------------------- reading Trello


def board_cards(conn, board_id):
    cards = pv.rows_of(conn, "/boards/%s/cards" % board_id, {"filter": "all", "fields": CARD_FIELDS, "limit": pv.CARD_LIMIT}, "the board's cards")
    if len(cards) >= pv.CARD_LIMIT:
        raise Refused("the board has more cards than this workflow reads")
    return cards


def read_card(conn, card_id):
    status, body = conn.get("/cards/%s" % card_id, {"fields": "all"})
    if status == 404:
        return None
    if status != 200 or not isinstance(body, dict) or body.get("id") != card_id:
        raise NeedsLooking("the card %s could not be read back from Trello (status %d)" % (card_id, status))
    return body


def instant(value):
    try:
        return datetime.datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%fZ")
    except (TypeError, ValueError):
        return None


def made_at(card_id):
    """When Trello made a card. The first eight characters of a Trello id are its creation time, in seconds."""
    try:
        return datetime.datetime.utcfromtimestamp(int(card_id[:8], 16)).strftime(TIME_FORMAT)
    except (ValueError, OverflowError, OSError):
        return "not readable from the id"


def ids_of(value):
    if isinstance(value, str):
        return sorted(item for item in value.split(",") if item)
    return sorted(str(item) for item in value) if isinstance(value, list) else None


def holds(card, payload):
    """Whether a card holds what the payload sent. The position is left out: it is a place, and places change."""
    return (card.get("idList") == payload["idList"] and card.get("name") == payload["name"]
            and (card.get("desc") or "") == payload.get("desc", "")
            and instant(card.get("due")) == instant(payload.get("due"))
            and ids_of(card.get("idLabels")) == ids_of(payload.get("idLabels", ""))
            and ids_of(card.get("idMembers")) == ids_of(payload.get("idMembers", "")))


# ---------------------------------------------------------------- compare


def brief(value):
    if value is None or value == "" or value == []:
        return "(none)"
    if isinstance(value, str) and len(value) > 70:
        return "%d characters, starting %s" % (len(value), json.dumps(value[:40], ensure_ascii=False))
    return json.dumps(value, ensure_ascii=False)


def compare(payload, card, board_id, others):
    """Each field the payload sent, against the card read back. Returns (rows, all the same, what Trello set).

    `others` are the board's cards, used to say where the card sits in its list.
    """
    rows, good = [], True

    def row(field, sent, back, same, extra=""):
        nonlocal good
        good = good and same
        rows.append((field, sent, back, ("the same" if same else "**DIFFERENT**") + extra))
    row("idList", payload["idList"], str(card.get("idList")), card.get("idList") == payload["idList"])
    here = sorted((c for c in others if c.get("idList") == card.get("idList") and c.get("closed") is False
                   and index.number(c.get("pos")) is not None), key=lambda c: (c["pos"], c["id"]))
    place = [c["id"] for c in here].index(card["id"]) + 1 if card["id"] in [c["id"] for c in here] else None
    where = "position number %s, number %s of %d open cards in the list" % (card.get("pos"), place, len(here))
    wanted = payload["pos"]
    if wanted == "bottom":
        same = place is not None and place == len(here)
    elif wanted == "top":
        same = place == 1
    else:
        same = card.get("pos") == wanted
    row("pos", json.dumps(wanted), where, same, ": it is last in the list" if same and wanted == "bottom" else ": it is first in the list" if same and wanted == "top" else "")
    row("name", brief(payload["name"]), brief(card.get("name")), card.get("name") == payload["name"])
    if "desc" in payload:
        row("desc", brief(payload["desc"]), brief(card.get("desc")), card.get("desc") == payload["desc"], ", character for character" if card.get("desc") == payload["desc"] else "")
    if "due" in payload:
        row("due", payload["due"], str(card.get("due")), instant(card.get("due")) is not None and instant(card.get("due")) == instant(payload["due"]))
    for field in ("idLabels", "idMembers"):
        if field in payload:
            row(field, ", ".join(ids_of(payload[field])), ", ".join(ids_of(card.get(field)) or []) or "(none)", ids_of(card.get(field)) == ids_of(payload[field]))
    row("idBoard", "not sent: it follows from the list", str(card.get("idBoard")), card.get("idBoard") == board_id, " as the board that was previewed" if card.get("idBoard") == board_id else "")
    unsent = [field for field in ("desc", "due", "idLabels", "idMembers") if field not in payload and card.get(field) not in (None, "", [])]
    for field in unsent:
        row(field, "not sent", brief(card.get(field)), False)
    extras = [("card id", card["id"]), ("short link", str(card.get("shortLink"))), ("number on the board", str(card.get("idShort"))),
              ("position number", str(card.get("pos"))), ("archived", "yes" if card.get("closed") else "no"),
              ("due marked complete", "yes" if card.get("dueComplete") else "no"),
              ("created, read from the card id", made_at(card["id"])), ("last activity", str(card.get("dateLastActivity")))]
    return rows, good, extras


# ---------------------------------------------------------------- working the change out


def gather(conn, args):
    """Everything a preview and a confirmation both need, worked out the same way from the draft and from Trello now."""
    draft = pv.read_draft(args.draft)
    pv.check_sources(draft)
    if draft["due"] and instant(draft["due"]) < args.now:
        raise Refused("the draft's due, %s, is before now, %s. A new card is not created already overdue"
                      % (draft["due"], args.now.strftime(TIME_FORMAT)))
    if draft["board"] not in pv.load_allowlist(args.allowlist):
        raise Refused("board %s is not on the sandbox allowlist (%s). This workflow writes only to boards listed there"
                      % (draft["board"], index.place(os.path.abspath(args.allowlist))))
    me = pv.read_me(conn)
    board = pv.read_board(conn, draft["board"])
    before = pv.snapshot(conn, board["id"])
    target = pv.read_list(conn, draft["list"], board, before["lists"])
    label_ids = pv.resolve_labels(conn, board, draft["labels"])
    pv.check_members(conn, board, draft["members"])
    payload, rows = pv.build_payload(draft, label_ids)
    body = pv.body_bytes(payload)
    permission, reasons = pv.check_permission(conn, board, me)
    cards = board_cards(conn, board["id"])
    same_name = sorted(card["id"] for card in cards if card.get("closed") is False
                       and " ".join(str(card.get("name")).split()).lower() == " ".join(draft["name"].split()).lower())
    result = pv.find_duplicates(draft, os.path.abspath(args.boards))
    duplicates, more = pv.duplicate_lines(draft, result, os.path.abspath(args.boards), len(cards))
    reasons += more
    uncovered = [card_id for card_id in same_name if card_id not in draft["candidates"]]
    if uncovered:
        reasons.append("Trello holds %s on this board with exactly this name (%s), and the draft records no person's decision "
                       "about %s" % (search.count(len(uncovered), "open card"), ", ".join("card " + c for c in uncovered),
                                     "it" if len(uncovered) == 1 else "them"))
    after = pv.snapshot(conn, board["id"])
    if after["shown"] != before["shown"]:
        raise Refused("the board's lists or cards changed in Trello while it was being read. Preview again")
    return {"draft": draft, "board": board, "target": target, "label_ids": label_ids, "payload": payload, "rows": rows, "body": body,
            "digest": hashlib.sha256(body).hexdigest(), "permission": permission, "reasons": reasons, "cards": cards,
            "same_name": same_name, "duplicates": duplicates, "before": before, "after": after}


def head(found):
    board, target = found["board"], found["target"]
    say("Board:  %s (board id %s). On the sandbox allowlist: yes." % (json.dumps(board["name"]), board["id"]))
    say("List:   %s (list id %s). Chosen by id. Trello says it belongs to board %s, the stated board: yes. Archived: no."
        % (json.dumps(target["name"]), target["id"], board["id"]))
    say("Draft:  %s" % index.place(found["draft"]["path"]))


def requests_line(conn):
    kinds = [method for method, _ in conn.sent]
    say("Requests sent to Trello: %d. %s" % (len(kinds), "Every one was a GET, which reads and cannot change anything."
                                             if set(kinds) == {"GET"} else "%d GET and %d POST. The POST is the one create."
                                             % (kinds.count("GET"), kinds.count("POST"))))
    for method, path in conn.sent:
        say("  %s %s" % (method, path))


def fingerprint_of(record):
    core = {name: record[name] for name in ("made_at", "nonce", "board", "list", "payload", "payload_sha256", "draft_sha256", "link")}
    return hashlib.sha256(json.dumps(core, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()


def save_json(path, data):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path + ".tmp", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, sort_keys=True)
        f.write("\n")
    os.replace(path + ".tmp", path)


# ---------------------------------------------------------------- preview


def cmd_preview(args, conn):
    refuse_if_linked(args.link, os.path.abspath(args.draft))
    found = gather(conn, args)
    draft, payload, board = found["draft"], found["payload"], found["board"]
    ready = not found["reasons"]

    say("PREVIEW OF CREATING ONE CARD. Nothing has been written to Trello.")
    say("")
    head(found)
    say("Link file: %s (not there yet: this draft has not been created)" % index.place(os.path.abspath(args.link)))
    say("The change: one new card would be created, with one request: POST %s/cards" % API)
    say("")
    say("FIELD BY FIELD, %d fields in the payload:" % len(found["rows"]))
    for key, shown, _ in found["rows"]:
        say("  %-10s %s" % (key, shown))
    say("Labels and members were each found on the board before being put in the payload: %s, %s."
        % (search.count(len(found["label_ids"]), "label"), search.count(len(draft["members"]), "member")))
    say("Not in the payload, so decided by Trello and not by this draft: the card's id, its short link and its number on")
    say("the board; who it is created by, which is the token's member; and, for \"top\" or \"bottom\", the position number.")
    say("")
    say("WHERE IN THE LIST. Position %s:" % json.dumps(draft["position"]))
    for line in pv.placement(draft, found["before"]["cards"]):
        say("  " + line)
    say("")
    say("THE EXACT PAYLOAD. This is the request body, not a summary of it:")
    for line in pv.pretty(payload).split("\n"):
        say("  " + line)
    say("As sent it is the same data with no spaces or line breaks and its names in alphabetical order:")
    say("  %d bytes, SHA-256 %s" % (len(found["body"]), found["digest"]))
    say("")
    say("THE TOKEN AND THE PERMISSION CHECK, asked of Trello for this board and this token:")
    for line in found["permission"]:
        say("  " + line)
    say("")
    say("DUPLICATE CHECKS:")
    say("  1. This draft's own link file: there is none, so this workflow has not created it before.")
    say("  2. Asked of Trello, open cards on this board with exactly this name: %d%s."
        % (len(found["same_name"]), " (%s)" % ", ".join("card " + c for c in found["same_name"]) if found["same_name"] else ""))
    say("  3. " + found["duplicates"][0])
    for line in found["duplicates"][1:]:
        say("     " + line)
    say("Where Trello cannot check: it has no way to refuse a second create of the same card, and no way to try a")
    say("  create without making one. The link file is this workflow's own protection against creating twice.")
    say("")
    say("Snapshot of the board in Trello before the preview: %d lists, %d cards, %s" % found["before"]["shown"])
    say("Snapshot of the board in Trello after the preview:  %d lists, %d cards, %s" % found["after"]["shown"])
    say("The two are the same. The board is unchanged.")
    requests_line(conn)
    say("")
    if not ready:
        say("VERDICT: NOT READY TO WRITE. %s:" % search.count(len(found["reasons"]), "reason"))
        for number, reason in enumerate(found["reasons"], 1):
            say("  %d. %s." % (number, reason[0].upper() + reason[1:]))
        say("No preview was saved and there is no fingerprint, so there is nothing to confirm.")
        say("")
        say("Nothing has been written to Trello.")
        return 3
    made = now_utc()
    record = {"made_at": made.strftime(TIME_FORMAT), "expires_at": (made + datetime.timedelta(minutes=LIMIT_MINUTES)).strftime(TIME_FORMAT),
              "nonce": secrets.token_hex(8), "board": board["id"], "list": found["target"]["id"], "payload": payload,
              "payload_sha256": found["digest"], "draft_sha256": sha_of(draft["path"]), "link": os.path.abspath(args.link), "state": "open"}
    record["fingerprint"] = fingerprint_of(record)
    code = record["fingerprint"][:12]
    save_json(os.path.join(args.state, "create-card-previews", code + ".json"), record)
    say("VERDICT: READY TO WRITE. Every check passed.")
    say("Fingerprint of this preview: %s" % code)
    say("Made:    %s" % record["made_at"])
    say("Expires: %s (%d minutes after it was made)" % (record["expires_at"], LIMIT_MINUTES))
    say("")
    say("Nothing has been written to Trello. To create this card, a person who has read this preview confirms it")
    say("by its fingerprint.")
    return 0


# ---------------------------------------------------------------- confirm


def read_preview_record(state, code):
    path = os.path.join(state, "create-card-previews", code + ".json")
    try:
        with open(path, encoding="utf-8") as f:
            record = json.load(f)
        made = datetime.datetime.strptime(record["made_at"], TIME_FORMAT)
        genuine = fingerprint_of(record)
        status = record["state"]
    except FileNotFoundError:
        raise Refused("there is no preview with the fingerprint %s. Make a preview, read it, and confirm that one" % code)
    except (ValueError, KeyError, TypeError):
        raise Refused("the saved preview %s cannot be read, so it cannot be confirmed" % code)
    if genuine != record.get("fingerprint") or genuine[:12] != code:
        raise Refused("the saved preview %s has been altered since it was made, so it cannot be confirmed" % code)
    return path, record, made, status


def cmd_confirm(args, conn):
    code = (args.fingerprint or "").strip().lower()
    if not code:
        raise Refused("no confirmation was given. A confirmation names the fingerprint of the preview it approves, and "
                      "there is no way to create without one")
    if len(code) != 12 or any(ch not in "0123456789abcdef" for ch in code):
        raise Refused("a fingerprint is 12 characters, each 0 to 9 or a to f")
    name = (args.confirmed_by or "").strip()
    if not name:
        raise Refused("no confirmation was given. A confirmation gives the name of the person confirming")
    if len(name) > 60 or "@" in name or any(ord(ch) < 32 or ord(ch) == 127 for ch in name):
        raise Refused("the confirming person's name must be short plain text, and not an email address")

    record_path, record, made, status = read_preview_record(args.state, code)
    if status == "written":
        raise Refused("the preview %s has already been confirmed and its card created. A fingerprint is used once" % code)
    if status != "open":
        raise Refused("the preview %s was confirmed before and a create was sent (recorded as '%s'). It cannot be used "
                      "again" % (code, status))
    refuse_if_linked(args.link, os.path.abspath(args.draft))
    if os.path.abspath(args.link) != record["link"]:
        raise Refused("the link file named is not the one the preview was made for")

    confirmed = now_utc()
    now = confirmed
    if args.pretend_minutes_later:
        say("TEST CLOCK: pretending it is %d minutes later than it is." % args.pretend_minutes_later)
        now += datetime.timedelta(minutes=args.pretend_minutes_later)
    age = now - made
    if age < datetime.timedelta(0):
        raise Refused("the preview %s is dated later than the clock says it is now" % code)
    if age > datetime.timedelta(minutes=LIMIT_MINUTES):
        raise Refused("this preview is too old. It was made %d minutes ago and the limit is %d. Make a new preview and "
                      "read it" % (age.total_seconds() // 60, LIMIT_MINUTES))

    found = gather(conn, args)
    board = found["board"]
    if board["id"] != record["board"] or found["target"]["id"] != record["list"]:
        raise Refused("the change is not the one that was previewed: it is for another board or list. Make a new preview "
                      "and read it")
    if found["digest"] != record["payload_sha256"] or sha_of(found["draft"]["path"]) != record["draft_sha256"]:
        fields = sorted(key for key in set(record["payload"]) | set(found["payload"]) if record["payload"].get(key) != found["payload"].get(key))
        raise Refused("the change is not the one that was previewed: %s. Make a new preview and read it"
                      % ("the payload now differs in %s" % ", ".join(fields) if fields else
                         "the draft file has been edited since the preview, though the payload comes out the same"))
    if found["reasons"]:
        raise Refused("a check that passed at the preview does not pass now: %s. Make a new preview and read it"
                      % "; ".join(found["reasons"]))

    minutes = age.total_seconds() // 60
    say("CONFIRMATION for preview %s, given by: %s (the name given with the confirmation)." % (code, name))
    say("")
    head(found)
    say("")
    say("Checked in this run, before writing:")
    say("  the preview is %d minute%s old, and the limit is %d: ok" % (minutes, "" if minutes == 1 else "s", LIMIT_MINUTES))
    say("  the saved preview is unaltered and has not been used: ok")
    say("  the draft file is byte for byte the one that was previewed: ok")
    say("  the payload worked out again now has the SHA-256 of the previewed one, %s: ok" % found["digest"])
    say("  the board is on the sandbox allowlist, and the list is on that board and not archived: ok")
    say("  Trello says the token may write and its member may add cards to this board: ok")
    say("  the duplicate checks still pass: ok")
    say("  this draft has no link file: ok")
    say("")

    front = {"format": LINK_FORMAT, "state": SENT, "draft": os.path.relpath(found["draft"]["path"], os.path.dirname(os.path.abspath(args.link))),
             "draft_sha256": record["draft_sha256"], "preview_fingerprint": record["fingerprint"], "payload_sha256": found["digest"],
             "board_id": board["id"], "list_id": found["target"]["id"], "card_id": None, "short_link": None, "confirmed_by": name,
             "confirmed_at": confirmed.strftime(TIME_FORMAT), "created_at": None, "trello_created_at": None, "compared_at": None,
             "comparison": None}
    before = sorted(card["id"] for card in found["cards"])
    write_link(args.link, front, found["draft"], found["payload"], before)
    record["state"] = "sending"
    save_json(record_path, record)
    say("Written to the link file before sending: a create is being sent, result not yet recorded, and the ids of the")
    say("%d cards on the board now." % len(before))
    try:
        status, body = conn.create(found["body"])
    except NeedsLooking:
        record["state"] = "sent, answer not received"
        save_json(record_path, record)
        raise
    if status != 200 or not isinstance(body, dict) or not isinstance(body.get("id"), str) or not pv.TRELLO_ID.fullmatch(body["id"]):
        record["state"] = "sent, Trello answered %d" % status
        save_json(record_path, record)
        said = str(body.get("message", ""))[:120] if isinstance(body, dict) else ""
        new = [card for card in board_cards(conn, board["id"]) if card["id"] not in before] if status in (400, 401, 403, 404, 422) else None
        if new == []:
            os.remove(args.link)
            raise NothingMade("Trello answered %d to the create and made no card%s. The board holds no card that was not there "
                          "before. The link file has been removed, and this preview cannot be used again"
                          % (status, ". Trello said: %s" % json.dumps(said) if said else ""))
        raise NeedsLooking("Trello answered %d to the create, and it is not certain that no card was made. The link file "
                           "says a create was sent. Run the reconcile command" % status)
    say("CREATED in Trello: one card. Trello answered 200 with the card id %s." % body["id"])
    say("The confirmation and the write happened in this one run of the command.")
    front.update(state=CREATED, card_id=body["id"], short_link=body.get("shortLink") if isinstance(body.get("shortLink"), str) else None,
                 created_at=now_utc().strftime(TIME_FORMAT), trello_created_at=made_at(body["id"]))
    try:
        write_link(args.link, front, found["draft"], found["payload"], note="Created. The read-back had not been done when this was written.")
    except OSError:
        raise NeedsLooking("the card was created with the card id %s and the link file COULD NOT BE WRITTEN. Write that id "
                           "down now. Do not create it again" % body["id"])
    say("Written to the link file: the card id %s, the list id %s and the board id %s." % (body["id"], front["list_id"], front["board_id"]))
    record["state"] = "written"
    save_json(record_path, record)
    return finish(args, conn, front, found["draft"], found["payload"], "confirm")


def finish(args, conn, front, draft, payload, mode):
    """Read the created card back by its id, compare it with the payload, and record both."""
    card = read_card(conn, front["card_id"])
    if card is None:
        raise NeedsLooking("the card %s was created and cannot be read back: Trello answered 404" % front["card_id"])
    others = board_cards(conn, card.get("idBoard") if isinstance(card.get("idBoard"), str) and pv.TRELLO_ID.fullmatch(card["idBoard"]) else front["board_id"])
    rows, good, extras = compare(payload, card, front["board_id"], others)
    front.update(compared_at=now_utc().strftime(TIME_FORMAT),
                 comparison="every field the payload sent reads back the same" if good else
                 "NOT ALL THE SAME: " + ", ".join(field for field, _, _, verdict in rows if "DIFFERENT" in verdict))
    write_link(args.link, front, draft, payload, rows=rows, extras=extras)
    say("")
    say("READ BACK from Trello by card id %s, and compared with the payload field for field:" % front["card_id"])
    for field, sent, back, verdict in rows:
        say("  %-10s sent %s" % (field, sent))
        say("  %-10s read %s: %s" % ("", back, verdict.replace("**", "")))
    say("Result: %s." % front["comparison"])
    say("What Trello set that the payload did not send:")
    for name, value in extras:
        say("  %-32s %s" % (name + ":", value))
    say("")
    say("The link file %s now holds the board, list and card ids and this comparison." % index.place(os.path.abspath(args.link)))
    result = ["Board id: %s, on the sandbox allowlist" % front["board_id"],
              "List id: %s" % front["list_id"],
              "Card id: %s" % front["card_id"],
              "Identifier of what was created: the card, Trello card id %s (short link %s)" % (front["card_id"], front["short_link"]),
              "Created at: %s by this workflow's clock; %s by Trello's, read from the card id" % (front["created_at"], front["trello_created_at"]),
              "Confirmed by: %s, at %s" % (front["confirmed_by"], front["confirmed_at"]),
              "Preview: fingerprint %s" % front["preview_fingerprint"][:12],
              "Payload: SHA-256 %s" % front["payload_sha256"],
              "Read back and compared at %s: %s" % (front["compared_at"], front["comparison"]),
              "Local link: %s" % index.place(os.path.abspath(args.link))]
    say("")
    say("RESULT RECORD")
    for line in result:
        say("  " + line)
    files = {}
    if getattr(args, "result", None):
        files[os.path.abspath(args.result)] = "\n".join(["# Result record: one Trello card created", ""] + ["- " + line for line in result]) + "\n"
        say("")
        say("The result record was also saved as Markdown where --result said.")
    say("")
    requests_line(conn)
    args.files = files
    if not good and mode == "verify":
        say("")
        say("THE CARD NO LONGER READS AS IT WAS SENT. It is the same card, by its id. Someone may have moved or edited it.")
        return 3
    if not good:
        raise NeedsLooking("the card exists as %s and does not read back as it was sent. A person needs to look at it" % front["card_id"])
    return 0


# ---------------------------------------------------------------- verify and reconcile


def linked_draft(link_path, front):
    path = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(link_path)), str(front.get("draft"))))
    try:
        return pv.read_draft(path)
    except Refused:
        raise Refused("the draft the link file names, %s, could not be read" % json.dumps(front.get("draft")))


def cmd_verify(args, conn):
    front, payload, _ = read_link(args.link)
    if front is None:
        raise Refused("there is no link file at the path given, so there is nothing to verify")
    if front["state"] != CREATED or not isinstance(front.get("card_id"), str) or not pv.TRELLO_ID.fullmatch(front["card_id"]):
        raise Refused("the link file says a create was sent and its result was never recorded. Run the reconcile command")
    card = read_card(conn, front["card_id"])
    if card is None:
        raise Refused("Trello answered 404 for card %s. The card has been deleted, or this token may not see it. The link "
                      "file is left as it is" % front["card_id"])
    say("VERIFY. Reads Trello and writes nothing to it.")
    say("Link file: %s" % index.place(os.path.abspath(args.link)))
    say("Matched to Trello by card id %s: found. The card is identified by its id, not by its name or its place." % front["card_id"])
    args.result = None
    return finish(args, conn, front, linked_draft(args.link, front), payload, "verify")


def cmd_reconcile(args, conn):
    front, payload, before = read_link(args.link)
    if front is None:
        raise Refused("there is no link file at the path given, so there is nothing to reconcile")
    if front["state"] != SENT:
        raise Refused("the link file already records the card %s. There is nothing to reconcile" % front.get("card_id"))
    if not isinstance(before, list):
        raise Refused("the link file does not hold the ids of the cards that were on the board before the create was sent")
    cards = board_cards(conn, front["board_id"])
    new = [card for card in cards if card["id"] not in before]
    matching = [card for card in new if holds(card, payload)]
    say("RECONCILE. Reads Trello and writes nothing to it.")
    say("The link file says a create was sent and its result was never recorded.")
    say("Asked of Trello: the cards on board %s. It holds %d now. %d were not there before the create was sent."
        % (front["board_id"], len(cards), len(new)))
    say("Of those, cards that hold what the payload sent (list, name, description, due, labels, members): %d." % len(matching))
    if not matching:
        say("")
        say("NOT FOUND. No card on the board is both new and the card that was sent, so as far as Trello's list of the")
        say("board's cards shows, the card was not created. Nothing has been created or changed, and the link file is left")
        say("as it is. A person decides: look at the board, and if the card is not there, delete the link file by hand")
        say("and make a new preview.")
        return 1
    if len(matching) > 1:
        raise Refused("%d new cards hold what was sent (%s). That should not be possible from one create, so nothing is "
                      "linked. A person needs to look" % (len(matching), ", ".join(card["id"] for card in matching)))
    card = matching[0]
    say("FOUND exactly one: card %s, made by Trello at %s. It is linked now." % (card["id"], made_at(card["id"])))
    front.update(state=CREATED, card_id=card["id"], short_link=None, trello_created_at=made_at(card["id"]),
                 created_at="not recorded: the create's answer was lost. Linked by reconcile at %s" % now_utc().strftime(TIME_FORMAT))
    full = read_card(conn, card["id"])
    if full is not None and isinstance(full.get("shortLink"), str):
        front["short_link"] = full["shortLink"]
    draft = linked_draft(args.link, front)
    write_link(args.link, front, draft, payload, note="Linked by reconcile. The read-back had not been done when this was written.")
    return finish(args, conn, front, draft, payload, "reconcile")


# ---------------------------------------------------------------- running


def minutes_forward(text):
    if not text.isascii() or not text.isdigit() or len(text) > 6:
        raise argparse.ArgumentTypeError("must be a whole number of minutes, 0 or more")
    return int(text)


COMMANDS = {"preview": cmd_preview, "confirm": cmd_confirm, "verify": cmd_verify, "reconcile": cmd_reconcile}


def run(args, conn):
    """One command, start to finish. Returns the exit code; what it said is in LINES."""
    try:
        return COMMANDS[args.command](args, conn)
    except Refused as refusal:
        if conn.wrote() and not isinstance(refusal, NothingMade):
            say("")
            say("A PERSON NEEDS TO LOOK: after the create was sent, %s." % refusal)
            say("Do not create this card again. The link file records where things stand.")
            say("")
            requests_line(conn)
            return 2
        say("")
        say("REFUSED: %s." % refusal)
        say("Nothing has been written to Trello." if not conn.wrote() else "No card was created.")
        if conn.wrote():
            say("")
            requests_line(conn)
        return 1
    except NeedsLooking as problem:
        say("")
        say("A PERSON NEEDS TO LOOK: %s." % problem)
        say("Do not create this card again. The link file records where things stand.")
        say("")
        requests_line(conn)
        return 2


def load_fake():
    """This skill's fake Trello, loaded from its file so that it cannot be mistaken for another skill's."""
    spec = importlib.util.spec_from_file_location("create_card_fake_trello", os.path.join(HERE, "fake_trello_write.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main(argv=None):
    parser = argparse.ArgumentParser(description="Preview, confirm, verify and reconcile the creation of one Trello card.")
    commands = parser.add_subparsers(dest="command", required=True)
    for command in COMMANDS:
        sub = commands.add_parser(command)
        sub.add_argument("--source", choices=("live", "fake"), required=True)
        sub.add_argument("--link", required=True, help="the link file: the local record of the card")
        sub.add_argument("--log", help="also save the output here")
        sub.add_argument("--fake-file", help="with --source fake: the file the made-up Trello is kept in between commands")
        if command in ("preview", "confirm"):
            sub.add_argument("--draft", required=True, help="the card draft")
            sub.add_argument("--allowlist", required=True, help="the sandbox allowlist of board ids")
            sub.add_argument("--boards", required=True, help="the folder of local board indexes to search for duplicates")
            sub.add_argument("--state", required=True, help="the folder where previews are kept until they are confirmed")
            sub.add_argument("--now", help="the time a due date is checked against, like 2026-11-20T09:00:00Z")
        if command in ("confirm", "reconcile"):
            sub.add_argument("--result", help="save the result record here, as Markdown")
        if command == "confirm":
            sub.add_argument("--fingerprint")
            sub.add_argument("--confirmed-by")
            sub.add_argument("--pretend-minutes-later", type=minutes_forward, default=0, metavar="N",
                             help="tests only: move 'now' forward by N minutes")
    args = parser.parse_args(argv)
    args.files = {}
    del LINES[:]
    found, conn, fake = [], None, None
    try:
        if hasattr(args, "now"):
            try:
                args.now = datetime.datetime.strptime(args.now, "%Y-%m-%dT%H:%M:%SZ") if args.now else now_utc()
            except ValueError:
                raise Refused("--now must be a time written like 2026-11-20T09:00:00Z")
        if args.source == "fake":
            if not args.fake_file:
                raise Refused("--source fake needs --fake-file, the file the made-up Trello is kept in")
            module = load_fake()
            fake = module.FakeTrello.open(args.fake_file)
            conn = Connection(fake.get, fake.post if args.command == "confirm" else None, module.TOKEN_PATH)
        else:
            conn, found = make_live(args.command == "confirm")
        code = run(args, conn)
    except Refused as refusal:
        say("REFUSED: %s." % refusal)
        say("Nothing has been written to Trello.")
        code = 1
    if fake is not None:
        fake.save(args.fake_file)
    text = "\n".join(LINES)
    if any(secret and secret in piece for secret in found for piece in [text] + list(args.files.values())):
        print("STOPPED: the key or the token was found in what would have been shown or saved, so it was not shown or saved.")
        return 2 if conn and conn.wrote() else 1
    for path, content in args.files.items():
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
    print(text)
    if found:
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
