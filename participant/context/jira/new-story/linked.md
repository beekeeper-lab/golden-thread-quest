---
format: "jira-linked-story/1"
state: "created"
draft: "draft-sandbox.md"
draft_sha256: "56c4a495a3f9567ffbb4cfdc150da71bb27b058a4a25907e1fcf67e06d8e3290"
marker: "gtq-57dc5556"
preview_fingerprint: "c931beb110b0ce15b6005149d1e07ce2cd8b1f1d53f90ab3dbb465eaf1272cf3"
payload_sha256: "d044842a49cf189564af35d662d55965e82c98e124751ecab09ed2eabe3ad3a2"
site_fingerprint: "4aabe3d08fbad6b1"
project_id: "10000"
project_key: "SCRUM"
jira_id: "10022"
jira_key: "SCRUM-23"
earlier_keys: []
confirmed_by: "the participant"
confirmed_at: "2026-11-19 21:34:22 UTC"
created_at: "2026-11-19 21:34:26 UTC"
compared_at: "2026-11-19 21:38:32 UTC"
comparison: "every field the payload sent reads back the same"
---

# Quarterly revenue by plan report for the finance team

> This file is written by `participant/skills/jira-create-story/create.py`. It is the local record of one
> Jira story. The story is identified by its issue id, `jira_id` above. A key can change.

Linked to Jira story **SCRUM-23**, issue id **10022**, in project SCRUM (project id 10000).

## Description

Finance needs a quarterly report of recognised revenue by subscription plan, split by region.

- Source of the figures: the billing warehouse, from the table of invoices.
- Format: a spreadsheet, with one sheet per region.
- First delivery: the second week of January, covering the fourth quarter.

## Sources

- summary: sources/intake-notes.md line 7: "a quarterly report of recognised revenue by subscription plan"
- description: sources/intake-notes.md line 7: "Finance needs a quarterly report of recognised revenue by subscription plan, split by region."
- description: sources/intake-notes.md line 8: "the billing warehouse, from the table of invoices"
- description: sources/intake-notes.md line 9: "a spreadsheet, with one sheet per region"
- description: sources/intake-notes.md line 10: "the second week of January, covering the fourth quarter"
- duedate: sources/intake-notes.md line 10: "15 January 2027 at the latest"
- labels: sources/intake-notes.md line 14: "Tag it reporting and revenue"

## Read-back and compare

The story was read back from Jira by its issue id at 2026-11-19 21:38:32 UTC and compared with the payload that was sent.
Result: **every field the payload sent reads back the same**

| Field | Sent | Read back from Jira | Verdict |
|---|---|---|---|
| `description` | 2 block(s) of document | 2 block(s) of document | the same, identical as sent |
| `duedate` | "2027-01-15" | "2027-01-15" | the same |
| `issuetype` | id 10004 | "Story" (id 10004) | the same |
| `labels` | \["gtq-57dc5556", "reporting", "revenue"\] | \["gtq-57dc5556", "reporting", "revenue"\] | the same |
| `project` | id 10000 | "SCRUM" (id 10000) | the same |
| `summary` | "Quarterly revenue by plan report for the finance team" | "Quarterly revenue by plan report for the finance team" | the same |

Fields Jira set that the payload did not send:

- `created`, Created: "2026-11-19T16:34:26.044-0500"
- `creator`, Creator: a person, not shown
- `priority`, Priority: "Medium" (id 3)
- `reporter`, Reporter: a person, not shown
- `status`, Status: "To Do" (id 10000)
- and 12 more that hold a value, by field id: `aggregateprogress`, `comment`, `customfield_10019`, `issuerestriction`, `progress`, `statusCategory`, `statuscategorychangedate`, `updated`, `votes`, `watches`, `worklog`, `workratio`

## The payload that was sent

907 bytes as sent, SHA-256 `d044842a49cf189564af35d662d55965e82c98e124751ecab09ed2eabe3ad3a2`.

```json
{
  "fields": {
    "description": {
      "content": [
        {
          "content": [
            {
              "text": "Finance needs a quarterly report of recognised revenue by subscription plan, split by region.",
              "type": "text"
            }
          ],
          "type": "paragraph"
        },
        {
          "content": [
            {
              "content": [
                {
                  "content": [
                    {
                      "text": "Source of the figures: the billing warehouse, from the table of invoices.",
                      "type": "text"
                    }
                  ],
                  "type": "paragraph"
                }
              ],
              "type": "listItem"
            },
            {
              "content": [
                {
                  "content": [
                    {
                      "text": "Format: a spreadsheet, with one sheet per region.",
                      "type": "text"
                    }
                  ],
                  "type": "paragraph"
                }
              ],
              "type": "listItem"
            },
            {
              "content": [
                {
                  "content": [
                    {
                      "text": "First delivery: the second week of January, covering the fourth quarter.",
                      "type": "text"
                    }
                  ],
                  "type": "paragraph"
                }
              ],
              "type": "listItem"
            }
          ],
          "type": "bulletList"
        }
      ],
      "type": "doc",
      "version": 1
    },
    "duedate": "2027-01-15",
    "issuetype": {
      "id": "10004"
    },
    "labels": [
      "reporting",
      "revenue",
      "gtq-57dc5556"
    ],
    "project": {
      "id": "10000"
    },
    "summary": "Quarterly revenue by plan report for the finance team"
  }
}
```
