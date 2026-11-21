#!/usr/bin/env python3
"""Read-only synchronization of the cards assigned to the signed-in Trello member.

See SKILL.md in this folder for what it does and the rules it follows.

    sync.py --source fake                      read the made-up boards in fake_trello.py
    sync.py --source fake --fake-after reassignment   the same, after one made-up card was given to someone else
    sync.py --source live --out FOLDER         read Trello as the member the token belongs to

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
MEMBER_CARDS_LIMIT = 1000  # Trello's own list of a member's cards holds no more than this
QUIET_DAYS = 30
MAX_WAITS = 3              # waits for one request before giving up
MAX_WAIT_SECONDS = 15      # the longest single wait
DEFAULT_WAIT_SECONDS = 10  # Trello counts requests in 10 second windows
CARD_FIELDS = "name,shortLink,idBoard,idList,idMembers,closed,dateLastActivity"
WATCHED = ("name", "board_id", "list_id", "list_name", "member_ids", "archived_by", "last_activity")
ARCHIVE_RULE = ("an archived card that is still assigned to the member is INCLUDED, in its own section, and is not "
                "counted as open work. A card is archived when the card, its list or its board is archived or closed")


class Stop(Exception):
    """The run cannot go on. The message says why, in plain words."""


class RateLimited(Exception):
    """Trello kept answering 429 after every allowed wait."""


def say(text):
    print("assigned-sync: " + text, flush=True)


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
        self.waits = []     # seconds waited for rate limits, in order
        self.count = 0      # requests answered

    @staticmethod
    def _wait_for(headers):
        lower = {str(name).lower(): value for name, value in (headers or {}).items()}
        if str(lower.get("retry-after", "")).isdigit():
            return int(lower["retry-after"])
        for name in ("x-rate-limit-api-token-interval-ms", "x-rate-limit-api-key-interval-ms"):
            if str(lower.get(name, "")).isdigit():
                return (int(lower[name]) + 999) // 1000
        return DEFAULT_WAIT_SECONDS

    def get(self, path, params=None):
        waited = 0
        while True:
            status, headers, body = self._get(path, params or {})
            self.count += 1
            if status != 429:
                break
            seconds = self._wait_for(headers)
            if seconds > MAX_WAIT_SECONDS or waited == MAX_WAITS:
                say("rate limited by Trello, and %s" % ("it asks for a %d second wait when the limit is %d"
                    % (seconds, MAX_WAIT_SECONDS) if seconds > MAX_WAIT_SECONDS else "still limited after %d waits" % MAX_WAITS))
                raise RateLimited()
            waited += 1
            say("rate limited by Trello. Wait %d of %d: %d seconds" % (waited, MAX_WAITS, seconds))
            self._sleep(seconds)
            self.waits.append(seconds)
        if status == 401 and path == "/members/me":
            raise Stop("Trello rejected the credentials (401). Check TRELLO_API_KEY and TRELLO_API_TOKEN. "
                       "A token also stops working when it expires")
        return status, headers, body


def need_list(client, path, params, what):
    """A request whose answer must be a list of records with ids. Anything else stops the run."""
    status, _, body = client.get(path, params)
    if status != 200 or not isinstance(body, list):
        raise Stop("Trello did not return %s (status %d). A part of the member's cards may be missing, so nothing "
                   "is saved" % (what, status))
    if any(not isinstance(row, dict) or not plain_id(row.get("id")) for row in body):
        raise Stop("Trello returned one of %s with no usable id" % what)
    return body


# ---------------------------------------------------------------- reading


def resolve_member(client):
    """Criterion 1: ask Trello who the token belongs to. No member is named in this skill or its configuration."""
    status, _, body = client.get("/members/me", {"fields": "id"})
    if status != 200 or not isinstance(body, dict) or not plain_id(body.get("id")):
        raise Stop("Trello did not say who the signed-in member is (status %d)" % status)
    return body["id"]


def read_boards(client):
    """Criterion 2: every board the connection can reach, closed ones included."""
    rows = need_list(client, "/members/me/boards", {"filter": "all", "fields": "name,shortLink,closed"},
                     "the member's boards")
    boards = [{"id": row["id"], "name": str(row.get("name", "")), "short_link": str(row.get("shortLink", "")),
               "closed": bool(row.get("closed"))} for row in rows]
    return sorted(boards, key=lambda board: board["id"])


def read_paged(client, path, params, what, page_size):
    """Criterion 3: ask again with `before` until a page comes back short. Returns (rows, the size of each page)."""
    seen, rows, pages = set(), [], []
    params = dict(params, limit=page_size)
    while True:
        page = need_list(client, path, params, what)
        if len(page) > page_size:
            raise Stop("Trello returned more of %s than were asked for, so paging cannot be trusted" % what)
        fresh = [row for row in page if row["id"] not in seen]
        pages.append(len(page))
        rows.extend(fresh)
        seen.update(row["id"] for row in fresh)
        if len(page) < page_size:
            return rows, pages
        if not fresh:
            # A full page that holds nothing new means asking for older ones did not work. There may be
            # more that were never reached, so this is not treated as the end.
            raise Stop("Trello kept returning the same of %s, so the skill cannot tell whether it has them all" % what)
        params["before"] = min(seen)  # ids sort by age, so this asks for the ones older than any held


def read_board_cards(client, board, member_id, page_size):
    """All of one board's cards, archived ones included, and those of them assigned to the member."""
    lists = {row["id"]: row for row in need_list(client, "/boards/%s/lists" % board["id"],
                                                 {"filter": "all", "fields": "name,pos,closed"},
                                                 "the lists of board %s" % board["id"])}
    rows, pages = read_paged(client, "/boards/%s/cards" % board["id"], {"filter": "all", "fields": CARD_FIELDS},
                             "the cards of board %s" % board["id"], page_size)
    cards = []
    for row in rows:
        members = row.get("idMembers")
        if not isinstance(members, list):
            raise Stop("Trello returned card %s without its members, so it cannot be told whose it is" % row["id"])
        if member_id not in members:
            continue                      # someone else's card: counted, never kept
        in_list = lists.get(row.get("idList")) or {}
        archived_by = [word for word, yes in (("card", row.get("closed")), ("list", in_list.get("closed")),
                                              ("board", board["closed"])) if yes]
        cards.append({"id": row["id"], "short_link": str(row.get("shortLink", "")), "name": str(row.get("name", "")),
                      "board_id": board["id"], "board_name": board["name"],
                      "list_id": str(row.get("idList", "")), "list_name": str(in_list.get("name", "")),
                      "list_pos": in_list.get("pos", 0), "member_ids": sorted(str(m) for m in members),
                      "archived_by": archived_by, "last_activity": row.get("dateLastActivity")})
    return cards, {"id": board["id"], "name": board["name"], "short_link": board["short_link"],
                   "closed": board["closed"], "cards": len(rows), "pages": pages, "assigned": len(cards)}


