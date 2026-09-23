# Local Setup

## Requirements

| Requirement | Version | Why |
|---|---|---|
| Python | 3.10 or newer | ADR-019, as amended in round 4. Newer is fine; 3.10 is the floor because that is what the Cowork sandbox ships. |
| uv | any recent | Creates the environment and installs dependencies |
| Git | 2.30 or newer | The application reports repository status and the participant's work lives in Git |
| A modern browser | — | The generated site is ordinary HTML opened from disk or from the local service |

Nothing else is required to read the curriculum or browse generated pages. Browser-driven tests
additionally download Chromium through Playwright.

## Install

```bash
make setup
source .venv/bin/activate
```

## Verify the install

```bash
make check
```

This runs format verification, lint, strict type checking, the YAML-safety rule, the secret scan,
and the test suite. All of it works offline.

## Validate the curriculum

```bash
make validate-content
```

This loads every quest, region, badge and track, validates each against its published
schema, cross-checks references, and reports problems with the file, the field and a
suggested correction. Errors go to stderr and warnings to stdout, so a pipeline can separate
them; `--json` gives the same result machine-readably.

## Run the application

```bash
make build     # generates the site into generated/
make serve     # builds, then starts the loopback service
```

`make serve` binds to `127.0.0.1` only. It refuses any other bind address at startup and
exposes no route that accepts a filesystem path or a command
(`docs/SECURITY-AND-PRIVACY.md`). It prints the address to open; it does **not** print a
token. The pages it serves carry one, substituted as they are served, so the token never
reaches a file.


Generated pages are readable without the service running and without JavaScript. With the service
down, browsing still works and state-changing controls are disabled with an explanation rather than
pretending to succeed.

## Where your work lives

| Path | Owner | Committed |
|---|---|---|
| `participant/` | You | Yes — this is your portfolio |
| `content/`, `schemas/`, `templates/`, `assets/`, `quest_app/`, `validators/` | The program | Yes |
| `generated/` | The machine | No — rebuild it |
| `local-data/` | The machine | No — caches and raw private responses |

`make clean` removes only the machine-owned paths. It refuses to remove anything under
`participant/`, and a test proves it.

## Environment configuration

Copy `.env.example` to `.env` and fill in what you need. `.env` is gitignored. The application reads
credentials from the environment or from an authenticated CLI and never stores them, never writes
them to evidence or logs, and never sends them anywhere you did not ask it to.

## Troubleshooting

**`make setup` cannot find uv.** Install it from <https://docs.astral.sh/uv/> or create the
environment yourself with `python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"`.

**`make test-ui` fails with a missing browser.** Run `make setup-ui`, which installs Playwright and
downloads Chromium.

**The secret scan fails on a file you know is safe.** It reports a pattern and a truncated excerpt,
never the value. If the value really is documentation, use one of the placeholder forms the scanner
recognizes (`<your-token>`, `${VAR}`, `changeme`) rather than loosening the scanner.

## Why there is no lockfile

Dependency resolution floats within the ranges in `pyproject.toml`, and `make check` is the
gate that says whether your resolution is sound. This is deliberate. A lockfile would pin a
resolution produced on one maintainer's machine and hand a participant on a different Python
patch a resolution failure instead of a working install, which is a worse first experience
than a version drift the test suite would catch anyway.

The trade is real: a future dependency release can break a previously working setup. `make
check` is how you find out, and it runs entirely offline in a few minutes.
