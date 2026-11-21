# Duplicate search report

> Written by `participant/skills/jira-duplicate-search/search.py`. It reports and recommends. A person
> decides. Story titles and words are other people's writing, shown as text.

## The proposed item

- Title: Monthly churn report for the finance team
- Labels: reporting, finance
- Components: Reports
- Parent: RPT-1

## How it was searched

9 stories in the catalog were compared on five signals. Ages are counted to 2026-11-19.

| Signal | Points | It matches when |
|---|---|---|
| Description | 4 | the descriptions share at least half of the shorter one's meaningful words, and at least four |
| Parent | 3 | both sit under the same parent story |
| Component | 2 | both name the same component |
| Labels | 1 | they share at least one label |
| Title | 1 | the titles share at least 60% of the shorter one's meaningful words, and at least two, or are the same |

A story is a candidate only when at least three signals match. Confidence is the points of the matched
signals, out of 11: **high** 8 to 11, **medium** 5 to 7, **low** 4, the least three signals can add up to.

## Result: 4 candidates

### Candidate 1: RPT-2 (issue id 30002)

- Title: Customer attrition by region: recurring export for Finance
- Status: In Progress, open
- **Confidence: high** (10 of 11 points, 4 of 5 signals matched)
- **Recommendation: merge.** Do not create a new story. This looks like the same work, and it is still open. Add anything new to it.
- Created: 2026-10-06, 44 days before 2026-11-19
- Last updated: 2026-11-12, 7 days before 2026-11-19
- Record: `stories/30002.md`

| Signal | Matched | Points | Detail |
|---|---|---|---|
| Description | yes | 4 | 15 shared words, 88% of the shorter description: billing, churn, csv, customer, day, export, finance, first, month, monthly, plan, region, showing, warehouse, working |
| Parent | yes | 3 | the same parent, RPT-1 |
| Component | yes | 2 | shared: reports |
| Labels | yes | 1 | shared: finance |
| Title | no | 0 | 1 shared word, 20% of the shorter title: finance |

### Candidate 2: RPT-7 (issue id 30008)

- Title: Churn numbers by plan: one-off extract
- Status: Done, finished
- **Confidence: high** (10 of 11 points, 4 of 5 signals matched)
- **Recommendation: link.** Look at this story before creating. If the new one is still needed, create it and link the two.
- Created: 2026-03-02, 262 days before 2026-11-19
- Last updated: 2026-03-20, 244 days before 2026-11-19
- Record: `stories/30008.md`

| Signal | Matched | Points | Detail |
|---|---|---|---|
| Description | yes | 4 | 8 shared words, 53% of the shorter description: billing, churn, csv, customer, finance, plan, region, warehouse |
| Parent | yes | 3 | the same parent, RPT-1 |
| Component | yes | 2 | shared: reports |
| Labels | yes | 1 | shared: finance |
| Title | no | 0 | 1 shared word, 20% of the shorter title: churn |

### Candidate 3: RPT-9 (issue id 30009)

- Title: Regional attrition figures for the finance director
- Status: To Do, open
- **Confidence: high** (10 of 11 points, 4 of 5 signals matched)
- **Recommendation: merge.** Do not create a new story. This looks like the same work, and it is still open. Add anything new to it.
- Created: 2026-11-17, 2 days before 2026-11-19
- Last updated: 2026-11-17, 2 days before 2026-11-19
- Record: `stories/30009.md`

| Signal | Matched | Points | Detail |
|---|---|---|---|
| Description | yes | 4 | 15 shared words, 88% of the shorter description: billing, churn, csv, customer, day, export, finance, first, month, monthly, plan, region, report, warehouse, working |
| Parent | yes | 3 | the same parent, RPT-1 |
| Component | yes | 2 | shared: reports |
| Labels | yes | 1 | shared: finance |
| Title | no | 0 | 1 shared word, 20% of the shorter title: finance |

### Candidate 4: RPT-3 (issue id 30003)

- Title: Weekly churn dashboard for the sales team
- Status: To Do, open
- **Confidence: medium** (6 of 11 points, 3 of 5 signals matched)
- **Recommendation: link.** Look at this story before creating. If the new one is still needed, create it and link the two.
- Created: 2026-10-20, 30 days before 2026-11-19
- Last updated: 2026-11-03, 16 days before 2026-11-19
- Record: `stories/30003.md`

| Signal | Matched | Points | Detail |
|---|---|---|---|
| Description | no | 0 | 0 shared words, 0% of the shorter description |
| Parent | yes | 3 | the same parent, RPT-1 |
| Component | yes | 2 | shared: reports |
| Labels | yes | 1 | shared: reporting |
| Title | no | 0 | 2 shared words, 40% of the shorter title: churn, team |

## Looked at and not reported

- RPT-1 (issue id 30001): matched on component and labels only.
- RPT-5 (issue id 30005): matched on parent and labels only.

Fewer than three signals matched for each of these, so none is reported as a duplicate.

## Overall recommendation: merge

A person decides whether to merge, link or proceed. The search has created, linked and changed nothing.