def cross_check(client, found, searched):
    """Compare what was found board by board with Trello's own list of the member's cards.

    Returns (how many Trello listed, how many of those are on boards that were not searched, whether the list was full).
    A card Trello lists on a searched board that the search did not find stops the run: the search was incomplete.
    """
    rows = need_list(client, "/members/me/cards", {"filter": "all", "fields": "idBoard"}, "Trello's own list of the member's cards")
    missed = [row["id"] for row in rows if row.get("idBoard") in searched and row["id"] not in found]
    if missed:
        raise Stop("Trello lists %d card(s) of the member on the boards searched that the search did not find, the "
                   "first being %s. The search was not complete, so nothing is saved" % (len(missed), missed[0]))
    return len(rows), sum(row.get("idBoard") not in searched for row in rows), len(rows) >= MEMBER_CARDS_LIMIT


def why_gone(client, card_id, member_id):
    """Criterion 6: look one card up to say why it is no longer among the member's cards."""
    status, _, body = client.get("/cards/%s" % card_id, {"fields": "idMembers,idBoard,closed"})
    if status == 404:
        return {"reason": "deleted", "detail": "Trello says there is no such card"}
    if status in (401, 403):
        return {"reason": "not reachable", "detail": "the connection may no longer see this card, for example "
                                                     "because the member left its board"}
    if status != 200 or not isinstance(body, dict) or not isinstance(body.get("idMembers"), list):
        raise Stop("Trello did not say what became of card %s (status %d), so nothing is saved" % (card_id, status))
    others = sorted(str(m) for m in body["idMembers"])
    if member_id in others:
        return {"reason": "board not searched", "detail": "the card is still the member's, on a board this sync "
                                                          "did not search"}
    if others:
        return {"reason": "reassigned", "detail": "now assigned to member id " + ", ".join(others), "now_member_ids": others}
    return {"reason": "unassigned", "detail": "now assigned to nobody", "now_member_ids": []}


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
    """Write the whole file or nothing. Refuses anything in the notes folder (criterion 7)."""
    notes = os.path.realpath(os.path.join(out_dir, "notes"))
    if os.path.commonpath([notes, os.path.realpath(path)]) == notes:
        raise Stop("the sync does not write in the notes folder")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(tmp, path)


