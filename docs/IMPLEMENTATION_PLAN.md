# OSAHI Implementation Plan

Status: v0.1 MVP is the scope of this repository's first milestone.
Source proposal: Open Standards Agent Harness Initiative (OSAHI).
Spec version targeted by the MVP: `0.1.0`.

This plan turns the proposal into a build sequence. The proposal's own constraint governs every cut: standardize the contract, not the implementation, and start from the smallest set of primitives that independent implementations can share.

## 1. Problem the plan is solving

An agent in production is not a prompt. It is a lifecycle:

```
model  →  tool decision  →  authorization  →  execution
       →  state change   →  failure        →  recovery
       →  human pause    →  resume         →  observation
```

MCP answers how a tool is connected. A2A answers how agents talk to each other. OpenTelemetry answers how spans are exported. A durable workflow engine answers how a process survives a crash. None of them answer, in a shared vocabulary:

- What constitutes one agent run?
- What is the ordered record of that run?
- What capability was requested, and what decision was made, before a tool ran?
- What state is recoverable, and from which checkpoint?
- Which recovery action was taken, and did it delete history?
- Which fields must every implementation emit so a trajectory can be compared across models and harnesses?

That missing layer is the "model × harness × workload" triad. The same model produces different reliability, cost, and safety outcomes under different harnesses. Without a shared run model, those outcomes cannot be compared, replayed, or certified.

OSAHI defines that layer as specifications, JSON Schemas, conformance tests, and one reference implementation that is allowed to be replaced.

## 2. Naming

The initiative keeps the proposal's name: **OSAHI**, the Open Standards Agent Harness Initiative.

The name is deliberate.

- It says *open standard*, not *platform*.
- It says *harness*, the execution wrapper around a model, not the model and not the application.
- It says *initiative*, because the durable artifacts are the spec and the conformance suite. The Python package is a reference, not the standard.

Repository: `osahi`. Spec version: `0.1.0`. Wire-format schema URNs use `urn:osahi:schema:v0.1:<document>`.

## 3. Principles that constrain the build

1. **Contract over runtime.** A second implementation must be able to satisfy the same tests without importing the reference harness's private objects. Conformance speaks JSON.
2. **Record nondeterminism; do not fake determinism.** Model text and live tool responses are stored on the event that observed them. Replay does not call the model again.
3. **The log is append-only.** Rollback, retry, and compensation are new events. They never rewrite or delete earlier events.
4. **Authorization is an event, not a side condition.** A tool invocation without a prior allow decision for the same call is a conformance failure.
5. **State is a projection.** The log is the source of truth. Working memory and the scratchpad are folded from events and can be folded again.
6. **Versions move forward.** A rollback restores snapshot *contents* and bumps `state_version`. The version counter never decreases.
7. **Unknown events are preserved.** An implementation MUST keep unrecognized event types in order and MUST NOT fail replay only because a type is unknown. It MUST NOT apply unknown types to the projection.
8. **No new dependency becomes a requirement of the standard.** The reference runtime may use Python, JSON Schema validation, and pytest. Those choices are not normative.

## 4. Normative surface of v0.1

Eight documents in `spec/`. Keywords follow RFC 2119.

| Document | Normative content |
| --- | --- |
| `00-overview.md` | Positioning, vocabulary, composition with MCP, A2A, OpenTelemetry, workflow engines |
| `01-agent-run.md` | Run identity, model/harness/workload refs, status machine |
| `02-trajectory.md` | Event envelope, sequence rules, event taxonomy |
| `03-capability.md` | Request → decision → invocation → audit |
| `04-state.md` | Projection rules, including rollback |
| `05-checkpoint-recovery.md` | Checkpoint snapshot, retry, rollback, escalate |
| `06-context.md` | L1 scratchpad and compaction event. L2/L3 named, not implemented |
| `07-telemetry.md` | Required attributes on model and tool events |
| `08-conformance.md` | What the checker MUST accept and MUST reject |

