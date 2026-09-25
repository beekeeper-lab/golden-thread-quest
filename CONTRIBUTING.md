# Contributing

## Setup from a clean clone

```bash
git clone <your fork> golden-thread-quest
cd golden-thread-quest
make setup            # creates .venv and installs the project with dev extras
source .venv/bin/activate
make check            # format, lint, types, YAML safety, secret scan, tests
```

`make setup` needs [uv](https://docs.astral.sh/uv/) and Python 3.10 or newer, which is the floor
`pyproject.toml` declares and CI tests. Everything else is installed into `.venv`, which is
gitignored.

Rebuilding the HTML user guide is a maintainer step, not one you need to take: the built
guide is committed at `artifacts/html/guides/user-guide.html`. It needs one more package,
because it re-encodes the diagrams (`uv pip install -e '.[docs]'`), and two stylesheets that
are not in this repository — `base.css` and `print.css` from the authoring tool the guide was
written with. Point `GTQ_HTML_SNIPPETS` at a directory holding those two files, then run
`python scripts/build_user_guide_html.py`. There is no fallback location: if the variable is
unset, or set to a directory missing either file, the script says so and stops.

Browser-driven tests need one extra step, because they download a browser:

```bash
make setup-ui
make test-ui
```

Optional: `pre-commit install` runs the fast half of `make check` (format, lint, YAML safety,
secret scan) on every commit. Every hook in `.pre-commit-config.yaml` is also a Makefile target
you can run yourself, so nothing it does is hidden.

## Commands

Run `make` with no arguments to list them. `make check` is exactly CI's `check` job, target for
target, so a green `make check` locally means a green `check` job. CI also runs a `browser` job
(`make test-ui`) and a `clean-export` job (`make verify-package`), which `make check` does not
cover.

| Command | What it does |
|---|---|
| `make check` | Everything CI's `check` job runs |
| `make format` | Rewrite code to the project style |
| `make lint` | Static lint |
| `make typecheck` | `mypy --strict` |
| `make test` | Every test except the browser-driven ones |
| `make test-ui` | Playwright flows |
| `make validate-content` | Validate authored content and participant state without building |
| `make build` | Generate the site into `generated/` |
| `make serve` | Build, then serve on loopback with the local action service |
| `make clean` | Remove generated output and caches |

## Ownership zones

Three kinds of file live in this repository and the rules differ for each
(`docs/ARCHITECTURE.md`).

- **Program-owned** — `content/`, `schemas/`, `templates/`, `assets/`, `quest_app/`,
  `validators/`, `tools/`, most of `docs/`. Upstream may change these.
- **Participant-owned** — everything under `participant/`. Upstream never replaces it. Nothing in
  the application may write there outside the documented narrow operations, and `make clean`
  refuses to touch it. `tests/security/test_cleanup_safety.py` is what holds that promise.
- **Machine-owned** — `generated/` and `local-data/`. Disposable, reproducible, gitignored.

## Adding curriculum

Adding a quest must not require a change to Python, Jinja2, JavaScript, or CSS. If you find
yourself editing UI code to make new content appear, that is a defect in the application, not a
step in the process. See `docs/CONTENT-AUTHORING-GUIDE.md`.

## Rules that are not negotiable

These come from `docs/SECURITY-AND-PRIVACY.md` and `docs/DECISIONS.md`. A change that breaks one of
them is not merged, and most of them have a test that fails first.

1. YAML is read with `yaml.safe_load`. Never `yaml.load` (ADR-025, enforced by
   `tools/check_yaml_safe.py`).
2. No caller-supplied string is ever executed as a shell command. Validators run from a registry
   with fixed entrypoints and typed, allowlisted arguments (ADR-014).
3. No path arrives from the browser. Routes carry stable IDs that the server resolves.
4. Nothing marks work `verified` except a reviewer decision (ADR-011).
5. A validation run never changes participant state (ADR-017).
6. Secrets never enter content, evidence, logs, generated output, or Git. `make secret-scan` runs
   in CI.
7. No test, schema constraint, or acceptance criterion is weakened to make a build pass.

## Commits and branches

Work on a `feature|fix|chore/<name>` branch. Never commit directly to `main`.