# ---------------------------------------------------------------- memory: assigned.json


def utc_now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_state(out_dir, source, member_id):
    path = os.path.join(out_dir, "assigned.json")
    if not os.path.exists(path):
        return {"schema": 1, "source": source, "member_id": member_id, "cards": {}}
    try:
        with open(path, encoding="utf-8") as f:
            state = json.load(f)
        assert state["schema"] == 1 and isinstance(state["cards"], dict)
    except (ValueError, KeyError, TypeError, AssertionError):
        raise Stop("%s cannot be read as this skill's memory. Move it aside to start again" % shown_path(path))
    if state.get("source") != source:
        raise Stop("%s holds cards from a %s run, and this is a %s run. One folder holds one source. Use another --out"
                   % (shown_path(out_dir), state.get("source"), source))
    if state.get("member_id") != member_id:
        raise Stop("%s holds another member's cards. One folder holds one member. Use another --out" % shown_path(out_dir))
    return state


def merge(state, cards, gone_reasons, now):
    """Fold what Trello returned into what was held, matching on the card's Trello id and nothing else.

    A card held and not returned is kept and flagged with why (criterion 6). No card is ever removed.
    Returns what changed, by kind (criterion 5: a re-sync of unchanged data gives no new and no changed).
    """
    held = state["cards"]
    changes = {"new": [], "changed": [], "unchanged": [], "flagged": [], "back": [], "still_flagged": []}
    for card in cards:
        old = held.get(card["id"])
        record = dict(card, status="assigned", first_seen=old["first_seen"] if old else now)
        if old is None:
            changes["new"].append(card["id"])
        elif old["status"] != "assigned":
            changes["back"].append(card["id"])
        elif any(old.get(field) != record[field] for field in WATCHED):
            changes["changed"].append((card["id"], [f for f in WATCHED if old.get(f) != record[f]]))
        else:
            changes["unchanged"].append(card["id"])
        held[card["id"]] = record
    returned = {card["id"] for card in cards}
    for card_id, old in held.items():
        if card_id in returned:
            continue
        if old["status"] == "assigned":
            old.update(status="not assigned", since=now, **gone_reasons[card_id])
            changes["flagged"].append(card_id)
        else:
            changes["still_flagged"].append(card_id)
    return changes


# ---------------------------------------------------------------- the index


def one_line(text):
    """A name on one line, with nothing that could start Markdown structure. Names are other people's writing."""
    return " ".join(str(text).split()).replace("|", "\\|").replace("[", "(").replace("]", ")").replace("`", "'") or "(no name)"


def days_quiet(card, now):
    try:
        then = datetime.datetime.strptime(card["last_activity"][:19], "%Y-%m-%dT%H:%M:%S")
        return (datetime.datetime.strptime(now[:19], "%Y-%m-%dT%H:%M:%S") - then).days
    except (TypeError, ValueError):
        return None


def order(cards):
    return sorted(cards, key=lambda c: (c["board_id"], c["list_pos"], c["id"]))