Machine-readable twins live in `schemas/`. If prose and schema disagree, the schema is the wire contract and the prose must be patched in the same change. Tests load every file in `schemas/examples/` and validate it.

### 4.1 Agent run

A run binds three coordinates so later evaluation can separate them:

- `model` — provider and name. v0.1's reference provider is `scripted`.
- `harness` — name and version of the execution substrate. Reference: `osahi-reference` / `0.1.0`.
- `workload` — the task identity, independent of which model ran it.

Status machine:

```
created → running → paused → running → completed
                  ↘ failed
                  ↘ cancelled
```

`created` exists only before `run.started` is appended. Once a terminal status (`completed`, `failed`, `cancelled`) is recorded, further lifecycle transitions are illegal. A terminal run's log remains readable.

### 4.2 Trajectory

Every event shares one envelope:

```json
{
  "event_id": "evt_0001",
  "run_id": "run_0001",
  "seq": 1,
  "type": "run.started",
  "at": "2026-10-04T04:30:00Z",
  "payload": {},
  "causation_id": null,
  "correlation_id": "run_0001"
}
```

Rules:

- `seq` starts at 1 and increases by 1 with no gaps. The log assigns `seq`. Callers do not choose it.
- `event_id` is unique within the log.
- `correlation_id` is the `run_id` for v0.1. Child runs are reserved and unused.
- `causation_id` points at the event that caused this one, or null for `run.started`.
- `at` is ISO-8601 UTC. Ordering authority is `seq`, not the clock.
- Payload values are JSON values.

Taxonomy for v0.1:

| Family | Types |
| --- | --- |
| Lifecycle | `run.started`, `run.paused`, `run.resumed`, `run.completed`, `run.failed`, `run.cancelled` |
| Model | `model.invoked`, `model.completed` |
| Tool and capability | `tool.requested`, `capability.decided`, `tool.invoked`, `tool.completed`, `tool.failed`, `tool.denied` |
| State | `state.updated`, `context.compacted` |
| Durability | `checkpoint.created`, `recovery.started`, `recovery.completed` |
| Human | `human.requested`, `human.responded` |

Extending the taxonomy is allowed. Breaking the envelope is not.

### 4.3 Capability

The only legal tool path is:

```
tool.requested
  → capability.decided   (effect = allow | deny)
  → tool.invoked         (only after allow)
  → tool.completed | tool.failed
```

A deny ends that call with `tool.denied` and MUST NOT be followed by `tool.invoked` for the same `call_id`.

The reference policy is an allowlist. The spec does not require an allowlist. It requires that some policy emit `capability.decided` before invocation. A later profile can map the same decision onto WASM capabilities or IAM.

### 4.4 State

`project(events)` is a pure function.

```text
state_version starts at 0
working_memory starts as {}
scratchpad starts as []
```

- `state.updated` merges `payload.patch` into `working_memory`, replaces `scratchpad` when `payload.scratchpad` is present, and increments `state_version`.
- `context.compacted` replaces `scratchpad` with `payload.retained` and increments `state_version`.
- `recovery.completed` with `action = rollback` copies `working_memory` and `scratchpad` from the named checkpoint's snapshot and increments `state_version`.
- Unknown event types do not change the projection.

### 4.5 Checkpoint and recovery

A checkpoint event carries the snapshot needed to restore contents:

```json
{
  "checkpoint_id": "ckpt_0001",
  "state_version": 1,
  "snapshot": { "working_memory": {}, "scratchpad": [] }
}
```

The reference harness writes a checkpoint after `run.started`, before each tool invocation, and on human pause.

Recovery actions:

| Action | Meaning | Model called again? |
| --- | --- | --- |
| `retry` | Re-invoke the same tool call. Legal only when the tool declares itself idempotent and attempts remain. | No |
| `rollback` | Restore the latest checkpoint's contents. Continue with the next model turn, which can see the failure in context. | Next turn only |
| `escalate` | Append `run.failed`. The run is terminal. | No |

