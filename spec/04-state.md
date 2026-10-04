# State

Version: 0.1.0

## Role

Execution state is a projection of the trajectory. Implementations MAY cache the projection. They MUST be able to rebuild it by folding the log from the start.

`project(events)` MUST be a pure function. It MUST NOT call a model, a tool, or a clock.

## Initial projection

| Field | Initial value |
| --- | --- |
| `status` | `created` |
| `state_version` | `0` |
| `working_memory` | `{}` |
| `scratchpad` | `[]` |
| `checkpoints` | `{}` |
| `terminal` | false |

## Fold rules

Apply events in `seq` order.

| Event | Effect |
| --- | --- |
| `run.started` | `status = running` |
| `run.paused` | `status = paused` |
| `run.resumed` | `status = running` |
| `run.completed` | `status = completed`, `terminal = true` |
| `run.failed` | `status = failed`, `terminal = true` |
| `run.cancelled` | `status = cancelled`, `terminal = true` |
| `state.updated` | Merge `payload.patch` into `working_memory`. If `payload.scratchpad` is present, replace `scratchpad`. Then `state_version = state_version + 1`. |
| `context.compacted` | Replace `scratchpad` with `payload.retained`. Then `state_version = state_version + 1`. |
| `checkpoint.created` | Store the snapshot under `payload.checkpoint_id`. |
| `recovery.completed` with `action = rollback` | Copy `working_memory` and `scratchpad` from the stored snapshot `payload.checkpoint_id`. Then `state_version = state_version + 1`. |
| any other known type | No change to status, memory, scratchpad, or version. |
| any unknown type | No change. The event remains in the log. |

## Merge

`payload.patch` MUST be a JSON object. Merge is shallow: each key in the patch replaces that key in `working_memory`. Keys absent from the patch are left in place. A patch value of `null` sets the key to null. It does not delete the key.

## Version monotonicity

`state_version` MUST NOT decrease, including across rollback. Rollback changes contents, not history. Consumers detect a restore by observing `recovery.completed` and a new version, not by watching the counter go backward.

## `state.updated` payload

| Field | Rule |
| --- | --- |
| `patch` | MUST be an object. |
| `scratchpad` | OPTIONAL. When present, MUST be an array of items. |
| `reason` | OPTIONAL string. |

## Agreement

After folding, `status` MUST be consistent with the lifecycle rules in the agent-run document. A second fold of the same events MUST produce a deeply equal projection.