def render_index(state, notes, quiet_days):
    now, me = state["last_successful_sync"], state["member_id"]
    cards = list(state["cards"].values())
    mine = [c for c in cards if c["status"] == "assigned"]
    is_open = order(c for c in mine if not c["archived_by"])
    archived = order(c for c in mine if c["archived_by"])
    gone = order(c for c in cards if c["status"] != "assigned")
    has_note = lambda c: "`notes/%s.md`" % c["id"] if c["id"] + ".md" in notes else ""
    others = lambda c: len([m for m in c["member_ids"] if m != me])
    quiet = [c for c in is_open if (days_quiet(c, now) or 0) >= quiet_days]
    out = ["# Cards assigned to the member", "",
           "Generated by the trello-read-assigned-cards skill from %s. Do not edit this file: the next sync replaces it."
           % ("a made-up Trello, `fake_trello.py`. Every board, card and member here is invented" if state["source"] == "fake" else "Trello"),
           "Your own notes on a card go in `notes/<card id>.md`, which the sync never writes to.", "",
           "| | |", "|---|---|",
           "| Member, read from the connection | member id `%s` |" % me,
           "| Last successful sync | %s |" % now,
           "| Boards searched | %d%s |" % (len(state["boards"]), state.get("restricted") or ""),
           "| Assigned and open | %d |" % len(is_open),
           "| Assigned and archived | %d |" % len(archived),
           "| No longer assigned, kept | %d |" % len(gone),
           "| Notes files | %d |" % len(notes),
           "", "Rule for archived cards: %s." % ARCHIVE_RULE, "",
           "## Boards searched (%d)" % len(state["boards"]), "",
           "| Board | Board id | State | Cards on it | Requests for its cards | Assigned to the member |", "|---|---|---|---|---|---|"]
    out += ["| %s | `%s` | %s | %d | %d | %d |" % (one_line(b["name"]), b["id"], "closed" if b["closed"] else "open",
                                                  b["cards"], len(b["pages"]), b["assigned"]) for b in state["boards"]]
    head = ["| Card | Card id | Board | List | Last activity | Also assigned to | Your notes |", "|---|---|---|---|---|---|---|"]
    row = lambda c, extra="": "| %s | `%s` | %s | %s | %s | %s | %s |%s" % (
        one_line(c["name"]), c["id"], one_line(c["board_name"]), one_line(c["list_name"]) if c["list_name"] else "unknown",
        c["last_activity"] or "not given", "%d other%s" % (others(c), "" if others(c) == 1 else "s") if others(c) else "",
        has_note(c), extra)
    out += ["", "## Assigned and open (%d)" % len(is_open), ""] + (head + [row(c) for c in is_open] if is_open else ["none"])
    out += ["", "## Assigned and archived (%d)" % len(archived), ""]
    if archived:
        out += ["Still assigned to the member, and archived in Trello. Not counted as open work.", "",
                head[0] + " Archived by |", head[1] + "---|"] + [row(c, " %s |" % ", ".join(c["archived_by"])) for c in archived]
    else:
        out += ["none"]
    out += ["", "## No longer assigned (%d)" % len(gone), ""]
    if gone:
        out += ["Held from an earlier sync and no longer among the member's cards. Nothing here has been deleted. Each",
                "row is the card as it was when last retrieved, and its notes are where they were.", "",
                "| Card | Card id | Board | List | Why | Noticed at the sync of | Your notes |", "|---|---|---|---|---|---|---|"]
        out += ["| %s | `%s` | %s | %s | **%s**: %s | %s | %s |" % (
            one_line(c["name"]), c["id"], one_line(c["board_name"]), one_line(c["list_name"]) if c["list_name"] else "unknown",
            c["reason"], c["detail"], c["since"], has_note(c)) for c in gone]
    else:
        out += ["none"]
    shared = [c for c in is_open if others(c)]
    out += ["", "## Assigned to several members (%d)" % len(shared), ""]
    out += (["Open cards the member shares. The other members are given by Trello member id.", "",
             "| Card | Card id | Board | Other members |", "|---|---|---|---|"]
            + ["| %s | `%s` | %s | %s |" % (one_line(c["name"]), c["id"], one_line(c["board_name"]),
                                            ", ".join("`%s`" % m for m in c["member_ids"] if m != me)) for c in shared]
            if shared else ["none"])
    out += ["", "## No activity for %d days or more (%d)" % (quiet_days, len(quiet)), ""]
    out += (["Open cards, counted back from the last successful sync.", "",
             "| Card | Card id | Board | Last activity | Days |", "|---|---|---|---|---|"]
            + ["| %s | `%s` | %s | %s | %d |" % (one_line(c["name"]), c["id"], one_line(c["board_name"]),
                                                 c["last_activity"], days_quiet(c, now)) for c in quiet]
            if quiet else ["none"])
    orphans = sorted(name for name in notes if name[:-3] not in state["cards"] or not name.endswith(".md"))
    if orphans:
        out += ["", "## Notes files with no card here (%d)" % len(orphans), "",
                "Left as they are. The sync does not move or remove notes.", ""] + ["- `notes/%s`" % one_line(n) for n in orphans]
    return "\n".join(out).rstrip("\n") + "\n"


