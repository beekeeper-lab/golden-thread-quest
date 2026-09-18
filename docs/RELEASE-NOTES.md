# Release Notes — Pilot Candidate

**Version:** 0.1.0
**Date:** 2026-09-17
**Status:** pilot candidate, pending the final audit

## What this is

A local-first training application for The Golden Thread Quest. A participant works through
curriculum held as Markdown and YAML, assembles evidence as ordinary files in their own
repository, runs registered checks against it, and submits it to a reviewer who decides
whether it is verified.

Everything it knows lives in files. It reads them and writes a narrow, documented set of
them. It does not own them.

## What works

- **Curriculum as content.** Adding a quest is one Markdown file. It appears in its region,
  the catalog, the filters, its tag page, the search index, the relationship graph and the
  prerequisite calculation with no change to Python, Jinja2, JavaScript or CSS. A test
  asserts those three directories are byte-identical after a quest is added.
- **Content that does not validate is never published.** Schema and cross-document
  validation reports the file, the field, the rule in words, a redacted value and — for a
  mistyped stable ID — a suggestion. A failed build leaves the last good site standing and
  writes the errors as their own page.
- **Eleven screens**, generated deterministically. Two builds of the same inputs are
  byte-identical. The site works served and opened from disk.
- **A loopback-only service** for the things a static page cannot safely do, with a per-run
  token, origin checks, a body-size cap, and an action allowlist that no path or command
  crosses.
- **A validator framework** where a quest names a check by ID and can never supply a
  command, an argument or a path. Registered validators run in their own process group with
  a constructed environment, a timeout that kills the group, capped and redacted output.
- **Claimed and verified progress kept apart.** Nothing a participant does and nothing a
  validator returns can produce verified completion or verified XP.
- **Submissions and reviews** with the guards that make a decision mean something: a
  verification statement to approve, a finding to ask for changes, and a refusal to approve
  evidence that changed since it was submitted.
- **Updates that keep your work.** The update helper reports and stops; it runs no merge.
  In-progress attempts stay on the quest version they started.
- **Accessibility as checks, not intentions.** WCAG contrast computed from the tokens, axe
  over eleven pages with serious and critical impacts failing the build, four viewports,
  200% zoom, keyboard flows, and core content present with every script stripped.

## Numbers

| | |
|---|---|
| Tests | 491 under `make check`, plus 42 browser-driven under `make test-ui` |
| Screens | 11, plus tag pages |
| Schemas | 10 |
| Sample validators | 3, plus a probe used only to prove the timeout |
| Build budget, 203 quests | asserted under 60s; observed under 1s |

## Known limitations

These are real and deliberate. Each one is written down where it matters rather than only
here.

0. **The reviewer decision form needs the local service.** A reviewer reads everything from
   generated pages, but recording a decision writes files, so it happens through the running
   service like every other state change.

1. **Reviewer provenance is conventional, not cryptographic** (ADR-030). A reviewer is
   identified by the display name in the record and by Git history. A participant with write
   access to their own repository could author a record naming someone else. Every
   *internally inconsistent* claim is refused; the remaining gap is social. If your program
   needs more, review through pull requests so the Git history carries the identity.
2. **Environment Health reports build-time facts, not live ones.** A generated page cannot
   inspect the machine at the moment it is read. Live checks arrive with the service.
3. **Reviewer-awarded badges cannot yet be awarded.** There is no badge-award record type, so
   meeting the criteria shows as "pending". Granting one by arithmetic would be exactly the
   blurring of authority the product exists to prevent.
4. **Validator isolation is policy plus process boundaries**, not a container or seccomp. The
   architecture permits adding one without changing quest content.
5. **Catalog filtering needs JavaScript.** A static page cannot filter itself. The routes
   that work without it are real pages: regions and tags, linked from every card and quest.
6. **No coverage reporting** and **no glossary content type** (D1, D2).
7. **Clean-clone installation is not tested automatically.** It needs a fresh checkout and a
   network install, which the suite deliberately does not do.

## For the pilot cohort

Start with `docs/guides/PARTICIPANT.md`. Reviewers should read
`docs/guides/REVIEWER.md`, particularly the provenance section — it says plainly what the
application does and does not guarantee about who approved what.

## Upgrading

There is nothing to upgrade from. Schema version 1 is the first. The migration machinery
exists already because the first real migration is the wrong moment to be designing the
safety around it.
