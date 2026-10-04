# Conformance

Version: 0.1.0

## Role

Conformance decides whether a trajectory implements this specification. The checker input is a JSON array of event envelopes. The checker MUST NOT require the reference harness, a particular language, or a live model.

## Result

`check_trajectory(events)` returns a list of violations. An empty list means the trajectory conforms. Each violation MUST include a stable `rule` id and a human-readable `message`.

Rule ids:

| Id | Condition that produces a violation |
| --- | --- |
| `seq.contiguous` | `seq` does not start at 1 or does not increase by 1. |
| `run.consistent` | An event's `run_id` differs from the first event, or `correlation_id` differs from `run_id`. |
| `lifecycle.initial` | The first event is not `run.started`. |
| `lifecycle.terminal` | A lifecycle event appears after a terminal lifecycle event. |
| `lifecycle.transition` | A lifecycle event is illegal from the status just before it. Pause from a non-running status, resume from a non-paused status, or a second `run.started`. |
| `envelope.fields` | An event is missing an envelope field, or `payload` is not an object. |
| `capability.allow_before_invoke` | `tool.invoked` has no prior `capability.decided` with `effect = allow` for its `call_id`. |
| `capability.deny_blocks_invoke` | `tool.invoked` appears after `deny` for the same `call_id`. |
| `capability.decision_shape` | `capability.decided` lacks `effect`, `call_id`, `reason`, or `policy_id`, or `effect` is not `allow` or `deny`. |
| `checkpoint.snapshot` | `checkpoint.created` lacks `snapshot.working_memory` or `snapshot.scratchpad`. |
| `recovery.checkpoint_exists` | `recovery.completed` with `action = rollback` names a `checkpoint_id` that no earlier checkpoint created. |
| `recovery.idempotent` | `recovery.completed` with `action = retry` refers to a `call_id` whose `tool.failed` event has `idempotent = false`. |
| `recovery.escalate` | `recovery.completed` with `action = escalate` is not followed by `run.failed`. |
| `telemetry.required` | A model or tool outcome event lacks a required attribute. |
| `payload.required` | A known event type lacks a required payload field from the trajectory document. |

## Fixtures

The repository ships fixtures under `conformance/fixtures/`.

- Fixtures whose names start with `accept-` MUST produce an empty violation list.
- Fixtures whose names start with `reject-` MUST produce at least one violation, and the expected rule id is recorded beside the fixture in `conformance/expected.json`.

The reference harness's own trajectories MUST also pass `check_trajectory`. That is necessary and not sufficient: the accept fixtures are hand-written so the checker is not graded only on logs it learned to emit.

## Semantic rules JSON Schema cannot express

JSON Schema validates one object. The following rules are semantic and live only in the checker:

- sequence contiguity across the array
- capability order across events
- lifecycle transitions
- rollback pointing at an earlier checkpoint
- retry paired with an idempotent failure

A trajectory MUST satisfy both schema validation of each event and `check_trajectory`.

## Versions

The checker defined here applies to `spec_version` `0.1.0`. A trajectory that declares another version MUST be rejected with `run.version` rather than partially checked. `run.started` payload `spec_version` is the declaration.