def rows_in_index(text):
    """How many card rows the three main sections of an index hold, counted from its text."""
    count, inside = 0, False
    for line in text.splitlines():
        if line.startswith("## "):
            inside = line.startswith(("## Assigned and open", "## Assigned and archived", "## No longer assigned"))
        elif inside and line.startswith("| ") and not line.startswith("| Card |"):
            count += 1
    return count


# ---------------------------------------------------------------- the run


def run(client, out_dir, source, now=None, page_size=PAGE_SIZE, only_boards=None, quiet_days=QUIET_DAYS):
    now = now or utc_now()
    notes_before = notes_checksums(out_dir)
    # Everything is read first. Nothing is written until every request has succeeded.
    try:
        member = resolve_member(client)
        say('member read from the connection: member id %s. Trello was asked "who am I?". No member is named '
            "in the skill or given to it" % member)
        state = load_state(out_dir, source, member)
        boards = read_boards(client)
        reachable = len(boards)
        say("boards the connection can reach: %d (%d open, %d closed)"
            % (reachable, sum(not b["closed"] for b in boards), sum(b["closed"] for b in boards)))
        restricted = ""
        if only_boards:
            unknown = sorted(set(only_boards) - {b["id"] for b in boards})
            if unknown:
                raise Stop("--only-boards names a board the connection cannot reach: %s" % ", ".join(unknown))
            boards = [b for b in boards if b["id"] in only_boards]
            restricted = " of the %d the connection can reach. RESTRICTED with --only-boards, so this is not every board" % reachable
            say("RESTRICTED to %d of them with --only-boards. This run does not cover every board" % len(boards))
        cards, searched = [], []
        for board in boards:
            found, summary = read_board_cards(client, board, member, page_size)
            cards += found
            searched.append(summary)
            say("  board %s, %s: %d cards read in %d request%s (%s), %d assigned to the member"
                % (board["id"], "closed" if board["closed"] else "open", summary["cards"], len(summary["pages"]),
                   "" if len(summary["pages"]) == 1 else "s", " + ".join(str(p) for p in summary["pages"]), summary["assigned"]))
        if len({card["id"] for card in cards}) != len(cards):
            raise Stop("the same card was returned on two boards, so the count cannot be trusted")
        largest = max([s["cards"] for s in searched] or [0])
        say("page limit: %d cards for one request. Largest board: %d cards, %s"
            % (page_size, largest, "more than one page, retrieved completely" if largest > page_size else "within one page"))
        listed, elsewhere, full = cross_check(client, {c["id"] for c in cards}, {b["id"] for b in boards})
        say("retrieved: %d cards assigned to the member, on %d boards searched" % (len(cards), len(boards)))
        say("Trello's own list of the member's cards holds %d%s. Every one of them on a board searched was found%s"
            % (listed, ", which is its limit, so it may not be all of them" if full else "",
               ". %d are on boards not searched" % elsewhere if elsewhere else ""))
        gone = {card_id: why_gone(client, card_id, member) for card_id, old in sorted(state["cards"].items())
                if old["status"] == "assigned" and card_id not in {c["id"] for c in cards}}
    except RateLimited:
        say("INCOMPLETE: Trello rate-limited this run. Nothing was written. The files from the last successful "
            "sync are as they were. Run it again later.")
        return 2

    held_before = len(state["cards"])
    changes = merge(state, cards, gone, now)
    state.update(boards=searched, restricted=restricted, last_successful_sync=now)
    archived = [c for c in cards if c["archived_by"]]
    say("archived cards: %s." % ARCHIVE_RULE)
    say("  of the %d retrieved: %d open, %d archived (%s)" % (
        len(cards), len(cards) - len(archived), len(archived),
        ", ".join("%d by %s" % (sum(way in c["archived_by"] for c in archived), way) for way in ("card", "list", "board"))))
    say("cards held before this sync: %d. This sync: %d new, %d changed, %d unchanged, %d newly flagged as no longer "
        "assigned, %d assigned again" % (held_before, len(changes["new"]), len(changes["changed"]),
                                        len(changes["unchanged"]), len(changes["flagged"]), len(changes["back"])))
    for card_id, fields in changes["changed"]:
        say("  changed: card %s (%s)" % (card_id, ", ".join(fields)))
    for card_id in changes["flagged"]:
        say("  FLAGGED, not deleted: card %s is no longer assigned to the member. %s: %s. Its row and its notes are kept"
            % (card_id, state["cards"][card_id]["reason"], state["cards"][card_id]["detail"]))
    for card_id in changes["back"]:
        say("  assigned again: card %s" % card_id)
    index_path = os.path.join(out_dir, "index.md")
    text = render_index(state, notes_before, quiet_days)
    write_text(index_path, text, out_dir)
    write_text(os.path.join(out_dir, "assigned.json"), json.dumps(state, indent=1, ensure_ascii=False, sort_keys=True) + "\n", out_dir)  # last
    flagged = sum(c["status"] != "assigned" for c in state["cards"].values())
    saved = rows_in_index(text)
    say("counts: retrieved %d, held and no longer assigned %d, expected in the index %d. Rows saved in the index: %d. %s"
        % (len(cards), flagged, len(cards) + flagged, saved, "The counts agree" if saved == len(cards) + flagged else "THE COUNTS DISAGREE"))
    notes_after = notes_checksums(out_dir)
    say("notes: %d file%s, opened for reading only. SHA-256 before and after this sync:" % (len(notes_before), "" if len(notes_before) == 1 else "s"))
    for name in sorted(set(notes_before) | set(notes_after)):
        say("  notes/%s  before %s  after %s  %s" % (name, notes_before.get(name, "absent"), notes_after.get(name, "absent"),
                                                    "same" if notes_before.get(name) == notes_after.get(name) else "DIFFERENT"))
    if client.waits:
        say("this run waited %d time(s) for Trello's rate limit" % len(client.waits))
    say("requests made: %d, every one a GET" % client.count)
    say("index written: %s" % shown_path(index_path))
    if saved != len(cards) + flagged or notes_before != notes_after:
        say("STOPPED AFTER WRITING: a check above failed. Do not rely on this index.")
        return 1
    return 0


