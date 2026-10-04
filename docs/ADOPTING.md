# Adopting the reference harness

This document is for an engineer who wants a harness this week. It describes the Python package in this repository.

It is not part of the OSAHI specification. The spec standardizes the contract: the run, the trajectory, capability decisions, state, checkpoints, recovery, and telemetry. Another implementation can ignore every file named here and still conform. `check_trajectory` reads a JSON trajectory. It does not load this configuration, and it does not import the harness.

Two profiles are provided. They differ by values in a JSON file. They do not select a second runtime.

## What you configure

A JSON object validated by `schemas/harness-config.schema.json`. Copy `profiles/startup.json` or `profiles/enterprise.json` and edit the fields. The loader fills omitted budget, retry, checkpoint, and telemetry values from the profile, then rejects the document before a run starts.

| Field | What you set |
| --- | --- |
| `spec_version` | `0.1.0`. A different version is rejected. |
| `profile` | `startup`, `enterprise`, or `custom`. |
| `model.provider`, `model.name` | Recorded on the run. The model object you pass to the builder produces the turns. |
| `workload.id`, `workload.name` | The task, independent of which model ran it. |
| `harness.name`, `harness.version` | Your harness identity. The reference name is `osahi-reference` / `0.1.0`. |
| `policy.policy_id`, `policy.allow` | The allowlist. A capability that is not listed is denied. The list is required. It may be empty, which denies every call. |
| `context.budget` | Scratchpad item budget. Minimum 2. Startup default is 8. Enterprise default is 4. |
| `recovery.max_retries` | Retry cap for an idempotent tool. Startup default is 2. Enterprise default is 1. |
| `recovery.checkpoints` | Must be `true`. The reference loop always writes checkpoints. This config cannot turn them off. |
| `telemetry.enabled` | Must be `true`. The reference loop always records the v0.1 telemetry attributes. |
| `metadata` | An object copied onto the run and onto `run.started`. Enterprise requires non-empty `owner` and `environment`. Startup does not. |

`python -m osahi.cli check-config <file.json>` exits 0 when the file is valid and 1 when it is not. The message names the field path, for example `context.budget` or `metadata.owner`.

## What you implement

Three adapters, and usually only the first:

1. **A tool function.** Wrap it in `ToolSpec(name, capability_id, fn, idempotent=True)`. `fn` receives the argument object and returns a JSON object. That object is stored as the tool output. Raise, or return `{"ok": False, "error": "..."}`, to record a failure. The builder does not read executables from JSON.
2. **A model adapter, if the scripted one is not enough.** Any object with `next_turn(context) -> dict` is enough. `kind` is `tool`, `finish`, or `human`. `ScriptedModel` is the in-process adapter. Do not add a provider SDK to this package.
3. **A policy, only when an allowlist is the wrong decision.** The builder installs `AllowlistPolicy` from `policy.allow`. A different policy is an object with `evaluate(capability_id)` returning `effect` (`allow` or `deny`), `reason`, and `policy_id`. Pass it as `policy=` to `build_harness`. You still do not write the loop.

A capability id in `policy.allow` with no registered tool is legal. The id is reserved: a later tool, or a later process, can provide it. A registered tool whose `capability_id` is absent from the allow list is also legal at build time. The policy denies that call at runtime, and the trajectory contains `tool.denied` with no `tool.invoked` for that call.

## What you do not rebuild

`build_harness` returns a `ReferenceHarness`. The package already owns:

- the turn loop
- the append-only event log and sequence numbers
- checkpoints after start, before each tool invocation, and on human pause
- retry, rollback, and escalation as new events
- L1 scratchpad compaction when the budget would overflow
- the conformance checker

Replace the harness later if you need to. Keep the JSON trajectory so the same checker still applies.

## Fifteen-minute path

From the repository root, with the package installed (`pip install -e ".[dev]"`):

1. Check the profile before you run anything:

   ```bash
   python -m osahi.cli check-config profiles/startup.json
   ```

2. Register one function and run the scripted echo:

   ```bash
   python examples/startup_echo.py
   ```

   That program loads `profiles/startup.json`, registers an echo function, runs a scripted tool turn and a finish turn, prints the status, and exits non-zero if `check_trajectory` rejects the log.

3. The same shape in your own process:

   ```python
   from osahi.build import build_harness
   from osahi.clock import FrozenClock
   from osahi.config import load_config
   from osahi.ids import SequentialIds
   from osahi.model import ScriptedModel
   from osahi.tools import ToolSpec

   def echo(arguments):
       return {"text": str(arguments.get("text", ""))}

   config = load_config("profiles/startup.json")
   harness = build_harness(
       config,
       tools=[ToolSpec("echo", "tool.echo", echo)],
       model=ScriptedModel(
           [
               {
                   "kind": "tool",
                   "text": "calling echo",
                   "tool_name": "echo",
                   "capability_id": "tool.echo",
                   "arguments": {"text": "hello"},
               },
               {"kind": "finish", "text": "echoed hello"},
           ]
       ),
       clock=FrozenClock("2026-10-04T04:30:00Z"),
       ids=SequentialIds(),
   )
   status = harness.run_until_blocked()
   ```

   `FrozenClock` and `SequentialIds` keep the trajectory reproducible. Omit them only when you accept wall-clock timestamps; the builder's default clock is frozen at the same instant the examples use, and the default identifiers are sequential.

4. Write `harness.events()` to a JSON file and check it the same way you would check a log from another language:

   ```bash
   python -m osahi.cli trajectory.json
   ```

## Startup and enterprise

| | Startup | Enterprise |
| --- | --- | --- |
| Profile file | `profiles/startup.json` | `profiles/enterprise.json` |
| Allow list | Small. The file allows `tool.echo`. | An explicit catalog. The file allows `tool.echo` and reserves `tool.audit`. |
| Context budget | 8 | 4, so the scratchpad compacts sooner |
| Retry cap | 2 | 1, then rollback because a checkpoint exists |
| Metadata | `{}` is valid | `owner` and `environment` are required and must be non-empty |
| Checkpoints | On. The schema rejects `false`. | On. Same rule. |
| Escalation | Available. Pass `recovery_policy` when a failure should end the run instead of rolling back. | Same hook. The built-in decision escalates only when no checkpoint exists, which this harness does not do after start. |
| Event schema | v0.1 trajectory | The same schema and the same checker |

`python examples/enterprise_audit.py` loads the enterprise profile, attempts a tool that is not on the catalog, then runs an allowed echo. The denied call has no `tool.invoked`. The allowed call completes. Workload, harness, and metadata on `run.started` are the values from the config.

`load_profile("startup")` and `load_profile("enterprise")` read those files. `custom` has the same safe defaults as startup (budget 8, retry cap 2, checkpoints on, telemetry on) and does not require `owner` or `environment`. There is no third runtime class.

## How conformance fits

Before you ship a change to a tool, a policy, or a model adapter, run the checker on the trajectory:

```bash
python -m osahi.cli path/to/trajectory.json
```

Exit 0 means the log satisfies the v0.1 rules (sequence, capability order, checkpoints, retry legality, telemetry). Exit 1 prints rule ids. The checker does not know whether the log came from `build_harness`, from `examples/echo_run.py`, or from another language. A config file is not a trajectory. Check it with `check-config`, not with the trajectory command.

Ship the trajectory, not a claim that the model was deterministic. v0.1 records the model and tool outputs that actually happened.