Retry exhaustion falls through to rollback if a checkpoint exists, otherwise to escalate. The attempt count lives on the recovery events. It is not a hidden counter outside the log: the projection can count `recovery.completed` events with `action = retry` for that `call_id`.

### 4.6 Context

v0.1 implements one tier: the L1 scratchpad, a bounded list of items `{role, content}`.

When the next item would exceed the item budget, the harness drops the oldest items, retains a summary item `compacted N items`, emits `context.compacted`, then appends the new item via `state.updated`.

L2 episodic cache and L3 cold storage are named in the spec so the lifecycle has a place to grow. They have no reference code in v0.1. Introducing them later must not change L1 event shapes.

### 4.7 Telemetry

v0.1 does not export OTLP. It requires a `telemetry` object on model completion and on tool completion, failure, and denial:

```json
{
  "trace_id": "trace_0001",
  "span_id": "span_0002",
  "attributes": {
    "osahi.spec.version": "0.1.0",
    "osahi.run.id": "run_0001",
    "gen_ai.operation.name": "chat"
  }
}
```

Model events MUST include `gen_ai.request.model` and `gen_ai.operation.name = chat`.
Tool events MUST include `osahi.tool.name`, `osahi.capability.effect`, and `gen_ai.operation.name = execute_tool`.

Attribute names that already exist in the emerging GenAI semantic conventions are reused on purpose. OSAHI-specific names use the `osahi.` prefix so a later OTLP exporter can map them without renaming the log.

### 4.8 Conformance

`check_trajectory(events) -> list[violation]` is the portable checker. It reads dicts, not Python objects. It MUST flag at least:

1. A sequence that does not start at 1 or that skips or repeats.
2. Mixed `run_id` values in one trajectory.
3. Any event after a terminal lifecycle event.
4. `tool.invoked` without a prior `capability.decided` of `allow` for the same `call_id`.
5. `tool.invoked` after `deny` for the same `call_id`.
6. `checkpoint.created` missing `snapshot.working_memory` or `snapshot.scratchpad`.
7. `recovery.completed` rollback naming an unknown checkpoint.
8. Model or tool outcome events missing required telemetry attributes.
9. `retry` for a call whose tool event declared `idempotent: false`.

Fixtures in `conformance/fixtures/` cover an accepted allow-path and several rejected mutations. A test mutates a valid log on purpose so the checker cannot pass by returning an empty list unconditionally.

## 5. Reference runtime (replaceable)

Python 3.11+, one runtime dependency (`jsonschema`), tests via pytest. No network, no API keys, no clock reads from the wall unless a caller injects `SystemClock`.

```
src/osahi/
  clock.py         FrozenClock, SystemClock
  ids.py           SequentialIds
  errors.py
  log.py           append-only EventLog
  project.py       pure project()
  capability.py    AllowlistPolicy
  context.py       L1 budget and compaction
  telemetry.py     attribute builders
  recovery.py      retry / rollback / escalate decision
  tools.py         echo, add, flaky
  model.py         ScriptedModel
  harness.py       ReferenceHarness loop
  schema.py        load and validate JSON Schemas
  conformance.py   check_trajectory
  cli.py           check a fixture file
```

### 5.1 Loop

```
start
  append run.started
  append checkpoint.created
until status is terminal or paused:
  if scratchpad would overflow: compact
  ask the model for one turn
  append model.invoked, model.completed
  if finish: append run.completed and stop
  if human: append human.requested, checkpoint, run.paused and stop
  if tool:
      append tool.requested
      append capability.decided
      if deny: append tool.denied and continue
      append checkpoint.created
      append tool.invoked
      call the tool
      on success: append tool.completed and state.updated
      on failure: append tool.failed
                   decide recovery
                   retry in place, or rollback and continue, or escalate
resume(human_text)
  append human.responded, run.resumed
  continue the loop
```

The model adapter is a protocol with one method, `next_turn(context) -> dict`. `ScriptedModel` replays a list. A future adapter can call an HTTP API and still append the same events. The harness does not import a provider SDK.

