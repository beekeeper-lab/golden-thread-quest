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
max_output_bytes: 200000
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

## Required controls

- Registry ID lookup occurs server-side.
- Entrypoints and fixed arguments are program-owned.
- Participant input is validated by type and allowlist.
- No request supplies a shell command string.
- Working directory is explicit.
- Read and write roots are explicit.
- Resolved symbolic links cannot escape roots.
- Environment is constructed from an allowlist.
- Time and output limits are mandatory.
- Interrupted validators produce an interrupted or inconclusive result.
- Process trees are terminated on timeout.
- Results are written atomically.
- Output is redacted before persistence or display.

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
