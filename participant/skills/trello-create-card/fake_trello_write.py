#!/usr/bin/env python3
"""A fake Trello that can also create a card, for testing the create workflow. No network.

It is the made-up Trello of the trello-create-card-preview skill, with the
same two boards, plus one thing: post("/cards", None, body) creates a card
from a JSON body, as Trello's POST /1/cards does. Nothing else can be written.

It can be saved to a file and opened again, so that a preview and a
confirmation run as two separate commands see the same boards.

Knobs, for tests. Each is a name in `knobs`:

    lose_answer   True: the card is created and then the connection fails, so
                  no answer comes back.
    drop_request  True: the connection fails before Trello sees the create.
    post_status   a status to answer the create with, creating nothing.
    alter         {field: value}: the card is created with this field changed,
                  as if Trello had altered what was sent.
    wrong_list    a list id: the card is created there instead.

A token that has no write permission is answered 401, as Trello answers.

Every board, list, card, label and member here is invented. It is a stand-in
built from Trello's public documentation and not checked against Trello field
by field.
"""
import copy
import importlib.util
import json
import os
import time

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location(
    "preview_fake_trello", os.path.join(HERE, "..", "trello-create-card-preview", "fake_trello.py"))
base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(base)

PLATFORM, SUPPORT, TOKEN_PATH = base.PLATFORM, base.SUPPORT, base.TOKEN_PATH
ME, BO, CY, DEE = base.ME, base.BO, base.CY, base.DEE
OLD_IDEAS, TO_DO, DOING, DONE, INBOX = base.OLD_IDEAS, base.TO_DO, base.DOING, base.DONE, base.INBOX
cid, lid, label_id = base.cid, base.lid, base.label_id


class FakeTrello(base.FakeTrello):
    def __init__(self):
        super().__init__()
        self.knobs, self.created = {}, 0
        for board in self.boards.values():
            for card in board["cards"]:
                card["idLabels"] = [label["id"] for label in card["labels"]]

    # ------------------------------------------------------------ saving and opening

    @classmethod
    def open(cls, path):
        fake = cls()
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            fake.boards, fake.token, fake.me = data["boards"], data["token"], data["me"]
            fake.knobs, fake.created = data["knobs"], data["created"]
        return fake

    def save(self, path):
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"boards": self.boards, "token": self.token, "me": self.me, "knobs": self.knobs, "created": self.created}, f, indent=1)

    # ------------------------------------------------------------ the one write

    def post(self, path, params, body):
        self.requests.append(("POST", path, {}))
        if path != "/cards" or params or not isinstance(body, bytes):
            return 404, {}, {"message": "The requested resource was not found."}
        if self.knobs.get("drop_request"):
            raise OSError("the fake dropped the request before Trello saw it")
        boards = [row for row in self.token["permissions"] if row.get("modelType") == "Board"]
        if not any(row.get("write") is True for row in boards):
            return 401, {}, {"message": "unauthorized permission requested"}
        if self.knobs.get("post_status"):
            return self.knobs["post_status"], {}, {"message": "the fake was told to answer %d" % self.knobs["post_status"]}
        try:
            sent = json.loads(body.decode("utf-8"))
        except ValueError:
            return 400, {}, {"message": "invalid JSON"}
        board, target = self._find("lists", self.knobs.get("wrong_list") or sent.get("idList"))
        if target is None or not isinstance(sent.get("name"), str):
            return 400, {}, {"message": "invalid value for idList"}
        labels = []
        for wanted in [item for item in str(sent.get("idLabels") or "").split(",") if item]:
            found = [label for label in board["labels"] if label["id"] == wanted]
            if not found:
                return 400, {}, {"message": "invalid value for idLabels"}
            labels.append(dict(found[0], idBoard=board["id"]))
        here = [card["pos"] for card in board["cards"] if card["idList"] == target["id"] and not card["closed"]]
        pos = sent.get("pos", "bottom")
        if pos == "bottom":
            pos = (max(here) if here else 0) + 65536
        elif pos == "top":
            pos = (min(here) if here else 131072) / 2
        self.created += 1
        new_id = "%08x%010d%06x" % (int(time.time()), 0, self.created)
        card = {"id": new_id, "shortLink": "NEW%05d" % self.created, "idShort": 90 + self.created, "idBoard": board["id"],
                "idList": target["id"], "name": sent["name"], "desc": sent.get("desc", ""), "closed": False, "pos": pos,
                "due": sent.get("due"), "dueComplete": False, "start": None, "dueReminder": None,
                "dateLastActivity": time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime()),
                "labels": labels, "idLabels": [label["id"] for label in labels],
                "idMembers": [item for item in str(sent.get("idMembers") or "").split(",") if item],
                "cover": {"idAttachment": None, "color": None, "size": "normal", "brightness": "dark"}, "_checklists": []}
        card.update(self.knobs.get("alter") or {})
        board["cards"].append(card)
        if self.knobs.get("lose_answer"):
            raise OSError("the fake lost the answer after Trello created the card")
        return 200, {}, copy.deepcopy(base.pick(card, "all"))
