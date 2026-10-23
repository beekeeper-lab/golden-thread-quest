---
id: playwright-project-setup
version: 1
title: "Create a Documented Playwright Project"
summary: "Set up a Playwright project that another person can clone, install and run from the documentation alone, with secrets kept out."
region: playwright-labyrinth
level: builder
xp: 30
estimated_minutes: 90
order: 40
tags:
  - playwright
  - setup
  - documentation
tools:
  - Markdown
  - YAML
bookend: foundation
risk:
  external_write: false
  sensitive_data: true
  notes: "The project targets a practice or local application."
prerequisites:
  - base-camp-repository-safety
outcomes:
  - "Create a project with a pinned configuration."
  - "Document setup so a stranger can run it."
  - "Keep credentials and generated output out of source control."
proof:
  required:
    - id: dependency-lock
      type: file
      description: "Provide the package manifest and lockfile showing pinned versions."
      path: participant/tests/playwright/package.json
    - id: setup-doc
      type: file
      description: "Provide the setup document: prerequisites with versions, install, run, where the target URL is set, how credentials are supplied, and what to do when the first run fails."
      path: participant/tests/playwright/README.md
    - id: config
      type: file
      description: "Provide the Playwright configuration showing the base URL taken from the environment, the browsers, retries set to zero or justified in a comment, and the output folder."
      path: participant/tests/playwright/playwright.config.ts
    - id: clean-run
      type: command-record
      description: "Save the redacted output of following the setup document from a clean checkout in a new folder, through to a passing run of one smoke test."
      path: participant/evidence/playwright-project-setup/attempt-001/logs/clean-run.txt
    - id: ignore-check
      type: command-record
      description: "Save the output showing that generated reports, traces, browser downloads and any environment file are ignored by Git, and a scan of the repository for credentials finding none."
      path: participant/evidence/playwright-project-setup/attempt-001/logs/ignore-check.txt
    - id: check-script
      type: file
      description: "Provide the script that produced the check output, so a reviewer can read what it tests."
      path: participant/tests/playwright/tools/project-setup-check.ts
    - id: proof-narrative
      type: file
      description: "Explain your approach, your choices and anything you could not do, citing the acceptance criteria by number."
      path: participant/evidence/playwright-project-setup/attempt-001/PROOF.md
author: Golden Thread maintainers
last_reviewed: "2026-10-20"
---

# Create a Documented Playwright Project

## Mission

Build the project so a stranger can run it from the README. Everything environment-specific comes from configuration, and nothing generated or secret is committed.

## Scenario

A new tester joins and spends two days getting the suite to run, because the setup was in one person's head and the target URL was hard-coded to their laptop.

## Acceptance criteria

1. The setup document lists every prerequisite with versions.
2. Following the document on a clean checkout reaches a passing smoke test.
3. The target URL comes from configuration, not from test code.
4. Credentials come from the environment and appear nowhere in the repository.
5. Reports, traces and downloads are ignored by Git.
6. Dependency versions are pinned.
7. The document says what to do when the first run fails.

## Required evidence

Provide the document, the configuration and the two records. In your `PROOF.md`, describe what broke when you followed your own document from scratch, citing the acceptance criteria by number.

## Safety constraints

- Test only an application you run yourself, such as a local demo app in your own folder or container that you may change and reset; never a public site, a production system or one holding real customer data.
- Do not put a real login, token or session cookie in a test, a log, a trace or a screenshot.
- Do not commit a generated report or trace.

## Hints

Follow your own README in a fresh folder before you call it done.

## Reflection

What is the first thing a new teammate would still get stuck on?

## Stretch goals

- Add a command that checks the environment before running.
- Run the setup on a second operating system.
