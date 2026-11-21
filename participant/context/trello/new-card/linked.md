---
format: "trello-linked-card/1"
state: "created"
draft: "draft-create.md"
draft_sha256: "7e77eafeffce56d8f56f0f9d07ea25d2b7a651b4cb676bb676b3feb34cfad107"
preview_fingerprint: "8471834218757f2cee91ab195c35b1f08c4ae494bf973bf13d6a85690ef6f9de"
payload_sha256: "c7eac8dfd8742d465d0a7c7d1354770828862f6530a3fa7aecbd1104a939c10b"
board_id: "6afdf376f8b9111df7e27f99"
list_id: "6afdf3911014b50669965df7"
card_id: "6b00b32ea6e47268f6721469"
short_link: "9hsNtGfm"
confirmed_by: "the participant"
confirmed_at: "2026-11-20 20:53:00 UTC"
created_at: "2026-11-20 20:53:02 UTC"
trello_created_at: "2026-11-20 20:53:02 UTC"
compared_at: "2026-11-20 21:01:47 UTC"
comparison: "every field the payload sent reads back the same"
---

# Made-up card to check the create workflow

> This file is written by `participant/skills/trello-create-card/create.py`. It is the local record of one
> Trello card. The card is identified by its card id, `card_id` above. A name, a list and a position can change.

Linked to Trello card **6b00b32ea6e47268f6721469** (short link 9hsNtGfm), created in list 6afdf3911014b50669965df7 on board 6afdf376f8b9111df7e27f99.

## Description

A made-up card. It checks that a card is created exactly as it was previewed.

It can be deleted.

## Sources

- name: sources/create-notes.md line 5: "create one made-up card on the sandbox board to check the create workflow"
- description: sources/create-notes.md line 6: "a made-up card that checks the card is created exactly as previewed"
- description: sources/create-notes.md line 7: "can be deleted afterwards"
- due: sources/create-notes.md line 8: "5 pm UTC on Friday 18 December 2026"

## Read-back and compare

The card was read back from Trello by its card id at 2026-11-20 21:01:47 UTC and compared with the payload that was sent.
Result: **every field the payload sent reads back the same**

| Field | Sent | Read back from Trello | Verdict |
|---|---|---|---|
| `idList` | 6afdf3911014b50669965df7 | 6afdf3911014b50669965df7 | the same |
| `pos` | "bottom" | position number 140737488388096, number 3 of 3 open cards in the list | the same: it is last in the list |
| `name` | "Made-up card to check the create workflow" | "Made-up card to check the create workflow" | the same |
| `desc` | 97 characters, starting "A made-up card. It checks that a card is" | 97 characters, starting "A made-up card. It checks that a card is" | the same, character for character |
| `due` | 2026-12-18T17:00:00.000Z | 2026-12-18T17:00:00.000Z | the same |
| `idBoard` | not sent: it follows from the list | 6afdf376f8b9111df7e27f99 | the same as the board that was previewed |

What Trello set that the payload did not send:

- card id: 6b00b32ea6e47268f6721469
- short link: 9hsNtGfm
- number on the board: 9
- position number: 140737488388096
- archived: no
- due marked complete: no
- created, read from the card id: 2026-11-20 20:53:02 UTC
- last activity: 2026-11-20T20:53:02.530Z

## The payload that was sent

245 bytes as sent, SHA-256 `c7eac8dfd8742d465d0a7c7d1354770828862f6530a3fa7aecbd1104a939c10b`.

```json
{
  "desc": "A made-up card. It checks that a card is created exactly as it was previewed.\n\nIt can be deleted.",
  "due": "2026-12-18T17:00:00.000Z",
  "idList": "6afdf3911014b50669965df7",
  "name": "Made-up card to check the create workflow",
  "pos": "bottom"
}
```
