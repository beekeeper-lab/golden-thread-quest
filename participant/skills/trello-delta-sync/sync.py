#!/usr/bin/env python3
"""Read-only delta synchronization of one Trello board, driven by the board's activity.

See SKILL.md in this folder for what it does and the rules it follows.

    sync.py --source fake [--fake-step N]      read the made-up board in fake_trello.py, as it is at step N
    sync.py --source live --board ID --out FOLDER
    sync.py --status [--out FOLDER]            say where the cursor is and how old. Contacts nothing

It only ever sends GET requests. There is no code here that creates, moves,
updates, archives or comments on anything in Trello.

Exit codes: 0 synchronized; 1 stopped, nothing written; 2 incomplete (rate-limited), nothing written.
"""
import argparse
import datetime
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

API_HOST = "api.trello.com"
PAGE_SIZE = 1000           # the most Trello returns for one request
STALE_HOURS = 24
MAX_WAITS = 3
MAX_WAIT_SECONDS = 15
DEFAULT_WAIT_SECONDS = 10
CARD_FIELDS = "name,shortLink,idBoard,idList,closed,labels,idMembers,due,dueComplete,dateLastActivity"
KEPT = ("short_link", "name", "list_id", "closed", "labels", "member_ids", "due", "due_complete", "last_activity")
CURSOR_SOURCE = "the newest entry of the board's activity that the last successful sync read from Trello"


class Stop(Exception):
    """The run cannot go on. The message says why, in plain words."""


class RateLimited(Exception):
    """Trello kept answering 429 after every allowed wait."""


def say(text):
    print("delta-sync: " + text, flush=True)


def shown_path(path):
    """A path as it is printed: from the folder the skill was run in, so a home folder's name is not shown."""
    try:
        relative = os.path.relpath(path)
    except ValueError:
        return os.path.basename(path)
    return os.path.basename(path) if relative.startswith("..") else relative


def plain_id(value):
    return isinstance(value, str) and value.isascii() and value.isalnum()


# ---------------------------------------------------------------- talking to Trello


def live_get(path, params=None):
    """One GET to api.trello.com. Returns (status, headers, body).

    The key and token come from the environment and go in a request header,
    so they are never part of an address that could be logged. They are never
    printed, returned or written.
    """
    key, token = os.environ.get("TRELLO_API_KEY"), os.environ.get("TRELLO_API_TOKEN")
    url = "https://%s/1%s" % (API_HOST, path)
    if params:
        url += "?" + urllib.parse.urlencode(params)
    request = urllib.request.Request(url, method="GET")
    request.add_header("Authorization", 'OAuth oauth_consumer_key="%s", oauth_token="%s"' % (key, token))
    request.add_header("Accept", "application/json")
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return response.status, dict(response.headers), json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as err:
        text = err.read().decode("utf-8", "replace")
        try:
            body = json.loads(text)
        except ValueError:
            body = {"message": text[:200]}
        return err.code, dict(err.headers), body
    except (urllib.error.URLError, OSError) as err:
        raise Stop("could not reach Trello: %s" % getattr(err, "reason", err))
    except ValueError:
        raise Stop("Trello's answer to %s was not JSON" % path)


class Client:
    """Every request the skill makes goes through here. It can only read."""

    def __init__(self, get, sleep=time.sleep):
        self._get = get
        self._sleep = sleep
        self.waits = []
        self.made = {}      # kind of request -> how many

    @staticmethod
    def _wait_for(headers):
        lower = {str(name).lower(): value for name, value in (headers or {}).items()}
        if str(lower.get("retry-after", "")).isdigit():
            return int(lower["retry-after"])
        for name in ("x-rate-limit-api-token-interval-ms", "x-rate-limit-api-key-interval-ms"):
            if str(lower.get(name, "")).isdigit():
                return (int(lower[name]) + 999) // 1000
        return DEFAULT_WAIT_SECONDS

    def get(self, kind, path, params=None):
        waited = 0
        while True:
            status, headers, body = self._get(path, params or {})
            self.made[kind] = self.made.get(kind, 0) + 1
            if status != 429:
                return status, headers, body
            seconds = self._wait_for(headers)
            if seconds > MAX_WAIT_SECONDS or waited == MAX_WAITS:
                say("rate limited by Trello, and %s" % ("it asks for a %d second wait when the limit is %d"
                    % (seconds, MAX_WAIT_SECONDS) if seconds > MAX_WAIT_SECONDS else "still limited after %d waits" % MAX_WAITS))
                raise RateLimited()
            waited += 1
            say("rate limited by Trello. Wait %d of %d: %d seconds" % (waited, MAX_WAITS, seconds))
            self._sleep(seconds)
            self.waits.append(seconds)


