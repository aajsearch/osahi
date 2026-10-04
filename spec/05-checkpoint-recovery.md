# Checkpoint and recovery

Version: 0.1.0

## Role

A checkpoint is a restorable snapshot of projected contents. Recovery is the recorded choice of what to do after a failed tool call or an equivalent fault. Recovery never rewrites earlier events.

## Checkpoint payload

`checkpoint.created` payload MUST contain:

| Field | Rule |
| --- | --- |
| `checkpoint_id` | Unique within the run. |
| `state_version` | The projection's `state_version` at the time of the snapshot. |
| `snapshot.working_memory` | Object. Deep copy of projected memory. |
| `snapshot.scratchpad` | Array. Deep copy of the projected scratchpad. |

A checkpoint that omits either snapshot field is non-conformant.

The reference harness MUST write a checkpoint:

- immediately after `run.started`
- immediately before `tool.invoked`
- when pausing for a human

Other emitters MAY write checkpoints at additional points. They MUST use the same payload shape.

## Recovery pair

A recovery is two events:

1. `recovery.started` with `action`, `call_id`, and `reason`
2. `recovery.completed` with the same `action` and `call_id`

`action` MUST be one of `retry`, `rollback`, `escalate`.

`rollback` MUST name `checkpoint_id` of a checkpoint already present in the log. Naming an unknown checkpoint is non-conformant.

`escalate` MUST be followed by `run.failed`. No further lifecycle events are legal after that.

## Actions

### retry

Re-invoke the same tool call. The implementation MUST NOT call the model again for this attempt. The original `model.completed` event remains the authority for `tool_name` and `arguments`.

Retry is legal only when the failed tool reported `idempotent = true` on `tool.failed` and the number of completed retries for that `call_id` is still below the emitter's cap. The cap is emitter policy. The reference cap is 2.

A `retry` whose matching `tool.failed` has `idempotent = false` is non-conformant.

After `recovery.completed` with `retry`, the emitter appends a new `tool.invoked` for the same `call_id`. The earlier allow decision remains in force. A new `capability.decided` is not required for a retry of the same call. It is not forbidden.

### rollback

Copy snapshot contents back into the projection as defined in the state document, then continue the run with a later model turn. The model MAY observe the failure because the harness includes it in context. That observation, if it changes memory, MUST be a later `state.updated`.

### escalate

Stop. `run.failed` payload `reason` SHOULD reference the recovery reason.

## Decision inputs

A recovery policy SHOULD be a function of observable facts: whether the tool is idempotent, how many retries already completed for the `call_id`, and whether a checkpoint exists. The reference policy is:

1. If idempotent and retries completed < 2, choose `retry`.
2. Else if a checkpoint exists, choose `rollback`.
3. Else choose `escalate`.

This ordering is reference behavior. Another policy is conformant when the events it emits satisfy the rules above. Conformance checks legality of the events, not that every emitter uses the reference thresholds.

## What recovery does not do

Recovery MUST NOT delete events. Recovery MUST NOT call the model in order to reconstruct a past turn when that turn is already on the log.