### 5.2 Why these tools

| Tool | What it makes testable |
| --- | --- |
| `echo` | Allow path, state patch, telemetry |
| `add` | Arguments survive onto `tool.completed` and into working memory |
| `flaky` | Fails N times, then succeeds, so retry is visible in the log |
| a tool absent from the allowlist | Deny path with no `tool.invoked` |
| a tool with `idempotent = false` | Retry is illegal; the run escalates or rolls back |

### 5.3 Determinism hooks

Tests construct the harness with `FrozenClock` and `SequentialIds`. Given the same script, policy, tools, and budget, `events()` is byte-stable. That property is itself a test.

## 6. Test strategy

Every module lands with the tests that pin its contract. The suite is the MVP's definition of done.

| Layer | What is asserted | Network |
| --- | --- | --- |
| Schema | Examples validate. A run missing `run_id` does not. | No |
| Log | Append assigns `seq`. Duplicate ids and caller-chosen seq are rejected. No mutation API exists. | No |
| Projection | Fold matches a hand-computed memory and version. Rollback bumps version and restores contents. Unknown events are ignored by the fold and kept by the log. | No |
| Capability | Allow and deny effects, with reasons. | No |
| Context | Crossing the budget emits one compaction and a shorter scratchpad. | No |
| Recovery decision | Idempotent failure under the attempt cap returns retry. Exhaustion with a checkpoint returns rollback. A non-idempotent tool does not return retry. | No |
| Harness | Echo completes. Denied tool never invokes. Flaky tool retries then completes. Non-idempotent failure escalates. Pause then resume completes. Two runs with the same script match. | No |
| Conformance | Reference trajectories pass. Mutated trajectories fail with a specific rule id. CLI exit code matches. | No |

A change that weakens a rule must update `spec/08-conformance.md` in the same commit. The test name and the rule id share a prefix (`seq.`, `capability.`, `telemetry.`, `recovery.`, `checkpoint.`).

## 7. MVP definition of done

The milestone is done when all of the following are true:

1. Specs 00–08 and the JSON Schemas describe the same envelopes.
2. `pytest` passes from a clean virtualenv with no secrets and no network.
3. `examples/echo_run.py` prints a trajectory that `check_trajectory` accepts.
4. The conformance fixtures include both accepted and rejected logs.
5. README states the non-goals so v0.1 cannot be mistaken for an MCP proxy, a sandbox, or a workflow engine.
6. The reference harness is the only implementation, and the checker does not import it. A second runtime can target the checker later without a rewrite.

## 8. Roadmap after the MVP

The proposal's three horizons stay intact. v0.1 is the first slice of the short-term horizon, narrowed until the contracts are real.

### Phase A — Protocol slice (this repository, now)

Corresponds to the proposal's months 1–6, reduced to what can be tested without a network.

- Agent run, trajectory, capability, state, checkpoint, recovery, telemetry contracts
- JSON Schema and conformance checker
- Reference loop with a scripted model and in-process tools
- Human pause and resume
- L1 compaction

#### Reference configuration surface

Companies that want the reference loop, log, checkpoints, recovery, and checker configure `schemas/harness-config.schema.json` and pass tool functions into `build_harness`. That file is a convenience of this package. It is not a requirement of the specification, and a second implementation does not have to read it.

`check_trajectory` is unchanged. It still scores a JSON trajectory and does not import the config loader. Startup and enterprise are two JSON profiles (`profiles/startup.json`, `profiles/enterprise.json`) consumed by the same `ReferenceHarness`. The enterprise profile uses a smaller scratchpad budget (4), a lower retry cap (1), and required `metadata.owner` and `metadata.environment`. The unconfigured harness default remains the spec's reference retry cap of 2. Checkpoints stay on. Invalid settings fail in `load_config` with `ConfigError` before a run starts. See [docs/ADOPTING.md](docs/ADOPTING.md).

Exit: an independent reader can implement `project` and `check_trajectory` from the spec alone.

