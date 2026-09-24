# Validator Contract

## Purpose

Validators establish objective facts about participant artifacts and executions. They support review but do not replace human judgment or grant reviewer-verified status.

## Registry model

Every executable validator is registered by a stable ID. Quest content references that ID and cannot supply a command.

Conceptual registry entry:

```yaml
id: validate-jira-read-assigned
version: 1
display_name: Validate Jira assigned-story synchronization
runner: python
entrypoint: validators.jira_read_assigned:run
working_directory: participant
timeout_seconds: 60
max_output_bytes: 20000
parameters:
  fixture_set:
    type: enum
    allowed: [happy-path, pagination, stale-item, duplicate-comment]
environment_allowlist:
  - JIRA_BASE_URL
read_roots:
  - participant/skills/jira-read-assigned
  - participant/context/jira
  - validators/fixtures/jira
write_roots:
  - participant/evidence/jira-read-assigned-stories
network:
  default: denied
result_schema: schemas/validation-result.schema.json
```

The exact registry storage format is an implementation decision. The policy is not.

`max_output_bytes` is capped at 20000, which is what `output_excerpt` holds in
`schemas/validation-result.schema.json`. A larger number could be declared and never
honoured: the excerpt was written at the declared size and the whole result — a
passing run included — was then refused for breaking its own schema. Output past the
cap is replaced by a truncation notice, and the notice is counted inside the budget.
A validator with more to say than that should summarize it in its checks.

## Required controls

- Registry ID lookup occurs server-side.
- Entrypoints and fixed arguments are program-owned.
- Participant input is validated by type and allowlist.
- No request supplies a shell command string.
- Working directory is explicit.
- Read and write roots are explicit.
- The attempt under validation is explicit. A validator receives the evidence package of
  that attempt and judges it by identifier, never by picking the newest file under
  `participant/evidence` (round 7, `Workspace.attempt_files`).
- Resolved symbolic links cannot escape roots.
- Environment is constructed from an allowlist.
- Time and output limits are mandatory. Output is read as it arrives and a run that
  writes more than 1 MiB on either stream is stopped, so the limit applies before the
  output is held in memory, not after.
- Interrupted validators produce an interrupted or inconclusive result. A run whose checks
  were all `skipped` is `inconclusive`: nothing was checked.
- A child that exits with a nonzero status is `environment_failure`, whatever it printed
  first: exit status is not separable from the result, and a process that considered
  itself to have failed is not trusted to have reported anything reliably.
- The process group is terminated when the validator exits and on timeout, so nothing it
  started outlives the run — always by the time the run returns, not only when the direct
  child happens to die on its own signal.
- The child's import path starts at the repository, never at its working directory, so a
  file in `participant/` cannot stand in for a registered validator or a standard module.
- Results are written atomically.
- Output is redacted before persistence or display.

## What these controls are not

Validators are program-owned code, reviewed like the rest of the application. The controls
above bound what a validator does through the `Workspace` it is handed and the process it
runs in. They are not an operating-system sandbox:

- `network: denied` is a declaration, recorded in every result. Nothing blocks a socket.
  Every shipped validator is written to make no connection, and review is what holds that.
- Read and write roots are enforced by `Workspace`. A validator that calls `open()`
  directly is not stopped.
- A process that leaves the validator's process group by starting a session of its own is
  not killed with it.

Enforcing any of these would need an isolation layer (namespaces, a container, seccomp)
that release one does not have. A validator taken from anywhere but this repository is
outside what this contract covers.

## Result semantics

Overall outcomes:

- `pass` — required checks passed.
- `fail` — participant artifact or behavior failed a required check.
- `warning` — core checks passed but material advisories remain.
- `environment_failure` — the validator could not evaluate due to environment/setup.
- `inconclusive` — evidence was insufficient to classify.
- `interrupted` — execution did not complete.

A failed validator is not automatically a failed quest. A reviewer considers its purpose, reliability, and supporting evidence.

## Check design

Every check should state:

- what it evaluated;
- why that matters;
- the outcome;
- the evidence observed;
- severity when not passing;
- an actionable next step where possible.

Avoid checks that merely restate file existence when the quest is about behavior. Avoid probabilistic AI classification as the sole blocker unless the policy includes human confirmation.

## Validator quality tests

Every validator requires:

- a known-good fixture;
- one fixture per important failure mode;
- environment-failure coverage;
- timeout/interruption coverage when external processes are used;
- redaction coverage;
- path and parameter abuse coverage;
- false-positive and false-negative review;
- documented limitations.

## AI-assisted evaluation

An AI evaluator may produce advisory findings when judgment is useful, but:

- its prompt, model, inputs, and rubric version are recorded;
- untrusted repository content is delimited and treated as data;
- deterministic checks run separately;
- the AI cannot execute instructions discovered in evidence;
- a human reviewer confirms any verification decision;
- reruns may differ and the limitation is visible.
