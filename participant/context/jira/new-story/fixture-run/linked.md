---
format: "jira-linked-story/1"
state: "created"
draft: "draft.md"
draft_sha256: "74410edf07a05e99f47155710217415c85fef75c5b3a490c8aadbf0c08b89ccc"
marker: "gtq-3d2f86e9"
preview_fingerprint: "df64d2e7a98a9151469926ba36c6c258c6d894e438b8a591c7d8c6ffbbe61e20"
payload_sha256: "9039d788799b8fdbead7bebcdd68d627b174890b185a50fd2b70da9d3e5ee4a0"
site_fingerprint: "738169e667642f09"
project_id: "30000"
project_key: "RPT"
jira_id: "30010"
jira_key: "RPT-99"
earlier_keys: ["RPT-10"]
confirmed_by: "the participant"
confirmed_at: "2026-11-19 21:38:42 UTC"
created_at: "2026-11-19 21:38:42 UTC"
compared_at: "2026-11-19 21:38:43 UTC"
comparison: "every field the payload sent reads back the same"
---

# Quarterly revenue by plan report for the finance team

> This file is written by `participant/skills/jira-create-story/create.py`. It is the local record of one
> Jira story. The story is identified by its issue id, `jira_id` above. A key can change.

Linked to Jira story **RPT-99**, issue id **30010**, in project RPT (project id 30000).

## Description

Finance needs a quarterly report of recognised revenue by subscription plan, split by region.

- Source of the figures: the billing warehouse, from the table of invoices.
- Format: a spreadsheet, with one sheet per region.
- First delivery: the second week of January, covering the fourth quarter.

## Sources

- summary: ../sources/intake-notes.md line 7: "a quarterly report of recognised revenue by subscription plan"
- description: ../sources/intake-notes.md line 7: "Finance needs a quarterly report of recognised revenue by subscription plan, split by region."
- description: ../sources/intake-notes.md line 8: "the billing warehouse, from the table of invoices"
- description: ../sources/intake-notes.md line 9: "a spreadsheet, with one sheet per region"
- description: ../sources/intake-notes.md line 10: "the second week of January, covering the fourth quarter"
- duedate: ../sources/intake-notes.md line 10: "15 January 2027 at the latest"
- components: ../sources/intake-notes.md line 11: "under the component Reports"
- custom Team: ../sources/intake-notes.md line 11: "The data team will build it"
- parent: ../sources/intake-notes.md line 12: "under the finance reporting epic, RPT-1"
- labels: ../sources/intake-notes.md line 14: "Tag it reporting and revenue"

## Read-back and compare

The story was read back from Jira by its issue id at 2026-11-19 21:38:43 UTC and compared with the payload that was sent.
Result: **every field the payload sent reads back the same**

| Field | Sent | Read back from Jira | Verdict |
|---|---|---|---|
| `components` | id 31001 | "Reports" (id 31001) | the same |
| `customfield_10050` | id 32001 | "Data" (id 32001) | the same |
| `description` | 2 block(s) of document | 2 block(s) of document | the same, identical as sent |
| `duedate` | "2027-01-15" | "2027-01-15" | the same |
| `issuetype` | id 10001 | "Story" (id 10001) | the same |
| `labels` | \["gtq-3d2f86e9", "reporting", "revenue"\] | \["gtq-3d2f86e9", "reporting", "revenue"\] | the same |
| `parent` | "RPT-1" | "RPT-1" (id 30001) | the same |
| `project` | id 30000 | "RPT" (id 30000) | the same |
| `summary` | "Quarterly revenue by plan report for the finance team" | "Quarterly revenue by plan report for the finance team" | the same |

Fields Jira set that the payload did not send:

- `created`, Created: "2026-11-19T12:00:01.000+0000"
- `creator`, Creator: a person, not shown
- `priority`, Priority: "Medium" (id 3)
- `reporter`, Reporter: a person, not shown
- `status`, Status: "To Do" (id 1)
- and 1 more that hold a value, by field id: `updated`

## The payload that was sent

997 bytes as sent, SHA-256 `9039d788799b8fdbead7bebcdd68d627b174890b185a50fd2b70da9d3e5ee4a0`.

```json
{
  "fields": {
    "components": [
      {
        "id": "31001"
      }
    ],
    "customfield_10050": {
      "id": "32001"
    },
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
      "id": "10001"
    },
    "labels": [
      "reporting",
      "revenue",
      "gtq-3d2f86e9"
    ],
    "parent": {
      "key": "RPT-1"
    },
    "project": {
      "id": "30000"
    },
    "summary": "Quarterly revenue by plan report for the finance team"
  }
}
```
