# Writing a Validator

## The boundary

A validator is a Python callable named in `validators/registry.yaml`. Quest content
references it by stable ID and can never supply a command, an argument, a path or an
environment variable. Those all live in the registry, which is program-owned and reviewed
like code.

This is why there is no injection surface: there is no argument string anywhere between a
request and a running validator.

## Registering one

```yaml
- id: validate-something
  version: 1
  display_name: Something worth checking
  description: >-
    What this establishes, in a sentence a participant would recognise.
  entrypoint: validators.something:run
  working_directory: participant
  timeout_seconds: 60
  max_output_bytes: 200000
  parameters:
    fixture_set:
      type: enum
      allowed: [happy-path, edge-case]
      default: happy-path
  environment_allowlist: []
  read_roots:
    - participant/skills/something
  write_roots: []
  network: denied
  quest_ids:
    - the-quest-this-belongs-to
```

Every field is a constraint the runner enforces. Note what is absent: there is no string
parameter type, because a free string is how an argument becomes an injection.

## Writing one

```python
def run(workspace: Workspace, output: ValidatorOutput) -> None:
    if not workspace.exists("participant/skills/something/main.py"):
        output.add(Check(
            id="entrypoint-exists",
            outcome="inconclusive",
            summary="There is nothing here to evaluate yet.",
            evidence="participant/skills/something/main.py is absent.",
            suggested_action="Write it, then run this again.",
        ))
        return
    ...
```

You get a `Workspace` and an `ValidatorOutput`. You do not get `open`, a path, or the
environment. Every `Workspace` call canonicalises and re-checks containment after symbolic
links are followed, so a link planted inside a read root is not a way out.

## Writing good checks

Each check states what it evaluated, why that matters, what it observed, and what to do.
`docs/VALIDATOR-CONTRACT.md` warns against checks that restate file existence when the quest
is about behaviour — look at what the file *says*, not whether it is there.

Choose the outcome honestly:

| Outcome | Means |
|---|---|
| `pass` | The check evaluated the work and it holds |
| `fail` | The check evaluated the work and it does not |
| `warning` | It holds, and there is something worth reading |
| `inconclusive` | You could not tell. **Not** a pass |
| `environment_failure` | You could not run. Not the participant's fault |

`inconclusive` never qualifies for `locally_validated`. Treating "we could not tell" as a
pass is the quietest possible way to make that state meaningless.

## Testing one

Every validator needs a known-good fixture, one fixture per important failure mode,
environment-failure coverage, redaction coverage, and a review for false positives and false
negatives. A validator that fails a participant for something they did correctly costs more
trust than one that misses a defect.

## What the runner does to you

Your process runs in its own process group with a constructed environment. A timeout kills
the group, not just you — so a child you spawned dies too. Output is capped, marked
truncated, and redacted before it is stored. An exception becomes an `environment_failure`,
never a `fail`, because a defect in the validator is not a defect in the work.
