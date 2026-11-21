# Tag scheme for the Tixly Playwright tests

Every test carries exactly one tag from each of the five dimensions below, and may carry one suite
tag. No other tag is allowed; `tests/playwright/tools/tagging-check.ts` checks every test against
this list. A word starting with `@` in a test's title is a tag too (Playwright counts it), so
titles don't use `@`. Decisions by Tom Carter; wording drafted with Claude (Claude Code), 11-12-2026.

## 1. Feature: which part of the app the test checks
| Tag | Means |
|---|---|
| `@events` | The events page: events, prices, choosing tickets, the running total. |
| `@order-review` | The review page: the summary of an order before it is saved, and its messages. |
| `@saved-orders` | Saving, listing and cancelling orders: the save form, "Your orders", the orders service. |

## 2. Risk: what a buyer would lose if what the test checks broke
| Tag | Means |
|---|---|
| `@risk-high` | Money is wrong, or an order is lost, wrongly kept or belongs to the wrong buyer. |
| `@risk-medium` | The buyer is blocked or misled, but no money or order is lost. |
| `@risk-low` | Cosmetic or wording only, or a check of the tests' own helpers that no buyer uses. |

## 3. Read or write: whether the test changes saved data
| Tag | Means |
|---|---|
| `@writes-data` | The test saves, changes or cancels data, in its steps, its setup or its cleanup, or would if the app were broken (a test that expects a save to be refused). Never run against a shared environment. |
| `@read-only` | Everything else. |

## 4. Layer: where the test works
| Tag | Means |
|---|---|
| `@layer-ui` | The screen only (cleanup behind the scenes doesn't count). |
| `@layer-api` | The orders service only, with no browser. |
| `@layer-mixed` | The orders service for setup or checks, around a behavior on the screen. |

## 5. Duration: how long the test may take
| Tag | Limit | Means |
|---|---|---|
| `@fast` | 2 seconds | Run on every change. |
| `@slow` | 30 seconds (Playwright's limit for one test) | Longer; run less often. |

A test's duration is its longest attempt in Playwright's report, on this computer, with the demo
app's simulated delay off. The check names any test over its tag's limit.

## Suite (optional, at most one): which quest experiment a test belongs to
| Tag | Means |
|---|---|
| `@locator-comparison` | The brittle and stable locator tests. |
| `@data-isolated` | The tests that own their data. |
| `@data-coupled` | The deliberately coupled pair. |
| `@api-assisted` | The API-assisted cancel test. |
| `@ui-only` | The UI-only cancel test. |

They keep the README's `--grep` commands for those experiments working; they say nothing about the
app. Only a table row's first cell defines a tag; a tag mentioned anywhere else is an example.
Choose a set with `--grep @fast`, or `--grep-invert @writes-data` against a shared environment.