### Phase B — Gateway and real models (next)

The proposal's Open MCP Router, still behind the same capability events.

- MCP client adapter that discovers tools and maps each tool onto a `capability_id`
- Router process: register, authenticate, route. The harness still sees `tool.requested` / `capability.decided` / `tool.invoked`
- One commercial or local model adapter beside `ScriptedModel`
- OTLP exporter that maps `telemetry.attributes` without changing event names
- State store interface with an in-memory implementation and one durable implementation (SQLite is enough). The projection function stays pure; the store only persists the log

Exit: the same conformance fixtures pass against the in-process tools and against one MCP server.

### Phase C — Durable execution and isolation (proposal months 7–12)

- Event log on a durable workflow engine, with the engine behind the log interface. Temporal (or an equivalent) is an adapter, not a dependency of the spec
- Checkpoint snapshots written to that log, crash the process, resume by replaying
- Capability profile for a WASM runtime: the decision event gains `constraints` (`network`, `filesystem`) that a sandbox enforces. The event shape from v0.1 remains valid
- L2 episodic cache. Compaction can move dropped L1 items to L2 instead of only summarizing them

Exit: kill-and-resume demo, plus a tool call whose network constraint is actually enforced.

### Phase D — Trajectory evaluation (proposal months 12–24)

- Invariant library over logs: no deny-then-invoke, no state version regression, token ceiling, recovery bounded
- A runner that executes one workload across two harnesses or two models and emits a comparison of trajectories, not just final text
- Backtracking policy as data: when to retry, when to roll back, when to ask a human. The v0.1 decision function is the first policy, not the last

Exit: a published workload where two models are compared on trajectory invariants, and the comparison uses OSAHI events rather than framework-private traces.

## 9. Decisions already made

| Decision | Choice | Why |
| --- | --- | --- |
| Initiative name | OSAHI | It is the proposal's name, and it describes a standards effort. |
| First code | Python reference + JSON contracts | The contract is JSON so the language of the reference runtime is not the standard. |
| Model in v0.1 | Scripted | The MVP must be testable in CI without keys, quotas, or flakes. |
| Ordering | `seq`, not timestamps | Clocks skew. Replay must not depend on them. |
| Rollback | New events, version increments | Deleting history makes conformance unverifiable. |
| Isolation | Capability decision only | Shipping a microVM in v0.1 would freeze a technology into the standard. |
| License | Apache-2.0 | Spec and reference code need patent and copyright terms that allow reimplementation. |

## 10. Risks

| Risk | Mitigation in v0.1 |
| --- | --- |
| The spec grows into a framework | Non-goals are in the README. New runtime features need a spec delta and a conformance rule, or they stay as examples. |
| Conformance couples to the reference class | Checker input is `list[dict]`. Tests include hand-written fixtures the harness did not generate. |
| Replay is mistaken for deterministic models | Spec states that recorded model output is an input to replay. A test shows two scripted turns producing two different logs. |
| Telemetry forks OpenTelemetry | Attribute names reuse `gen_ai.*` where the community convention already has a name. No exporter is written. |
| Recovery policy is overfit to three tools | The policy is a function of `(idempotent, attempts, checkpoint_exists)`. Tools only supply those facts. |

## 11. Immediate build order

The repository is built in small commits so each commitment is reviewable on its own:

1. Name, license, and the boundary of v0.1
2. This plan
3. Architecture decisions: contract vs implementation, append-only log, recorded nondeterminism
4. Normative specs, one concern per document
5. JSON Schemas and examples
6. Schema loader and negative tests
7. Clock, ids, and the event log
8. Pure projection
9. Capability policy
10. Context compaction
11. Recovery decision
12. Telemetry attributes
13. Tools and the scripted model
14. Reference harness, one behavior per commit: success, denial, retry, rollback, escalation, pause/resume
15. Conformance checker, accepted fixtures, rejected fixtures
16. Example program and CI

Each code commit keeps `pytest` green.
