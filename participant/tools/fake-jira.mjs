// A pretend Jira for the jira-read-assigned-stories quest. It serves one of the quest's practice
// data sets (validators/fixtures/jira/<name>.json) the way Jira's REST API answers, so the
// synchronization talks to it exactly as it would talk to Jira, with nothing real involved:
//
//   myself()                              -> the authenticated user (a made-up account)
//   searchAssigned({ startAt, maxResults }) -> one page of the stories assigned to that user,
//                                            with Jira's paging fields: startAt, maxResults,
//                                            total and isLast
//   comments(key, { startAt })            -> one page of a story's comments, also paged
//
// Like Jira, the server decides the page size: a caller asking for 50 may get fewer, and must
// keep asking until isLast. The "pagination" set is served two stories a page, so a caller that
// stops after one page misses two. Comments are served two a page, so the "duplicate-comment"
// set's comment 9001, listed on both of GTQ-101's comment pages, arrives twice.
//
// The "stale-item" set has a previous state: created with { phase: "previous" }, the stories in
// its previously_assigned list are assigned too; with "current" (the default) they are gone.
//
// For practice only, a fault can be switched on (option `fault`, or the environment variable
// JIRA_PRACTICE_FAULT). The synchronization must refuse each one, writing nothing:
//   "empty-page"   claims more pages but sends an empty one
//   "wrong-total"  reports one story more than it sends
//   "repeat-page"  ignores startAt, sending the first page again and again, never the last
//   "comment-gap"  claims more comments but sends an empty comment page
//   "unsafe-key"   returns a story whose key is not a Jira key (it tries to leave the folder)
//   "shrinking-total" reports one story fewer on the last page, and leaves that story out
//   "missing-key"  returns a story with no key at all
//   "missing-summary" returns a story with no summary
//   "comment-no-id" returns comments with no id
//   "assignee-no-id" returns a story whose assignee has no account id
//   "comment-bad-body" returns a comment whose body is not text
// and one that is not refused but must stay harmless text:
//   "markdown-summary" gives a story a summary full of Markdown and HTML (a link, an image, a tag)
//
// It reads only the practice file and returns copies; it has no network access and writes
// nothing. Every address in its answers is under .invalid, a top-level domain reserved so it can
// never resolve: jira.example.invalid, and two other made-up names in the markdown-summary twist.
// The signed-in account below (ME) is the server's made-up user, as a real Jira knows its own
// users; the synchronization learns it only by asking myself().

import { readFileSync } from "node:fs";

export const FIXTURES = ["happy-path", "pagination", "stale-item", "duplicate-comment"];
const SITE = "https://jira.example.invalid";
const ME = { accountId: "fixture-account-0001", displayName: "Fixture User" };

export function fakeJira({ fixturesDir, fixture, phase = "current", fault = process.env.JIRA_PRACTICE_FAULT ?? "" }) {
  const FAULTS = ["", "empty-page", "wrong-total", "repeat-page", "comment-gap", "unsafe-key", "shrinking-total", "missing-key", "missing-summary", "comment-no-id", "assignee-no-id", "comment-bad-body", "markdown-summary"];
  if (!FAULTS.includes(fault)) throw new Error(`unknown practice fault ${JSON.stringify(fault)}`);
  if (!FIXTURES.includes(fixture)) throw new Error(`unknown practice set ${JSON.stringify(fixture)}`);
  if (phase !== "current" && phase !== "previous") throw new Error(`unknown phase ${JSON.stringify(phase)}`);
  const data = JSON.parse(readFileSync(`${fixturesDir}/${fixture}.json`, "utf8"));
  const stories = [...data.stories, ...(phase === "previous" ? data.previously_assigned ?? [] : [])]
    .sort((a, b) => a.key.localeCompare(b.key, "en", { numeric: true }));
  const storyPage = fixture === "pagination" ? 2 : 50; // the server's own limit
  const commentPage = 2;
  let calls = 0;

  // A story as Jira's search returns it: identity and fields, with Jira's own field names.
  const issue = (s, n) => {
    const it = {
    id: String(10000 + n),
    key: fault === "unsafe-key" && n === 0 ? `../${s.key}` : s.key,
    self: `${SITE}/rest/api/3/issue/${10000 + n}`,
    fields: {
      summary: fault === "markdown-summary" && n === 0
        ? `${s.summary} [click me](https://phish.example.invalid) ![x](https://img.example.invalid/x.png) <b>bold</b> *star*`
        : s.summary,
      status: { name: s.status },
      issuetype: { name: "Story" },
      priority: { name: "Medium" },
      assignee: { accountId: ME.accountId, displayName: ME.displayName },
      labels: [],
      description: null,
      parent: null,
      created: "2026-09-01T09:00:00.000+0000",
      updated: "2026-09-15T09:00:00.000+0000",
      // A field only this platform has; it is kept, but apart from the normal fields.
      customfield_10016: 3,
    },
    };
    if (n === 0 && fault === "missing-key") delete it.key;
    if (n === 0 && fault === "missing-summary") delete it.fields.summary;
    if (n === 0 && fault === "assignee-no-id") it.fields.assignee = { displayName: ME.displayName };
    return it;
  };

  return {
    calls: () => calls,
    myself() {
      calls++;
      return structuredClone(ME);
    },
    searchAssigned({ startAt = 0, maxResults = 50 } = {}) {
      calls++;
      const size = Math.max(0, Math.min(maxResults, storyPage));
      if (fault === "repeat-page") startAt = 0;
      let page = stories.slice(startAt, startAt + size).map((s) => issue(s, stories.indexOf(s)));
      if (fault === "shrinking-total" && startAt > 0) {
        // The last page claims a smaller total and leaves one story out.
        page = page.slice(0, -1);
        return { startAt, maxResults: size, total: stories.length - 1, isLast: true, issues: page };
      }
      const total = stories.length + (fault === "wrong-total" ? 1 : 0);
      const isLast = fault === "empty-page" || fault === "repeat-page" ? false : fault === "wrong-total" ? startAt + page.length >= stories.length : startAt + page.length >= total;
      return { startAt, maxResults: size, total, isLast, issues: page };
    },
    comments(key, { startAt = 0 } = {}) {
      calls++;
      const s = stories.find((x) => x.key === key);
      const all = (s?.comments ?? []).map((c, n) => ({
        ...(fault === "comment-no-id" ? {} : { id: c.id }),
        author: { displayName: c.author },
        body: fault === "comment-bad-body" && n === 0 ? { unexpected: ["not", "text"] } : c.body,
      }));
      if (fault === "comment-gap" && all.length > 0) return { startAt, maxResults: commentPage, total: all.length, isLast: false, comments: [] };
      const page = all.slice(startAt, startAt + commentPage);
      return { startAt, maxResults: commentPage, total: all.length, isLast: startAt + page.length >= all.length, comments: page };
    },
  };
}
