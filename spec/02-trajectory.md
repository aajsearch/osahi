# Trajectory

Version: 0.1.0

## Role

The trajectory is the immutable, ordered record of a run. Replay, audit, and conformance all read this log and nothing more private.

## Envelope

Every event MUST contain:

| Field | Type | Rule |
| --- | --- | --- |
| `event_id` | string | Unique within the trajectory. |
| `run_id` | string | MUST equal the run's `run_id`. Every event in one trajectory MUST share it. |
| `seq` | integer | Starts at 1. Each next event MUST use the previous `seq` plus 1. No gaps, no duplicates. |
| `type` | string | An event type. Unknown types are legal. |
| `at` | string | ISO-8601 UTC. Informational. |
| `payload` | object | JSON object. Shape depends on `type`. |
| `causation_id` | string or null | `event_id` of the causing event, or null. |
| `correlation_id` | string | MUST equal `run_id` in 0.1. |

The log assigns `seq`. An emitter MUST NOT let a caller choose a `seq` that breaks contiguity.

Ordering authority is `seq`. Consumers MUST NOT reorder events by `at`.

## Immutability

An implementation MUST NOT provide an operation that changes or removes an appended event. Recovery, correction, and compaction of *context* are expressed as later events.

## Unknown types

An implementation MUST retain events whose `type` it does not recognize, in order. It MUST NOT reject a trajectory solely because a type is unknown. Projection MUST ignore unknown types (see State).

## Taxonomy

The following types are defined in 0.1. Emitters MAY add types. They MUST NOT reuse a defined type for a different meaning.

Lifecycle: `run.started`, `run.paused`, `run.resumed`, `run.completed`, `run.failed`, `run.cancelled`.

Model: `model.invoked`, `model.completed`.

Tool and capability: `tool.requested`, `capability.decided`, `tool.invoked`, `tool.completed`, `tool.failed`, `tool.denied`.

State: `state.updated`, `context.compacted`.

Durability: `checkpoint.created`, `recovery.started`, `recovery.completed`.

Human: `human.requested`, `human.responded`.

## Required payload fields by type

`run.started` payload MUST include `spec_version`, `model`, `workload`, and `harness`, equal to the run object.

`run.failed` payload MUST include `reason` (string).

`run.completed` payload MUST include `text` (string). The text MAY be empty.

`model.invoked` payload MUST include `turn_index` (integer, zero-based among model calls).

`model.completed` payload MUST include `kind` (`tool`, `finish`, or `human`), `text` (string), and `telemetry` (see Telemetry). When `kind` is `tool`, payload MUST include `call_id`, `tool_name`, `capability_id`, and `arguments`.

`tool.requested` payload MUST include `call_id`, `tool_name`, `capability_id`, and `arguments`.

`capability.decided` payload MUST include `call_id`, `capability_id`, `effect` (`allow` or `deny`), `reason`, and `policy_id`.

`tool.invoked` payload MUST include `call_id`, `tool_name`, and `arguments`.

`tool.completed` payload MUST include `call_id`, `tool_name`, `output`, and `telemetry`.

`tool.failed` payload MUST include `call_id`, `tool_name`, `error`, `idempotent` (boolean), and `telemetry`.

`tool.denied` payload MUST include `call_id`, `tool_name`, `capability_id`, and `telemetry`.

`human.requested` payload MUST include `text`.

`human.responded` payload MUST include `text`.

Remaining payload shapes are defined in the state, checkpoint, and context documents.

## Causation

`run.started` MUST use `causation_id = null`. Every later event SHOULD set `causation_id` to the event that directly caused it. Conformance checks the MUST and does not fail a trajectory for a missing SHOULD.