def need_list(client, kind, path, params, what):
    status, _, body = client.get(kind, path, params)
    if status != 200 or not isinstance(body, list):
        raise Stop("Trello did not return %s (status %d)" % (what, status))
    if any(not isinstance(row, dict) or not plain_id(row.get("id")) for row in body):
        raise Stop("Trello returned one of %s with no usable id" % what)
    return body


def read_paged(client, kind, path, params, what, page_size):
    """Ask again with `before` until a page comes back short. Nothing is kept twice."""
    seen, rows = set(), []
    params = dict(params, limit=page_size)
    while True:
        page = need_list(client, kind, path, params, what)
        fresh = [row for row in page if row["id"] not in seen]
        rows.extend(fresh)
        seen.update(row["id"] for row in fresh)
        if len(page) < page_size:
            return rows
        if not fresh:
            raise Stop("Trello kept returning the same of %s, so the skill cannot tell whether it has them all" % what)
        params["before"] = min(seen)  # ids sort by age, so this asks for the ones older than any held


# ---------------------------------------------------------------- reading


def read_board(client, board_ref):
    if not plain_id(board_ref):
        raise Stop("the board is given as its id or the short code in its web address, letters and digits only")
    status, _, body = client.get("board", "/boards/%s" % board_ref, {"fields": "name,closed"})
    if status == 401:
        raise Stop("Trello rejected the credentials or the board (401). Check TRELLO_API_KEY and TRELLO_API_TOKEN, "
                   "and that the token's account can see the board. A token also stops working when it expires")
    if status != 200 or not isinstance(body, dict) or not plain_id(body.get("id")):
        raise Stop("Trello did not return the board (status %d)" % status)
    return {"id": body["id"], "name": str(body.get("name", "")), "closed": bool(body.get("closed"))}


def read_lists(client, board_id):
    rows = need_list(client, "lists", "/boards/%s/lists" % board_id, {"filter": "all", "fields": "name,pos,closed"}, "the board's lists")
    lists = [{"id": r["id"], "name": str(r.get("name", "")), "pos": r.get("pos", 0), "closed": bool(r.get("closed"))} for r in rows]
    return sorted(lists, key=lambda item: (item["pos"], item["id"]))


def read_activity(client, board_id, cursor, page_size):
    """Criterion 1: the board's activity after the cursor, oldest first. With no cursor, only the newest entry."""
    params = {"filter": "all", "fields": "type,date,data", "memberCreator": "false", "member": "false"}
    if cursor is None:
        rows = need_list(client, "activity", "/boards/%s/actions" % board_id, dict(params, limit=1), "the board's activity")
        return rows[:1], 0
    rows = read_paged(client, "activity", "/boards/%s/actions" % board_id, dict(params, since=cursor["action_id"]),
                      "the board's activity", page_size)
    # Entries at or before the cursor are dropped, in case `since` returned more than was asked for.
    fresh = sorted((row for row in rows if row["id"] > cursor["action_id"]), key=lambda row: row["id"])
    return fresh, len(rows) - len(fresh)


def what_happened(entry):
    """One activity entry in a few words. Only its type, ids and the names of changed fields are used: no text from it."""
    data = entry.get("data") if isinstance(entry.get("data"), dict) else {}
    old = data.get("old") if isinstance(data.get("old"), dict) else {}
    kind = str(entry.get("type", ""))
    if kind == "updateCard" and "idList" in old:
        return "moved from list %s to list %s" % ((data.get("listBefore") or {}).get("id", "?"), (data.get("listAfter") or {}).get("id", "?"))
    if kind == "updateCard" and "closed" in old:
        return "archived" if old["closed"] is False else "restored from the archive"
    if kind == "updateCard":
        return "changed (%s)" % ", ".join(sorted(str(k) for k in old)) if old else "changed"
    return {"createCard": "created", "copyCard": "created as a copy", "commentCard": "commented on", "deleteCard": "deleted",
            "moveCardFromBoard": "moved to another board", "moveCardToBoard": "moved here from another board"}.get(
        kind, "activity of type %s" % "".join(ch for ch in kind if ch.isalnum())[:40])


