# Repository ownership

This is my copy of the Golden Thread Quest. It holds three kinds of files: the program's, mine, and files a machine builds. Each kind has an owner, and the table further down says who may change what.

For more detail, see `docs/guides/PILOT.md` (how I do and hand in a quest), `docs/guides/PARTICIPANT.md` (what the application writes) and `docs/guides/REVIEWER.md` (how a reviewer records a decision).

## The three zones

### 1. Program-owned: read, do not change

The curriculum, the application and its checks. The Golden Thread Quest maintainers own these and change them in their own repository (`upstream`). I read them but never edit them, and they never go into my hand-in.

- Curriculum and its rules: `content/`, `schemas/`, `templates/`, `assets/`, `artifacts/`, `fixtures/`
- The application and its checks: `quest_app/`, `validators/`, `tests/`, `tools/`, `scripts/`, `vendor/`, `prototype/`
- Documentation: `docs/`, `README.md`, `CONTRIBUTING.md`, `CLAUDE.md`, `HANDOFF-PROMPT.md`, `PACKAGE-MANIFEST.md`, `PLANNING-STATUS.md`, `IMAGE-PLAN.md`, `VALIDATION-REPORT.md`, `LICENSE`, `LICENSE-CONTENT`
- Setup and configuration: `Makefile`, `pyproject.toml`, `install.sh`, `.env.example`, `.gitignore`, `.gitattributes`, `.pre-commit-config.yaml`, `.github/`, `.claude/` (except the two ignored local files listed under zone 3)

### 2. Participant-owned: mine, and committed when I hand in

Everything under `participant/`. This is the only folder that goes into my pull request: `gtq hand-in` stages `participant/` and nothing else.

Inside it, some files are mine to write and some are written by the application:

- **I write:** `participant/context/` (notes like this one), and in each evidence folder, `PROOF.md`, `logs/` and `screenshots/`
- **The application writes, so I do not hand-edit:** `participant/progress.yaml`, `participant/ACTIVITY.md`, and the validation, submission and review records inside `participant/evidence/`

### 3. Generated or private: never committed

These are ignored by Git (see `.gitignore`). Generated files can be deleted and rebuilt with `make build`. Private files must never leave this machine.

- **Generated output:** `generated/`, `generated.lock`, `generated.building/`, `generated.previous/`, `dist/`
- **Private runtime data:** `local-data/`, which holds local data, caches and raw responses from outside systems
- **Credentials:** `.env` and `.env.*` (but `.env.example` is committed, because it holds no real values), plus key, token and credential files such as `*.pem`, `*.key`, `*.token`, `credentials.json`, `.netrc` and any `secrets/` folder
- **Local tooling:** `.venv/`, `*.egg-info/`, `uv.lock`, `node_modules/`, Python caches (`__pycache__/`, `.pytest_cache/` and similar), `.claude/settings.local.json`, `.claude/worktrees/`
- **Short-lived locks:** `participant/.progress.lock`, held by the application only while it is saving
- **Editor and system files:** `.DS_Store`, `.idea/`, `.vscode/`

## Who may change what

| Actor | May change | Must not change |
|---|---|---|
| **Me (the participant)** | `participant/context/`; `PROOF.md`, `logs/` and `screenshots/` in my evidence folders | Program-owned files. `progress.yaml`, `ACTIVITY.md` and validation or review records (the application writes those). |
| **The application** (`gtq start` and its web pages) | `participant/progress.yaml`, `participant/ACTIVITY.md`, the records inside `participant/evidence/`, and `generated/` | Anything else. It never commits, pushes, merges or deletes my files. |
| **The AI agent** (Claude, working in this folder) | Only the files I ask for, and only inside `participant/context/` or my current evidence folder | Program-owned files, the application's files, `local-data/` and credential files. It does not commit, push or run `gtq hand-in` unless I ask. |
| **`gtq hand-in`** (run only by me) | Commits `participant/`, pushes my branch and opens or updates my pull request | Anything outside `participant/`. It never merges. |
| **The reviewer / pilot lead** | Records a decision through the application, then commits `participant/` and pushes to my branch | Never merges my pull request into the program's `main`. |
| **Program maintainers** | Program-owned files, in the program's own repository | My `participant/` folder |

The rule for the AI agent is my own rule for this quest, not something the application enforces. The rest come from the guides listed at the top.

## Before committing

`git status` should show changes only under `participant/`. If anything else shows up, stop and find out why before handing in.