def main(argv=None):
    here = os.path.dirname(os.path.abspath(__file__))
    default_out = os.path.join(here, "..", "..", "context", "trello", "assigned")
    parser = argparse.ArgumentParser(description="Synchronize the cards assigned to the signed-in Trello member. Read-only.")
    parser.add_argument("--source", choices=("live", "fake"), required=True)
    parser.add_argument("--out", help="folder to write into (default: participant/context/trello/assigned)")
    parser.add_argument("--only-boards", help="search only these board ids, separated by commas. The index then says it is restricted")
    parser.add_argument("--quiet-days", type=int, default=QUIET_DAYS, help="list open cards with no activity for this many days (default %d)" % QUIET_DAYS)
    parser.add_argument("--fake-after", choices=("reassignment",), help="with --source fake: first change the made-up Trello, "
                        "as if one card (Support task 4) had been reassigned to another member since the last sync")
    args = parser.parse_args(argv)
    out = os.path.normpath(args.out or default_out)
    try:
        only = [b.strip() for b in (args.only_boards or "").split(",") if b.strip()]
        if any(not plain_id(b) for b in only):
            raise Stop("--only-boards takes board ids, letters and digits only")
        if args.quiet_days < 1:
            raise Stop("--quiet-days is a whole number of days, 1 or more")
        if args.source == "fake":
            sys.path.insert(0, here)
            import fake_trello
            fake = fake_trello.FakeTrello()
            if args.fake_after == "reassignment":
                fake.reassign("Support", 4, [fake_trello.BO])
            # The fake's limit for one request is 50, where Trello's is 1000, so that a made-up board needs several.
            return run(Client(fake.get), out, "fake", now=fake.now, page_size=fake.page_limit, only_boards=only,
                       quiet_days=args.quiet_days)
        if args.fake_after:
            raise Stop("--fake-after only goes with --source fake")
        for name in ("TRELLO_API_KEY", "TRELLO_API_TOKEN"):
            if not os.environ.get(name):
                raise Stop("the environment variable %s is not set" % name)
        return run(Client(live_get), out, "live", only_boards=only, quiet_days=args.quiet_days)
    except Stop as stop:
        say("STOPPED: %s." % stop)
        say("Nothing was written.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
