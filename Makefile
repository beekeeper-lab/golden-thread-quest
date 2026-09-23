# Local commands. CI runs exactly these targets, so a green `make check` means a green CI.
.DEFAULT_GOAL := help
PYTHON ?= python3
VENV := .venv
BIN := $(VENV)/bin

.PHONY: help setup setup-ui format format-check lint typecheck secret-scan yaml-safe test test-ui build serve validate-content update-check migrate clean check

help: ## Show available commands
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  %-16s %s\n", $$1, $$2}'

setup: ## Create the virtual environment and install the project with dev extras
	uv venv $(VENV)
	uv pip install --python $(BIN)/python -e ".[dev]"
	@echo "Activate with: source $(BIN)/activate"

setup-ui: ## Additionally install Playwright and its browser (needed for make test-ui)
	uv pip install --python $(BIN)/python -e ".[dev,ui]"
	$(BIN)/playwright install chromium

format: ## Rewrite code to the project style
	$(BIN)/ruff format quest_app validators tests tools

format-check: ## Fail if code is not formatted
	$(BIN)/ruff format --check quest_app validators tests tools

lint: ## Static lint
	$(BIN)/ruff check quest_app validators tests tools

typecheck: ## Strict type checking
	$(BIN)/mypy

secret-scan: ## Fail if a secret-like value is tracked in the repository
	$(BIN)/python tools/secret_scan.py

yaml-safe: ## Fail if YAML is parsed with anything but safe_load (ADR-025)
	$(BIN)/python tools/check_yaml_safe.py

test: ## Run every test except the browser-driven ones
	$(BIN)/pytest -m "not ui"

test-ui: ## Run the browser-driven tests (requires make setup-ui)
	$(BIN)/pytest -m ui

validate-content: ## Validate authored content and participant state without building
	$(BIN)/python -m quest_app.cli validate

build: ## Generate the site into generated/
	$(BIN)/python -m quest_app.cli build

serve: ## Build, then serve on 127.0.0.1 with the local action service
	$(BIN)/python -m quest_app.cli serve


update-check: ## Check whether it is safe to take upstream curriculum changes
	$(BIN)/python -m quest_app.cli update

migrate: ## Move participant/progress.yaml to the current schema, validating before and after
	$(BIN)/python -m quest_app.cli update --migrate

package: ## Export a participant-facing archive of tracked files only
	@rm -rf dist
	@mkdir -p dist
	git archive --format=tar.gz --prefix=golden-thread-quest/ \
	  -o dist/golden-thread-quest.tar.gz HEAD
	@printf 'dist/golden-thread-quest.tar.gz  %s  %s files\n' \
	  "$$(du -h dist/golden-thread-quest.tar.gz | cut -f1)" \
	  "$$(tar -tzf dist/golden-thread-quest.tar.gz | grep -vc '/$$')"

verify-package: package ## Prove the exported archive installs and builds on its own
	@rm -rf dist/verify
	@mkdir -p dist/verify
	tar -xzf dist/golden-thread-quest.tar.gz -C dist/verify
	cd dist/verify/golden-thread-quest && \
	  uv venv .venv && \
	  uv pip install --python .venv/bin/python -e ".[dev]" && \
	  .venv/bin/python -m quest_app.cli validate && \
	  .venv/bin/python -m quest_app.cli build
	@echo "clean-export install, validate and build: OK"

clean: ## Remove generated output and caches (never participant files)
	$(BIN)/python tools/clean.py --apply

check: format-check lint typecheck yaml-safe secret-scan test ## Everything CI runs