def cards_named(activity):
    """{card id: [what happened, ...]} for every entry that names a card."""
    named = {}
    for entry in activity:
        data = entry.get("data") if isinstance(entry.get("data"), dict) else {}
        card = data.get("card") if isinstance(data.get("card"), dict) else {}
        if plain_id(card.get("id")):
            named.setdefault(card["id"], []).append(what_happened(entry))
    return named


def as_record(row):
    if not isinstance(row.get("idList"), str):
        raise Stop("Trello returned card %s without its list" % row["id"])
    return {"id": row["id"], "short_link": str(row.get("shortLink", "")), "name": str(row.get("name", "")),
            "list_id": row["idList"], "closed": bool(row.get("closed")),
            "labels": sorted(str(l.get("name") or l.get("color") or "") for l in row.get("labels") or [] if isinstance(l, dict)),
            "member_ids": sorted(str(m) for m in row.get("idMembers") or []),
            "due": row.get("due"), "due_complete": bool(row.get("dueComplete")), "last_activity": row.get("dateLastActivity")}


def fetch_card(client, card_id, board_id):
    """One card, in full. Returns ("present", record) or ("gone", why)."""
    status, _, body = client.get("card", "/cards/%s" % card_id, {"fields": CARD_FIELDS})
    if status == 404:
        return "gone", "deleted"
    if status in (401, 403):
        return "gone", "not reachable"
    if status != 200 or not isinstance(body, dict) or body.get("id") != card_id:
        raise Stop("Trello did not return card %s (status %d). The sync is not complete, so nothing is saved and the "
                   "cursor stays where it was" % (card_id, status))
    if body.get("idBoard") != board_id:
        return "gone", "moved to another board"
    return "present", as_record(body)


# ---------------------------------------------------------------- the person's notes


def notes_checksums(out_dir):
    """SHA-256 of every notes file. The files are opened for reading only. Nothing in this skill writes there."""
    folder, sums = os.path.join(out_dir, "notes"), {}
    if os.path.isdir(folder):
        for name in sorted(os.listdir(folder)):
            path = os.path.join(folder, name)
            if os.path.isfile(path):
                with open(path, "rb") as f:
                    sums[name] = hashlib.sha256(f.read()).hexdigest()
    return sums


def write_text(path, text, out_dir):
    """Write the whole file or nothing. Refuses anything in the notes folder (criterion 6)."""
    notes = os.path.realpath(os.path.join(out_dir, "notes"))
    if os.path.commonpath([notes, os.path.realpath(path)]) == notes:
        raise Stop("the sync does not write in the notes folder")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(tmp, path)


# ---------------------------------------------------------------- memory: state.json


def utc_now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_state(out_dir):
    path = os.path.join(out_dir, "state.json")
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            state = json.load(f)
        assert state["schema"] == 1 and isinstance(state["cards"], dict)
        assert state["cursor"] is None or plain_id(state["cursor"]["action_id"])
    except (ValueError, KeyError, TypeError, AssertionError):
        raise Stop("%s cannot be read as this skill's memory. Move it aside to start again" % shown_path(path))
    return state


