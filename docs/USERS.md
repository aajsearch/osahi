# Who OSAHI is for

A product that is only a prompt box calling one model has nothing to conform. A team building a chatbot or assistant that must connect a model, hydrate context from tools, decide whether a call is allowed, and then answer the user or reach a goal is building an execution lifecycle. That lifecycle is the OSAHI surface: run, trajectory, capability decision, state, checkpoint, recovery, telemetry. OSAHI does not ship the chat UI, the prompt playground, or a finished assistant. It gives that team the contract and a replaceable reference loop so the orchestrator is not a private script.

The normative contracts are in `spec/`. The reference-package steps are in [ADOPTING.md](ADOPTING.md). Later phases are in [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md).

## Who has a job in v0.1

**Startup engineer building an internal agent or assistant orchestrator.** This includes the person building the orchestrator behind a chatbot or assistant. Their v0.1 path is the reference package: `profiles/startup.json`, `build_harness`, and the checker. They register tool functions, run the loop, and keep the JSON trajectory.

**Enterprise platform team.** They adopt the spec and the checker. `profiles/enterprise.json` is a prototype of that adoption: a stricter budget, a lower retry cap, and required `owner` and `environment` on the run. It is not a control plane, an IAM system, or a hosted environment.

**Security and audit.** They use the checker only. A denied call is `capability.decided` with effect `deny`, then `tool.denied`, and no `tool.invoked` for that call. The checker records that the decision happened. It does not enforce a sandbox.

**Evaluation researchers.** They can archive a run labeled by model, harness, and workload now. A runner that compares two models or two harnesses on the same workload is Phase D. It is not in this repository.

**Agent-framework and orchestrator authors.** Their success is JSON that passes `check_trajectory`. The Python loop in `src/osahi` is a reference. It is replaceable. They do not have to adopt `ReferenceHarness` as their runtime.

**Deferred.** MCP hosts, workflow engines, and model providers have no v0.1 adoption step. They show up when the gateway, durable log, and live model adapter exist (Phases B and C). v0.1 does not ask them to integrate.

## Use cases, today and later

| Job | Today | Later |
| --- | --- | --- |
| Record an in-process tool call as a conforming run | `examples/startup_echo.py`, or the same shape with `build_harness`, writes a trajectory the checker accepts. The model is scripted. Tools are functions in the process. | A live model adapter, MCP tools, and a crash-safe log (Phases B and C). |
| Deny a call and attach an owner | `examples/enterprise_audit.py` denies a tool that is not on the allow list and copies `owner` and `environment` onto the run. That is a log. | Enforced IAM or WASM constraints, an OTLP export, and a durable store (Phases B and C). |
| Run your own runtime | Emit the v0.1 trajectory and pass the same checker. Profiles are irrelevant. | Same checker. |
| Score someone else's trajectory | `python -m osahi.cli path/to/trajectory.json`. Exit 0 accepts. Exit 1 prints rule ids. The checker does not load a profile or call a model. | Same checker. |
| Archive a run for evaluation | Keep the JSON. The run already names model, harness, and workload. | A comparison runner that executes one workload across two models or two harnesses (Phase D). |

## Three ways to use it

**Path A — reference package.** Check the settings file, register tools, build the harness, run until blocked, then check the trajectory.

```bash
python -m osahi.cli check-config profiles/startup.json
```

In process: `ToolSpec(name, capability_id, fn)`, `build_harness`, `run_until_blocked`, then `check_trajectory` on `events()`. A model turn with `kind` `human` pauses the run (`human.requested`, a checkpoint, `run.paused`). `resume(text)` appends `human.responded` and `run.resumed` and continues. The steps are written out in [ADOPTING.md](ADOPTING.md).

**Path B — your own runtime.** Implement the contract in another language or framework. Ignore `profiles/` and `schemas/harness-config.schema.json`. Emit a JSON trajectory and run only the checker. Conformance does not import the reference harness.

**Path C — publish or consume trajectories.** No profile, no tools, no model. An auditor or a researcher takes a log that already exists and scores it, or stores it. The checker is the whole interface.

## What they need, and what still blocks production

A conforming run needs a workload id so the task is separate from the model and the harness. Path A also needs an allow list (`policy.allow`, which may be empty) and the tool functions those calls will execute. The builder does not read executables from JSON.

They do not need a specific model, an API key, a cloud account, a database, or a particular agent framework. The reference model is scripted. The clock and identifiers can be injected. The test suite runs with no network.

What still blocks a production assistant on this repository alone:

- no live model adapter
- no MCP router
- no OTLP export
- no crash-safe log
- no sandbox isolation
- no chat UI

They can adopt the contract and the checker now. They cannot operate a production assistant on this repository alone.

## Who it is not for

It is not for a team that wants a finished chat product, a prompt playground, or a hosted assistant they do not have to orchestrate. A prompt box that calls one model has no run, no trajectory, and no capability decision to conform.

It is not a replacement for MCP, a workflow engine, an OpenTelemetry backend, a vector store, or a sandbox. Those stay beside the lifecycle. OSAHI does not implement them.

It is not an orchestrator a framework author must adopt as their runtime. `ReferenceHarness` is one implementation. Their success is a trajectory that passes `check_trajectory`.

The builder of the chatbot's orchestrator is a user. The exclusion is the finished chat product and the prompt box, not the person who has to connect the model, hydrate context, decide the call, and then answer.