def digest(state):
    """A SHA-256 of what is held about the cards on the board and its lists, and nothing about when it was synced.

    Two local copies with the same digest hold the same board (criterion 7).
    """
    cards = {card_id: {field: card[field] for field in KEPT} for card_id, card in state["cards"].items() if card["status"] == "present"}
    text = json.dumps({"lists": state["lists"], "cards": cards}, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def hours_between(earlier, later):
    try:
        a = datetime.datetime.strptime(earlier[:19], "%Y-%m-%dT%H:%M:%S")
        b = datetime.datetime.strptime(later[:19], "%Y-%m-%dT%H:%M:%S")
        return (b - a).total_seconds() / 3600
    except (TypeError, ValueError):
        return None


def age(hours):
    if hours is None:
        return "an unknown time"
    return "%d minutes" % round(hours * 60) if hours < 1 else "%.1f hours" % hours if hours < 48 else "%.1f days" % (hours / 24)


def staleness(state, now, stale_hours):
    """The second stretch goal: how old the cursor is, in words."""
    since = hours_between(state["last_successful_sync"], now)
    text = "the last successful sync was %s, %s before now (%s)" % (state["last_successful_sync"], age(since), now)
    if state["cursor"]:
        text += ". The cursor's entry is from %s, %s before now" % (state["cursor"]["action_date"], age(hours_between(state["cursor"]["action_date"], now)))
    if since is not None and since > stale_hours:
        text += ". STALE: more than %d hours since a successful sync. The local copy may be well behind the board" % stale_hours
    return text


# ---------------------------------------------------------------- what is written


def one_line(text):
    """A name on one line, with nothing that could start Markdown structure. Names are other people's writing."""
    return " ".join(str(text).split()).replace("|", "\\|").replace("[", "(").replace("]", ")").replace("`", "'") or "(no name)"


def render_cards(state, notes):
    lists = {item["id"]: item for item in state["lists"]}
    cards = sorted(state["cards"].values(), key=lambda c: c["id"])
    present = [c for c in cards if c["status"] == "present"]
    archived = lambda c: c["closed"] or lists.get(c["list_id"], {}).get("closed", False)
    note = lambda c: "`notes/%s.md`" % c["id"] if c["id"] + ".md" in notes else ""
    row = lambda c: "| %s | `%s` | %s | %s | %s | %s |" % (
        one_line(c["name"]), c["id"], ", ".join(one_line(l) for l in c["labels"]),
        "%d member%s" % (len(c["member_ids"]), "" if len(c["member_ids"]) == 1 else "s") if c["member_ids"] else "",
        c["last_activity"] or "not given", note(c))
    head = ["| Card | Card id | Labels | Members | Last activity | Your notes |", "|---|---|---|---|---|---|"]
    out = ["# %s" % one_line(state["board"]["name"]), "",
           "Generated by the trello-delta-sync skill from %s. Do not edit this file: the next sync replaces it."
           % ("a made-up Trello, `fake_trello.py`. Every card and member here is invented" if state["source"] == "fake" else "Trello"),
           "Your own notes on a card go in `notes/<card id>.md`, which the sync never writes to.", "",
           "Board id `%s`. %d cards on the board: %d open, %d archived. %d kept that are no longer on the board."
           % (state["board"]["id"], len(present), sum(not archived(c) for c in present), sum(archived(c) for c in present),
              len(cards) - len(present)), ""]
    for item in state["lists"]:
        here = [c for c in present if c["list_id"] == item["id"] and not archived(c)]
        if item["closed"] and not here:
            continue
        out += ["## %s (%d)" % (one_line(item["name"]), len(here)), "", "List id `%s`." % item["id"], ""] + (head + [row(c) for c in here] if here else ["none"]) + [""]
    gone_list = [c for c in present if not archived(c) and c["list_id"] not in lists]
    if gone_list:
        out += ["## In a list the board did not return (%d)" % len(gone_list), ""] + head + [row(c) for c in gone_list] + [""]
    old = [c for c in present if archived(c)]
    out += ["## Archived (%d)" % len(old), ""]
    out += (["Still on the board, and archived in Trello. Kept here, with their notes.", "", head[0] + " List | Archived by |", head[1] + "---|---|"]
            + [row(c) + " %s | %s |" % (one_line(lists.get(c["list_id"], {}).get("name", "unknown")), "card" if c["closed"] else "list") for c in old]
            if old else ["none"])
    gone = [c for c in cards if c["status"] != "present"]
    out += ["", "## No longer on the board (%d)" % len(gone), ""]
    out += (["Held from an earlier sync. Nothing here has been deleted locally. Each row is the card as last retrieved.", "",
             "| Card | Card id | Why | Noticed at the sync of | Your notes |", "|---|---|---|---|---|"]
            + ["| %s | `%s` | **%s** | %s | %s |" % (one_line(c["name"]), c["id"], c["gone_reason"], c["gone_since"], note(c)) for c in gone]
            if gone else ["none"])
    return "\n".join(out).rstrip("\n") + "\n"


def render_state_doc(state, out_dir, now, stale_hours):
    cursor, last = state["cursor"], state["last_run"]
    out = ["# Sync state: %s" % one_line(state["board"]["name"]), "",
           "Generated by the trello-delta-sync skill from `%s`, which is where the cursor is kept. Do not edit this file:"
           % shown_path(os.path.join(out_dir, "state.json")).replace(os.sep, "/"),
           "it is rewritten after every successful sync, and by `sync.py --status`.", "",
           "## The last successful point", "", "| | |", "|---|---|",
           "| Board | `%s`%s |" % (state["board"]["id"], ", a made-up board" if state["source"] == "fake" else ""),
           "| Cursor | %s |" % ("activity entry `%s`, dated %s by Trello" % (cursor["action_id"], cursor["action_date"]) if cursor
                               else "none: the board had no activity at the last sync, so the next sync reads all of it"),
           "| Last successful sync | %s, by %s clock |" % (state["last_successful_sync"], "the made-up Trello's" if state["source"] == "fake" else "this machine's"),
           "| That sync was | %s |" % last["kind"],
           "| It read | %d activity entr%s, naming %d card%s |" % (last["entries"], "y" if last["entries"] == 1 else "ies", last["named"], "" if last["named"] == 1 else "s"),
           "| It fetched | %d card%s of the %d on the board |" % (last["fetched"], "" if last["fetched"] == 1 else "s", last["on_board"]),
           "| It found | %d new, %d changed, %d unchanged, %d no longer on the board |" % (last["new"], last["changed"], last["unchanged"], last["gone"]),
           "| Successful syncs so far | %d |" % state["syncs"],
           "| Digest of the local state | `%s` |" % digest(state),
           "| How stale, when this file was written | %s |" % staleness(state, now, stale_hours),
           "", "## What the cursor is taken from", "",
           "The cursor is %s." % CURSOR_SOURCE,
           "Every entry in a Trello board's activity has an id and a time, both given by Trello. The cursor is that id.",
           "It is a position in Trello's own record. It is not a time read from this machine's clock, and it is not",
           "worked out from any card's fields.", "",
           "The first sync has no cursor. It reads the newest activity entry, then every card on the board, and sets",
           "the cursor to that entry. Every later sync asks Trello for the activity after the cursor, with `since`.", "",
           "## How it advances", "",
           "1. The activity after the cursor is read first, then every card it names is fetched. All of it is held in",
           "   memory. Nothing is written yet.",
           "2. If any request fails, the run stops. No file is written. The cursor, the cards and this file are exactly",
           "   as the last successful sync left them.",
           "3. Only when every card has been fetched are the files written: `cards.md`, then `state.json`, which holds",
           "   the cursor, and last this file. The new cursor is the newest activity entry that was read in step 1.",
           "4. A sync that finds no new activity succeeds and leaves the cursor on the same entry.", "",
           "So the next sync after a failed one asks for the same stretch of activity again, and fetches every card",
           "the failed one would have. A change made while a sync is running has an entry newer than the cursor that",
           "sync sets, so the next sync reads it."]
    return "\n".join(out) + "\n"


# ---------------------------------------------------------------- the run


def run(client, board_ref, out_dir, source, now=None, page_size=PAGE_SIZE, full=False, stale_hours=STALE_HOURS, doc_path=None):
    now = now or utc_now()
    doc_path = doc_path or os.path.join(out_dir, "sync-state.md")
    notes_before = notes_checksums(out_dir)
    state = load_state(out_dir)
    if state is not None and state["source"] != source:
        raise Stop("%s holds a %s run, and this is a %s run. One folder holds one source. Use another --out"
                   % (shown_path(out_dir), state["source"], source))
    first = state is None
    try:
        board = read_board(client, board_ref)
        if state is not None and state["board"]["id"] != board["id"]:
            raise Stop("%s holds another board. One folder holds one board. Use another --out" % shown_path(out_dir))
        if first:
            say("no cursor yet: this is the first sync of board %s into %s. Reading the whole board" % (board["id"], shown_path(out_dir)))
            state = {"schema": 1, "source": source, "board": board, "cursor": None, "cards": {}, "lists": [], "syncs": 0}
        else:
            say("cursor before this sync: %s" % ("activity entry %s, dated %s" % (state["cursor"]["action_id"], state["cursor"]["action_date"])
                                                 if state["cursor"] else "none"))
            say("how stale: %s" % staleness(state, now, stale_hours))
        whole = first or full
        if full and not first:
            say("--full: reading the whole board, not only what the activity names")

        # 1. The activity, before any card, so that a change made during the sync is read again next time.
        activity, ignored = read_activity(client, board["id"], None if whole else state["cursor"], page_size)
        if whole:
            newest, named = (activity[0] if activity else None), {}
            say("newest activity entry on the board: %s" % ("%s, dated %s" % (newest["id"], newest.get("date")) if newest else "none"))
        else:
            newest, named = (activity[-1] if activity else None), cards_named(activity)
            say("board activity after the cursor: %d entr%s, naming %d card%s%s"
                % (len(activity), "y" if len(activity) == 1 else "ies", len(named), "" if len(named) == 1 else "s",
                   ". %d at or before the cursor were returned and ignored" % ignored if ignored else ""))
            for card_id in sorted(named):
                say("  activity: card %s %s" % (card_id, "; then ".join(named[card_id])))
        lists = read_lists(client, board["id"])
        held = {card_id for card_id, card in state["cards"].items() if card["status"] == "present"}

        # 2. Which cards to fetch.
        fetched, gone = {}, {}
        if whole:
            rows = read_paged(client, "all cards", "/boards/%s/cards" % board["id"], {"filter": "all", "fields": CARD_FIELDS}, "the board's cards", page_size)
            fetched = {row["id"]: as_record(row) for row in rows}
            silent, on_board = [], set(fetched)
            for card_id in sorted(held - on_board):
                kind, result = fetch_card(client, card_id, board["id"])
                if kind == "present":
                    raise Stop("Trello says card %s is on the board and did not list it, so the board was not read whole" % card_id)
                gone[card_id] = result
        else:
            listing = read_paged(client, "listing", "/boards/%s/cards" % board["id"], {"filter": "all", "fields": "dateLastActivity"},
                                 "the board's list of cards", page_size)
            on_board = {row["id"] for row in listing}
            # A change with no activity entry, such as a label, still moves a card's last-activity time.
            silent = sorted(row["id"] for row in listing if row["id"] not in named and
                            (row["id"] not in held or state["cards"][row["id"]]["last_activity"] != row.get("dateLastActivity")))
            missing = sorted((held - on_board) - set(named))
            say("cross-check of last-activity times: %d card%s on the board. %d changed with no activity entry naming %s%s"
                % (len(on_board), "" if len(on_board) == 1 else "s", len(silent), "it" if len(silent) == 1 else "them",
                   ". %d held and no longer listed" % len(missing) if missing else ""))
            for card_id in sorted(set(named) | set(silent) | set(missing)):
                kind, result = fetch_card(client, card_id, board["id"])
                if kind == "present":
                    fetched[card_id] = result
                elif card_id in state["cards"]:
                    gone[card_id] = result       # a card created and deleted between two syncs was never held: nothing to keep
            say("fetched in full: %d card%s, the ones with new activity. Not fetched: %d"
                % (len(fetched) + len(gone), "" if len(fetched) + len(gone) == 1 else "s", len(on_board - set(fetched))))
    except RateLimited:
        say("INCOMPLETE: Trello rate-limited this run. Nothing was written. The cursor is where it was. Run it again later.")
        return 2

    # 3. Everything was read. Fold it in.
    counts = {"new": [], "changed": [], "same": [], "gone": []}
    for card_id, record in sorted(fetched.items()):
        old = state["cards"].get(card_id)
        if old is None or old["status"] != "present":
            counts["new"].append(card_id)
        else:
            differs = [field for field in KEPT if old[field] != record[field]]
            counts["changed" if differs else "same"].append((card_id, differs) if differs else card_id)
        state["cards"][card_id] = dict(record, status="present", first_seen=old["first_seen"] if old else now)
    for card_id, why in sorted(gone.items()):
        if state["cards"][card_id]["status"] == "present":
            state["cards"][card_id].update(status="gone", gone_reason=why, gone_since=now)
            counts["gone"].append(card_id)
    present = [c for c in state["cards"].values() if c["status"] == "present"]
    unchanged = len(present) - len(counts["new"]) - len(counts["changed"])
    old_lists = {item["id"]: item for item in state["lists"]}
    state.update(lists=lists, board=board, last_successful_sync=now, syncs=state["syncs"] + 1)
    if newest is not None:
        state["cursor"] = {"action_id": newest["id"], "action_date": str(newest.get("date", "")), "taken_from": CURSOR_SOURCE}
    state["last_run"] = {"kind": "a full read of the board" if whole else "a delta, from the board's activity",
                         "entries": len(activity) if not whole else 0, "named": len(named), "fetched": len(fetched) + len(gone),
                         "on_board": len(present), "new": len(counts["new"]), "changed": len(counts["changed"]),
                         "unchanged": unchanged, "gone": len(counts["gone"])}

    say("cards on the board: %d. This sync: %d new, %d changed, %d unchanged, %d no longer on the board"
        % (len(present), len(counts["new"]), len(counts["changed"]), unchanged, len(counts["gone"])))
    for card_id in [] if whole else counts["new"]:
        say("  new: card %s" % card_id)
    for card_id, differs in counts["changed"]:
        card, words = state["cards"][card_id], []
        if "list_id" in differs:
            words.append("MOVED to list %s" % card["list_id"])
        if "closed" in differs:
            words.append("ARCHIVED in Trello. Flagged, and kept with its notes" if card["closed"] else "restored from the archive")
        rest = [f for f in differs if f not in ("list_id", "closed", "last_activity")]
        words += ["changed: " + ", ".join(rest)] if rest else []
        say("  changed: card %s. %s%s" % (card_id, ". ".join(words) or "new activity and no field changed",
                                          "" if whole or card_id in named else ". Found by the cross-check: no activity entry names it"))
    for card_id in counts["gone"]:
        say("  NO LONGER ON THE BOARD: card %s, %s. Flagged, not deleted. Its row and its notes are kept" % (card_id, state["cards"][card_id]["gone_reason"]))
    for item in lists:
        before = old_lists.get(item["id"])
        if before and (before["name"], before["closed"]) != (item["name"], item["closed"]):
            say("  list %s was %s. No card was fetched for that" % (item["id"], "archived" if item["closed"] and not before["closed"] else "renamed or restored"))

    # 4. Write. The cards first, then state.json with the cursor, then its description.
    write_text(os.path.join(out_dir, "cards.md"), render_cards(state, notes_before), out_dir)
    write_text(os.path.join(out_dir, "state.json"), json.dumps(state, indent=1, ensure_ascii=False, sort_keys=True) + "\n", out_dir)
    write_text(doc_path, render_state_doc(state, out_dir, now, stale_hours), out_dir)
    say("cursor after this sync: %s%s" % ("activity entry %s, dated %s" % (state["cursor"]["action_id"], state["cursor"]["action_date"])
                                          if state["cursor"] else "none", "" if newest is not None or whole else ". Not moved: there was no new activity"))
    say("local state digest: %s (%d cards on the board; %d more kept that are no longer on it)"
        % (digest(state), len(present), len(state["cards"]) - len(present)))
    notes_after = notes_checksums(out_dir)
    say("notes: %d file%s, opened for reading only. SHA-256 before and after this sync:" % (len(notes_before), "" if len(notes_before) == 1 else "s"))
    for name in sorted(set(notes_before) | set(notes_after)):
        say("  notes/%s  before %s  after %s  %s" % (name, notes_before.get(name, "absent"), notes_after.get(name, "absent"),
                                                    "same" if notes_before.get(name) == notes_after.get(name) else "DIFFERENT"))
    say("requests made: %d, every one a GET (%s)" % (sum(client.made.values()), ", ".join("%d %s" % (n, kind) for kind, n in client.made.items())))
    say("written: %s, %s and %s" % (shown_path(os.path.join(out_dir, "cards.md")), shown_path(os.path.join(out_dir, "state.json")), shown_path(doc_path)))
    return 0 if notes_before == notes_after else 1


def status(out_dir, doc_path, now, stale_hours):
    state = load_state(out_dir)
    if state is None:
        say("there is no sync state in %s. Nothing has been synchronized there yet." % shown_path(out_dir))
        return 0
    say("board %s. Successful syncs so far: %d" % (state["board"]["id"], state["syncs"]))
    say("cursor: %s" % ("activity entry %s, dated %s" % (state["cursor"]["action_id"], state["cursor"]["action_date"]) if state["cursor"] else "none"))
    say("how stale: %s" % staleness(state, now, stale_hours))
    write_text(doc_path, render_state_doc(state, out_dir, now, stale_hours), out_dir)
    say("Trello was not contacted. Rewritten: %s" % shown_path(doc_path))
    return 0


def main(argv=None):
    here = os.path.dirname(os.path.abspath(__file__))
    default_out = os.path.normpath(os.path.join(here, "..", "..", "context", "trello", "delta"))
    parser = argparse.ArgumentParser(description="Delta synchronization of one Trello board, from its activity. Read-only.")
    parser.add_argument("--source", choices=("live", "fake"))
    parser.add_argument("--status", action="store_true", help="say where the cursor is and how old, without contacting Trello")
    parser.add_argument("--board", help="the board's id, for a live run (or set TRELLO_BOARD)")
    parser.add_argument("--out", help="folder to write into (default: participant/context/trello/delta)")
    parser.add_argument("--full", action="store_true", help="read the whole board instead of only what the activity names")
    parser.add_argument("--stale-hours", type=int, default=STALE_HOURS, help="say STALE when the last successful sync is older than this (default %d)" % STALE_HOURS)
    parser.add_argument("--fake-step", type=int, default=0, help="with --source fake: the made-up board as it is at step 0, 1 or 2")
    parser.add_argument("--fake-fail-card", type=int, default=0, metavar="N", help="with --source fake: the Nth card fetched fails, as if Trello had an error")
    args = parser.parse_args(argv)
    out = os.path.normpath(args.out) if args.out else default_out
    # The description of the state sits beside the folder when the default folder is used, and inside it otherwise.
    doc = os.path.join(os.path.dirname(out), "sync-state.md") if out == default_out else os.path.join(out, "sync-state.md")
    try:
        if args.status:
            return status(out, doc, _fake_now(here, args.fake_step) if args.source == "fake" else utc_now(), args.stale_hours)
        if args.source == "fake":
            sys.path.insert(0, here)
            import fake_trello
            if not 0 <= args.fake_step <= fake_trello.LAST_STEP:
                raise Stop("--fake-step is 0 to %d" % fake_trello.LAST_STEP)
            fake = fake_trello.FakeTrello(args.fake_step)
            if args.fake_fail_card:
                fake.fail("/cards/", status=500, times=1, after=args.fake_fail_card - 1)
            return run(Client(fake.get), fake_trello.BOARD_ID, out, "fake", now=fake.now, full=args.full,
                       stale_hours=args.stale_hours, doc_path=doc)
        if args.source != "live":
            raise Stop("give --source fake or --source live, or --status")
        if args.fake_step or args.fake_fail_card:
            raise Stop("--fake-step and --fake-fail-card only go with --source fake")
        for name in ("TRELLO_API_KEY", "TRELLO_API_TOKEN"):
            if not os.environ.get(name):
                raise Stop("the environment variable %s is not set" % name)
        board = args.board or os.environ.get("TRELLO_BOARD", "")
        if not board:
            raise Stop("no board is given. Use --board with the board's id")
        return run(Client(live_get), board, out, "live", full=args.full, stale_hours=args.stale_hours, doc_path=doc)
    except Stop as stop:
        say("STOPPED: %s." % stop)
        say("Nothing was written. The cursor is where it was.")
        return 1


def _fake_now(here, step):
    sys.path.insert(0, here)
    import fake_trello
    return fake_trello.CLOCK[min(max(step, 0), fake_trello.LAST_STEP) + 1]


if __name__ == "__main__":
    sys.exit(main())
